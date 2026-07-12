import os
import threading
import time
import customtkinter as ctk
from tkinter import filedialog
import subprocess

from ui import AppUI
from ollama_client import check_ollama_status, get_models, ensure_model_exists
from agent_loop import AgentState
from git_manager import get_diff, commit_and_push, is_git_repo

class MainApp:
    def __init__(self):
        self.ui = AppUI()
        self.workspace_path = None
        self.agent = None
        
        # Buffer variables for UI performance optimization
        self._stream_buffer = ""
        self._last_update_time = 0
        
        # Bindings
        self.ui.btn_select_folder.configure(command=self.select_folder)
        self.ui.btn_send.configure(command=self.send_message)
        self.ui.btn_refresh_diff.configure(command=self.refresh_diff)
        self.ui.btn_git_push.configure(command=self.push_to_git)
        
        self.check_ollama()
        
    def check_ollama(self):
        def task():
            is_running = check_ollama_status()
            if is_running:
                self.ui.lbl_ollama_status.configure(text="● Ollama: Modeller Kontrol Ediliyor...", text_color="#EAB308")
                
                # Auto-pull default models if missing
                def update_progress(msg):
                    self.ui.after(0, lambda: self.ui.lbl_ollama_status.configure(text=msg))
                
                ensure_model_exists("qwen:3.5b", update_progress)
                ensure_model_exists("qwen2.5-coder:7b", update_progress)
                
                models = get_models()
                if models:
                    self.ui.combo_router.configure(values=models)
                    self.ui.combo_coder.configure(values=models)
                    if "qwen:3.5b" in models:
                        self.ui.combo_router.set("qwen:3.5b")
                    if "qwen2.5-coder:7b" in models:
                        self.ui.combo_coder.set("qwen2.5-coder:7b")
                        
                self.ui.lbl_ollama_status.configure(text="● Ollama: Aktif", text_color="#6DD58C")
            else:
                self.ui.lbl_ollama_status.configure(text="● Ollama: Kapalı/Bulunamadı", text_color="#EF4444")
        threading.Thread(target=task, daemon=True).start()

    def select_folder(self):
        path = filedialog.askdirectory(title="Çalışma Dizini Seçin")
        if path:
            self.workspace_path = path
            self.ui.btn_select_folder.configure(text=f"📁 {os.path.basename(path)}")
            self.populate_tree(path)
            self.refresh_diff()
            
            self.agent = AgentState(
                router_model=self.ui.combo_router.get(),
                coder_model=self.ui.combo_coder.get(),
                workspace_path=self.workspace_path,
                ui_callback=self.agent_callback
            )

    def populate_tree(self, path):
        for item in self.ui.tree.get_children():
            self.ui.tree.delete(item)
            
        root_node = self.ui.tree.insert('', 'end', text=os.path.basename(path), open=True)
        self._add_tree_nodes(root_node, path)

    def _add_tree_nodes(self, parent, path):
        try:
            for p in os.listdir(path):
                if p in ['.git', 'venv', '__pycache__', 'node_modules']:
                    continue
                abspath = os.path.join(path, p)
                isdir = os.path.isdir(abspath)
                oid = self.ui.tree.insert(parent, 'end', text=p, open=False)
                if isdir:
                    self._add_tree_nodes(oid, abspath)
        except PermissionError:
            pass

    def send_message(self):
        if not self.workspace_path:
            self.ui.append_chat("\n[HATA] Lütfen önce bir çalışma alanı seçin.\n", tag="system")
            return
            
        text = self.ui.chat_input.get("1.0", "end").strip()
        if not text:
            return
            
        self.ui.chat_input.delete("1.0", "end")
        self.ui.append_chat(f"\nSiz: {text}\n\n", tag="system")
        
        self.agent.router_model = self.ui.combo_router.get()
        self.agent.coder_model = self.ui.combo_coder.get()
        self.agent.add_user_message(text)
        
        self.ui.btn_send.configure(state="disabled")
        
        def task():
            self.agent.process_input()
            # Flush any remaining buffer
            self._flush_buffer()
            self.ui.after(0, self.refresh_diff)
            self.ui.after(0, lambda: self.ui.btn_send.configure(state="normal"))
            self.ui.after(0, lambda: self.populate_tree(self.workspace_path))
            
        threading.Thread(target=task, daemon=True).start()

    def _flush_buffer(self):
        if self._stream_buffer:
            text = self._stream_buffer
            self._stream_buffer = ""
            self.ui.after(0, lambda: self.ui.append_chat(text))

    def agent_callback(self, chunk, is_system=False):
        if is_system:
            self._flush_buffer()
            self.ui.after(0, lambda: self.ui.append_chat(chunk, tag="system"))
        else:
            self._stream_buffer += chunk
            current_time = time.time()
            if current_time - self._last_update_time > 0.05: # Her 50ms'de bir güncelle (UI Donmasını engeller)
                self._flush_buffer()
                self._last_update_time = current_time

    def refresh_diff(self):
        if not self.workspace_path:
            return
        diff_text = get_diff(self.workspace_path)
        if not diff_text:
            diff_text = "Değişiklik bulunamadı."
        self.ui.set_diff(diff_text)

    def push_to_git(self):
        if not self.workspace_path:
            return
            
        msg = self.ui.commit_msg_input.get().strip()
        if not msg:
            msg = "AI: Otonom değişiklikler."
            
        self.ui.btn_git_push.configure(state="disabled", text="Gönderiliyor...")
        self.ui.append_log(f"Çalıştırılıyor: Git Commit & Push (Mesaj: {msg})")
        
        def task():
            success, log = commit_and_push(self.workspace_path, msg)
            def update_ui():
                self.ui.append_log(log)
                self.refresh_diff()
                if success:
                    self.ui.btn_git_push.configure(state="normal", text="✅ Başarılı")
                    self.ui.after(3000, lambda: self.ui.btn_git_push.configure(text="✅ Güvenli Commit & Push"))
                    self.ui.commit_msg_input.delete(0, "end")
                else:
                    self.ui.btn_git_push.configure(state="normal", text="❌ Hata (Logu İnceleyin)")
                    self.ui.after(3000, lambda: self.ui.btn_git_push.configure(text="✅ Güvenli Commit & Push"))
            self.ui.after(0, update_ui)
            
        threading.Thread(target=task, daemon=True).start()

    def run(self):
        self.ui.mainloop()

if __name__ == "__main__":
    app = MainApp()
    app.run()
