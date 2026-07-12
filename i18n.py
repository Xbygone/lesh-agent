import json
import os

CONFIG_FILE = os.path.expanduser("~/.yerel_agent_config.json")

def load_lang_preference():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("language", "en")
        except:
            return "en"
    return "en"

def save_lang_preference(lang):
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except:
            pass
    config["language"] = lang
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
    except:
        pass

CURRENT_LANG = load_lang_preference()

def set_lang(lang):
    global CURRENT_LANG
    CURRENT_LANG = lang
    save_lang_preference(lang)

TEXTS = {
    "en": {
        "title": "Lesh - Local Agent Coder",
        "header": "✦ Lesh Agent",
        "api_key": "API Key / Token",
        "api_key_placeholder": "Enter token...",
        "select_workspace": "✚  Select Workspace",
        "files_tab": "FILES",
        "chats_tab": "CHATS",
        "provider": "Provider",
        "model": "Model",
        "status_ready": "● Ready",
        "btn_update": "🔄 Check for Updates",
        "chat_send": "Send",
        "git_diff": "GIT CHANGES",
        "agent_log": "AGENT TERMINAL LOG",
        "commit_placeholder": "Commit message...",
        "btn_push": "✅  Commit & Push",
        "err_no_workspace": "\n[ERROR] Select a workspace first.\n",
        "err_no_token": "\n[ERROR] You must enter an API Key / Token to use {provider}!\n",
        "sys_you": "━━━ You ━━━",
        "sys_history_loaded": "\n[SYSTEM] Previous chat history loaded.\n",
        "sys_checking_updates": "Checking...",
        "sys_restarting": "Restarting...",
        "no_changes": "No changes.",
        "pushing": "Pushing...",
        "status_err": "❌ Error",
        "new_chat": "✚ New Chat",
        "ollama_checking": "● Checking Ollama...",
        "ollama_not_found": "● Ollama not found - please start it",
        "models_checking": "● Checking models...",
        "ollama_active": "● Ollama: Active"
    },
    "tr": {
        "title": "Lesh - Local Agent Coder",
        "header": "✦ Lesh Ajan",
        "api_key": "API Key / Token",
        "api_key_placeholder": "Token girin...",
        "select_workspace": "✚  Çalışma Alanı Seç",
        "files_tab": "DOSYALAR",
        "chats_tab": "SOHBETLER",
        "provider": "Sağlayıcı (Provider)",
        "model": "Model",
        "status_ready": "● Hazır",
        "btn_update": "🔄 Güncellemeleri Kontrol Et",
        "chat_send": "Gönder",
        "git_diff": "GİT DEĞİŞİKLİKLERİ",
        "agent_log": "AJAN TERMİNAL LOGU",
        "commit_placeholder": "Commit mesajı...",
        "btn_push": "✅  Commit & Push",
        "err_no_workspace": "\n[HATA] Önce bir çalışma alanı seçin.\n",
        "err_no_token": "\n[HATA] {provider} kullanmak için sol panele API Key / Token girmelisiniz!\n",
        "sys_you": "━━━ Siz ━━━",
        "sys_history_loaded": "\n[SİSTEM] Önceki sohbet geçmişi yüklendi.\n",
        "sys_checking_updates": "Kontrol ediliyor...",
        "sys_restarting": "Yeniden başlatılıyor...",
        "no_changes": "Değişiklik yok.",
        "pushing": "Gönderiliyor...",
        "status_err": "❌ Hata",
        "new_chat": "✚ Yeni Sohbet",
        "ollama_checking": "● Ollama kontrol ediliyor...",
        "ollama_not_found": "● Ollama bulunamadı - lütfen başlatın",
        "models_checking": "● Modeller kontrol ediliyor...",
        "ollama_active": "● Ollama: Aktif"
    }
}

def t(key, **kwargs):
    text = TEXTS.get(CURRENT_LANG, TEXTS["en"]).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
