"""Lesh Agent — main window (reactive dark UI).

Layout:  Sidebar (300) | Chat (flex) | Inspector (410, tabbed Diff/Log)
All long-running work happens off the UI thread; widgets update via .after().
"""

import os
import customtkinter as ctk
from tkinter import ttk

from theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_2, SURFACE_HOVER, BORDER_COLOR,
    PRIMARY_COLOR, PRIMARY_HOVER, TEXT_PRIMARY, TEXT_SECONDARY,
    SUCCESS_COLOR, WARN_COLOR, ERROR_COLOR, THINK_COLOR, PILOT_COLOR,
    FONT_FAMILY, MONO_FAMILY,
)

ctk.set_appearance_mode("Dark")


class AppUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Lesh — Local Agent Coder")
        self.geometry("1440x900")
        self.minsize(1080, 680)
        self.configure(fg_color=BG_COLOR)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=410)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_chat()
        self._build_inspector()
        self._apply_tree_style()

        # Hidden until auth resolves
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
        self.event_generate("<<AuthSuccess>>")

    # ═════════════════════════════════════════════════════
    # LEFT SIDEBAR
    # ═════════════════════════════════════════════════════
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=SURFACE_COLOR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(3, weight=1)  # tabs stretch

        # ── Header + status ──
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(22, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="⚡ Lesh Agent", font=(FONT_FAMILY, 20, "bold"),
            text_color=TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")

        self.lbl_status = ctk.CTkLabel(
            header, text="● Başlatılıyor...", font=(FONT_FAMILY, 12),
            text_color=WARN_COLOR
        )
        self.lbl_status.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # ── Mode selector ──
        self.mode_selector = ctk.CTkSegmentedButton(
            self.sidebar, values=["Standart", "Oto-Pilot", "Yazılım Ofisi"],
            fg_color=SURFACE_2, selected_color=PRIMARY_COLOR,
            selected_hover_color=PRIMARY_HOVER, unselected_color=SURFACE_2,
            unselected_hover_color=SURFACE_HOVER, text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"), corner_radius=8, height=34
        )
        self.mode_selector.grid(row=1, column=0, padx=16, pady=(6, 12), sticky="ew")
        self.mode_selector.set("Standart")

        # ── Config card ──
        card = ctk.CTkFrame(
            self.sidebar, fg_color=SURFACE_2, corner_radius=10,
            border_width=1, border_color=BORDER_COLOR
        )
        card.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="SAĞLAYICI", font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SECONDARY
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))

        self.combo_provider = ctk.CTkComboBox(
            card, values=["Yerel (Ollama)"], state="readonly",
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR,
            button_color=SURFACE_COLOR, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE_2, dropdown_hover_color=SURFACE_HOVER,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 12), corner_radius=6, height=32
        )
        self.combo_provider.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        ctk.CTkLabel(
            card, text="MODEL", font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SECONDARY
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(2, 2))

        self.combo_model = ctk.CTkComboBox(
            card, values=["qwen2.5-coder:7b"],
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR,
            button_color=SURFACE_COLOR, button_hover_color=SURFACE_HOVER,
            dropdown_fg_color=SURFACE_2, dropdown_hover_color=SURFACE_HOVER,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 12), corner_radius=6, height=32
        )
        self.combo_model.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.lbl_token = ctk.CTkLabel(
            card, text="API ANAHTARI", font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SECONDARY
        )
        self.lbl_token.grid(row=4, column=0, sticky="w", padx=14, pady=(2, 2))

        self.entry_pat = ctk.CTkEntry(
            card, placeholder_text="Token girin...", show="•",
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR, height=32,
            corner_radius=6, font=(FONT_FAMILY, 12), text_color=TEXT_PRIMARY
        )
        self.entry_pat.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.btn_select_folder = ctk.CTkButton(
            card, text="📁 Çalışma Klasörü Seç",
            fg_color=SURFACE_COLOR, hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 12, "bold"),
            corner_radius=6, height=36, anchor="w"
        )
        self.btn_select_folder.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 14))

        # ── Tabs: files / sessions ──
        self.tabs = ctk.CTkTabview(
            self.sidebar, fg_color=SURFACE_2, corner_radius=10,
            border_width=1, border_color=BORDER_COLOR,
            segmented_button_fg_color=SURFACE_COLOR,
            segmented_button_selected_color=SURFACE_HOVER,
            segmented_button_selected_hover_color=BORDER_COLOR,
            segmented_button_unselected_color=SURFACE_COLOR,
            text_color=TEXT_PRIMARY
        )
        self.tabs.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="nsew")

        tab_files = self.tabs.add("📂 Dosyalar")
        tab_chats = self.tabs.add("💬 Sohbetler")

        self.tree = ttk.Treeview(tab_files, show="tree", selectmode="browse")
        self.tree.pack(expand=True, fill="both", padx=2, pady=2)

        self.chat_list = ttk.Treeview(tab_chats, show="tree", selectmode="browse")
        self.chat_list.pack(expand=True, fill="both", padx=2, pady=2)

        # ── Bottom: auto-approve + update ──
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        bottom.grid_columnconfigure(0, weight=1)

        self.switch_auto_approve = ctk.CTkSwitch(
            bottom, text="Komutları otomatik onayla",
            font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY,
            progress_color=WARN_COLOR, button_color=TEXT_PRIMARY,
            fg_color=SURFACE_HOVER
        )
        self.switch_auto_approve.grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.btn_update = ctk.CTkButton(
            bottom, text="Güncellemeleri Denetle",
            fg_color="transparent", hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_SECONDARY, font=(FONT_FAMILY, 12),
            corner_radius=6, height=32
        )
        self.btn_update.grid(row=1, column=0, sticky="ew")

    # ═════════════════════════════════════════════════════
    # CENTER CHAT
    # ═════════════════════════════════════════════════════
    def _build_chat(self):
        self.chat_panel = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_COLOR)
        self.chat_panel.grid(row=0, column=1, sticky="nsew")
        self.chat_panel.grid_rowconfigure(1, weight=1)
        self.chat_panel.grid_columnconfigure(0, weight=1)

        # ── Top bar ──
        topbar = ctk.CTkFrame(self.chat_panel, fg_color="transparent", height=48)
        topbar.grid(row=0, column=0, sticky="ew", padx=28, pady=(18, 4))
        topbar.grid_columnconfigure(0, weight=1)

        self.lbl_chat_title = ctk.CTkLabel(
            topbar, text="Yeni Sohbet", font=(FONT_FAMILY, 15, "bold"),
            text_color=TEXT_PRIMARY, anchor="w"
        )
        self.lbl_chat_title.grid(row=0, column=0, sticky="w")

        self.btn_stop = ctk.CTkButton(
            topbar, text="⏹ Durdur", width=90, height=30,
            fg_color=ERROR_COLOR, hover_color="#F6A9A2", text_color="#0F1011",
            font=(FONT_FAMILY, 12, "bold"), corner_radius=8
        )
        self.btn_stop.grid(row=0, column=1, padx=(0, 8))
        self.btn_stop.grid_remove()  # only visible while agent runs

        self.btn_new_chat = ctk.CTkButton(
            topbar, text="＋ Yeni Sohbet", width=110, height=30,
            fg_color="transparent", hover_color=SURFACE_HOVER,
            border_width=1, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, font=(FONT_FAMILY, 12), corner_radius=8
        )
        self.btn_new_chat.grid(row=0, column=2)

        # ── Message area ──
        self.chat_display = ctk.CTkTextbox(
            self.chat_panel, state="disabled",
            font=(MONO_FAMILY, 13), fg_color="transparent",
            text_color=TEXT_PRIMARY, wrap="word", corner_radius=0
        )
        self.chat_display.grid(row=1, column=0, padx=28, pady=(4, 8), sticky="nsew")

        self.chat_display.tag_config("user", foreground=PRIMARY_COLOR)
        self.chat_display.tag_config("user_chip", foreground=PRIMARY_COLOR)
        self.chat_display.tag_config("agent_chip", foreground=SUCCESS_COLOR)
        self.chat_display.tag_config("system", foreground=TEXT_SECONDARY)
        self.chat_display.tag_config("tool", foreground=WARN_COLOR)
        self.chat_display.tag_config("tool_ok", foreground=SUCCESS_COLOR)
        self.chat_display.tag_config("think", foreground=THINK_COLOR)
        self.chat_display.tag_config("pilot", foreground=PILOT_COLOR)
        self.chat_display.tag_config("error", foreground=ERROR_COLOR)

        # ── Input bar ──
        bar = ctk.CTkFrame(
            self.chat_panel, fg_color=SURFACE_2,
            corner_radius=14, border_width=1, border_color=BORDER_COLOR
        )
        bar.grid(row=2, column=0, padx=28, pady=(0, 22), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkTextbox(
            bar, height=54, font=(FONT_FAMILY, 14),
            fg_color="transparent", border_width=0,
            text_color=TEXT_PRIMARY, wrap="word"
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=8)

        self.btn_send = ctk.CTkButton(
            bar, text="Gönder ➤", width=104, height=40,
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER,
            text_color="#0F1011", font=(FONT_FAMILY, 13, "bold"),
            corner_radius=10
        )
        self.btn_send.grid(row=0, column=1, padx=(0, 12))

        hint = ctk.CTkLabel(
            bar, text="Enter: gönder  •  Shift+Enter: yeni satır",
            font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY
        )
        hint.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 6))

    # ═════════════════════════════════════════════════════
    # RIGHT INSPECTOR (tabbed)
    # ═════════════════════════════════════════════════════
    def _build_inspector(self):
        self.inspector = ctk.CTkFrame(self, corner_radius=0, fg_color=SURFACE_COLOR)
        self.inspector.grid(row=0, column=2, sticky="nsew")
        self.inspector.grid_rowconfigure(0, weight=1)
        self.inspector.grid_columnconfigure(0, weight=1)

        self.inspector_tabs = ctk.CTkTabview(
            self.inspector, fg_color=SURFACE_COLOR, corner_radius=0,
            segmented_button_fg_color=SURFACE_2,
            segmented_button_selected_color=SURFACE_HOVER,
            segmented_button_selected_hover_color=BORDER_COLOR,
            segmented_button_unselected_color=SURFACE_2,
            text_color=TEXT_PRIMARY
        )
        self.inspector_tabs.grid(row=0, column=0, sticky="nsew", padx=12, pady=(8, 4))

        tab_diff = self.inspector_tabs.add("Git Diff")
        tab_log = self.inspector_tabs.add("Ajan Logu")

        # ── Diff tab ──
        tab_diff.grid_rowconfigure(1, weight=1)
        tab_diff.grid_columnconfigure(0, weight=1)

        diff_toolbar = ctk.CTkFrame(tab_diff, fg_color="transparent")
        diff_toolbar.grid(row=0, column=0, sticky="ew", pady=(4, 6))
        diff_toolbar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            diff_toolbar, text="Kaydedilmemiş değişiklikler",
            font=(FONT_FAMILY, 11), text_color=TEXT_SECONDARY
        ).grid(row=0, column=0, sticky="w", padx=4)

        self.btn_refresh_diff = ctk.CTkButton(
            diff_toolbar, text="🔄 Yenile", width=76, height=26,
            fg_color="transparent", border_width=1, corner_radius=6,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            hover_color=SURFACE_HOVER, font=(FONT_FAMILY, 11)
        )
        self.btn_refresh_diff.grid(row=0, column=1, sticky="e")

        self.diff_display = ctk.CTkTextbox(
            tab_diff, font=(MONO_FAMILY, 11),
            fg_color=BG_COLOR, text_color=TEXT_PRIMARY,
            corner_radius=8, border_width=1, border_color=BORDER_COLOR,
            wrap="none", state="disabled"
        )
        self.diff_display.grid(row=1, column=0, sticky="nsew")
        self.diff_display.tag_config("add", foreground=SUCCESS_COLOR)
        self.diff_display.tag_config("del", foreground=ERROR_COLOR)
        self.diff_display.tag_config("meta", foreground=PRIMARY_COLOR)

        # ── Log tab ──
        tab_log.grid_rowconfigure(0, weight=1)
        tab_log.grid_columnconfigure(0, weight=1)

        self.terminal_log = ctk.CTkTextbox(
            tab_log, font=(MONO_FAMILY, 11),
            fg_color="#0A0A0B", text_color=TEXT_SECONDARY,
            corner_radius=8, border_width=1, border_color=BORDER_COLOR,
            wrap="word", state="disabled"
        )
        self.terminal_log.grid(row=0, column=0, sticky="nsew", pady=(4, 0))

        # ── Commit bar ──
        push_bar = ctk.CTkFrame(self.inspector, fg_color="transparent")
        push_bar.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="ew")
        push_bar.grid_columnconfigure(0, weight=1)

        self.commit_msg_input = ctk.CTkEntry(
            push_bar, placeholder_text="Commit mesajı...",
            fg_color=SURFACE_2, border_color=BORDER_COLOR,
            height=36, corner_radius=8, font=(FONT_FAMILY, 12),
            text_color=TEXT_PRIMARY
        )
        self.commit_msg_input.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.btn_git_push = ctk.CTkButton(
            push_bar, text="Commit & Push",
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER,
            text_color="#0F1011", font=(FONT_FAMILY, 13, "bold"),
            height=38, corner_radius=8
        )
        self.btn_git_push.grid(row=1, column=0, sticky="ew")

    # ═════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════
    def _apply_tree_style(self):
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=SURFACE_2, foreground=TEXT_PRIMARY,
            rowheight=26, fieldbackground=SURFACE_2,
            borderwidth=0, font=(FONT_FAMILY, 11)
        )
        style.map(
            "Treeview",
            background=[("selected", SURFACE_HOVER)],
            foreground=[("selected", PRIMARY_COLOR)]
        )

    def set_busy(self, busy: bool):
        """Reactive state: toggles Send/Stop and status label."""
        if busy:
            self.btn_send.configure(state="disabled", text="⏳ Çalışıyor")
            self.btn_stop.grid()
            self.lbl_status.configure(text="● Ajan çalışıyor...", text_color=WARN_COLOR)
        else:
            self.btn_send.configure(state="normal", text="Gönder ➤")
            self.btn_stop.grid_remove()
            self.lbl_status.configure(text="● Hazır", text_color=SUCCESS_COLOR)

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
        self.terminal_log.insert("end", str(text) + "\n")
        self.terminal_log.see("end")
        self.terminal_log.configure(state="disabled")

    def set_diff(self, text):
        """Render a unified diff with +/- coloring."""
        self.diff_display.configure(state="normal")
        self.diff_display.delete("1.0", "end")
        for line in (text or "").splitlines(keepends=True):
            if line.startswith(("+++", "---", "diff ", "index ", "@@")):
                self.diff_display.insert("end", line, "meta")
            elif line.startswith("+"):
                self.diff_display.insert("end", line, "add")
            elif line.startswith("-"):
                self.diff_display.insert("end", line, "del")
            else:
                self.diff_display.insert("end", line)
        self.diff_display.configure(state="disabled")

    def ask_approval(self, title: str, detail: str, on_result):
        """Modal approval dialog. Calls on_result(bool) on the UI thread."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("560x300")
        dialog.configure(fg_color=SURFACE_COLOR)
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            dialog, text=f"⚠️  {title}", font=(FONT_FAMILY, 15, "bold"),
            text_color=WARN_COLOR
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))

        box = ctk.CTkTextbox(
            dialog, font=(MONO_FAMILY, 12), fg_color=BG_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
            border_width=1, border_color=BORDER_COLOR
        )
        box.grid(row=1, column=0, sticky="nsew", padx=20)
        box.insert("1.0", detail)
        box.configure(state="disabled")

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=20, pady=16)
        btns.grid_columnconfigure((0, 1), weight=1)

        decided = {"done": False}

        def _decide(value):
            if decided["done"]:
                return
            decided["done"] = True
            dialog.grab_release()
            dialog.destroy()
            on_result(value)

        ctk.CTkButton(
            btns, text="✔ Onayla ve Çalıştır", height=38, corner_radius=8,
            fg_color=SUCCESS_COLOR, hover_color="#A3D9B1", text_color="#0F1011",
            font=(FONT_FAMILY, 13, "bold"), command=lambda: _decide(True)
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            btns, text="✖ Reddet", height=38, corner_radius=8,
            fg_color=ERROR_COLOR, hover_color="#F6A9A2", text_color="#0F1011",
            font=(FONT_FAMILY, 13, "bold"), command=lambda: _decide(False)
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        dialog.protocol("WM_DELETE_WINDOW", lambda: _decide(False))
