"""Login screen. Passwords are NEVER written to disk; sessions are restored
with a Supabase refresh token. When cloud sync is not configured the screen
is skipped entirely (fully-local mode)."""

import threading
import customtkinter as ctk

from db_manager import db
from app_config import load_config, update_config
from theme import (
    SURFACE_COLOR, SURFACE_2, BORDER_COLOR, PRIMARY_COLOR, PRIMARY_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, SUCCESS_COLOR, ERROR_COLOR, FONT_FAMILY,
)


class AuthFrame(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color=SURFACE_COLOR, corner_radius=0)
        self.on_success = on_success

        # Fully local install → no login concept at all.
        if not db.cloud_enabled:
            self.after(50, self._finish)
            return

        card = ctk.CTkFrame(
            self, fg_color=SURFACE_2, corner_radius=16,
            border_width=1, border_color=BORDER_COLOR
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=48, pady=40)

        ctk.CTkLabel(
            inner, text="Lesh Agent", font=(FONT_FAMILY, 30, "bold"),
            text_color=PRIMARY_COLOR
        ).pack(pady=(0, 6))
        ctk.CTkLabel(
            inner, text="Sign in to sync your API keys across devices",
            font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY
        ).pack(pady=(0, 26))

        self.entry_email = ctk.CTkEntry(
            inner, placeholder_text="Email", width=280, height=42,
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR, corner_radius=8
        )
        self.entry_email.pack(pady=6)

        self.entry_password = ctk.CTkEntry(
            inner, placeholder_text="Password", show="•", width=280, height=42,
            fg_color=SURFACE_COLOR, border_color=BORDER_COLOR, corner_radius=8
        )
        self.entry_password.pack(pady=6)
        self.entry_password.bind("<Return>", lambda e: self.do_login())

        self.lbl_msg = ctk.CTkLabel(
            inner, text="", font=(FONT_FAMILY, 12), text_color=ERROR_COLOR,
            wraplength=280
        )
        self.lbl_msg.pack(pady=6)

        self.btn_login = ctk.CTkButton(
            inner, text="Sign In", width=280, height=42, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color=PRIMARY_HOVER, text_color="#0F1011",
            font=(FONT_FAMILY, 14, "bold"), command=self.do_login
        )
        self.btn_login.pack(pady=(8, 4))

        self.btn_register = ctk.CTkButton(
            inner, text="Sign Up", width=280, height=42, corner_radius=8,
            fg_color="transparent", hover_color=SURFACE_COLOR,
            border_width=1, border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13), command=self.do_register
        )
        self.btn_register.pack(pady=4)

        self.btn_skip = ctk.CTkButton(
            inner, text="Continue as guest →", width=280, height=38,
            fg_color="transparent", hover_color=SURFACE_COLOR,
            text_color=TEXT_SECONDARY, font=(FONT_FAMILY, 12),
            command=self._finish
        )
        self.btn_skip.pack(pady=(16, 0))

        self.after(150, self._try_session_restore)

    # ── flows ─────────────────────────────────────────────
    def _try_session_restore(self):
        token = load_config().get("refresh_token")
        if not token:
            return
        self._show_msg("Restoring session...", SUCCESS_COLOR)

        def _run():
            ok = db.restore_session(token)
            if ok:
                new_token = db.get_refresh_token()
                if new_token:
                    update_config(refresh_token=new_token)
                self.after(0, self._finish)
            else:
                self.after(0, lambda: self._show_msg("", TEXT_SECONDARY))

        threading.Thread(target=_run, daemon=True).start()

    def do_login(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_password.get()
        if not email or not pwd:
            self._show_msg("Email and password are required.", ERROR_COLOR)
            return
        self.btn_login.configure(state="disabled", text="Please wait...")

        def _run():
            success, msg = db.login(email, pwd)
            if success:
                token = db.get_refresh_token()
                if token:
                    update_config(refresh_token=token)
                self.after(0, self._finish)
            else:
                self.after(0, lambda: self._show_msg(f"Error: {msg}", ERROR_COLOR))
                self.after(0, lambda: self.btn_login.configure(state="normal", text="Sign In"))

        threading.Thread(target=_run, daemon=True).start()

    def do_register(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_password.get()
        if not email or not pwd:
            self._show_msg("Email and password are required.", ERROR_COLOR)
            return
        self.btn_register.configure(state="disabled", text="Please wait...")

        def _run():
            success, msg = db.register(email, pwd)
            color = SUCCESS_COLOR if success else ERROR_COLOR
            text = "Registration successful! Please sign in." if success else f"Error: {msg}"
            self.after(0, lambda: self._show_msg(text, color))
            self.after(0, lambda: self.btn_register.configure(state="normal", text="Sign Up"))

        threading.Thread(target=_run, daemon=True).start()

    # ── helpers ───────────────────────────────────────────
    def _show_msg(self, text, color):
        try:
            self.lbl_msg.configure(text=text, text_color=color)
        except Exception:
            pass

    def _finish(self):
        self.destroy()
        self.on_success()
