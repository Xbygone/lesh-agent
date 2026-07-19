"""Lesh Agent — application entry point / controller."""

import os
import sys
import subprocess


def ensure_dependencies():
    """Dev-mode convenience: install missing packages once.
    NEVER runs in the frozen exe (sys.executable would relaunch the app!)."""
    if getattr(sys, "frozen", False):
        return
    required = {
        "customtkinter": "customtkinter", "openai": "openai", "ollama": "ollama",
        "requests": "requests", "cryptography": "cryptography",
        "duckduckgo_search": "duckduckgo-search", "bs4": "beautifulsoup4",
    }
    missing = []
    for module, pip_name in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pip_name)
    if missing:
        print(f"[SYSTEM] Installing missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing, "--disable-pip-version-check"]
            )
        except Exception as e:
            print(f"[ERROR] Package installation failed: {e}\n"
                  f"Please install manually: pip install {' '.join(missing)}")


ensure_dependencies()

import json
import time
import datetime
import threading
from tkinter import filedialog

from ui import AppUI
from app_config import load_config, update_config
from ollama_client import check_ollama_status
from agent_engine import AgentState
from git_manager import get_diff, commit_and_push
from tools import read_file
from updater import check_for_updates

MODEL_CATALOG = {
    "Local (Ollama)": [
        "qwen2.5-coder:7b", "qwen2.5-coder:1.5b", "deepseek-r1:7b",
        "llama3.2:3b", "phi4-mini",
    ],
    "GitHub Models": [
        "openai/gpt-4.1", "openai/gpt-4.1-mini", "openai/gpt-4o-mini",
        "openai/o4-mini", "deepseek/DeepSeek-R1", "deepseek/DeepSeek-V3-0324",
        "meta/Llama-3.3-70B-Instruct", "meta/Llama-4-Scout-17B-16E-Instruct",
        "mistral-ai/Codestral-2501", "microsoft/Phi-4",
    ],
    "Google AI Studio": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    "Groq Cloud": [
        "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
        "deepseek-r1-distill-llama-70b", "qwen/qwen3-32b",
        "moonshotai/kimi-k2-instruct",
    ],
    "NVIDIA Build": [
        "meta/llama-3.3-70b-instruct", "qwen/qwen2.5-coder-32b-instruct",
        "mistralai/codestral-2501", "deepseek-ai/deepseek-r1",
    ],
}

TOKEN_LABELS = {
    "GitHub Models": "GITHUB PAT TOKEN",
    "Google AI Studio": "GOOGLE API KEY",
    "Groq Cloud": "GROQ API KEY",
    "NVIDIA Build": "NVIDIA API KEY",
}

CROSS_PLATFORM = "Cross-Platform (NVIDIA/GitHub/Google)"


class MainApp:
    def __init__(self):
        self.ui = AppUI()
        self.workspace_path = None
        self.agent = None
        self.current_session_id = None

        self._buf = ""
        self._buf_time = 0.0
        self._token_dirty = False

        # ── wiring ──
        self.ui.btn_select_folder.configure(command=self.select_folder)
        self.ui.btn_send.configure(command=self.send_message)
        self.ui.btn_stop.configure(command=self.stop_agent)
        self.ui.btn_new_chat.configure(command=self.start_new_session)
        self.ui.btn_refresh_diff.configure(command=self.refresh_diff)
        self.ui.btn_git_push.configure(command=self.push_to_git)
        self.ui.btn_update.configure(command=self.run_updater)
        self.ui.switch_auto_approve.configure(command=self.on_auto_approve_toggle)

        self.ui.mode_selector.configure(command=self.on_mode_change)
        self.ui.combo_provider.configure(command=self.on_provider_change)
        self.ui.combo_model.configure(command=self.on_model_change)

        self.ui.entry_pat.bind("<FocusOut>", self.save_token)
        self.ui.entry_pat.bind("<KeyRelease>", self._mark_token_dirty)

        self.ui.chat_input.bind("<Return>", self._on_enter)
        self.ui.chat_input.bind("<Shift-Return>", lambda e: None)

        self.ui.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.ui.chat_list.bind("<<TreeviewSelect>>", self.on_chat_select)
        self.ui.bind("<<AuthSuccess>>", self._on_auth_success)

        threading.Thread(target=self._check_ollama, daemon=True).start()
        self.run_updater(auto=True)

    # ─────────────────────────────────────────────
    # STARTUP / AUTH
    # ─────────────────────────────────────────────
    def _on_auth_success(self, event=None):
        self.on_mode_change(self.ui.mode_selector.get())
        self._restore_workspace()

    def _restore_workspace(self):
        path = load_config().get("last_workspace")
        if path and os.path.isdir(path):
            self._activate_workspace(path)

    def run_updater(self, auto=False):
        # Auto-update only makes sense for the packaged exe. Running the
        # updater from source would overwrite the git working tree!
        if auto and not getattr(sys, "frozen", False):
            self.ui.btn_update.configure(text="Check for Updates")
            return

        self.ui.btn_update.configure(state="disabled", text="Checking...")

        def status_cb(msg):
            self.ui.after(0, lambda: self.ui.btn_update.configure(text=msg[:34]))
            self._log(f"[UPDATER] {msg}")

        def complete_cb(success):
            if success and getattr(sys, "frozen", False):
                self.ui.after(0, lambda: self.ui.btn_update.configure(text="Restarting..."))
                try:
                    subprocess.Popen("start update.bat", shell=True)
                    os._exit(0)
                except Exception:
                    pass
            else:
                self.ui.after(3000, lambda: self.ui.btn_update.configure(
                    state="normal", text="Check for Updates"))

        check_for_updates(status_cb, complete_cb)

    def _check_ollama(self):
        self._set_status("● Checking Ollama...", "#FDD663")
        if check_ollama_status():
            self._set_status("● Ready", "#81C995")
        else:
            self._set_status("● Ollama not found (local mode disabled)", "#F28B82")

    def _set_status(self, text, color):
        self.ui.after(0, lambda: self.ui.lbl_status.configure(text=text, text_color=color))

    # ─────────────────────────────────────────────
    # MODE / PROVIDER / MODEL
    # ─────────────────────────────────────────────
    def on_mode_change(self, mode):
        if mode == "Standard":
            self.ui.combo_provider.configure(values=list(MODEL_CATALOG.keys()), state="readonly")
            self.ui.combo_model.configure(state="normal")
            if self.ui.combo_provider.get() not in MODEL_CATALOG:
                self.ui.combo_provider.set("Local (Ollama)")
            self.on_provider_change(self.ui.combo_provider.get())
        elif mode == "Auto-Pilot":
            cloud = [p for p in MODEL_CATALOG if p != "Local (Ollama)"]
            self.ui.combo_provider.configure(values=cloud, state="readonly")
            if self.ui.combo_provider.get() not in cloud:
                self.ui.combo_provider.set("GitHub Models")
            self.ui.combo_model.configure(values=["Dynamic Routing (Easy→Local, Hard→Cloud)"])
            self.ui.combo_model.set("Dynamic Routing (Easy→Local, Hard→Cloud)")
            self.ui.combo_model.configure(state="disabled")
            self.on_provider_change(self.ui.combo_provider.get(), mode_override=mode)
        elif mode == "Software Office":
            self.ui.combo_provider.configure(values=[CROSS_PLATFORM])
            self.ui.combo_provider.set(CROSS_PLATFORM)
            self.ui.combo_provider.configure(state="disabled")
            self.ui.combo_model.configure(values=["5-Agent Consensus"])
            self.ui.combo_model.set("5-Agent Consensus")
            self.ui.combo_model.configure(state="disabled")
            self.on_provider_change(CROSS_PLATFORM, mode_override=mode)

        if self.agent:
            self.agent.run_mode = mode

    def on_provider_change(self, choice, mode_override=None):
        mode = mode_override or self.ui.mode_selector.get()

        # Load saved key in background (avoid network on the UI thread)
        def _load_key():
            from db_manager import db
            saved = db.get_api_key(choice) or ""

            def _apply():
                self.ui.entry_pat.delete(0, "end")
                if saved:
                    self.ui.entry_pat.insert(0, saved)
                self._token_dirty = False
            self.ui.after(0, _apply)

        threading.Thread(target=_load_key, daemon=True).start()

        if "Local" in choice:
            self.ui.lbl_token.grid_remove()
            self.ui.entry_pat.grid_remove()
        elif "Cross-Platform" in choice:
            self.ui.lbl_token.configure(text="ENTER API KEYS FROM STANDARD MODE")
            self.ui.lbl_token.grid()
            self.ui.entry_pat.grid_remove()
        else:
            self.ui.lbl_token.configure(text=TOKEN_LABELS.get(choice, "API KEY"))
            self.ui.lbl_token.grid()
            self.ui.entry_pat.grid()

        if mode == "Standard" and choice in MODEL_CATALOG:
            models = MODEL_CATALOG[choice]
            self.ui.combo_model.configure(values=models, state="normal")
            self.ui.combo_model.set(models[0])

        self.on_model_change(self.ui.combo_model.get())

    def on_model_change(self, choice):
        if self.agent:
            self.agent.model = choice
            self.agent.provider = self.ui.combo_provider.get()
            self._log(f"Model: {choice}")

    # ─────────────────────────────────────────────
    # TOKEN (debounced persistence)
    # ─────────────────────────────────────────────
    def _mark_token_dirty(self, event=None):
        self._token_dirty = True

    def save_token(self, event=None):
        if not self._token_dirty:
            return
        self._token_dirty = False
        provider = self.ui.combo_provider.get()
        token = self.ui.entry_pat.get().strip()
        if not token or provider not in MODEL_CATALOG or "Local" in provider:
            return

        def _save():
            from db_manager import db
            db.set_api_key(provider, token)
        threading.Thread(target=_save, daemon=True).start()

    # ─────────────────────────────────────────────
    # WORKSPACE
    # ─────────────────────────────────────────────
    def select_folder(self):
        path = filedialog.askdirectory(title="Select Workspace")
        if not path:
            return
        update_config(last_workspace=path)
        self._activate_workspace(path)

    def _activate_workspace(self, path):
        self.workspace_path = path
        self.ui.btn_select_folder.configure(text=f"📁 {os.path.basename(path)}")
        self._populate_tree(path)
        self._populate_chats()
        self.refresh_diff()
        self._make_agent()
        self._log(f"Workspace: {path}")
        self.start_new_session()

    def _make_agent(self):
        provider = self.ui.combo_provider.get()
        model = self.ui.combo_model.get()
        token = self.ui.entry_pat.get().strip()
        self.agent = AgentState(
            provider=provider,
            model=model,
            workspace_path=self.workspace_path,
            token=token,
            chat_callback=self._chat_cb,
            log_callback=self._log_cb,
            approval_callback=self._approval_bridge,
        )
        self.agent.run_mode = self.ui.mode_selector.get()
        self.agent.auto_approve = bool(self.ui.switch_auto_approve.get())

    def on_auto_approve_toggle(self):
        if self.agent:
            self.agent.auto_approve = bool(self.ui.switch_auto_approve.get())

    def _approval_bridge(self, title, detail) -> bool:
        """Called from the agent worker thread; shows a modal on the UI thread
        and blocks the worker until the user decides (5 min timeout = reject)."""
        decided = threading.Event()
        result = {"ok": False}

        def _open():
            self.ui.ask_approval(title, detail, lambda ok: (result.update(ok=ok), decided.set()))

        self.ui.after(0, _open)
        decided.wait(timeout=300)
        return result["ok"]

    # ─────────────────────────────────────────────
    # FILE TREE
    # ─────────────────────────────────────────────
    def _populate_tree(self, path):
        for item in self.ui.tree.get_children():
            self.ui.tree.delete(item)
        root = self.ui.tree.insert("", "end", text=os.path.basename(path), open=True)

        def _scan():
            def _scan_dir(current_path, depth=0):
                nodes = []
                if depth > 6:
                    return nodes
                try:
                    for name in sorted(os.listdir(current_path)):
                        if name in (".git", "venv", ".venv", "__pycache__", "node_modules",
                                    ".lesh", "dist", "build", ".idea", ".vscode", ".venv-build"):
                            continue
                        full = os.path.join(current_path, name)
                        if os.path.isdir(full):
                            nodes.append({"name": name, "is_dir": True,
                                          "children": _scan_dir(full, depth + 1)})
                        else:
                            nodes.append({"name": name, "is_dir": False})
                except (PermissionError, OSError):
                    pass
                return nodes

            tree_data = _scan_dir(path)

            def _insert_nodes(parent, nodes):
                for node in nodes:
                    icon = "📁 " if node["is_dir"] else "📄 "
                    n = self.ui.tree.insert(parent, "end", text=icon + node["name"], open=False)
                    if node["is_dir"]:
                        _insert_nodes(n, node.get("children", []))

            self.ui.after(0, lambda: _insert_nodes(root, tree_data))

        threading.Thread(target=_scan, daemon=True).start()

    def on_tree_select(self, event):
        if not self.agent or not self.workspace_path:
            return
        selected = self.ui.tree.selection()
        if not selected:
            return
        item = selected[0]
        path_parts = []
        current = item
        while current:
            text = self.ui.tree.item(current, "text").replace("📁 ", "").replace("📄 ", "")
            path_parts.insert(0, text)
            current = self.ui.tree.parent(current)

        rel_path = os.path.join(*path_parts[1:]) if len(path_parts) > 1 else ""
        if not rel_path:
            return
        full = os.path.join(self.workspace_path, rel_path)
        if os.path.isdir(full):
            return
        read_res = json.loads(read_file(rel_path, self.workspace_path))
        if read_res.get("success"):
            self.agent.set_active_file(rel_path, read_res["content"])
        else:
            self._log(f"Could not read file: {rel_path}")

    # ─────────────────────────────────────────────
    # SESSIONS
    # ─────────────────────────────────────────────
    def get_sessions_dir(self):
        d = os.path.join(self.workspace_path, ".lesh", "sessions") if self.workspace_path \
            else os.path.expanduser("~/.lesh/sessions")
        os.makedirs(d, exist_ok=True)
        return d

    def start_new_session(self):
        self.current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.agent:
            self.agent.messages = []
            self.agent.active_file_context = None
        self.ui.clear_chat()
        self.ui.lbl_chat_title.configure(text="New Chat")
        self.ui.append_chat("[SYSTEM] New chat started.\n", tag="system")

    def _populate_chats(self):
        for item in self.ui.chat_list.get_children():
            self.ui.chat_list.delete(item)

        sessions_dir = self.get_sessions_dir()
        root = self.ui.chat_list.insert("", "end", text="Chats", open=True)
        self.ui.chat_list.insert(root, "end", text="＋ New Chat", tags=("new",))

        try:
            files = sorted(os.listdir(sessions_dir), reverse=True)
            for f in files:
                if not f.endswith(".json"):
                    continue
                session_id = f[:-5]
                title = session_id
                try:
                    with open(os.path.join(sessions_dir, f), "r", encoding="utf-8") as jf:
                        hist = json.load(jf)
                    for msg in hist:
                        if msg.get("role") == "user" and msg.get("content"):
                            c = msg["content"]
                            title = (c[:28] + "…") if len(c) > 28 else c
                            break
                except (OSError, ValueError):
                    pass
                self.ui.chat_list.insert(root, "end", text=title, values=(session_id,))
        except OSError as e:
            self._log(f"Chat list error: {e}")

    def on_chat_select(self, event):
        selected = self.ui.chat_list.selection()
        if not selected:
            return
        item = selected[0]
        if "new" in self.ui.chat_list.item(item, "tags"):
            self.start_new_session()
            return
        values = self.ui.chat_list.item(item, "values")
        if not values:
            return
        self.current_session_id = values[0]
        self._load_session(values[0], self.ui.chat_list.item(item, "text"))

    def _load_session(self, session_id, title="Chat"):
        fpath = os.path.join(self.get_sessions_dir(), f"{session_id}.json")
        if not os.path.exists(fpath):
            return
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (OSError, ValueError) as e:
            self._log(f"Could not load session: {e}")
            return

        if not self.agent:
            self._make_agent()
        self.agent.messages = history
        self.ui.clear_chat()
        self.ui.lbl_chat_title.configure(text=title)
        for msg in history:
            r, c = msg.get("role"), msg.get("content", "")
            if r == "user":
                self.ui.append_chat("\n[You]\n", tag="user_chip")
                self.ui.append_chat(f"{c}\n", tag="user")
            elif r == "assistant" and c:
                self.ui.append_chat("\n[Agent]\n", tag="agent_chip")
                self.ui.append_chat(f"{c}\n")
            elif r == "tool":
                self.ui.append_chat(f"🛠 {msg.get('name', 'tool')} executed\n", tag="tool_ok")

    def _save_session(self):
        try:
            if self.current_session_id and self.agent:
                fpath = os.path.join(self.get_sessions_dir(), f"{self.current_session_id}.json")
                with open(fpath, "w", encoding="utf-8") as f:
                    json.dump(self.agent.messages, f, ensure_ascii=False, indent=2)
        except OSError as e:
            self._log(f"[WARNING] Could not save session: {e}")

    # ─────────────────────────────────────────────
    # SEND / STOP
    # ─────────────────────────────────────────────
    def _on_enter(self, event):
        self.send_message()
        return "break"

    def stop_agent(self):
        if self.agent:
            self.agent.cancel()
            self._log("[SYSTEM] Stop requested; will halt after the current step.")

    def send_message(self):
        if self.agent and self.agent.is_running:
            return
        if not self.workspace_path:
            self.ui.append_chat("Select a workspace folder first.\n", tag="error")
            return

        text = self.ui.chat_input.get("1.0", "end").strip()
        if not text:
            return

        provider = self.ui.combo_provider.get()
        token = self.ui.entry_pat.get().strip()
        needs_token = ("Local" not in provider) and ("Cross-Platform" not in provider)
        if needs_token and not token:
            self.ui.append_chat(f"{provider} requires an API key.\n", tag="error")
            return

        self.save_token()

        self.ui.chat_input.delete("1.0", "end")
        self.ui.append_chat("\n[You]\n", tag="user_chip")
        self.ui.append_chat(f"{text}\n\n", tag="user")
        self.ui.append_chat("[Agent]\n", tag="agent_chip")

        if not self.agent:
            self._make_agent()
        self.agent.provider = provider
        if self.ui.mode_selector.get() == "Standard":
            self.agent.model = self.ui.combo_model.get()
        self.agent.token = token
        self.agent.run_mode = self.ui.mode_selector.get()
        self.agent.auto_approve = bool(self.ui.switch_auto_approve.get())

        if not self.current_session_id:
            self.start_new_session()

        self.agent.add_user_message(text)
        self.ui.set_busy(True)

        def _run():
            try:
                self.agent.run()
            except Exception as e:
                import traceback
                self._log(f"[CRITICAL] Agent crashed: {e}")
                self._log(traceback.format_exc())
                self._chat_cb(f"\n[SYSTEM ERROR] {e}\n", tag="error")
            finally:
                self._flush()
                self._save_session()
                self.ui.after(0, self.refresh_diff)
                self.ui.after(0, lambda: self._populate_tree(self.workspace_path))
                self.ui.after(0, self._populate_chats)
                self.ui.after(0, lambda: self.ui.set_busy(False))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────
    # CALLBACKS (stream buffering)
    # ─────────────────────────────────────────────
    def _chat_cb(self, text, tag=None):
        if tag:
            self._flush()
            self.ui.after(0, lambda t=text, tg=tag: self.ui.append_chat(t, tag=tg))
        else:
            self._buf += text
            now = time.time()
            if now - self._buf_time > 0.05:
                self._flush()
                self._buf_time = now

    def _flush(self):
        if self._buf:
            text, self._buf = self._buf, ""
            self.ui.after(0, lambda t=text: self.ui.append_chat(t))

    def _log_cb(self, text):
        self.ui.after(0, lambda t=text: self.ui.append_log(t))

    def _log(self, text):
        self._log_cb(text)

    # ─────────────────────────────────────────────
    # GIT
    # ─────────────────────────────────────────────
    def refresh_diff(self):
        if not self.workspace_path:
            self.ui.set_diff("No workspace selected.")
            return

        def _bg():
            diff = get_diff(self.workspace_path) or "No changes detected."
            self.ui.after(0, lambda: self.ui.set_diff(diff))
        threading.Thread(target=_bg, daemon=True).start()

    def push_to_git(self):
        if not self.workspace_path:
            return
        msg = self.ui.commit_msg_input.get().strip() or "AI: Autonomous commit"

        self.ui.btn_git_push.configure(state="disabled", text="Pushing...")

        def _run():
            # Prefer the stored GitHub PAT; fall back to the visible field only
            # when the GitHub provider is selected.
            from db_manager import db
            token = db.get_api_key("GitHub Models") or ""
            if not token and "GitHub" in self.ui.combo_provider.get():
                token = self.ui.entry_pat.get().strip()

            success, log = commit_and_push(self.workspace_path, msg, pat_token=token or None)
            self.ui.after(0, lambda: self.ui.append_log(log))
            self.ui.after(0, self.refresh_diff)
            label = "✔ Pushed" if success else "✖ Error!"
            self.ui.after(0, lambda: self.ui.btn_git_push.configure(state="normal", text=label))
            self.ui.after(3500, lambda: self.ui.btn_git_push.configure(text="Commit & Push"))
            if success:
                self.ui.after(0, lambda: self.ui.commit_msg_input.delete(0, "end"))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────
    def run(self):
        self.ui.mainloop()


if __name__ == "__main__":
    try:
        app = MainApp()
        app.run()
    except Exception as e:
        import traceback
        try:
            with open("crash_log.txt", "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.datetime.now()}] CRASH:\n{traceback.format_exc()}")
        except OSError:
            pass
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
