import os
import sys
import json
import zipfile
import requests
import threading

CURRENT_VERSION = "1.1.2"
REPO_OWNER = "Xbygone"
REPO_NAME = "lesh-agent"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

def check_for_updates(status_callback=None, complete_callback=None):
    """
    Arka planda çalışarak GitHub API üzerinden en son sürümü kontrol eder,
    varsa zip olarak indirip çıkartır ve update.bat'ı hazırlar.
    """
    def _run():
        try:
            if status_callback:
                status_callback("Checking for updates...")
                
            resp = requests.get(GITHUB_API_URL, timeout=10)
            if resp.status_code == 404:
                if status_callback: status_callback("System is up to date!")
                if complete_callback: complete_callback(False)
                return
            elif resp.status_code != 200:
                if status_callback: status_callback("Update check failed.")
                if complete_callback: complete_callback(False)
                return

            data = resp.json()
            latest_version = data.get("tag_name", "").lstrip("v")
            
            def parse_v(v):
                return [int(x) for x in v.split(".") if x.isdigit()]
            
            if parse_v(latest_version) <= parse_v(CURRENT_VERSION):
                if status_callback: status_callback("System is up to date!")
                if complete_callback: complete_callback(False)
                return

            if status_callback:
                status_callback(f"New version ({latest_version}) found! Downloading...")

            assets = data.get("assets", [])
            download_url = None
            for asset in assets:
                if asset.get("name", "").endswith(".zip"):
                    download_url = asset.get("browser_download_url")
                    break

            if not download_url:
                if status_callback: status_callback("Zip archive not found!")
                if complete_callback: complete_callback(False)
                return

            zip_path = "lesh-agent.zip"
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if status_callback:
                status_callback("Download complete. Extracting...")

            temp_dir = "_temp_update_"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            if status_callback:
                status_callback("Extraction complete. Preparing update...")

            extracted_items = os.listdir(temp_dir)
            source_dir = temp_dir
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                source_dir = os.path.join(temp_dir, extracted_items[0])

            bat_path = "update.bat"
            bat_content = f"""@echo off
echo Applying update, please wait...
timeout /t 2 /nobreak >nul

xcopy /s /e /y /q "{source_dir}\\*" "."

rmdir /s /q "{temp_dir}"
del /q "{zip_path}"

start lesh-agent.exe

(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)

            if status_callback:
                status_callback("Update ready! Restarting...")
                
            if complete_callback:
                complete_callback(True)

        except Exception as e:
            if status_callback:
                status_callback(f"Update Error: {e}")
            if complete_callback:
                complete_callback(False)

    # Thread üzerinde çalıştır
    t = threading.Thread(target=_run, daemon=True)
    t.start()
