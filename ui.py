import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Autonomous Coding Agent")
        self.geometry("1300x800")
        
        # Ana Grid Yapılandırması (3 Kolon)
        self.grid_columnconfigure(0, weight=0, minsize=260)  # Sol Menü
        self.grid_columnconfigure(1, weight=1)               # Orta Sohbet
        self.grid_columnconfigure(2, weight=0, minsize=380)  # Sağ Git/Diff
        self.grid_rowconfigure(0, weight=1)
        
        self._build_left_panel()
        self._build_middle_panel()
        self._build_right_panel()
        self.apply_styles()

    def _build_left_panel(self):
        self.left_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#151515")
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1)
        
        # Klasör Seçimi
        self.btn_select_folder = ctk.CTkButton(self.left_frame, text="📁 Klasör Seç", fg_color="#2D2D2D", hover_color="#3D3D3D")
        self.btn_select_folder.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        
        # Dosya Ağacı (Treeview)
        self.tree_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.tree_frame.grid(row=1, column=0, padx=15, pady=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        # Model Ayarları
        self.model_frame = ctk.CTkFrame(self.left_frame, fg_color="#1E1E1E", corner_radius=10)
        self.model_frame.grid(row=2, column=0, padx=15, pady=(10, 5), sticky="ew")
        
        ctk.CTkLabel(self.model_frame, text="Yönlendirici (Router):", font=("Inter", 11)).pack(anchor="w", padx=10, pady=(5,0))
        self.combo_router = ctk.CTkComboBox(self.model_frame, values=["qwen:3.5b"])
        self.combo_router.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(self.model_frame, text="Kodlayıcı (Coder):", font=("Inter", 11)).pack(anchor="w", padx=10, pady=(5,0))
        self.combo_coder = ctk.CTkComboBox(self.model_frame, values=["qwen2.5-coder:7b"])
        self.combo_coder.pack(fill="x", padx=10, pady=(0, 10))
        
        self.btn_pull_model = ctk.CTkButton(self.model_frame, text="⬇️ Yeni Model İndir", fg_color="#2D2D2D", hover_color="#3D3D3D")
        self.btn_pull_model.pack(fill="x", padx=10, pady=(0, 10))
        
        # Ollama Durumu
        self.lbl_ollama_status = ctk.CTkLabel(self.left_frame, text="Ollama: Bağlanıyor...", text_color="orange", font=("Inter", 11, "bold"))
        self.lbl_ollama_status.grid(row=3, column=0, padx=15, pady=(5, 15), sticky="w")

    def _build_middle_panel(self):
        self.mid_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1A1A1A")
        self.mid_frame.grid(row=0, column=1, sticky="nsew")
        self.mid_frame.grid_rowconfigure(0, weight=1)
        
        # Sohbet Ekranı
        self.chat_display = ctk.CTkTextbox(self.mid_frame, state="disabled", font=("Consolas", 13), fg_color="#1E1E1E", text_color="#E0E0E0")
        self.chat_display.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="nsew")
        
        # Tag konfigürasyonu ile renkli metin desteği (CTKTextbox underlying tkinter Text widget destekler)
        self.chat_display.tag_config("system", foreground="#8B8B8B")
        self.chat_display.tag_config("think", foreground="#4A90E2", font=("Consolas", 12, "italic"))
        self.chat_display.tag_config("tool", foreground="#F5A623")
        
        # Girdi Alanı
        self.input_frame = ctk.CTkFrame(self.mid_frame, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, padx=15, pady=(0,15), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkTextbox(self.input_frame, height=60, font=("Inter", 13), fg_color="#2D2D2D")
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0,10))
        
        self.btn_send = ctk.CTkButton(self.input_frame, text="Gönder", width=80, height=60, fg_color="#0066CC", hover_color="#0052A3", font=("Inter", 13, "bold"))
        self.btn_send.grid(row=0, column=1)

    def _build_right_panel(self):
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#151515")
        self.right_frame.grid(row=0, column=2, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        # Diff Görüntüleyici
        diff_label_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        diff_label_frame.grid(row=0, column=0, sticky="nw", padx=15, pady=(15, 0))
        ctk.CTkLabel(diff_label_frame, text="📝 Değişiklikler (Diff)", font=("Inter", 12, "bold")).pack(side="left")
        
        self.btn_refresh_diff = ctk.CTkButton(diff_label_frame, text="Yenile", width=50, height=20, fg_color="#2D2D2D", hover_color="#3D3D3D")
        self.btn_refresh_diff.pack(side="left", padx=10)
        
        self.diff_display = ctk.CTkTextbox(self.right_frame, font=("Consolas", 12), fg_color="#1E1E1E", text_color="#A9DC76")
        self.diff_display.grid(row=0, column=0, padx=15, pady=(45, 10), sticky="nsew")
        
        # Terminal/Git Log
        ctk.CTkLabel(self.right_frame, text="Terminal Log", font=("Inter", 12, "bold")).grid(row=1, column=0, sticky="nw", padx=15, pady=(5, 0))
        self.git_log = ctk.CTkTextbox(self.right_frame, font=("Consolas", 11), fg_color="#000000", text_color="#00FF00")
        self.git_log.grid(row=1, column=0, padx=15, pady=(30, 10), sticky="nsew")
        
        # Git Kontrolleri
        self.git_control_frame = ctk.CTkFrame(self.right_frame, fg_color="#1E1E1E", corner_radius=10)
        self.git_control_frame.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        self.commit_msg_input = ctk.CTkEntry(self.git_control_frame, placeholder_text="Commit mesajınızı girin...", fg_color="#2D2D2D")
        self.commit_msg_input.pack(fill="x", padx=10, pady=(10, 10))
        
        self.btn_git_push = ctk.CTkButton(self.git_control_frame, text="✅ Onayla & GitHub'a Pushla", fg_color="#28A745", hover_color="#218838", font=("Inter", 13, "bold"))
        self.btn_git_push.pack(fill="x", padx=10, pady=(0, 10))

    def apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#1E1E1E",
                        foreground="#E0E0E0",
                        rowheight=25,
                        fieldbackground="#1E1E1E",
                        bordercolor="#151515",
                        borderwidth=0,
                        font=("Inter", 11))
        style.map('Treeview', background=[('selected', '#0066CC')])
        
    def append_chat(self, text, tag=None):
        self.chat_display.configure(state="normal")
        if tag:
            self.chat_display.insert("end", text, tag)
        else:
            self.chat_display.insert("end", text)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
        
    def set_diff(self, text):
        self.diff_display.configure(state="normal")
        self.diff_display.delete("1.0", "end")
        self.diff_display.insert("end", text)
        self.diff_display.configure(state="disabled")

    def append_log(self, text):
        self.git_log.configure(state="normal")
        self.git_log.insert("end", text + "\n")
        self.git_log.see("end")
        self.git_log.configure(state="disabled")
