import os
import sys
import subprocess

def install_requirements():
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        return
    
    print("[SİSTEM] Eksik paketler kontrol ediliyor...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--disable-pip-version-check"])
    except Exception as e:
        print(f"[HATA] Paketler yüklenemedi: {e}")

install_requirements()

import threading
import time
import json
import datetime
from tkinter import filedialog

from ui import AppUI
from i18n import t
from ollama_client import check_ollama_status, get_models, ensure_model_exists
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
        
        # Wire up Combobox
        self.ui.combo_provider.configure(command=self.on_provider_change)
        self.ui.combo_model.configure(command=self.on_model_change)
        
        self.ui.entry_pat.bind("<KeyRelease>", self.on_token_change)

        self.ui.chat_input.bind("<Return>", self._on_enter)
        self.ui.chat_input.bind("<Shift-Return>", lambda e: None)
        
        self.ui.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.ui.chat_list.bind("<<TreeviewSelect>>", self.on_chat_select)

        threading.Thread(target=self._check_ollama, daemon=True).start()
        
        self._load_initial_config()
        self.run_updater()

    def run_updater(self):
        self.ui.btn_update.configure(state="disabled", text=t("sys_checking_updates"))
        def status_cb(msg):
            self.ui.after(0, lambda: self.ui.btn_update.configure(text=msg))
            self._log(f"[GÜNCELLEYİCİ] {msg}")
            
        def complete_cb(success):
            if success:
                self.ui.after(0, lambda: self.ui.btn_update.configure(text=t("sys_restarting"), text_color="#6DD58C"))
                try:
                    subprocess.Popen("start update.bat", shell=True)
                    os._exit(0)
                except:
                    pass
            else:
                self.ui.after(3000, lambda: self.ui.btn_update.configure(state="normal", text=t("btn_update")))

        check_for_updates(status_cb, complete_cb)

    def _load_initial_config(self):
        config = load_config()
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
        
        self.on_provider_change(self.ui.combo_provider.get())

    # ─────────────────────────────────────────────
    # OLLAMA INIT & UI EVENTS
    # ─────────────────────────────────────────────
    def _check_ollama(self):
        self._set_status(t("ollama_checking"), "#EAB308")
        if not check_ollama_status():
            self._set_status(t("ollama_not_found"), "#EF4444")
            return

        self._set_status(t("models_checking"), "#EAB308")

        def progress(msg):
            self._set_status(t("ollama_not_found"), "#EF4444")
            return
        ensure_model_exists("qwen2.5-coder:7b", lambda msg: self._set_status(f"● {msg}", "#EAB308"))
        self._set_status(t("ollama_active"), "#6DD58C")

    def _set_status(self, text, color):
        self.ui.after(0, lambda: self.ui.lbl_status.configure(text=text, text_color=color))

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    def on_token_change(self, event):
        provider = self.ui.combo_provider.get()
        token = self.ui.entry_pat.get().strip()
        config = load_config()
        config[provider] = token
        save_config(config)

    def on_model_change(self, choice):
        if self.agent:
            model_str = choice.split(" ")[0]
            self.agent.model = model_str
            self.agent.provider = self.ui.combo_provider.get()
            self._log(f"Model: {model_str}")

    def on_provider_change(self, choice):
        config = load_config()
        saved_token = config.get(choice, "")
        
        self.ui.entry_pat.delete(0, "end")
        self.ui.entry_pat.insert(0, saved_token)

        if "Yerel" in choice:
            self.ui.lbl_token.grid_remove()
            self.ui.entry_pat.grid_remove()
            self.ui.combo_model.configure(values=["qwen2.5-coder:7b", "qwen3.5:4b", "deepseek-r1:8b"])
            self.ui.combo_model.set("qwen2.5-coder:7b")
        else:
            self.ui.lbl_token.grid()
            self.ui.entry_pat.grid()
            
            if "GitHub" in choice:
                self.ui.lbl_token.configure(text="GitHub PAT Token")
                gh_models = [
                    "deepseek-r1-0528 (Reasoning)", "llama-4-scout-17b-16e (Reasoning)", "o4-mini (Reasoning)",
                    "codestral-25.01 (Coding)", "gpt-4.1-mini (Coding)", "gpt-4.1 (Coding)",
                    "phi-4-mini-instruct (Routine)"
                ]
                self.ui.combo_model.configure(values=gh_models)
                self.ui.combo_model.set("gpt-4.1-mini (Coding)")
            elif "Google" in choice:
                self.ui.lbl_token.configure(text="Google API Key")
                gg_models = ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash']
                self.ui.combo_model.configure(values=gg_models)
                self.ui.combo_model.set("gemini-2.0-flash")
            elif "Groq" in choice:
                self.ui.lbl_token.configure(text="Groq API Key")
                groq_models = ['deepseek-r1-distill-llama-70b', 'llama-3.3-70b-versatile', 'qwen-2.5-coder-32b']
                self.ui.combo_model.configure(values=groq_models)
                self.ui.combo_model.set("deepseek-r1-distill-llama-70b")
        
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
            return None
        d = os.path.join(self.workspace_path, ".lesh", "sessions")
        os.makedirs(d, exist_ok=True)
        return d

    def start_new_session(self):
        self.current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.agent:
            self.agent.messages = []
        self.ui.clear_chat()
        self.ui.append_chat(f"\n[SYSTEM] {t('new_chat')} started.\n\n", tag="system")

    def _populate_chats(self):
        for item in self.ui.chat_list.get_children():
            self.ui.chat_list.delete(item)
            
        sessions_dir = self.get_sessions_dir()
        if not sessions_dir:
            return
            
        root = self.ui.chat_list.insert("", "end", text="Chats", open=True)
        self.ui.chat_list.insert(root, "end", text=t("new_chat"), tags=("new",))
        
        try:
            files = sorted(os.listdir(sessions_dir), reverse=True)
            for f in files:
                if f.endswith(".json"):
                    session_id = f.replace(".json", "")
                    # Try to get the first prompt to show as title
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
                        self.ui.append_chat(t("sys_history_loaded"), tag="system")
                        for msg in history:
                            r = msg.get("role")
                            c = msg.get("content", "")
                            if r == "user":
                                self.ui.append_chat(f"\n{t('sys_you')}\n{c}\n\n", tag="user")
                            elif r == "assistant" and c:
                                self.ui.append_chat(f"\n[Ajan]\n{c}\n\n", tag="agent")
                            elif r == "tool" and c:
                                self.ui.append_chat(f"\n[Araç: {msg.get('name')}] Başarılı.\n", tag="tool_ok")
            except Exception as e:
                self._log(f"Error loading session: {e}")

    # ─────────────────────────────────────────────
    # WORKSPACE
    # ─────────────────────────────────────────────
    def select_folder(self):
        path = filedialog.askdirectory(title="Çalışma Dizini Seçin")
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
        self._log(f"Çalışma alanı: {path}")
        self.start_new_session()

    def _make_agent(self):
        model_str = self.ui.combo_model.get()
        actual_model = model_str.split(" ")[0]
        
        self.agent = AgentState(
            provider=self.ui.combo_provider.get(),
            model=actual_model,
            workspace_path=self.workspace_path,
            token=self.ui.entry_pat.get().strip(),
            chat_callback=self._chat_cb,
            log_callback=self._log_cb
        )

    # ─────────────────────────────────────────────
    # FILE TREE
    # ─────────────────────────────────────────────
    def _populate_tree(self, path):
        for item in self.ui.tree.get_children():
            self.ui.tree.delete(item)
        root = self.ui.tree.insert("", "end", text=os.path.basename(path), open=True)
        self._fill_tree(root, path)

    def _fill_tree(self, parent, path):
        try:
            entries = sorted(os.listdir(path))
            for name in entries:
                if name in (".git", "venv", "__pycache__", "node_modules", ".venv", ".lesh"):
                    continue
                full = os.path.join(path, name)
                node = self.ui.tree.insert(parent, "end", text=name, open=False)
                if os.path.isdir(full):
                    self._fill_tree(node, full)
        except PermissionError:
            pass

    # ─────────────────────────────────────────────
    # SEND MESSAGE
    # ─────────────────────────────────────────────
    def _on_enter(self, event):
        self.send_message()
        return "break"

    def send_message(self):
        if not self.workspace_path:
            self.ui.append_chat(t("err_no_workspace"), tag="system")
            return

        text = self.ui.chat_input.get("1.0", "end").strip()
        if not text:
            return

        provider = self.ui.combo_provider.get()
        token = self.ui.entry_pat.get().strip()
        if "Yerel" not in provider and not token:
            self.ui.append_chat(t("err_no_token", provider=provider), tag="system")
            return
            
        self.on_token_change(None)

        self.ui.chat_input.delete("1.0", "end")
        self.ui.append_chat(f"\n{t('sys_you')}\n{text}\n\n", tag="user")

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
            self.agent.run()
            self._flush()
            
            try:
                s_dir = self.get_sessions_dir()
                if s_dir and self.current_session_id:
                    with open(os.path.join(s_dir, f"{self.current_session_id}.json"), "w", encoding="utf-8") as f:
                        json.dump(self.agent.messages, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._log(f"[UYARI] Session save err: {e}")
                
            self.ui.after(0, self.refresh_diff)
            self.ui.after(0, lambda: self._populate_tree(self.workspace_path))
            self.ui.after(0, self._populate_chats)
            self.ui.after(0, lambda: self.ui.btn_send.configure(state="normal", text=t("chat_send")))

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
            return
        diff = get_diff(self.workspace_path) or t("no_changes")
        self.ui.after(0, lambda: self.ui.set_diff(diff))

    def push_to_git(self):
        if not self.workspace_path:
            return
        msg = self.ui.commit_msg_input.get().strip() or "AI: Otonom değişiklikler"
        token = self.ui.entry_pat.get().strip()
        
        self.ui.btn_git_push.configure(state="disabled", text=t("pushing"))
        self._log(f"$ git add . && git commit -m '{msg}' && git push")

        def _run():
            success, log = commit_and_push(self.workspace_path, msg, pat_token=token)
            self.ui.after(0, lambda: self.ui.append_log(log))
            self.ui.after(0, self.refresh_diff)
            label = t("btn_push") if success else t("status_err")
            self.ui.after(0, lambda: self.ui.btn_git_push.configure(state="normal", text=label))
            self.ui.after(3500, lambda: self.ui.btn_git_push.configure(text=t("btn_push")))
            if success:
                self.ui.after(0, lambda: self.ui.commit_msg_input.delete(0, "end"))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────
    def run(self):
        self.ui.mainloop()


if __name__ == "__main__":
    app = MainApp()
    app.run()
