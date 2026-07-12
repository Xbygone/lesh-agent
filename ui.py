import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

# ==========================================
# GOOGLE MATERIAL DESIGN 3 - DARK THEME
# ==========================================
BG_COLOR = "#131314"
SURFACE_COLOR = "#1E1F20"
SURFACE_HOVER = "#282A2C"
BORDER_COLOR = "#444746"
PRIMARY_COLOR = "#A8C7FA"
PRIMARY_HOVER = "#D3E3FD"
TEXT_PRIMARY = "#E3E3E3"
TEXT_SECONDARY = "#C4C7C5"
SUCCESS_COLOR = "#6DD58C"
WARN_COLOR = "#FCD34D"
THINK_COLOR = "#9AA0A6"
FONT_FAMILY = "Segoe UI"

ctk.set_appearance_mode("Dark")


class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Yerel Ajan — Autonomous Coding Agent")
        self.geometry("1440x900")
        self.configure(fg_color=BG_COLOR)

        # Layout: Sidebar(280) | Chat(flex) | Inspector(400)
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_chat()
        self._build_inspector()
        self._apply_tree_style()

    # ─────────────────────────────────────────────
    # LEFT SIDEBAR
    # ─────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, corner_radius=0, fg_color=SURFACE_COLOR,
            border_width=1, border_color=BORDER_COLOR
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)  # Treeview expands
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            self.sidebar, text="✦ Yerel Ajan",
            font=(FONT_FAMILY, 20, "bold"), text_color=PRIMARY_COLOR
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(28, 16))
        
        # PAT/API Key Input
        self.lbl_token = ctk.CTkLabel(
            self.sidebar, text="API Key / Token",
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY
        )
        self.lbl_token.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 4))
        
        self.entry_pat = ctk.CTkEntry(
            self.sidebar, placeholder_text="Token girin...", show="*",
            fg_color=BG_COLOR, border_color=BORDER_COLOR, height=36,
            font=(FONT_FAMILY, 12)
        )
        self.entry_pat.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")

        # Workspace button
        self.btn_select_folder = ctk.CTkButton(
            self.sidebar, text="✚  Çalışma Alanı Seç",
            fg_color=BG_COLOR, hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 13, "bold"),
            corner_radius=20, height=44
        )
        self.btn_select_folder.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")

        # File tree
        tree_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        tree_frame.grid(row=4, column=0, padx=16, pady=0, sticky="nsew")
        tree_frame.grid_rowconfigure(1, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tree_frame, text="DOSYALAR (Tıklayarak Bağlama Ekle)",
            font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SECONDARY
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        self.tree.grid(row=1, column=0, sticky="nsew")

        # Model card — double selector (Provider -> Model)
        model_card = ctk.CTkFrame(self.sidebar, fg_color=BG_COLOR, corner_radius=14)
        model_card.grid(row=5, column=0, padx=16, pady=16, sticky="ew")

        ctk.CTkLabel(
            model_card, text="Sağlayıcı (Provider)",
            font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=14, pady=(14, 4))

        self.combo_provider = ctk.CTkComboBox(
            model_card, values=["Yerel (Ollama)", "GitHub Models (Bulut)", "Google AI Studio (Gemini)", "Groq Cloud"],
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR,
            button_color=SURFACE_COLOR, text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13)
        )
        self.combo_provider.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(
            model_card, text="Model",
            font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=14, pady=(4, 4))

        self.combo_model = ctk.CTkComboBox(
            model_card, values=["qwen2.5-coder:7b", "qwen3.5:4b"],
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR,
            button_color=SURFACE_COLOR, text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13)
        )
        self.combo_model.pack(fill="x", padx=14, pady=(0, 14))

        # Status
        self.lbl_status = ctk.CTkLabel(
            self.sidebar, text="● Hazır",
            text_color=WARN_COLOR, font=(FONT_FAMILY, 12)
        )
        self.lbl_status.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Update Button
        self.btn_update = ctk.CTkButton(
            self.sidebar, text="🔄 Güncellemeleri Kontrol Et",
            fg_color="transparent", hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 12)
        )
        self.btn_update.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")

    # ─────────────────────────────────────────────
    # CENTER CHAT PANEL
    # ─────────────────────────────────────────────
    def _build_chat(self):
        self.chat_panel = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_COLOR)
        self.chat_panel.grid(row=0, column=1, sticky="nsew")
        self.chat_panel.grid_rowconfigure(0, weight=1)
        self.chat_panel.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(
            self.chat_panel, state="disabled",
            font=("Consolas", 14), fg_color="transparent",
            text_color=TEXT_PRIMARY, wrap="word"
        )
        self.chat_display.grid(row=0, column=0, padx=36, pady=(36, 12), sticky="nsew")

        # Tags
        self.chat_display.tag_config("system", foreground=TEXT_SECONDARY)
        self.chat_display.tag_config("user", foreground=PRIMARY_COLOR)
        self.chat_display.tag_config("tool_ok", foreground=SUCCESS_COLOR)
        self.chat_display.tag_config("think", foreground=THINK_COLOR)  # Görsel olarak ayrışan gri ton

        # Input bar
        bar = ctk.CTkFrame(self.chat_panel, fg_color=SURFACE_COLOR, corner_radius=22)
        bar.grid(row=1, column=0, padx=36, pady=(0, 36), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkTextbox(
            bar, height=56, font=(FONT_FAMILY, 14),
            fg_color="transparent", border_width=0,
            text_color=TEXT_PRIMARY
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=18, pady=10)

        self.btn_send = ctk.CTkButton(
            bar, text="Gönder", width=90, height=44,
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER,
            text_color=BG_COLOR, font=(FONT_FAMILY, 14, "bold"),
            corner_radius=18
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 14))

    # ─────────────────────────────────────────────
    # RIGHT INSPECTOR
    # ─────────────────────────────────────────────
    def _build_inspector(self):
        self.inspector = ctk.CTkFrame(
            self, corner_radius=0, fg_color=SURFACE_COLOR,
            border_width=1, border_color=BORDER_COLOR
        )
        self.inspector.grid(row=0, column=2, sticky="nsew")
        self.inspector.grid_rowconfigure(1, weight=2)  # terminal log bigger
        self.inspector.grid_rowconfigure(0, weight=1)
        self.inspector.grid_columnconfigure(0, weight=1)

        # ── Diff panel ──
        diff_header = ctk.CTkFrame(self.inspector, fg_color="transparent")
        diff_header.grid(row=0, column=0, sticky="new", padx=20, pady=(24, 0))
        diff_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            diff_header, text="GİT DEĞİŞİKLİKLERİ",
            font=(FONT_FAMILY, 11, "bold"), text_color=TEXT_SECONDARY
        ).grid(row=0, column=0, sticky="w")

        self.btn_refresh_diff = ctk.CTkButton(
            diff_header, text="↺", width=32, height=24,
            fg_color="transparent", border_width=1,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 14)
        )
        self.btn_refresh_diff.grid(row=0, column=1, sticky="e")

        self.diff_display = ctk.CTkTextbox(
            self.inspector, font=("Consolas", 12),
            fg_color=BG_COLOR, text_color="#A9DC76", corner_radius=10
        )
        self.diff_display.grid(row=0, column=0, padx=20, pady=(52, 8), sticky="nsew")

        # ── Terminal / Agent Log ──
        ctk.CTkLabel(
            self.inspector, text="AJAN TERMİNAL LOGU",
            font=(FONT_FAMILY, 11, "bold"), text_color=TEXT_SECONDARY
        ).grid(row=1, column=0, sticky="nw", padx=20, pady=(8, 0))

        self.terminal_log = ctk.CTkTextbox(
            self.inspector, font=("Consolas", 12),
            fg_color="#0D0D0D", text_color=SUCCESS_COLOR,
            corner_radius=10
        )
        self.terminal_log.grid(row=1, column=0, padx=20, pady=(30, 8), sticky="nsew")

        # ── Git push bar ──
        push_bar = ctk.CTkFrame(self.inspector, fg_color="transparent")
        push_bar.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        push_bar.grid_columnconfigure(0, weight=1)

        self.commit_msg_input = ctk.CTkEntry(
            push_bar, placeholder_text="Commit mesajı...",
            fg_color=BG_COLOR, border_color=BORDER_COLOR,
            height=42, corner_radius=10, font=(FONT_FAMILY, 13),
            text_color=TEXT_PRIMARY
        )
        self.commit_msg_input.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.btn_git_push = ctk.CTkButton(
            push_bar, text="✅  Commit & Push",
            fg_color=SUCCESS_COLOR, hover_color="#5CB87A",
            text_color="#000000", font=(FONT_FAMILY, 14, "bold"),
            height=46, corner_radius=10
        )
        self.btn_git_push.grid(row=1, column=0, sticky="ew")

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _apply_tree_style(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=SURFACE_COLOR, foreground=TEXT_PRIMARY,
            rowheight=28, fieldbackground=SURFACE_COLOR,
            borderwidth=0, font=(FONT_FAMILY, 12)
        )
        style.map("Treeview", background=[("selected", BORDER_COLOR)])

    def append_chat(self, text, tag=None):
        self.chat_display.configure(state="normal")
        if tag:
            self.chat_display.insert("end", text, tag)
        else:
            self.chat_display.insert("end", text)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def append_log(self, text):
        self.terminal_log.configure(state="normal")
        self.terminal_log.insert("end", text + "\n")
        self.terminal_log.see("end")
        self.terminal_log.configure(state="disabled")

    def set_diff(self, text):
        self.diff_display.configure(state="normal")
        self.diff_display.delete("1.0", "end")
        self.diff_display.insert("end", text)
        self.diff_display.configure(state="disabled")
