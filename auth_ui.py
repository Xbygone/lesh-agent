import customtkinter as ctk
from db_manager import db
import threading

class AuthWindow(ctk.CTk):
    def __init__(self, on_success):
        super().__init__()
        self.title("Lesh Agent - Authentication")
        self.geometry("400x450")
        self.resizable(False, False)
        
        self.on_success = on_success

        # Tema
        ctk.set_appearance_mode("dark")
        self.configure(fg_color="#1E1F20")
        
        # Başlık
        self.lbl_title = ctk.CTkLabel(self, text="Lesh Agent", font=("Inter", 24, "bold"), text_color="#8AB4F8")
        self.lbl_title.pack(pady=(40, 10))
        
        self.lbl_sub = ctk.CTkLabel(self, text="Güvenli giriş yapın veya kayıt olun", font=("Inter", 12), text_color="#AAAAAA")
        self.lbl_sub.pack(pady=(0, 30))

        # Form
        self.entry_email = ctk.CTkEntry(self, placeholder_text="E-posta", width=250, height=40)
        self.entry_email.pack(pady=10)
        
        self.entry_password = ctk.CTkEntry(self, placeholder_text="Şifre", show="*", width=250, height=40)
        self.entry_password.pack(pady=10)

        # Hata / Bilgi Mesajı
        self.lbl_msg = ctk.CTkLabel(self, text="", font=("Inter", 12), text_color="#F28B82")
        self.lbl_msg.pack(pady=5)

        # Butonlar
        self.btn_login = ctk.CTkButton(self, text="Giriş Yap", width=250, height=40, font=("Inter", 14, "bold"), command=self.do_login)
        self.btn_login.pack(pady=10)
        
        self.btn_register = ctk.CTkButton(self, text="Kayıt Ol", width=250, height=40, fg_color="#333333", hover_color="#444444", font=("Inter", 14), command=self.do_register)
        self.btn_register.pack(pady=5)
        
        self.btn_skip = ctk.CTkButton(self, text="Misafir Olarak Devam Et (Atla)", width=250, height=40, fg_color="transparent", hover_color="#333333", border_width=1, border_color="#555555", font=("Inter", 13), command=self.do_skip)
        self.btn_skip.pack(pady=(15, 5))
        
    def do_skip(self):
        self.destroy()
        self.on_success()

    def do_login(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_password.get().strip()
        if not email or not pwd:
            self.lbl_msg.configure(text="E-posta ve şifre gerekli!", text_color="#F28B82")
            return
            
        self.btn_login.configure(state="disabled", text="Bekleyin...")
        
        def _run():
            success, msg = db.login(email, pwd)
            if success:
                self.after(0, self._login_success)
            else:
                self.after(0, lambda: self._show_msg(f"Hata: {msg}", "#F28B82"))
                self.after(0, lambda: self.btn_login.configure(state="normal", text="Giriş Yap"))
                
        threading.Thread(target=_run, daemon=True).start()

    def do_register(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_password.get().strip()
        if not email or not pwd:
            self.lbl_msg.configure(text="E-posta ve şifre gerekli!", text_color="#F28B82")
            return
            
        self.btn_register.configure(state="disabled", text="Bekleyin...")
        
        def _run():
            success, msg = db.register(email, pwd)
            if success:
                self.after(0, lambda: self._show_msg("Kayıt başarılı! Lütfen giriş yapın.", "#81C995"))
            else:
                self.after(0, lambda: self._show_msg(f"Hata: {msg}", "#F28B82"))
            self.after(0, lambda: self.btn_register.configure(state="normal", text="Kayıt Ol"))
                
        threading.Thread(target=_run, daemon=True).start()

    def _show_msg(self, text, color):
        self.lbl_msg.configure(text=text, text_color=color)

    def _login_success(self):
        self.destroy()
        self.on_success()
