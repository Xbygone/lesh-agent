import os
import sys
import json
import zipfile
import requests
import threading

CURRENT_VERSION = "1.0.0"
REPO_OWNER = "Xbygone"
REPO_NAME = "yerel-agent"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def check_for_updates(status_callback=None, complete_callback=None):
    """
    Arka planda çalışarak GitHub API üzerinden en son sürümü kontrol eder,
    varsa zip olarak indirip çıkartır ve update.bat'ı hazırlar.
    """
    def _run():
        try:
            if status_callback:
                status_callback("Sürüm kontrol ediliyor...")
                
            resp = requests.get(GITHUB_API_URL, timeout=10)
            if resp.status_code == 404:
                if status_callback: status_callback("Sisteminiz güncel! (Henüz sürüm yayımlanmamış)")
                if complete_callback: complete_callback(False)
                return
            elif resp.status_code != 200:
                if status_callback: status_callback("Sürüm kontrolü başarısız.")
                if complete_callback: complete_callback(False)
                return

            data = resp.json()
            latest_version = data.get("tag_name", "").lstrip("v")
            
            # Basit versiyon karşılaştırma (örn. 1.0.0 vs 1.0.1)
            def parse_v(v):
                return [int(x) for x in v.split(".") if x.isdigit()]
            
            if parse_v(latest_version) <= parse_v(CURRENT_VERSION):
                if status_callback: status_callback("Sisteminiz güncel!")
                if complete_callback: complete_callback(False)
                return

            if status_callback:
                status_callback(f"Yeni sürüm ({latest_version}) bulundu! İndiriliyor...")

            # .zip uzantılı asset'i bul
            assets = data.get("assets", [])
            download_url = None
            for asset in assets:
                if asset.get("name", "").endswith(".zip"):
                    download_url = asset.get("browser_download_url")
                    break

            if not download_url:
                if status_callback: status_callback("Zip arşivi bulunamadı!")
                if complete_callback: complete_callback(False)
                return

            # Zip'i indir
            zip_path = "yerel-agent.zip"
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if status_callback:
                status_callback("İndirme bitti. Ayıklanıyor...")

            # _temp_update_ klasörünü hazırla
            temp_dir = "_temp_update_"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            # Zip'i ayıkla
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            if status_callback:
                status_callback("Ayıklama tamamlandı. Güncelleme hazırlanıyor...")

            # update.bat oluştur
            bat_path = "update.bat"
            bat_content = f"""@echo off
echo Guncelleme uygulaniyor, lutfen bekleyin...
timeout /t 2 /nobreak >nul

:: Yeni dosyalari ana dizine kopyala
xcopy /s /e /y /q "{temp_dir}\\*" "."

:: Gecici klasoru ve zip dosyasini sil
rmdir /s /q "{temp_dir}"
del /q "{zip_path}"

:: Uygulamayi yeniden baslat
start main.exe

:: Bat dosyasinin kendini silmesi
(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)

            if status_callback:
                status_callback("Güncelleme hazır! Yeniden başlatılıyor...")
                
            if complete_callback:
                complete_callback(True)

        except Exception as e:
            if status_callback:
                status_callback(f"Güncelleme Hatası: {e}")
            if complete_callback:
                complete_callback(False)

    # Thread üzerinde çalıştır
    t = threading.Thread(target=_run, daemon=True)
    t.start()
