# Yerel Ajan (Autonomous Coding Agent)

Tamamen yerel (Ollama) ve bulut tabanlı (GitHub Models) API'leri bir arada kullanarak yazılım geliştirme süreçlerinizi otomatize eden otonom bir kodlama asistanıdır. Dark Mode destekli şık bir arayüze sahiptir ve projelerinizdeki değişiklikleri otonom şekilde oluşturup Git üzerinden commit ve push yapabilir.

## 🚀 Özellikler

- **Çift Sağlayıcı Desteği:** İster tamamen ücretsiz ve yerel olan Ollama (ör: `qwen2.5-coder:7b`) modellerini, isterseniz GitHub Models üzerinden güçlü bulut modellerini (`deepseek-r1`, `gpt-4.1`, `codestral`) kullanın.
- **Otonom Dosya Yönetimi:** Agent, yazdığınız koda göre dosyaları doğrudan oluşturur, düzenler. Sadece bir metin botu değildir.
- **Güvenli Kimlik Doğrulama:** Tek bir "GitHub PAT" ile hem GitHub Models API'sine erişebilir hem de oluşturulan kodları şifre girmeden otomatik olarak GitHub'a pushlayabilirsiniz.
- **Performanslı Arayüz:** Arka plan işlemleri worker thread'ler ile yönetildiğinden uygulama asla donmaz (Not Responding hatası vermez).
- **Akıllı Bağlam (Context) Yönetimi:** Dosya ağacından tıkladığınız dosyalar anında ajanın hafızasına eklenir. Böylece gereksiz token tüketimi önlenir.
- **Gelişmiş Görsellik:** `<think>` (muhakeme) blokları metinlerden görsel olarak ayrılarak okunabilirliği artırır.
- **Güvenilir Git Yönetimi:** Git komutları zaman aşımlarına (timeout) karşı korunur ve tam hata yakalama mekanizmasına sahiptir.

## 📦 Kurulum

1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/KULLANICI_ADINIZ/yerel-agent.git
   cd yerel-agent
   ```

2. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

3. (Opsiyonel) Yerel modelleri kullanmak için [Ollama](https://ollama.com/) kurun ve çalıştırın.

4. Uygulamayı başlatın:
   ```bash
   python main.py
   ```

## ⚙️ GitHub PAT (Personal Access Token) Kurulumu

Uygulama üzerinden GitHub Models (Bulut) modellerini kullanmak veya Git push işlemlerini otomatikleştirmek için GitHub PAT oluşturmalısınız:

1. GitHub'da `Settings` > `Developer settings` > `Personal access tokens` > `Tokens (classic)` bölümüne gidin.
2. `Generate new token`'a tıklayın.
3. Kapsam (Scope) olarak hem `repo` (kod pushlayabilmesi için) hem de GitHub Models izinlerini verin.
4. Oluşturulan token'ı kopyalayın ve `Yerel Ajan` arayüzünün sol panelindeki **GitHub PAT Token** giriş alanına yapıştırın.

## 🛠️ Proje Mimarisi

- `main.py`: Ana uygulama döngüsü, UI bileşenlerini ve agent durumlarını birbirine bağlar.
- `ui.py`: `customtkinter` tabanlı, 3 panelli ve Dark Theme destekli arayüz tasarımı.
- `agent_engine.py`: Ollama ve GitHub Models ile iletişim kuran, otonom kararlar veren araç motoru (Engine).
- `git_manager.py`: Güvenli Git operasyonları, diff okuma ve PAT-tabanlı push sistemi.
- `tools.py`: Agent'in kullandığı temel yetenekler (okuma, yazma, terminal komutu vb.).

## 📜 Lisans

Bu proje açık kaynak olup [MIT Lisansı](LICENSE) altında dağıtılmaktadır.
