# Lesh Agent v1.5.0 — Güvenlik ve Yeniden Yazım Sürümü

## 🛡️ Güvenlik (kritik)

- Kaynak koda gömülü tüm sırlar (Supabase URL/anahtarı, Fernet şifreleme anahtarı) kaldırıldı. Uygulama artık varsayılan olarak **%100 yerel** çalışır; API anahtarları makineye özel üretilen bir anahtarla şifrelenip `~/.lesh/` altında saklanır.
- Kullanıcı şifresi artık **asla diske yazılmıyor**; otomatik giriş Supabase refresh token ile yapılıyor.
- Path traversal açığı kapatıldı (`startswith` yerine `realpath` + `commonpath`; kardeş-önek klasör ve symlink kaçışları engellendi).
- Ajanın çalıştırmak istediği **her terminal komutu artık onay penceresinden geçiyor** (isteğe bağlı otomatik onay anahtarı ile). Açıkça yıkıcı komutlar her durumda engelli.
- Terminal komutlarına zaman aşımı ve çıktı sınırı eklendi.
- Git geçmişi sızmış anahtarlardan tamamen temizlendi.

## 🐛 Hata Düzeltmeleri

- Uygulamanın hiç açılmamasına yol açan eksik bağımlılıklar (`duckduckgo-search`, `beautifulsoup4`) requirements.txt'ye eklendi.
- Paketlenmiş exe'nin açılışta kendini yeniden başlatmasına yol açan pip özyineleme hatası giderildi.
- Kaynaktan çalıştırırken otomatik güncelleyicinin git çalışma ağacının üzerine yazma riski kaldırıldı (otomatik güncelleme artık sadece exe'de).
- Her tuş vuruşunda Supabase'e istek atılması (UI donması) giderildi; anahtar kaydı artık odak kaybında yapılıyor.
- "Yazılım Ofisi" modunun sohbet geçmişini silmesi düzeltildi.
- GitHub Models eski (kapatılan) endpoint'ten yenisine taşındı: `models.github.ai/inference` + yayıncı önekli model ID'leri.
- Var olmayan `diff_textbox` referansı, grid çakışmaları ve durum etiketinin model kartına binmesi düzeltildi.
- Ollama model adları düzeltildi (ör. `phi4-mini`), model katalogları güncellendi (Gemini 2.5, Groq güncel modelleri).
- Commit & Push artık her zaman GitHub PAT'ını kullanıyor (seçili sağlayıcının anahtarını değil).

## ✨ Yeni Arayüz

- Arayüz sıfırdan yazıldı: çakışmasız responsive yerleşim, Diff/Log sekmeli denetim paneli, renklendirilmiş git diff (+/-), durum göstergeleri.
- Ajan çalışırken **Durdur** butonu, tek tıkla **Yeni Sohbet**, Enter/Shift+Enter desteği.
- Komut onay penceresi ve "Komutları otomatik onayla" anahtarı.
- Sohbet akışında Sen/Ajan rozetleri, düşünme (`<think>`) vurgusu, araç çağrısı vurguları.

## ⚠️ Yükseltme Notları

- Eski sürümlerin kaydettiği şifreli API anahtarları (sızmış ortak anahtarla şifrelenmişti) geçersizdir; anahtarlarınızı bir kez yeniden girin.
- Supabase bulut senkronizasyonu isteğe bağlıdır; kendi örneğinizi `.env` ile bağlayabilirsiniz (`.env.example`'a bakın).
