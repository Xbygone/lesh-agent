"""Small persistent app config (workspace path, session token, ui prefs)."""

import os
import json

_OLD_CONFIG = os.path.expanduser("~/.yerel_agent_config.json")
CONFIG_FILE = os.path.expanduser("~/.lesh/config.json")


def load_config() -> dict:
    for path in (CONFIG_FILE, _OLD_CONFIG):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                # Migration: never keep stored passwords around (legacy versions
                # of the app wrote them; that was a security bug).
                if "auto_pwd" in cfg or "auto_email" in cfg:
                    cfg.pop("auto_pwd", None)
                    cfg.pop("auto_email", None)
                    save_config(cfg)
                return cfg
            except (OSError, ValueError):
                continue
    return {}


def save_config(cfg: dict):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except OSError:
        pass


def update_config(**kwargs):
    cfg = load_config()
    cfg.update(kwargs)
    save_config(cfg)
    return cfg
