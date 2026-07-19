"""Build + publish a Lesh Agent release.

Usage:
    python release.py <NEW_VERSION> [GITHUB_TOKEN]

The token is read from the GITHUB_TOKEN entry in .env when not passed as an
argument (preferred — tokens on the command line leak into shell history).
"""

import os
import sys
import re
import zipfile
import subprocess

import requests

# Windows Türkçe konsolda (cp1254) Unicode print hatalarını önle
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = "Xbygone/lesh-agent"


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip("\"'"))


def update_version_in_updater(new_version):
    with open("updater.py", "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'CURRENT_VERSION\s*=\s*"[^"]+"',
        f'CURRENT_VERSION = "{new_version}"',
        content,
    )
    with open("updater.py", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] updater.py sürümü {new_version} olarak güncellendi.")


def run_build():
    print("[+] PyInstaller çalıştırılıyor...")
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--onedir", "--windowed",
            "--name", "lesh-agent",
            "--icon", "assets/logo.ico",
            "main.py",
        ],
        check=True,
    )
    print("[+] Build tamamlandı.")


def create_zip():
    print("[+] dist/lesh-agent zipleniyor...")
    dist_dir = os.path.join("dist", "lesh-agent")
    zip_path = "lesh-agent.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, "dist"))
    print(f"[+] {zip_path} oluşturuldu.")
    return zip_path


def get_or_create_release(token, version):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    tag = f"v{version}"

    resp = requests.get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}", headers=headers)
    if resp.status_code == 200:
        print(f"[+] Mevcut release bulundu: {tag}")
        return resp.json(), headers

    body = f"Lesh Agent v{version}"
    notes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RELEASE_NOTES.md")
    if os.path.exists(notes_path):
        with open(notes_path, "r", encoding="utf-8") as f:
            body = f.read()

    release_data = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": f"v{version}",
        "body": body,
        "draft": False,
        "prerelease": False,
    }
    resp = requests.post(f"https://api.github.com/repos/{REPO}/releases", json=release_data, headers=headers)
    if resp.status_code != 201:
        print("[-] Release oluşturulamadı:", resp.text)
        sys.exit(1)
    return resp.json(), headers


def upload_asset(release_info, headers, zip_path):
    upload_url = release_info["upload_url"].split("{")[0]

    # Remove stale asset with the same name (allows re-runs)
    for asset in release_info.get("assets", []):
        if asset.get("name") == "lesh-agent.zip":
            requests.delete(
                f"https://api.github.com/repos/{REPO}/releases/assets/{asset['id']}",
                headers=headers,
            )
            print("[+] Eski zip asset silindi.")

    print(f"[+] {zip_path} yükleniyor (dosya boyutuna göre 1-2 dk sürebilir)...")
    with open(zip_path, "rb") as f:
        upload_headers = dict(headers)
        upload_headers["Content-Type"] = "application/zip"
        resp = requests.post(f"{upload_url}?name=lesh-agent.zip", headers=upload_headers, data=f)

    if resp.status_code == 201:
        print(f"[OK] Yayinlandi: {release_info['html_url']}")
    else:
        print("[-] Yükleme hatası:", resp.text)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python release.py <YENİ_SÜRÜM> [GITHUB_TOKEN]")
        sys.exit(1)

    new_version = sys.argv[1].lstrip("v")
    load_env()
    token = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN bulunamadı (.env dosyasına ekleyin veya argüman geçin).")
        sys.exit(1)

    update_version_in_updater(new_version)
    run_build()
    zip_file = create_zip()
    release, hdrs = get_or_create_release(token, new_version)
    upload_asset(release, hdrs, zip_file)
