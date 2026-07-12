import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

# ==========================================
# GOOGLE MATERIAL DESIGN 3 - DARK THEME
# ==========================================
BG_COLOR = "#131314"          # Very dark grey (Gemini Background)
SURFACE_COLOR = "#1E1F20"     # Cards / Panels
SURFACE_HOVER = "#282A2C"     # Hovered cards
BORDER_COLOR = "#444746"      # Dividers
PRIMARY_COLOR = "#A8C7FA"     # Google Light Blue (Dark Mode)
PRIMARY_HOVER = "#D3E3FD"
TEXT_PRIMARY = "#E3E3E3"      # High emphasis
TEXT_SECONDARY = "#C4C7C5"    # Medium emphasis
SUCCESS_COLOR = "#6DD58C"     # Google Green
FONT_FAMILY = "Segoe UI"      # Clean Sans-serif

ctk.set_appearance_mode("Dark")

class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Workspace - Autonomous Agent")
        self.geometry("1400x900")
        self.configure(fg_color=BG_COLOR)
        
        # Grid - 3 Panels: Sidebar(280px), Main Chat(Flex), Right Inspector(400px)
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=420)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_main_chat()
        self._build_right_inspector()
        self.apply_styles()

    def _build_sidebar(self):
        """Sol Panel: Proje ve Model Yönetimi"""
        self.sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=SURFACE_COLOR, border_width=1, border_color=BORDER_COLOR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1) # Treeview expands
        
        # Google Style Header
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(32, 20))
        ctk.CTkLabel(header, text="✨ Workspace", font=(FONT_FAMILY, 22, "bold"), text_color=PRIMARY_COLOR).pack(anchor="w")
        
        # Action Button (Like Google "New Chat" or "Compose")
        self.btn_select_folder = ctk.CTkButton(
            self.sidebar, text="✚ Çalışma Alanı Seç", 
            fg_color=BG_COLOR, hover_color=SURFACE_HOVER, border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 14, "bold"), corner_radius=24, height=48
        )
        self.btn_select_folder.grid(row=1, column=0, padx=24, pady=(0, 20), sticky="ew")
        
        # File Explorer
        tree_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        tree_container.grid(row=2, column=0, padx=24, pady=0, sticky="nsew")
        tree_container.grid_rowconfigure(1, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(tree_container, text="PROJE DOSYALARI", font=(FONT_FAMILY, 11, "bold"), text_color=TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=(0, 8))
        
        self.tree = ttk.Treeview(tree_container, show="tree")
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        # Model Settings Card
        model_card = ctk.CTkFrame(self.sidebar, fg_color=BG_COLOR, corner_radius=16)
        model_card.grid(row=3, column=0, padx=24, pady=24, sticky="ew")
        
        ctk.CTkLabel(model_card, text="Yönlendirici Model", font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(16, 4))
        self.combo_router = ctk.CTkComboBox(model_card, values=["qwen:3.5b"], fg_color=SURFACE_COLOR, border_color=BORDER_COLOR, button_color=SURFACE_COLOR)
        self.combo_router.pack(fill="x", padx=16, pady=(0, 12))
        
        ctk.CTkLabel(model_card, text="Kodlayıcı Model", font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(0, 4))
        self.combo_coder = ctk.CTkComboBox(model_card, values=["qwen2.5-coder:7b"], fg_color=SURFACE_COLOR, border_color=BORDER_COLOR, button_color=SURFACE_COLOR)
        self.combo_coder.pack(fill="x", padx=16, pady=(0, 16))
        
        self.lbl_ollama_status = ctk.CTkLabel(self.sidebar, text="● Ollama Bağlantısı Aranıyor...", text_color="#EAB308", font=(FONT_FAMILY, 12))
        self.lbl_ollama_status.grid(row=4, column=0, padx=24, pady=(0, 24), sticky="w")

    def _build_main_chat(self):
        """Orta Panel: Google Gemini tarzı Chat Arayüzü"""
        self.main_chat = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_COLOR)
        self.main_chat.grid(row=0, column=1, sticky="nsew")
        self.main_chat.grid_rowconfigure(0, weight=1)
        self.main_chat.grid_columnconfigure(0, weight=1)
        
        # Chat Display
        self.chat_display = ctk.CTkTextbox(
            self.main_chat, state="disabled", font=("Consolas", 15), 
            fg_color="transparent", text_color=TEXT_PRIMARY, wrap="word"
        )
        self.chat_display.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="nsew")
        
        # Tags for colored text
        self.chat_display.tag_config("system", foreground=TEXT_SECONDARY)
        self.chat_display.tag_config("think", foreground=PRIMARY_COLOR) 
        self.chat_display.tag_config("tool", foreground="#FCD34D") 
        
        # Input Area (Rounded, floating look)
        input_container = ctk.CTkFrame(self.main_chat, fg_color=SURFACE_COLOR, corner_radius=24)
        input_container.grid(row=1, column=0, padx=40, pady=(0, 40), sticky="ew")
        input_container.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkTextbox(input_container, height=60, font=(FONT_FAMILY, 15), fg_color="transparent", border_width=0, text_color=TEXT_PRIMARY)
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        
        self.btn_send = ctk.CTkButton(
            input_container, text="Gönder", width=80, height=48, 
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER, text_color=BG_COLOR,
            font=(FONT_FAMILY, 14, "bold"), corner_radius=20
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 16))

    def _build_right_inspector(self):
        """Sağ Panel: Kod ve Git Denetleyicisi (Inspector)"""
        self.inspector = ctk.CTkFrame(self, corner_radius=0, fg_color=SURFACE_COLOR, border_width=1, border_color=BORDER_COLOR)
        self.inspector.grid(row=0, column=2, sticky="nsew")
        self.inspector.grid_rowconfigure(0, weight=1)
        self.inspector.grid_rowconfigure(1, weight=1)
        self.inspector.grid_columnconfigure(0, weight=1)
        
        # Diff View
        diff_header = ctk.CTkFrame(self.inspector, fg_color="transparent")
        diff_header.grid(row=0, column=0, sticky="nw", padx=24, pady=(32, 0))
        ctk.CTkLabel(diff_header, text="DEĞİŞİKLİKLER", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY).pack(side="left")
        self.btn_refresh_diff = ctk.CTkButton(diff_header, text="Yenile", width=60, height=24, fg_color="transparent", border_width=1, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY)
        self.btn_refresh_diff.pack(side="left", padx=16)
        
        self.diff_display = ctk.CTkTextbox(self.inspector, font=("Consolas", 13), fg_color=BG_COLOR, text_color="#A9DC76", corner_radius=12)
        self.diff_display.grid(row=0, column=0, padx=24, pady=(70, 16), sticky="nsew")
        
        # Terminal Log
        ctk.CTkLabel(self.inspector, text="TERMİNAL LOG", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY).grid(row=1, column=0, sticky="nw", padx=24, pady=(16, 0))
        self.git_log = ctk.CTkTextbox(self.inspector, font=("Consolas", 12), fg_color="#000000", text_color=SUCCESS_COLOR, corner_radius=12)
        self.git_log.grid(row=1, column=0, padx=24, pady=(45, 16), sticky="nsew")
        
        # Actions
        actions_frame = ctk.CTkFrame(self.inspector, fg_color="transparent")
        actions_frame.grid(row=2, column=0, padx=24, pady=(0, 32), sticky="ew")
        
        self.commit_msg_input = ctk.CTkEntry(actions_frame, placeholder_text="Commit mesajı...", fg_color=BG_COLOR, border_color=BORDER_COLOR, height=48, corner_radius=12)
        self.commit_msg_input.pack(fill="x", pady=(0, 16))
        
        self.btn_git_push = ctk.CTkButton(
            actions_frame, text="✅ Güvenli Commit & Push", 
            fg_color=SUCCESS_COLOR, hover_color="#5CB87A", text_color="#000000",
            font=(FONT_FAMILY, 15, "bold"), height=52, corner_radius=12
        )
        self.btn_git_push.pack(fill="x")

    def apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Treeview", 
                        background=SURFACE_COLOR,
                        foreground=TEXT_PRIMARY,
                        rowheight=32,
                        fieldbackground=SURFACE_COLOR,
                        bordercolor=SURFACE_COLOR,
                        borderwidth=0,
                        font=(FONT_FAMILY, 12))
        style.map('Treeview', background=[('selected', BORDER_COLOR)])
        
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
