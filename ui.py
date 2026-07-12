import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

# Gelişmiş Profesyonel Renk Paleti (Premium Dark Theme)
BG_COLOR = "#0B0B0F"          # Ana Arka Plan
PANEL_COLOR = "#15151A"       # Yan Paneller
WIDGET_BG = "#1C1C24"         # Girdi ve Metin Alanları
ACCENT_COLOR = "#6366F1"      # İndigo (Ana Butonlar)
ACCENT_HOVER = "#4F46E5"      # İndigo Hover
TEXT_COLOR = "#F8FAFC"        # Parlak Beyaz (Başlıklar)
TEXT_MUTED = "#94A3B8"        # Soluk Beyaz (Açıklamalar)
BORDER_COLOR = "#2D2D3B"      # İnce Çizgiler
SUCCESS_COLOR = "#10B981"     # Yeşil (Git Onay)
SUCCESS_HOVER = "#059669"

ctk.set_appearance_mode("Dark")

class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Antigravity - Autonomous Coding Agent")
        self.geometry("1400x850")
        self.configure(fg_color=BG_COLOR)
        
        # Grid Yapılandırması
        self.grid_columnconfigure(0, weight=0, minsize=300)  # Sol Menü (Biraz daha geniş)
        self.grid_columnconfigure(1, weight=1)               # Orta Sohbet
        self.grid_columnconfigure(2, weight=0, minsize=400)  # Sağ Git/Diff (Daha geniş ve rahat)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_left_panel()
        self._build_middle_panel()
        self._build_right_panel()
        self.apply_styles()

    def _build_left_panel(self):
        self.left_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR)
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        self.left_frame.grid_rowconfigure(2, weight=1)
        
        # Logo / Başlık Alanı
        title_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(title_frame, text="ANTIGRAVITY", font=("Inter", 20, "bold"), text_color=ACCENT_COLOR, letter_spacing=2).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="AGENTIC WORKSPACE", font=("Inter", 10), text_color=TEXT_MUTED).pack(anchor="w")
        
        # Klasör Seçimi
        self.btn_select_folder = ctk.CTkButton(
            self.left_frame, text="📁 Çalışma Alanı Seç", 
            fg_color=WIDGET_BG, hover_color=BORDER_COLOR, 
            text_color=TEXT_COLOR, font=("Inter", 13), corner_radius=8, height=40
        )
        self.btn_select_folder.grid(row=1, column=0, padx=20, pady=(15, 10), sticky="ew")
        
        # Dosya Ağacı (Treeview)
        self.tree_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.tree_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.tree_frame.grid_rowconfigure(1, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.tree_frame, text="PROJE DOSYALARI", font=("Inter", 11, "bold"), text_color=TEXT_MUTED).grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        # Model Ayarları
        self.model_frame = ctk.CTkFrame(self.left_frame, fg_color=WIDGET_BG, corner_radius=12)
        self.model_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        ctk.CTkLabel(self.model_frame, text="YÖNLENDİRİCİ (ROUTER)", font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=15, pady=(15,0))
        self.combo_router = ctk.CTkComboBox(self.model_frame, values=["qwen:3.5b"], fg_color=PANEL_COLOR, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, dropdown_fg_color=PANEL_COLOR)
        self.combo_router.pack(fill="x", padx=15, pady=(5, 10))
        
        ctk.CTkLabel(self.model_frame, text="KODLAYICI (CODER)", font=("Inter", 10, "bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=15, pady=(5,0))
        self.combo_coder = ctk.CTkComboBox(self.model_frame, values=["qwen2.5-coder:7b"], fg_color=PANEL_COLOR, border_color=BORDER_COLOR, button_color=ACCENT_COLOR, dropdown_fg_color=PANEL_COLOR)
        self.combo_coder.pack(fill="x", padx=15, pady=(5, 15))
        
        self.btn_pull_model = ctk.CTkButton(self.model_frame, text="Model İndir", fg_color="transparent", border_width=1, border_color=BORDER_COLOR, hover_color=BORDER_COLOR, text_color=TEXT_COLOR)
        self.btn_pull_model.pack(fill="x", padx=15, pady=(0, 15))
        
        self.lbl_ollama_status = ctk.CTkLabel(self.left_frame, text="● Ollama Bağlantısı Aranıyor...", text_color="#EAB308", font=("Inter", 11))
        self.lbl_ollama_status.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="w")

    def _build_middle_panel(self):
        self.mid_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_COLOR)
        self.mid_frame.grid(row=0, column=1, sticky="nsew")
        self.mid_frame.grid_rowconfigure(0, weight=1)
        
        # Sohbet Ekranı
        self.chat_display = ctk.CTkTextbox(
            self.mid_frame, state="disabled", font=("Consolas", 14), 
            fg_color=BG_COLOR, text_color=TEXT_COLOR, wrap="word", border_spacing=20
        )
        self.chat_display.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.chat_display.tag_config("system", foreground=TEXT_MUTED)
        self.chat_display.tag_config("think", foreground="#38BDF8") # Açık Mavi
        self.chat_display.tag_config("tool", foreground="#FCD34D") # Sarımsı
        
        # Girdi Alanı
        self.input_frame = ctk.CTkFrame(self.mid_frame, fg_color=WIDGET_BG, corner_radius=15, border_width=1, border_color=BORDER_COLOR)
        self.input_frame.grid(row=1, column=0, padx=20, pady=(0, 30), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkTextbox(self.input_frame, height=60, font=("Inter", 14), fg_color="transparent", border_width=0, text_color=TEXT_COLOR)
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        self.btn_send = ctk.CTkButton(
            self.input_frame, text="Gönder", width=100, height=50, 
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, 
            font=("Inter", 14, "bold"), corner_radius=10
        )
        self.btn_send.grid(row=0, column=1, padx=10, pady=10)

    def _build_right_panel(self):
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=PANEL_COLOR, border_width=1, border_color=BORDER_COLOR)
        self.right_frame.grid(row=0, column=2, sticky="nsew")
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        # Diff Görüntüleyici
        diff_label_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        diff_label_frame.grid(row=0, column=0, sticky="nw", padx=20, pady=(20, 0))
        ctk.CTkLabel(diff_label_frame, text="DEĞİŞİKLİKLER", font=("Inter", 11, "bold"), text_color=TEXT_MUTED).pack(side="left")
        
        self.btn_refresh_diff = ctk.CTkButton(diff_label_frame, text="Yenile", width=60, height=24, fg_color=WIDGET_BG, hover_color=BORDER_COLOR, text_color=TEXT_COLOR, font=("Inter", 11))
        self.btn_refresh_diff.pack(side="left", padx=15)
        
        self.diff_display = ctk.CTkTextbox(self.right_frame, font=("Consolas", 12), fg_color=WIDGET_BG, text_color="#A9DC76", corner_radius=10, border_spacing=10)
        self.diff_display.grid(row=0, column=0, padx=20, pady=(55, 10), sticky="nsew")
        
        # Terminal/Git Log
        ctk.CTkLabel(self.right_frame, text="TERMİNAL LOG", font=("Inter", 11, "bold"), text_color=TEXT_MUTED).grid(row=1, column=0, sticky="nw", padx=20, pady=(10, 0))
        self.git_log = ctk.CTkTextbox(self.right_frame, font=("Consolas", 11), fg_color="#000000", text_color=SUCCESS_COLOR, corner_radius=10, border_spacing=10)
        self.git_log.grid(row=1, column=0, padx=20, pady=(40, 10), sticky="nsew")
        
        # Git Kontrolleri
        self.git_control_frame = ctk.CTkFrame(self.right_frame, fg_color=WIDGET_BG, corner_radius=12)
        self.git_control_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        self.commit_msg_input = ctk.CTkEntry(self.git_control_frame, placeholder_text="Commit mesajı...", fg_color=PANEL_COLOR, border_color=BORDER_COLOR, height=40)
        self.commit_msg_input.pack(fill="x", padx=15, pady=(15, 10))
        
        self.btn_git_push = ctk.CTkButton(
            self.git_control_frame, text="✅ Güvenli Commit & Push", 
            fg_color=SUCCESS_COLOR, hover_color=SUCCESS_HOVER, 
            font=("Inter", 14, "bold"), height=45, corner_radius=8
        )
        self.btn_git_push.pack(fill="x", padx=15, pady=(0, 15))

    def apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", 
                        background=WIDGET_BG,
                        foreground=TEXT_COLOR,
                        rowheight=28,
                        fieldbackground=WIDGET_BG,
                        bordercolor=WIDGET_BG,
                        borderwidth=0,
                        font=("Inter", 11))
        style.map('Treeview', background=[('selected', ACCENT_COLOR)])
        
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
