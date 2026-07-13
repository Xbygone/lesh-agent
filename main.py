import os
import sys
import subprocess

def install_requirements():
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        return
    
    print("[SYSTEM] Checking required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--disable-pip-version-check"])
    except Exception as e:
        print(f"[ERROR] Failed to install packages: {e}")

install_requirements()

import threading
import time
import json
import datetime
from tkinter import filedialog

from ui import AppUI
from ollama_client import check_ollama_status, ensure_model_exists
from agent_engine import AgentState
from git_manager import get_diff, commit_and_push
from tools import read_file
from updater import check_for_updates

CONFIG_FILE = os.path.expanduser("~/.yerel_agent_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except:
        pass

class MainApp:
    def __init__(self):
        self.ui = AppUI()
        self.workspace_path = None
        self.agent = None
        self.current_session_id = None

        self._buf = ""
        self._buf_time = 0.0

        # Wire up buttons
        self.ui.btn_select_folder.configure(command=self.select_folder)
        self.ui.btn_send.configure(command=self.send_message)
        self.ui.btn_refresh_diff.configure(command=self.refresh_diff)
        self.ui.btn_git_push.configure(command=self.push_to_git)
        self.ui.btn_update.configure(command=self.run_updater)
        
        # Wire up Combobox and Mode Selector
        self.ui.mode_selector.configure(command=self.on_mode_change)
        self.ui.combo_provider.configure(command=self.on_provider_change)
        self.ui.combo_model.configure(command=self.on_model_change)
        
        self.ui.entry_pat.bind("<KeyRelease>", self.on_token_change)

        self.ui.chat_input.bind("<Return>", self._on_enter)
        self.ui.chat_input.bind("<Shift-Return>", lambda e: None)
        
        self.ui.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.ui.chat_list.bind("<<TreeviewSelect>>", self.on_chat_select)
        self.ui.bind("<<AuthSuccess>>", self._on_auth_success)
        threading.Thread(target=self._check_ollama, daemon=True).start()
        
        self.run_updater()

    def _on_auth_success(self, event=None):
        self.on_mode_change(self.ui.mode_selector.get())

    def run_updater(self):
        self.ui.btn_update.configure(state="disabled", text="Checking updates...")
        def status_cb(msg):
            self.ui.after(0, lambda: self.ui.btn_update.configure(text=msg))
            self._log(f"[UPDATER] {msg}")
            
        def complete_cb(success):
            if success:
                self.ui.after(0, lambda: self.ui.btn_update.configure(text="Restarting...", text_color="#81C995"))
                try:
                    subprocess.Popen("start update.bat", shell=True)
                    os._exit(0)
                except:
                    pass
            else:
                self.ui.after(3000, lambda: self.ui.btn_update.configure(state="normal", text="Check for Updates"))

        check_for_updates(status_cb, complete_cb)

    def _load_initial_config(self):
        config = {} # Config fetching was removed because it's now in Supabase
        self.workspace_path = config.get("last_workspace", None)
        if self.workspace_path and os.path.exists(self.workspace_path):
            self.ui.workspace_path_text = os.path.basename(self.workspace_path)
            self.ui.btn_select_folder.configure(text=f"📁 {self.ui.workspace_path_text}")
            self._populate_tree(self.workspace_path)
            self._populate_chats()
            self.refresh_diff()
            self._make_agent()
            
            # Create a new session automatically
            self.start_new_session()
        
        self.on_mode_change(self.ui.mode_selector.get())

    def on_mode_change(self, mode):
        # Depending on mode, we might lock or hide provider/model combos
        if mode == "Standart":
            self.ui.combo_provider.configure(values=["Yerel (Ollama)", "GitHub Models", "NVIDIA Build", "Google AI Studio", "Groq Cloud"])
            self.ui.combo_provider.configure(state="normal")
            self.ui.combo_model.configure(state="normal")
            self.on_provider_change(self.ui.combo_provider.get())
        elif mode == "Oto-Pilot":
            self.ui.combo_provider.configure(state="normal")
            self.ui.combo_provider.configure(values=["GitHub Models", "NVIDIA Build", "Google AI Studio", "Groq Cloud"])
            self.ui.combo_provider.set("GitHub Models")
            self.ui.combo_model.configure(values=["Dinamik Yönlendirme (Zor -> Bulut)"])
            self.ui.combo_model.set("Dinamik Yönlendirme (Zor -> Bulut)")
            self.ui.combo_model.configure(state="disabled")
            self.on_provider_change("GitHub Models", mode_override=mode)
        elif mode == "Yazılım Ofisi":
            self.ui.combo_provider.configure(state="normal")
            self.ui.combo_provider.configure(values=["Çapraz Platform (NVIDIA/GitHub/Google)"])
            self.ui.combo_provider.set("Çapraz Platform (NVIDIA/GitHub/Google)")
            self.ui.combo_provider.configure(state="disabled")
            self.ui.combo_model.configure(values=["5-Agent Consensus"])
            self.ui.combo_model.set("5-Agent Consensus")
            self.ui.combo_model.configure(state="disabled")
            self.on_provider_change("Çapraz Platform (NVIDIA/GitHub/Google)", mode_override=mode)
            
        if self.agent:
            self.agent.run_mode = mode

    # ─────────────────────────────────────────────
    # OLLAMA INIT & UI EVENTS
    # ─────────────────────────────────────────────
    def _check_ollama(self):
        self._set_status("Checking Ollama...", "#FDE293")
        if not check_ollama_status():
            self._set_status("Ollama Not Found", "#F28B82")
            return

        self._set_status("Checking Models...", "#FDE293")

        def progress(msg):
            self._set_status(f"● {msg}", "#FDE293")
            
        ensure_model_exists("qwen2.5-coder:7b", progress)
        self._set_status("⚡ Ready", "#81C995")

    def _set_status(self, text, color):
        self.ui.after(0, lambda: self.ui.lbl_status.configure(text=text, text_color=color))

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    def on_token_change(self, event):
        provider = self.ui.combo_provider.get()
        token = self.ui.entry_pat.get().strip()
        from db_manager import db
        db.set_api_key(provider, token)

    def on_model_change(self, choice):
        if self.agent:
            model_str = choice.split(" ")[0]
            self.agent.model = model_str
            self.agent.provider = self.ui.combo_provider.get()
            self._log(f"Model: {model_str}")

    def on_provider_change(self, choice, mode_override=None):
        # Fetch key from Supabase DB
        from db_manager import db
        saved_token = db.get_api_key(choice) or ""
        
        self.ui.entry_pat.delete(0, "end")
        self.ui.entry_pat.insert(0, saved_token)

        mode = mode_override or self.ui.mode_selector.get()

        if "Yerel" in choice:
            self.ui.lbl_token.grid_remove()
            self.ui.entry_pat.grid_remove()
            if mode == "Standart":
                self.ui.combo_model.configure(values=['qwen2.5-coder:7b', 'qwen3.5:4b', 'phi-4-mini-instruct'])
                self.ui.combo_model.set("qwen2.5-coder:7b")
        elif "Çapraz Platform" in choice:
            self.ui.lbl_token.configure(text="Standart moddan API Anahtarlarını girin")
            self.ui.lbl_token.grid()
            self.ui.entry_pat.grid_remove()
        else:
            self.ui.lbl_token.grid()
            self.ui.entry_pat.grid()
            
            if "GitHub" in choice:
                self.ui.lbl_token.configure(text="GitHub PAT Token")
                gh_models = [
                    'gpt-5', 'gpt-5-chat (preview)', 'gpt-5-mini', 'gpt-5-nano', 
                    'o4-mini', 'o3-mini', 'o1', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4o-mini',
                    'llama-4-scout-17b-16e', 'llama-4-maverick-17b-128e', 'llama-3.1-405b',
                    'deepseek-r1-0528', 'deepseek-r1', 'deepseek-v3-0324',
                    'codestral-25.01', 'mistral-medium-3 (25.05)', 'cohere-command-a', 'phi-4-reasoning'
                ]
                if mode == "Standart":
                    self.ui.combo_model.configure(values=gh_models)
                    self.ui.combo_model.set("gpt-4.1-mini")
            elif "Google" in choice:
                self.ui.lbl_token.configure(text="Google API Key")
                gg_models = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
                if mode == "Standart":
                    self.ui.combo_model.configure(values=gg_models)
                    self.ui.combo_model.set("gemini-2.0-flash")
            elif "Groq" in choice:
                self.ui.lbl_token.configure(text="Groq API Key")
                groq_models = ['qwen-2.5-coder-32b', 'llama-3.3-70b', 'mistral-small-3.1']
                if mode == "Standart":
                    self.ui.combo_model.configure(values=groq_models)
                    self.ui.combo_model.set("llama-3.3-70b")
            elif "NVIDIA" in choice:
                self.ui.lbl_token.configure(text="NVIDIA API Key")
                nvidia_models = ['meta/llama-3.3-70b-instruct', 'mistralai/codestral-2501', 'nvidia/llama-3.1-nemotron-51b-instruct']
                if mode == "Standart":
                    self.ui.combo_model.configure(values=nvidia_models)
                    self.ui.combo_model.set("meta/llama-3.3-70b-instruct")
        
        self.on_model_change(self.ui.combo_model.get())

    def on_tree_select(self, event):
        if not self.agent or not self.workspace_path:
            return
            
        selected_item = self.ui.tree.selection()
        if not selected_item:
            return
            
        item = selected_item[0]
        path_parts = []
        current = item
        while current:
            text = self.ui.tree.item(current, "text")
            path_parts.insert(0, text)
            current = self.ui.tree.parent(current)
            
        if len(path_parts) > 1:
            rel_path = os.path.join(*path_parts[1:])
        else:
            rel_path = ""
            
        if rel_path:
            read_res = json.loads(read_file(rel_path, self.workspace_path))
            if read_res.get("success"):
                content = read_res["content"]
                self.agent.set_active_file(rel_path, content)
            else:
                self._log(f"File read error: {rel_path}")

    # ─────────────────────────────────────────────
    # SESSIONS (CHATS)
    # ─────────────────────────────────────────────
    def get_sessions_dir(self):
        if not self.workspace_path:
            d = os.path.expanduser("~/.lesh/sessions")
        else:
            d = os.path.join(self.workspace_path, ".lesh", "sessions")
        os.makedirs(d, exist_ok=True)
        return d

    def start_new_session(self):
        self.current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.agent:
            self.agent.messages = []
        self.ui.clear_chat()
        self.ui.append_chat(f"\n[SYSTEM] New chat started.\n\n", tag="system")

    def _populate_chats(self):
        for item in self.ui.chat_list.get_children():
            self.ui.chat_list.delete(item)
            
        sessions_dir = self.get_sessions_dir()
        if not sessions_dir:
            return
            
        root = self.ui.chat_list.insert("", "end", text="Chats", open=True)
        self.ui.chat_list.insert(root, "end", text="New Chat", tags=("new",))
        
        try:
            files = sorted(os.listdir(sessions_dir), reverse=True)
            for f in files:
                if f.endswith(".json"):
                    session_id = f.replace(".json", "")
                    title = session_id
                    try:
                        with open(os.path.join(sessions_dir, f), "r", encoding="utf-8") as jf:
                            hist = json.load(jf)
                            for msg in hist:
                                if msg.get("role") == "user":
                                    content = msg.get("content", "")
                                    if content:
                                        title = (content[:25] + "...") if len(content) > 25 else content
                                        break
                    except:
                        pass
                    node = self.ui.chat_list.insert(root, "end", text=title, values=(session_id,))
        except Exception as e:
            print("Populate chats error:", e)

    def on_chat_select(self, event):
        selected_item = self.ui.chat_list.selection()
        if not selected_item:
            return
        
        item = selected_item[0]
        tags = self.ui.chat_list.item(item, "tags")
        if "new" in tags:
            self.start_new_session()
            return
            
        values = self.ui.chat_list.item(item, "values")
        if not values:
            return
            
        session_id = values[0]
        self.current_session_id = session_id
        self._load_session(session_id)

    def _load_session(self, session_id):
        sessions_dir = self.get_sessions_dir()
        if not sessions_dir:
            return
        fpath = os.path.join(sessions_dir, f"{session_id}.json")
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    if self.agent:
                        self.agent.messages = history
                        self.ui.clear_chat()
                        self.ui.append_chat("History loaded.", tag="system")
                        for msg in history:
                            r = msg.get("role")
                            c = msg.get("content", "")
                            if r == "user":
                                self.ui.append_chat(f"\n[You]\n{c}\n\n", tag="user")
                            elif r == "assistant" and c:
                                self.ui.append_chat(f"\n[Agent]\n{c}\n\n", tag="agent")
                            elif r == "tool" and c:
                                self.ui.append_chat(f"\n[Tool: {msg.get('name')}] Success.\n", tag="tool_ok")
            except Exception as e:
                self._log(f"Error loading session: {e}")

    # ─────────────────────────────────────────────
    # WORKSPACE
    # ─────────────────────────────────────────────
    def select_folder(self):
        path = filedialog.askdirectory(title="Select Workspace")
        if not path:
            return
        self.workspace_path = path
        
        config = load_config()
        config["last_workspace"] = path
        save_config(config)
        
        self.ui.workspace_path_text = os.path.basename(path)
        self.ui.btn_select_folder.configure(text=f"📁 {self.ui.workspace_path_text}")
        self._populate_tree(path)
        self._populate_chats()
        self.refresh_diff()
        self._make_agent()
        self._log(f"Workspace: {path}")
        self.start_new_session()

    def _make_agent(self):
        provider = self.ui.combo_provider.get()
        model_str = self.ui.combo_model.get().split(" ")[0]
        token = self.ui.entry_pat.get().strip()
        self.agent = AgentState(
            provider=provider,
            model=model_str,
            workspace_path=self.workspace_path,
            token=token,
            chat_callback=self._chat_cb,
            log_callback=self._log_cb
        )
        self.agent.run_mode = self.ui.mode_selector.get()

    # ─────────────────────────────────────────────
    # FILE TREE
    # ─────────────────────────────────────────────
    def _populate_tree(self, path):
        for item in self.ui.tree.get_children():
            self.ui.tree.delete(item)
        root = self.ui.tree.insert("", "end", text=os.path.basename(path), open=True)

        def _scan():
            def _scan_dir(current_path):
                nodes = []
                try:
                    entries = sorted(os.listdir(current_path))
                    for name in entries:
                        if name in (".git", "venv", "__pycache__", "node_modules", ".venv", ".lesh"):
                            continue
                        full = os.path.join(current_path, name)
                        if os.path.isdir(full):
                            nodes.append({"name": name, "is_dir": True, "children": _scan_dir(full)})
                        else:
                            nodes.append({"name": name, "is_dir": False})
                except PermissionError:
                    pass
                return nodes
            
            tree_data = _scan_dir(path)
            
            def _insert_nodes(parent, nodes):
                for node in nodes:
                    n = self.ui.tree.insert(parent, "end", text=node["name"], open=False)
                    if node["is_dir"]:
                        _insert_nodes(n, node.get("children", []))

            self.ui.after(0, lambda: _insert_nodes(root, tree_data))

        threading.Thread(target=_scan, daemon=True).start()

    # ─────────────────────────────────────────────
    # SEND MESSAGE
    # ─────────────────────────────────────────────
    def _on_enter(self, event):
        self.send_message()
        return "break"

    def send_message(self):
        if not self.workspace_path:
            self.ui.append_chat("Error: Select a workspace first.", tag="system")
            return

        text = self.ui.chat_input.get("1.0", "end").strip()
        if not text:
            return

        provider = self.ui.combo_provider.get()
        token = self.ui.entry_pat.get().strip()
        if "Yerel" not in provider and not token:
            self.ui.append_chat(f"Error: {provider} requires an API Key/Token.", tag="system")
            return
            
        self.on_token_change(None)

        self.ui.chat_input.delete("1.0", "end")
        self.ui.append_chat(f"\n[You]\n{text}\n\n", tag="user")

        model_str = self.ui.combo_model.get().split(" ")[0]
        if self.agent:
            self.agent.provider = provider
            self.agent.model = model_str
            self.agent.token = token
        else:
            self._make_agent()

        if not self.current_session_id:
            self.start_new_session()

        self.agent.add_user_message(text)
        self.ui.btn_send.configure(state="disabled", text="⏳")

        def _run():
            try:
                self.agent.run()
            except Exception as e:
                self._log(f"[FATAL ERROR] AgentState.run crashed: {e}")
                import traceback
                self._log(traceback.format_exc())
                self.ui.append_chat(f"\n[SİSTEM HATASI] Ajan çöktü: {e}\n", tag="system")
            finally:
                self._flush()
            
            try:
                s_dir = self.get_sessions_dir()
                if s_dir and self.current_session_id:
                    with open(os.path.join(s_dir, f"{self.current_session_id}.json"), "w", encoding="utf-8") as f:
                        json.dump(self.agent.messages, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._log(f"[WARNING] Session save err: {e}")
                
            self.ui.after(0, self.refresh_diff)
            self.ui.after(0, lambda: self._populate_tree(self.workspace_path))
            self.ui.after(0, self._populate_chats)
            self.ui.after(0, lambda: self.ui.btn_send.configure(state="normal", text="Send 🚀"))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────
    # CALLBACKS
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
            text = self._buf
            self._buf = ""
            self.ui.after(0, lambda t=text: self.ui.append_chat(t))

    def _log_cb(self, text):
        self.ui.after(0, lambda t=text: self.ui.append_log(t))

    def _log(self, text):
        self.ui.after(0, lambda t=text: self.ui.append_log(t))

    # ─────────────────────────────────────────────
    # GIT
    # ─────────────────────────────────────────────
    def refresh_diff(self):
        if not self.workspace_path:
            self.ui.diff_text = "No workspace selected."
            if hasattr(self.ui, 'diff_textbox'):
                self.ui.diff_textbox.configure(state="normal")
                self.ui.diff_textbox.delete("1.0", "end")
                self.ui.diff_textbox.insert("1.0", self.ui.diff_text)
                self.ui.diff_textbox.configure(state="disabled")
            return
        
        def _get_diff_bg():
            diff = get_diff(self.workspace_path) or "No changes detected."
            self.ui.after(0, lambda: self.ui.set_diff(diff))
            
        threading.Thread(target=_get_diff_bg, daemon=True).start()

    def push_to_git(self):
        if not self.workspace_path:
            return
        msg = self.ui.commit_msg_input.get().strip() or "AI: Autonomous commit"
        token = self.ui.entry_pat.get().strip()
        
        self.ui.btn_git_push.configure(state="disabled", text="Pushing...")
        self._log(f"$ git add . && git commit -m '{msg}' && git push")

        def _run():
            success, log = commit_and_push(self.workspace_path, msg, pat_token=token)
            self.ui.after(0, lambda: self.ui.append_log(log))
            self.ui.after(0, self.refresh_diff)
            label = "Commit & Push" if success else "Error!"
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
        with open("crash_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now()}] CRASH:\n")
            f.write(traceback.format_exc())
        print(f"FATAL ERROR: {e}")
