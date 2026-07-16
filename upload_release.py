import requests
import json
import os

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip().strip('"\'')

load_env()
token = os.environ.get("GITHUB_TOKEN", "")
if not token:
    print("GITHUB_TOKEN bulunamadı. Lütfen .env dosyasını kontrol edin.")
    exit(1)
repo = "Xbygone/lesh-agent"
tag = "v1.4.3"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

# Just fetch existing release and upload zip
resp = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}", headers=headers)
    
if resp.status_code not in [200, 201]:
    print(f"Error fetching release: {resp.status_code} - {resp.text}")
    exit(1)

release_id = resp.json()["id"]
upload_url = resp.json()["upload_url"].split("{")[0]
print(f"Release ID: {release_id}, Upload URL: {upload_url}")

# 2. Upload Asset
asset_path = r"dist\lesh-agent.zip"
print("Uploading zip asset...")
with open(asset_path, "rb") as f:
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "application/zip"
    upload_resp = requests.post(
        f"{upload_url}?name=lesh-agent.zip",
        headers=upload_headers,
        data=f
    )

if upload_resp.status_code in [201, 200]:
    print("Zip asset uploaded successfully!")
else:
    print(f"Error uploading zip asset: {upload_resp.status_code} - {upload_resp.text}")
