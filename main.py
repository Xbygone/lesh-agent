import os
import threading
import time
from tkinter import filedialog

from ui import AppUI
from ollama_client import check_ollama_status, get_models, ensure_model_exists
from agent_loop import AgentState
from git_manager import get_diff, commit_and_push


class MainApp:
    def __init__(self):
        self.ui = AppUI()
        self.workspace_path = None
        self.agent = None

        # Stream buffer for smoother UI updates
        self._buf = ""
        self._buf_time = 0.0

        # Wire up buttons
        self.ui.btn_select_folder.configure(command=self.select_folder)
        self.ui.btn_send.configure(command=self.send_message)
        self.ui.btn_refresh_diff.configure(command=self.refresh_diff)
        self.ui.btn_git_push.configure(command=self.push_to_git)

        # Bind Enter key in chat input (Shift+Enter = newline)
        self.ui.chat_input.bind("<Return>", self._on_enter)
        self.ui.chat_input.bind("<Shift-Return>", lambda e: None)

        # Check Ollama on startup
        threading.Thread(target=self._check_ollama, daemon=True).start()

    # ─────────────────────────────────────────────
    # OLLAMA INIT
    # ─────────────────────────────────────────────
    def _check_ollama(self):
        self._set_status("● Ollama kontrol ediliyor...", "#EAB308")
        if not check_ollama_status():
            self._set_status("● Ollama bulunamadı — lütfen başlatın", "#EF4444")
            return

        self._set_status("● Modeller kontrol ediliyor...", "#EAB308")

        def progress(msg):
            self.ui.after(0, lambda: self._set_status(f"● {msg}", "#EAB308"))

        # Auto-pull if missing
        ensure_model_exists("qwen2.5-coder:7b", progress)

        models = get_models()
        if models:
            self.ui.after(0, lambda: self.ui.combo_model.configure(values=models))
            if "qwen2.5-coder:7b" in models:
                self.ui.after(0, lambda: self.ui.combo_model.set("qwen2.5-coder:7b"))
            elif models:
                self.ui.after(0, lambda: self.ui.combo_model.set(models[0]))

        self._set_status("● Ollama: Aktif", "#6DD58C")

    def _set_status(self, text, color):
        self.ui.after(0, lambda: self.ui.lbl_status.configure(text=text, text_color=color))

    # ─────────────────────────────────────────────
    # WORKSPACE
    # ─────────────────────────────────────────────
    def select_folder(self):
        path = filedialog.askdirectory(title="Çalışma Dizini Seçin")
        if not path:
            return
        self.workspace_path = path
        self.ui.btn_select_folder.configure(text=f"📁  {os.path.basename(path)}")
        self._populate_tree(path)
        self.refresh_diff()
        self._make_agent()
        self._log(f"Çalışma alanı: {path}")

    def _make_agent(self):
        self.agent = AgentState(
            model=self.ui.combo_model.get(),
            workspace_path=self.workspace_path,
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
                if name in (".git", "venv", "__pycache__", "node_modules", ".venv"):
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
        return "break"  # prevent newline in input

    def send_message(self):
        if not self.workspace_path:
            self.ui.append_chat("\n[HATA] Önce bir çalışma alanı seçin.\n", tag="system")
            return

        text = self.ui.chat_input.get("1.0", "end").strip()
        if not text:
            return

        self.ui.chat_input.delete("1.0", "end")
        self.ui.append_chat(f"\n━━━ Siz ━━━\n{text}\n\n", tag="user")

        # Update model in case user changed it
        if self.agent:
            self.agent.model = self.ui.combo_model.get()
        else:
            self._make_agent()

        self.agent.add_user_message(text)
        self.ui.btn_send.configure(state="disabled", text="⏳")

        def _run():
            self.agent.run()
            self._flush()
            self.ui.after(0, self.refresh_diff)
            self.ui.after(0, lambda: self._populate_tree(self.workspace_path))
            self.ui.after(0, lambda: self.ui.btn_send.configure(state="normal", text="Gönder"))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────
    # CALLBACKS
    # ─────────────────────────────────────────────
    def _chat_cb(self, text, tag=None):
        """Agent → chat window. Buffered for performance."""
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
        """Agent → terminal log panel."""
        self.ui.after(0, lambda t=text: self.ui.append_log(t))

    def _log(self, text):
        self.ui.after(0, lambda t=text: self.ui.append_log(t))

    # ─────────────────────────────────────────────
    # GIT
    # ─────────────────────────────────────────────
    def refresh_diff(self):
        if not self.workspace_path:
            return
        diff = get_diff(self.workspace_path) or "Değişiklik yok."
        self.ui.after(0, lambda: self.ui.set_diff(diff))

    def push_to_git(self):
        if not self.workspace_path:
            return
        msg = self.ui.commit_msg_input.get().strip() or "AI: Otonom değişiklikler"
        self.ui.btn_git_push.configure(state="disabled", text="Gönderiliyor...")
        self._log(f"$ git add . && git commit -m '{msg}' && git push")

        def _run():
            success, log = commit_and_push(self.workspace_path, msg)
            self.ui.after(0, lambda: self.ui.append_log(log))
            self.ui.after(0, self.refresh_diff)
            label = "✅  Commit & Push" if success else "❌  Hata"
            self.ui.after(0, lambda: self.ui.btn_git_push.configure(state="normal", text=label))
            self.ui.after(3500, lambda: self.ui.btn_git_push.configure(text="✅  Commit & Push"))
            if success:
                self.ui.after(0, lambda: self.ui.commit_msg_input.delete(0, "end"))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────
    def run(self):
        self.ui.mainloop()


if __name__ == "__main__":
    app = MainApp()
    app.run()
