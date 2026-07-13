import os
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import sys
import subprocess

# ==========================================
# LESH AGENT - ANTIGRAVITY PROFESSIONAL THEME
# ==========================================
BG_COLOR = "#131314"           # Deep dark background
SURFACE_COLOR = "#1E1F20"      # Elevated surface
SURFACE_HOVER = "#282A2C"      # Button hover
BORDER_COLOR = "#444746"       # Subtle border
PRIMARY_COLOR = "#8AB4F8"      # Professional Google Blue
PRIMARY_HOVER = "#A8C7FA"      # Lighter blue for hover
TEXT_PRIMARY = "#E3E3E3"       # High contrast text
TEXT_SECONDARY = "#C4C7C5"     # Muted text
SUCCESS_COLOR = "#81C995"      # Muted green
WARN_COLOR = "#FDE293"         # Muted yellow
THINK_COLOR = "#F28B82"        # Muted red/pink
FONT_FAMILY = "Segoe UI"

ctk.set_appearance_mode("Dark")


class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Lesh - Local Agent Coder")
        self.geometry("1440x900")
        self.configure(fg_color=BG_COLOR)
        
        icon_path = os.path.join("assets", "logo.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass

        # Layout: Sidebar(320) | Chat(flex) | Inspector(420)
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=420)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_chat()
        self._build_inspector()
        self._apply_tree_style()
        
        # Hide main layout initially
        self.sidebar.grid_remove()
        self.chat_panel.grid_remove()
        self.inspector.grid_remove()
        
        from auth_ui import AuthFrame
        self.auth_frame = AuthFrame(self, on_success=self._on_auth_success)
        self.auth_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _on_auth_success(self):
        self.sidebar.grid()
        self.chat_panel.grid()
        self.inspector.grid()
        # Trigger an event to main.py to fetch tokens
        self.event_generate("<<AuthSuccess>>")

    # ─────────────────────────────────────────────
    # LEFT SIDEBAR
    # ─────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, corner_radius=0, fg_color=SURFACE_COLOR,
            border_width=1, border_color=BORDER_COLOR
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(28, 16))
        header_frame.grid_columnconfigure(0, weight=1)

        self.header_label = ctk.CTkLabel(
            header_frame, text="Lesh Agent",
            font=(FONT_FAMILY, 20, "bold"), text_color=TEXT_PRIMARY
        )
        self.header_label.grid(row=0, column=0, sticky="w")
        
        # Mode Selector
        self.mode_selector = ctk.CTkSegmentedButton(
            self.sidebar, values=["Standart", "Oto-Pilot", "Yazılım Ofisi"],
            fg_color=BG_COLOR, selected_color=PRIMARY_COLOR, selected_hover_color=PRIMARY_HOVER,
            unselected_color=BG_COLOR, text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 12, "bold")
        )
        self.mode_selector.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.mode_selector.set("Standart")
        
        # PAT/API Key Input
        self.lbl_token = ctk.CTkLabel(
            self.sidebar, text="API Key / PAT",
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY
        )
        self.lbl_token.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 4))
        
        self.entry_pat = ctk.CTkEntry(
            self.sidebar, placeholder_text="Enter token...", show="*",
            fg_color=BG_COLOR, border_color=BORDER_COLOR, height=36,
            corner_radius=6, font=(FONT_FAMILY, 13)
        )
        self.entry_pat.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")

        # Workspace button (Subtle 3D look)
        self.btn_select_folder = ctk.CTkButton(
            self.sidebar, text="📁 Select Workspace",
            fg_color=BG_COLOR, hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 13, "bold"),
            corner_radius=6, height=40
        )
        self.btn_select_folder.grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")

        # File tree & Chats (Tabs)
        self.tabs = ctk.CTkTabview(
            self.sidebar, fg_color="transparent",
            segmented_button_selected_color=SURFACE_HOVER,
            segmented_button_selected_hover_color=BORDER_COLOR,
            segmented_button_unselected_color=BG_COLOR,
            text_color_disabled=TEXT_SECONDARY
        )
        self.tabs.grid(row=5, column=0, padx=16, pady=0, sticky="nsew")
        
        self.tab_files = self.tabs.add("📂 Workspace")
        self.tab_chats = self.tabs.add("💬 Sessions")
        
        self.tree = ttk.Treeview(self.tab_files, show="tree", selectmode="browse")
        self.tree.pack(expand=True, fill="both")
        
        self.chat_list = ttk.Treeview(self.tab_chats, show="tree", selectmode="browse")
        self.chat_list.pack(expand=True, fill="both")

        # Model card
        model_card = ctk.CTkFrame(
            self.sidebar, fg_color=BG_COLOR, corner_radius=8,
            border_width=1, border_color=BORDER_COLOR
        )
        model_card.grid(row=6, column=0, padx=16, pady=16, sticky="ew")

        self.lbl_provider = ctk.CTkLabel(
            model_card, text="Provider",
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY
        )
        self.lbl_provider.pack(anchor="w", padx=16, pady=(12, 4))

        self.combo_provider = ctk.CTkComboBox(
            model_card, values=["Yerel (Ollama)", "GitHub Models", "Google AI Studio", "Groq Cloud", "NVIDIA Build"],
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR,
            button_color=SURFACE_COLOR, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE_COLOR, dropdown_hover_color=SURFACE_HOVER,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 13), corner_radius=6
        )
        self.combo_provider.pack(fill="x", padx=16, pady=(0, 12))

        self.lbl_model = ctk.CTkLabel(
            model_card, text="Model",
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY
        )
        self.lbl_model.pack(anchor="w", padx=16, pady=(4, 4))

        self.combo_model = ctk.CTkComboBox(
            model_card, values=["qwen2.5-coder:7b", "qwen3.5:4b"],
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR,
            button_color=SURFACE_COLOR, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE_COLOR, dropdown_hover_color=SURFACE_HOVER,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 13), corner_radius=6
        )
        self.combo_model.pack(fill="x", padx=16, pady=(0, 16))

        # Status
        self.lbl_status = ctk.CTkLabel(
            self.sidebar, text="⚡ Ready",
            text_color=WARN_COLOR, font=(FONT_FAMILY, 12, "bold")
        )
        self.lbl_status.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")
        
        # Update Button
        self.btn_update = ctk.CTkButton(
            self.sidebar, text="Check for Updates",
            fg_color="transparent", hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_SECONDARY, font=(FONT_FAMILY, 12, "bold"), corner_radius=6
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
        self.chat_display.tag_config("think", foreground=THINK_COLOR)
        self.chat_display.tag_config("pilot", foreground="#888888")

        # Input bar (Rounded, professional)
        bar = ctk.CTkFrame(
            self.chat_panel, fg_color=SURFACE_COLOR, 
            corner_radius=16, border_width=1, border_color=BORDER_COLOR
        )
        bar.grid(row=1, column=0, padx=36, pady=(0, 36), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkTextbox(
            bar, height=56, font=(FONT_FAMILY, 14),
            fg_color="transparent", border_width=0,
            text_color=TEXT_PRIMARY
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=16, pady=10)

        self.btn_send = ctk.CTkButton(
            bar, text="Send 🚀", width=80, height=44,
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER,
            text_color="#000000", font=(FONT_FAMILY, 14, "bold"),
            corner_radius=12
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 16))

    # ─────────────────────────────────────────────
    # RIGHT INSPECTOR
    # ─────────────────────────────────────────────
    def _build_inspector(self):
        self.inspector = ctk.CTkFrame(
            self, corner_radius=0, fg_color=SURFACE_COLOR,
            border_width=1, border_color=BORDER_COLOR
        )
        self.inspector.grid(row=0, column=2, sticky="nsew")
        self.inspector.grid_rowconfigure(1, weight=2)
        self.inspector.grid_rowconfigure(0, weight=1)
        self.inspector.grid_columnconfigure(0, weight=1)

        # ── Diff panel ──
        diff_header = ctk.CTkFrame(self.inspector, fg_color="transparent")
        diff_header.grid(row=0, column=0, sticky="new", padx=20, pady=(24, 0))
        diff_header.grid_columnconfigure(0, weight=1)

        self.lbl_diff = ctk.CTkLabel(
            diff_header, text="Git Diff",
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY
        )
        self.lbl_diff.grid(row=0, column=0, sticky="w")

        self.btn_refresh_diff = ctk.CTkButton(
            diff_header, text="🔄", width=32, height=26,
            fg_color="transparent", border_width=1, corner_radius=6,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            hover_color=SURFACE_HOVER,
            font=(FONT_FAMILY, 12)
        )
        self.btn_refresh_diff.grid(row=0, column=1, sticky="e")

        self.diff_display = ctk.CTkTextbox(
            self.inspector, font=("Consolas", 12),
            fg_color=BG_COLOR, text_color=SUCCESS_COLOR, 
            corner_radius=8, border_width=1, border_color=BORDER_COLOR
        )
        self.diff_display.grid(row=0, column=0, padx=20, pady=(56, 8), sticky="nsew")

        # ── Terminal / Agent Log ──
        self.lbl_log = ctk.CTkLabel(
            self.inspector, text="Agent Log",
            font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY
        )
        self.lbl_log.grid(row=1, column=0, sticky="nw", padx=20, pady=(12, 0))

        self.terminal_log = ctk.CTkTextbox(
            self.inspector, font=("Consolas", 12),
            fg_color="#000000", text_color=TEXT_SECONDARY,
            corner_radius=8, border_width=1, border_color=BORDER_COLOR
        )
        self.terminal_log.grid(row=1, column=0, padx=20, pady=(40, 8), sticky="nsew")

        # ── Git push bar ──
        push_bar = ctk.CTkFrame(self.inspector, fg_color="transparent")
        push_bar.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        push_bar.grid_columnconfigure(0, weight=1)

        self.commit_msg_input = ctk.CTkEntry(
            push_bar, placeholder_text="Commit message...",
            fg_color=BG_COLOR, border_color=BORDER_COLOR,
            height=40, corner_radius=8, font=(FONT_FAMILY, 13),
            text_color=TEXT_PRIMARY
        )
        self.commit_msg_input.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.btn_git_push = ctk.CTkButton(
            push_bar, text="Commit & Push",
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER,
            text_color="#000000", font=(FONT_FAMILY, 14, "bold"),
            height=44, corner_radius=8
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
            background=BG_COLOR, foreground=TEXT_PRIMARY,
            rowheight=28, fieldbackground=BG_COLOR,
            borderwidth=0, font=(FONT_FAMILY, 12)
        )
        style.map("Treeview", background=[("selected", SURFACE_HOVER)])

    def append_chat(self, text, tag=None):
        self.chat_display.configure(state="normal")
        if tag:
            self.chat_display.insert("end", text, tag)
        else:
            self.chat_display.insert("end", text)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
        
    def clear_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
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
