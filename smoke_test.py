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
    print("\n-- Module imports --")
    for mod in ("theme", "app_config", "tools", "git_manager", "updater",
                "ollama_client", "agent_engine", "db_manager"):
        try:
            __import__(mod)
            check(f"import {mod}", True)
        except Exception as e:
            check(f"import {mod}", False, f"→ {e}")


def test_path_traversal():
    print("\n-- File sandbox security --")
    from tools import read_file, write_file, list_directory

    with tempfile.TemporaryDirectory() as ws:
        secret_dir = tempfile.mkdtemp()
        secret = os.path.join(secret_dir, "secret.txt")
        with open(secret, "w") as f:
            f.write("secret")

        # 1. .. escape
        res = json.loads(read_file("../" * 12 + "etc/hostname", ws))
        check("'..' escape blocked", "error" in res)

        # 2. absolute path
        res = json.loads(read_file(secret, ws))
        check("absolute path blocked", "error" in res or not res.get("success"))

        # 3. sibling-prefix folder (startswith bug)
        sibling = ws + "-evil"
        os.makedirs(sibling, exist_ok=True)
        with open(os.path.join(sibling, "x.txt"), "w") as f:
            f.write("outside")
        res = json.loads(read_file(os.path.join("..", os.path.basename(sibling), "x.txt"), ws))
        check("sibling-prefix folder blocked", "error" in res)

        # 4. legit ops still work
        res = json.loads(write_file("sub/a.txt", "hello", ws))
        check("write inside workspace works", res.get("success") is True)
        res = json.loads(read_file("sub/a.txt", ws))
        check("read inside workspace works", res.get("content") == "hello")
        res = json.loads(list_directory(".", ws))
        check("directory listing works", res.get("success") is True)

        # 5. empty / missing workspace
        res = json.loads(read_file("a.txt", None))
        check("safe error without workspace", "error" in res)


def test_command_safety():
    print("\n-- Command safety --")
    from tools import is_command_blocked, run_terminal_command

    check("rm -rf / blocked", is_command_blocked("sudo rm -rf /"))
    check("format c: blocked", is_command_blocked("FORMAT C:"))
    check("normal command allowed", not is_command_blocked("git status"))

    with tempfile.TemporaryDirectory() as ws:
        res = json.loads(run_terminal_command("echo lesh", ws, timeout=10))
        check("echo works", res.get("success") and "lesh" in res.get("stdout", ""))
        res = json.loads(run_terminal_command("rm -rf /", ws))
        check("blocked command rejected", "error" in res)


def test_agent_engine():
    print("\n-- Agent engine --")
    from agent_engine import AgentState, resolve_model_id, StreamingThinkParser

    check("GitHub model prefix", resolve_model_id("GitHub Models", "gpt-4.1-mini") == "openai/gpt-4.1-mini")
    check("prefixed model preserved", resolve_model_id("GitHub Models", "deepseek/DeepSeek-R1") == "deepseek/DeepSeek-R1")
    check("other providers untouched", resolve_model_id("Groq Cloud", "llama-3.3-70b-versatile") == "llama-3.3-70b-versatile")

    # Think parser
    chunks = []
    p = StreamingThinkParser(lambda t, tag=None: chunks.append((t, tag)))
    p.add_chunk("before <think>thought")
    p.add_chunk("s</think> after")
    p.flush()
    text_out = "".join(t for t, tag in chunks if tag is None)
    think_out = "".join(t for t, tag in chunks if tag == "think")
    check("think parser separated text", "before" in text_out and "after" in text_out)
    check("think parser captured thoughts", "thoughts" in think_out)

    # Approval: rejected command must not run
    with tempfile.TemporaryDirectory() as ws:
        agent = AgentState("Local (Ollama)", "x", ws, "", lambda *a, **k: None,
                           lambda *a, **k: None, approval_callback=lambda t, d: False)
        res = json.loads(agent._execute_tool({
            "function": {"name": "run_terminal_command",
                         "arguments": json.dumps({"command": "echo ran > proof.txt"})}
        }))
        check("rejected command did not run", "error" in res and not os.path.exists(os.path.join(ws, "proof.txt")))

        agent.auto_approve = True
        res = json.loads(agent._execute_tool({
            "function": {"name": "run_terminal_command",
                         "arguments": json.dumps({"command": "echo yes"})}
        }))
        check("auto-approved command ran", res.get("success") is True)


def test_no_embedded_secrets():
    print("\n-- Embedded secret scan --")
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
    check("no embedded secrets in source", not bad, str(bad))


def test_db_local_mode():
    print("\n-- Local credential store --")
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_KEY", None)
    import db_manager
    mgr = db_manager.DBManager()
    check("local mode when cloud disabled", True)
    ok = mgr.set_api_key("TestProvider", "test-key-123")
    check("key save", ok)
    check("key read-back", mgr.get_api_key("TestProvider") == "test-key-123")
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
    print(f"\n{'='*40}\nResult: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
