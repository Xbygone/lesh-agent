# Lesh - Local Agent Coder

Lesh, veri gizliliğini ve kontrolünü tamamen sana bırakarak temel olarak yerel donanımda çalışacak şekilde tasarlanmış gelişmiş ve otonom bir yapay zeka kodlama asistanıdır. Güçlü otomatik güncelleme mekanizması ve zarif Material Design 3 arayüzü ile Lesh, kodlama iş akışını hızlandırır ve sana özel yapay zeka destekli bir çalışma arkadaşı gibi davranır.

## Özellikler

- 🌍 **Çift Dil Desteği (EN / TR)**: Üst menüden İngilizce ve Türkçe arayüz arasında kolayca geçiş yapabilirsin.
- 💬 **Kalıcı Sohbet Oturumları**: Geçmiş sohbetlerin `.lesh/sessions/` dizinine otomatik kaydedilir. Sol paneli kullanarak geçmiş sohbetlerine kolayca erişebilir ve konuşmaya kaldığın yerden devam edebilirsin.
- ⚡ **Otomatik Güncelleme Sistemi**: Lesh, her açıldığında GitHub API üzerinden yeni bir sürüm olup olmadığını kontrol eder. Yeni sürüm varsa arka planda zip dosyasını indirir, eski dosyalarla değiştirir ve hiçbir manuel işleme gerek kalmadan uygulamanın güncel sürümle yeniden başlatılmasını sağlar.
- 🤖 **Çoklu Dil Modeli (LLM) Kapasitesi**:
  - **Yerel (Ollama)**: Gerçek gizlilik! `qwen2.5-coder`, `deepseek-r1` ve daha fazlasını destekler.
  - **Bulut (Cloud) Sağlayıcıları**: PAT veya API anahtarları kullanarak GitHub Models, Google AI Studio (Gemini) veya Groq Cloud'a bağlanabilirsin. `gpt-4o`, `gemini-2.0-flash` ve `llama-3.3-70b` gibi son teknoloji modelleri kullanabilirsin.
- 📁 **Çalışma Alanı Yönetimi (Workspace)**: Ajana bir proje klasörü bağladığında, ajan bu dosyaları okuyabilir, terminal komutları çalıştırabilir, kod yazıp test edebilir ve otonom olarak yaptığı değişiklikleri kendi başına git commit ve push edebilir.
- 📦 **Klasör Mimarisi (One-Dir)**: Tüm bağımlılıkların klasörde barındırıldığı bir sistemdir (`--onedir`). İçeriğin tamamen şeffaf, incelenebilir ve düzenlenebilir kalması için kaynak kodları kapalı bir `.exe`'ye sıkıştırmak yerine dışarıda bırakır.

## Hızlı Başlangıç

1. En son `yerel-agent.zip` (Lesh Agent) sürümünü [Releases](../../releases) sekmesinden indirin.
2. Klasörü bilgisayarınızda istediğiniz bir yere çıkarın.
3. `yerel-agent.exe`'yi çalıştırın.
4. Bir proje dizini bağlamak için **Çalışma Alanı Seç** düğmesine tıklayın.
5. (Opsiyonel) Bulut modelleri için API tokenlarınızı girin veya tamamen yerelde kalmak için `Yerel (Ollama)`'yı seçin.
6. Kodlamaya başlayın!

## Geliştirici Kurulumu

Python kodunu doğrudan çalıştırmak veya uygulamayı kendi bilgisayarınızda derlemek isterseniz:

```bash
git clone https://github.com/Xbygone/lesh-agent.git
cd lesh-agent
pip install -r requirements.txt
python main.py
```

### Otomatik Yayınlama (Auto-Release)

Yeni bir güncelleme (.exe) derlemek ve GitHub'a otomatik yollamak isterseniz:
```bash
python release.py 1.0.4 GITHUB_TOKEN
```

Bu otomasyon scripti uygulamanın içindeki sürüm numarasını arttırır, PyInstaller ile derler, klasörü zipler ve doğrudan GitHub Releases'e v1.0.4 etiketiyle yükler.

## Lisans

Açık Kaynak. Lesh Topluluğu tarafından 💙 ile geliştirilmiştir.
