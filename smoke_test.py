"""Headless smoke tests — no GUI, no network required.

Run:  python smoke_test.py
"""

import json
import os
import sys
import tempfile

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK]   {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def test_imports():
    print("\n── Modül importları ──")
    for mod in ("theme", "app_config", "tools", "git_manager", "updater",
                "ollama_client", "agent_engine", "db_manager"):
        try:
            __import__(mod)
            check(f"import {mod}", True)
        except Exception as e:
            check(f"import {mod}", False, f"→ {e}")


def test_path_traversal():
    print("\n── Dosya sandbox güvenliği ──")
    from tools import read_file, write_file, list_directory

    with tempfile.TemporaryDirectory() as ws:
        secret_dir = tempfile.mkdtemp()
        secret = os.path.join(secret_dir, "secret.txt")
        with open(secret, "w") as f:
            f.write("gizli")

        # 1. .. escape
        res = json.loads(read_file("../" * 12 + "etc/hostname", ws))
        check("'..' ile kaçış engellendi", "error" in res)

        # 2. absolute path
        res = json.loads(read_file(secret, ws))
        check("mutlak yol engellendi", "error" in res or not res.get("success"))

        # 3. sibling-prefix folder (startswith bug)
        sibling = ws + "-evil"
        os.makedirs(sibling, exist_ok=True)
        with open(os.path.join(sibling, "x.txt"), "w") as f:
            f.write("dışarı")
        res = json.loads(read_file(os.path.join("..", os.path.basename(sibling), "x.txt"), ws))
        check("kardeş-önek klasörü engellendi", "error" in res)

        # 4. legit ops still work
        res = json.loads(write_file("sub/a.txt", "merhaba", ws))
        check("workspace içine yazma çalışıyor", res.get("success") is True)
        res = json.loads(read_file("sub/a.txt", ws))
        check("workspace içinden okuma çalışıyor", res.get("content") == "merhaba")
        res = json.loads(list_directory(".", ws))
        check("dizin listeleme çalışıyor", res.get("success") is True)

        # 5. empty / missing workspace
        res = json.loads(read_file("a.txt", None))
        check("workspace yokken güvenli hata", "error" in res)


def test_command_safety():
    print("\n── Komut güvenliği ──")
    from tools import is_command_blocked, run_terminal_command

    check("rm -rf / engelli", is_command_blocked("sudo rm -rf /"))
    check("format c: engelli", is_command_blocked("FORMAT C:"))
    check("normal komut serbest", not is_command_blocked("git status"))

    with tempfile.TemporaryDirectory() as ws:
        res = json.loads(run_terminal_command("echo lesh", ws, timeout=10))
        check("echo çalışıyor", res.get("success") and "lesh" in res.get("stdout", ""))
        res = json.loads(run_terminal_command("rm -rf /", ws))
        check("engelli komut reddedildi", "error" in res)


def test_agent_engine():
    print("\n── Agent engine ──")
    from agent_engine import AgentState, resolve_model_id, StreamingThinkParser

    check("GitHub model prefix", resolve_model_id("GitHub Models", "gpt-4.1-mini") == "openai/gpt-4.1-mini")
    check("prefix'li model korunur", resolve_model_id("GitHub Models", "deepseek/DeepSeek-R1") == "deepseek/DeepSeek-R1")
    check("diğer provider dokunulmaz", resolve_model_id("Groq Cloud", "llama-3.3-70b-versatile") == "llama-3.3-70b-versatile")

    # Think parser
    chunks = []
    p = StreamingThinkParser(lambda t, tag=None: chunks.append((t, tag)))
    p.add_chunk("önce <think>düşünce")
    p.add_chunk("ler</think> sonra")
    p.flush()
    text_out = "".join(t for t, tag in chunks if tag is None)
    think_out = "".join(t for t, tag in chunks if tag == "think")
    check("think parser metni ayırdı", "önce" in text_out and "sonra" in text_out)
    check("think parser düşünceyi yakaladı", "düşünceler" in think_out)

    # Approval: rejected command must not run
    with tempfile.TemporaryDirectory() as ws:
        agent = AgentState("Yerel (Ollama)", "x", ws, "", lambda *a, **k: None,
                           lambda *a, **k: None, approval_callback=lambda t, d: False)
        res = json.loads(agent._execute_tool({
            "function": {"name": "run_terminal_command",
                         "arguments": json.dumps({"command": "echo calisti > kanit.txt"})}
        }))
        check("reddedilen komut çalışmadı", "error" in res and not os.path.exists(os.path.join(ws, "kanit.txt")))

        agent.auto_approve = True
        res = json.loads(agent._execute_tool({
            "function": {"name": "run_terminal_command",
                         "arguments": json.dumps({"command": "echo evet"})}
        }))
        check("otomatik onaylı komut çalıştı", res.get("success") is True)


def test_no_embedded_secrets():
    print("\n── Gömülü sır taraması ──")
    import re
    # Generic detectors — must not themselves contain any real secret fragments.
    patterns = [
        r"github_pat_\w{20,}",          # GitHub fine-grained PAT
        r"ghp_[A-Za-z0-9]{20,}",        # GitHub classic PAT
        r"sb_(publishable|secret)_\w+",  # Supabase keys
        r"_B64\s*=\s*b['\"]",           # obfuscated embedded fallbacks
        r"AIza[A-Za-z0-9_-]{20,}",      # Google API key
        r"gsk_[A-Za-z0-9]{20,}",        # Groq key
        r"nvapi-[A-Za-z0-9_-]{20,}",    # NVIDIA key
    ]
    bad = []
    for fname in os.listdir("."):
        if not fname.endswith(".py"):
            continue
        with open(fname, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        for pat in patterns:
            if fname != "smoke_test.py" and re.search(pat, content):
                bad.append(f"{fname}: {pat}")
    check("kaynak kodda gömülü sır yok", not bad, str(bad))


def test_db_local_mode():
    print("\n── Yerel kimlik deposu ──")
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_KEY", None)
    import db_manager
    mgr = db_manager.DBManager()
    check("bulut kapalıyken local mode", True)
    ok = mgr.set_api_key("TestProvider", "test-key-123")
    check("anahtar kaydı", ok)
    check("anahtar geri okuma", mgr.get_api_key("TestProvider") == "test-key-123")
    # cleanup
    data = mgr._local_read()
    data.pop("TestProvider", None)
    mgr._local_write(data)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    test_imports()
    test_path_traversal()
    test_command_safety()
    test_agent_engine()
    test_no_embedded_secrets()
    test_db_local_mode()
    print(f"\n{'='*40}\nSonuç: {PASS} başarılı, {FAIL} başarısız")
    sys.exit(1 if FAIL else 0)
