# Autonomous Coding Agent

Yerel Ollama modelleri ile (tamamen offline ve güvenli) çalışan, Aider benzeri otonom bir kodlama asistanı. "Antigravity" tarzı profesyonel bir karanlık tema arayüzü sunar. 

## Özellikler

- **Akıllı Yönlendirme (Router):** Küçük modeller (örn. qwen:3.5b) ile hızlı değerlendirme yapar, kodlama gerektiğinde görevi büyük modele (örn. qwen2.5-coder:7b) devreder.
- **Otonom Döngü:** Ajan dosya okuyabilir, dosya yazabilir, internette arama yapabilir ve kodunuzdaki sorunları otomatik olarak çözer.
- **Git Entegrasyonu:** Kod değişikliklerinizi anında diff olarak görür ve tek tuşla GitHub'a commit & push yapabilirsiniz.
- **Model Yönetimi:** Arayüz üzerinden yeni modeller indirebilir (pull) ve aktif modelleri seçebilirsiniz.
- **Performans:** Akıcı UI, arka plan (thread) işlemleri ve streaming (anlık akış) desteği.

## Gereksinimler

1. Sisteminizde [Ollama](https://ollama.com/) kurulu olmalıdır.
2. Python 3.9 veya üzeri bir sürüm.

## Kurulum Adımları

**1. Depoyu klonlayın ve klasöre girin:**
```bash
git clone https://github.com/KULLANICI_ADINIZ/autonomous-coding-agent.git
cd autonomous-coding-agent
```

**2. Sanal ortam (Virtual Environment) oluşturun ve aktif edin:**
```bash
# Windows için
python -m venv venv
venv\Scripts\activate

# macOS/Linux için
python3 -m venv venv
source venv/bin/activate
```

**3. Gerekli kütüphaneleri yükleyin:**
```bash
pip install -r requirements.txt
```

**4. Ollama'nın çalıştığından emin olun ve varsayılan modelleri indirin (Opsiyonel, arayüzden de indirebilirsiniz):**
```bash
# Hızlı yönlendirme modeli (Örnek)
ollama run qwen:3.5b

# Kodlama modeli
ollama run qwen2.5-coder:7b
```

**5. Uygulamayı başlatın:**
```bash
python main.py
```

## Kullanım

1. **Uygulama Açılışı:** Sol üstteki "Klasör Seç" butonu ile üzerinde çalışmak istediğiniz Git projesini seçin.
2. **Model Seçimi:** Sol alttaki panelden Yönlendirici (Router) ve Kodlayıcı (Coder) modellerinizi seçin. Modeliniz yoksa "Model İndir" diyerek indirebilirsiniz.
3. **Sohbet:** Ortadaki panele talimatlarınızı yazın (Örn: `main.py dosyasındaki bug'ı düzelt` veya `Ağdaki paketleri çeken bir script yaz`).
4. **Onaylama:** Sağ panelde ajan tarafından önerilen değişikliklerin Diff (fark) özetini inceleyin ve "Commit & Push" butonuna basarak GitHub'a gönderin.
