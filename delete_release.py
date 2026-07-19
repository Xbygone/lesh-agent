"""Delete a GitHub release (and its remote tag) by tag name.

Usage:  python delete_release.py v1.5.0
"""

import os
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_release.py <tag>")
        sys.exit(1)
    tag = sys.argv[1]

    load_env()
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN not found in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Find the release by tag (includes drafts, which tag-based lookup misses)
    release_id = None
    resp = requests.get(f"https://api.github.com/repos/{REPO}/releases?per_page=100", headers=headers, timeout=15)
    if resp.status_code == 200:
        for rel in resp.json():
            if rel.get("tag_name") == tag:
                release_id = rel["id"]
                break

    if release_id:
        d = requests.delete(f"https://api.github.com/repos/{REPO}/releases/{release_id}", headers=headers, timeout=15)
        print(f"[delete release {tag}] HTTP {d.status_code}" + (" OK" if d.status_code == 204 else f" {d.text[:200]}"))
    else:
        print(f"[delete release {tag}] not found (already gone)")

    # Delete the remote tag ref too (ignore 422 if it does not exist)
    t = requests.delete(f"https://api.github.com/repos/{REPO}/git/refs/tags/{tag}", headers=headers, timeout=15)
    print(f"[delete tag {tag}] HTTP {t.status_code}" + (" OK" if t.status_code == 204 else " (may not exist)"))


if __name__ == "__main__":
    main()
