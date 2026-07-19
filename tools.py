"""Agent tools: sandboxed file IO, web search and terminal execution.

All file operations are strictly confined to the selected workspace folder
(realpath + commonpath check — resistant to `..` tricks, sibling-prefix
folders like `workspace-evil`, and symlink escapes).
"""

import os
import json
import subprocess

MAX_TOOL_OUTPUT = 12000  # chars fed back to the model
COMMAND_TIMEOUT = 120    # seconds

# Commands that are never allowed to run, even with user approval.
BLOCKED_COMMAND_PATTERNS = (
    "rm -rf /", "rm -rf /*", "mkfs", ":(){", "format c:", "format c ",
    "del /f /s /q c:\\", "rd /s /q c:\\", "shutdown", "reg delete hklm",
)


def _safe_path(filepath, workspace_path):
    """Resolve filepath inside workspace. Returns (abs_path, error_or_None)."""
    if not workspace_path:
        return None, "Çalışma dizini seçilmemiş."
    filepath = (filepath or "").strip()
    if not filepath:
        return None, "Dosya yolu boş."
    ws_real = os.path.realpath(workspace_path)
    abs_path = os.path.realpath(os.path.join(ws_real, filepath))
    try:
        if os.path.commonpath([ws_real, abs_path]) != ws_real:
            return None, "Güvenlik İhlali: Çalışma dizini dışına çıkılamaz."
    except ValueError:
        # Different drives on Windows
        return None, "Güvenlik İhlali: Çalışma dizini dışına çıkılamaz."
    return abs_path, None


def _truncate(text, limit=MAX_TOOL_OUTPUT):
    if text and len(text) > limit:
        return text[:limit] + f"\n... (kırpıldı, toplam {len(text)} karakter)"
    return text


def read_file(filepath, workspace_path):
    abs_path, err = _safe_path(filepath, workspace_path)
    if err:
        return json.dumps({"error": err})
    if not os.path.isfile(abs_path):
        return json.dumps({"error": f"Dosya bulunamadı: {filepath}"})
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return json.dumps({"success": True, "content": _truncate(content, 60000)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def write_file(filepath, content, workspace_path):
    abs_path, err = _safe_path(filepath, workspace_path)
    if err:
        return json.dumps({"error": err})
    try:
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content if content is not None else "")
        return json.dumps({"success": True, "message": f"{filepath} başarıyla kaydedildi."})
    except Exception as e:
        return json.dumps({"error": str(e)})


def list_directory(filepath, workspace_path):
    abs_path, err = _safe_path(filepath or ".", workspace_path)
    if err:
        return json.dumps({"error": err})
    try:
        if not os.path.isdir(abs_path):
            return json.dumps({"error": "Klasör değil."})
        entries = []
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            entries.append(name + "/" if os.path.isdir(full) else name)
        return json.dumps({"success": True, "files": entries})
    except Exception as e:
        return json.dumps({"error": str(e)})


def search_web(query, max_results=3):
    """DuckDuckGo search. Import is lazy so a missing optional package
    doesn't prevent the whole app from starting."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return json.dumps({"error": "duckduckgo-search paketi kurulu değil (pip install duckduckgo-search)."})
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title"),
                    "href": r.get("href"),
                    "body": r.get("body"),
                })
        return json.dumps({"success": True, "results": results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Arama yapılamadı: {str(e)}"})


def fetch_url(url):
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return json.dumps({"error": "requests/beautifulsoup4 paketleri kurulu değil."})
    if not str(url).lower().startswith(("http://", "https://")):
        return json.dumps({"error": "Sadece http(s) adresleri desteklenir."})
    try:
        headers = {"User-Agent": "Mozilla/5.0 (LeshAgent)"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return json.dumps({"error": f"HTTP Hatası: {response.status_code}"})
        soup = BeautifulSoup(response.text, "html.parser")
        for s in soup(["script", "style", "nav", "footer", "header"]):
            s.decompose()
        text = " ".join(soup.stripped_strings)
        return json.dumps({"success": True, "content": _truncate(text, 5000)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def is_command_blocked(command: str) -> bool:
    lowered = " ".join((command or "").lower().split())
    return any(p in lowered for p in BLOCKED_COMMAND_PATTERNS)


def run_terminal_command(command, workspace_path, timeout=COMMAND_TIMEOUT):
    """Run a shell command inside the workspace with a hard timeout.
    NOTE: user approval is enforced by the agent layer before this is called."""
    if not workspace_path or not os.path.isdir(workspace_path):
        return json.dumps({"error": "Geçerli bir çalışma dizini yok."})
    if is_command_blocked(command):
        return json.dumps({"error": "Bu komut güvenlik nedeniyle engellendi."})
    try:
        result = subprocess.run(
            command,
            cwd=workspace_path,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return json.dumps({
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": _truncate(result.stdout),
            "stderr": _truncate(result.stderr, 4000),
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Komut zaman aşımına uğradı (>{timeout}s)."})
    except Exception as e:
        return json.dumps({"error": str(e)})
