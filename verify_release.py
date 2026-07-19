"""Verify the GitHub release state (ASCII-only output, safe on any console)."""

import os
import re
import sys

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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


def current_version_tag():
    """Default tag = CURRENT_VERSION from updater.py."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "updater.py")
        with open(path, "r", encoding="utf-8") as f:
            m = re.search(r'CURRENT_VERSION\s*=\s*"([^"]+)"', f.read())
        if m:
            return "v" + m.group(1)
    except OSError:
        pass
    return "v1.5.1"


def main():
    load_env()
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    tag = sys.argv[1] if len(sys.argv) > 1 else current_version_tag()

    r = requests.get(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}", headers=headers, timeout=15)
    print(f"[release/{tag}] HTTP {r.status_code}")
    if r.status_code == 200:
        rel = r.json()
        print(f"  name     : {rel.get('name')}")
        print(f"  url      : {rel.get('html_url')}")
        print(f"  draft    : {rel.get('draft')}  prerelease: {rel.get('prerelease')}")
        assets = rel.get("assets", [])
        print(f"  assets   : {len(assets)}")
        for a in assets:
            print(f"    - {a.get('name')}  {a.get('size'):,} bytes  state={a.get('state')}  downloads={a.get('download_count')}")
    else:
        print("  RELEASE NOT FOUND!")

    r2 = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", headers=headers, timeout=15)
    if r2.status_code == 200:
        print(f"[latest] {r2.json().get('tag_name')}")

    r3 = requests.get(f"https://api.github.com/repos/{REPO}/branches/main", headers=headers, timeout=15)
    if r3.status_code == 200:
        print(f"[remote main] {r3.json()['commit']['sha'][:9]}")


if __name__ == "__main__":
    main()
