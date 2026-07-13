import customtkinter as ctk
from db_manager import db
import threading
import os
import json
import webbrowser

CONFIG_FILE = os.path.expanduser("~/.yerel_agent_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

class AuthFrame(ctk.CTkFrame):
    def __init__(self, master, on_success):
        super().__init__(master, fg_color="#1E1F20", corner_radius=10)
        self.on_success = on_success
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_title = ctk.CTkLabel(self.container, text="Lesh Agent", font=("Inter", 28, "bold"), text_color="#8AB4F8")
        self.lbl_title.pack(pady=(0, 10))
        
        self.lbl_sub = ctk.CTkLabel(self.container, text="Güvenli giriş yapın veya kayıt olun", font=("Inter", 12), text_color="#AAAAAA")
        self.lbl_sub.pack(pady=(0, 30))

        self.entry_email = ctk.CTkEntry(self.container, placeholder_text="E-posta", width=250, height=40)
        self.entry_email.pack(pady=10)
        
        self.entry_password = ctk.CTkEntry(self.container, placeholder_text="Şifre", show="*", width=250, height=40)
        self.entry_password.pack(pady=10)

        self.lbl_msg = ctk.CTkLabel(self.container, text="", font=("Inter", 12), text_color="#F28B82")
        self.lbl_msg.pack(pady=5)

        self.btn_login = ctk.CTkButton(self.container, text="Giriş Yap", width=250, height=40, font=("Inter", 14, "bold"), command=self.do_login)
        self.btn_login.pack(pady=5)
        
        self.btn_github = ctk.CTkButton(self.container, text="GitHub ile Giriş Yap", width=250, height=40, fg_color="#24292e", hover_color="#2f363d", font=("Inter", 14), command=self.do_github_login)
        self.btn_github.pack(pady=5)
        
        self.btn_register = ctk.CTkButton(self.container, text="Kayıt Ol", width=250, height=40, fg_color="#333333", hover_color="#444444", font=("Inter", 14), command=self.do_register)
        self.btn_register.pack(pady=5)
        
        self.btn_skip = ctk.CTkButton(self.container, text="Misafir Olarak Devam Et (Atla)", width=250, height=40, fg_color="transparent", hover_color="#333333", border_width=1, border_color="#555555", font=("Inter", 13), command=self.do_skip)
        self.btn_skip.pack(pady=(15, 5))
        
        # Check auto-login
        self.after(100, self.check_auto_login)

    def check_auto_login(self):
        config = load_config()
        saved_email = config.get("auto_email")
        saved_pwd_enc = config.get("auto_pwd")
        if saved_email and saved_pwd_enc:
            try:
                pwd = db.decrypt(saved_pwd_enc)
                self.entry_email.insert(0, saved_email)
                self.entry_password.insert(0, pwd)
                self._show_msg("Otomatik giriş yapılıyor...", "#81C995")
                self.do_login()
            except:
                pass

    def do_skip(self):
        self.destroy()
        self.on_success()

    def do_github_login(self):
        try:
            res = db.supabase.auth.sign_in_with_oauth({
                "provider": "github",
                "options": {
                    "redirect_to": "http://localhost:54321/callback"
                }
            })
            if res and hasattr(res, "url"):
                webbrowser.open(res.url)
                self._show_msg("Tarayıcıda GitHub girişi açıldı.", "#81C995")
        except Exception as e:
            self._show_msg(f"GitHub hatası: {str(e)}", "#F28B82")

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
                # Save credentials for auto-login
                config = load_config()
                config["auto_email"] = email
                config["auto_pwd"] = db.encrypt(pwd)
                save_config(config)
                
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
