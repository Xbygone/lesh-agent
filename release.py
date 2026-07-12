import os
import sys
import shutil
import subprocess
import requests
import re
import zipfile

def update_version_in_updater(new_version):
    updater_path = "updater.py"
    with open(updater_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # CURRENT_VERSION değerini güncelle
    content = re.sub(r'CURRENT_VERSION\s*=\s*"[^"]+"', f'CURRENT_VERSION = "{new_version}"', content)
    
    with open(updater_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] updater.py sürümü {new_version} olarak güncellendi.")

def run_build():
    print("[+] PyInstaller çalıştırılıyor...")
    subprocess.run(["python", "-m", "PyInstaller", "--onedir", "--noconsole", "-y", "--name", "lesh-agent", "main.py"], check=True)
    print("[+] Build tamamlandı.")

def create_zip():
    print("[+] dist/lesh-agent klasörü zipleniyor...")
    dist_dir = os.path.join("dist", "lesh-agent")
    zip_path = "lesh-agent.zip"
    
    if os.path.exists(zip_path):
        os.remove(zip_path)
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Sadece 'lesh-agent/...' olacak şekilde arşiv ismini ayarla
                arcname = os.path.relpath(file_path, "dist")
                zipf.write(file_path, arcname)
    print(f"[+] {zip_path} başarıyla oluşturuldu.")
    return zip_path

def create_github_release(token, version, zip_path):
    print(f"[+] GitHub'da v{version} sürümü oluşturuluyor...")
    repo = "Xbygone/lesh-agent"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Release Oluştur
    release_data = {
        "tag_name": f"v{version}",
        "target_commitish": "main",
        "name": f"v{version} Release",
        "body": f"Otomatik yayımlanan sürüm v{version}.",
        "draft": False,
        "prerelease": False
    }
    
    resp = requests.post(f"https://api.github.com/repos/{repo}/releases", json=release_data, headers=headers)
    if resp.status_code != 201:
        print("[-] Release oluşturulamadı:", resp.text)
        return
        
    release_info = resp.json()
    upload_url = release_info["upload_url"].split("{")[0]
    
    # 2. Asset'i (Zip) Yükle
    print(f"[+] {zip_path} GitHub'a yükleniyor... Bu işlem dosya boyutuna bağlı olarak 1-2 dakika sürebilir.")
    with open(zip_path, "rb") as f:
        upload_resp = requests.post(
            f"{upload_url}?name=lesh-agent.zip",
            headers={
                "Authorization": f"token {token}",
                "Content-Type": "application/zip",
                "Accept": "application/vnd.github.v3+json"
            },
            data=f
        )
        
    if upload_resp.status_code == 201:
        print(f"[+] Başarılı! v{version} yayınlandı. İndirme Linki: {release_info['html_url']}")
    else:
        print("[-] Dosya yüklenirken hata oluştu:", upload_resp.text)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python release.py <YENİ_SÜRÜM> <GITHUB_TOKEN>")
        sys.exit(1)
        
    new_version = sys.argv[1]
    token = sys.argv[2]
    
    update_version_in_updater(new_version)
    run_build()
    zip_file = create_zip()
    create_github_release(token, new_version, zip_file)
