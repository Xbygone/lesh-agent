import os
import threading
import customtkinter as ctk
from tkinter import filedialog
import subprocess

from ui import AppUI
from ollama_client import check_ollama_status, get_models, pull_model
from agent_loop import AgentState
from git_manager import get_diff, commit_and_push, is_git_repo

class MainApp:
    def __init__(self):
        self.ui = AppUI()
        self.workspace_path = None
        self.agent = None
        
        # Olay bağlamaları (Bindings)
        self.ui.btn_select_folder.configure(command=self.select_folder)
        self.ui.btn_pull_model.configure(command=self.download_model)
        self.ui.btn_send.configure(command=self.send_message)
        self.ui.btn_refresh_diff.configure(command=self.refresh_diff)
        self.ui.btn_git_push.configure(command=self.push_to_git)
        
        # İlk Yüklemeler
        self.check_ollama()
        
    def check_ollama(self):
        def task():
            is_running = check_ollama_status()
            if is_running:
                self.ui.lbl_ollama_status.configure(text="Ollama: Bağlı", text_color="#00FF00")
                models = get_models()
                if models:
                    self.ui.combo_router.configure(values=models)
                    self.ui.combo_coder.configure(values=models)
                    if "qwen:3.5b" in models:
                        self.ui.combo_router.set("qwen:3.5b")
                    if "qwen2.5-coder:7b" in models:
                        self.ui.combo_coder.set("qwen2.5-coder:7b")
            else:
                self.ui.lbl_ollama_status.configure(text="Ollama: Kapalı/Bulunamadı", text_color="red")
        threading.Thread(target=task, daemon=True).start()

    def download_model(self):
        # Dialog kutusu ile model adı iste
        dialog = ctk.CTkInputDialog(text="İndirmek istediğiniz modelin adını girin (Örn: qwen:3.5b):", title="Model İndir")
        model_name = dialog.get_input()
        if not model_name:
            return
            
        self.ui.btn_pull_model.configure(state="disabled", text="İndiriliyor...")
        
        def progress(status):
            # UI'ı güvenli şekilde güncelle
            self.ui.after(0, lambda: self.ui.lbl_ollama_status.configure(text=f"İndiriliyor: {status[:30]}", text_color="yellow"))
            
        def task():
            success = pull_model(model_name, progress)
            def update_ui():
                self.ui.btn_pull_model.configure(state="normal", text="⬇️ Yeni Model İndir")
                self.check_ollama()
                if success:
                    self.ui.append_chat(f"\n[SİSTEM] {model_name} başarıyla indirildi.\n", tag="system")
                else:
                    self.ui.append_chat(f"\n[SİSTEM] {model_name} indirilirken hata oluştu.\n", tag="system")
            self.ui.after(0, update_ui)
            
        threading.Thread(target=task, daemon=True).start()

    def select_folder(self):
        path = filedialog.askdirectory(title="Çalışma Dizini Seçin")
        if path:
            self.workspace_path = path
            self.ui.btn_select_folder.configure(text=f"📁 {os.path.basename(path)}")
            self.populate_tree(path)
            self.refresh_diff()
            
            # Agent'ı sıfırla
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
            self.ui.append_chat("\n[HATA] Lütfen önce bir klasör seçin.\n", tag="system")
            return
            
        text = self.ui.chat_input.get("1.0", "end").strip()
        if not text:
            return
            
        self.ui.chat_input.delete("1.0", "end")
        self.ui.append_chat(f"\nSiz: {text}\n", tag="system")
        
        # Seçili modelleri güncelle
        self.agent.router_model = self.ui.combo_router.get()
        self.agent.coder_model = self.ui.combo_coder.get()
        self.agent.add_user_message(text)
        
        self.ui.btn_send.configure(state="disabled")
        
        def task():
            self.agent.process_input()
            # İşlem bittikten sonra Diff'i güncelle
            self.ui.after(0, self.refresh_diff)
            self.ui.after(0, lambda: self.ui.btn_send.configure(state="normal"))
            
        threading.Thread(target=task, daemon=True).start()

    def agent_callback(self, chunk, is_system=False):
        tag = None
        if is_system:
            tag = "system"
        elif "<tool>" in chunk or "</tool>" in chunk:
            tag = "tool"
        elif "<think>" in chunk or "</think>" in chunk:
            tag = "think"
            
        # UI güncellemeleri ana thread'de olmalı
        self.ui.after(0, lambda: self.ui.append_chat(chunk, tag=tag))

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
                    self.ui.after(3000, lambda: self.ui.btn_git_push.configure(text="✅ Onayla & GitHub'a Pushla"))
                    self.ui.commit_msg_input.delete(0, "end")
                else:
                    self.ui.btn_git_push.configure(state="normal", text="❌ Hata (Logu İnceleyin)")
                    self.ui.after(3000, lambda: self.ui.btn_git_push.configure(text="✅ Onayla & GitHub'a Pushla"))
            self.ui.after(0, update_ui)
            
        threading.Thread(target=task, daemon=True).start()

    def run(self):
        self.ui.mainloop()

if __name__ == "__main__":
    app = MainApp()
    app.run()
