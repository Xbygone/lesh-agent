"""
Credential / key management for Lesh Agent.

Two modes:
  - CLOUD mode: if SUPABASE_URL + SUPABASE_KEY are provided via environment/.env,
    API keys are stored encrypted in Supabase (per-user, protected by RLS).
  - LOCAL mode (default): no cloud connection at all. API keys are stored in
    ~/.lesh/credentials.json, encrypted with a per-machine key generated on
    first run (never shipped with the app, never committed to git).

SECURITY: No secrets are embedded in this file. Do not add fallback keys here.
"""

import os
import json
import stat
from cryptography.fernet import Fernet

LESH_DIR = os.path.expanduser("~/.lesh")
LOCAL_KEYFILE = os.path.join(LESH_DIR, ".keyfile")
LOCAL_CREDS = os.path.join(LESH_DIR, "credentials.json")


def load_env():
    """Load .env sitting next to the application (dev mode only)."""
    base = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base, ".env")
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip("\"'"))
    except OSError:
        pass


load_env()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CLOUD_ENABLED = bool(SUPABASE_URL and SUPABASE_KEY)


def _ensure_lesh_dir():
    os.makedirs(LESH_DIR, exist_ok=True)


def _restrict_permissions(path):
    """Best effort chmod 600 (no-op meaningful on POSIX, harmless on Windows)."""
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _get_machine_key() -> bytes:
    """Per-machine encryption key. Generated on first run, kept out of git."""
    env_key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key.encode()
    _ensure_lesh_dir()
    if os.path.exists(LOCAL_KEYFILE):
        try:
            with open(LOCAL_KEYFILE, "rb") as f:
                key = f.read().strip()
            if key:
                return key
        except OSError:
            pass
    key = Fernet.generate_key()
    with open(LOCAL_KEYFILE, "wb") as f:
        f.write(key)
    _restrict_permissions(LOCAL_KEYFILE)
    return key


class DBManager:
    def __init__(self):
        self.user = None
        self.session = None
        self.supabase = None
        self.cloud_enabled = CLOUD_ENABLED
        self._cipher = Fernet(_get_machine_key())

        if self.cloud_enabled:
            try:
                from supabase import create_client
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"[DB] Supabase unavailable, falling back to local mode: {e}")
                self.cloud_enabled = False

    # ── crypto ────────────────────────────────────────────
    def encrypt(self, plain_text: str) -> str:
        return self._cipher.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        return self._cipher.decrypt(cipher_text.encode()).decode()

    # ── auth ──────────────────────────────────────────────
    def login(self, email, password):
        if not self.cloud_enabled:
            return False, "Cloud sync is disabled (no Supabase config). Use guest mode."
        try:
            response = self.supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            self.user = response.user
            self.session = response.session
            return True, "Login successful"
        except Exception as e:
            return False, str(e)

    def restore_session(self, refresh_token: str):
        """Auto-login using a stored refresh token (no password on disk)."""
        if not self.cloud_enabled or not refresh_token:
            return False
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            self.user = response.user
            self.session = response.session
            return self.user is not None
        except Exception:
            return False

    def get_refresh_token(self):
        try:
            return self.session.refresh_token if self.session else None
        except Exception:
            return None

    def register(self, email, password):
        if not self.cloud_enabled:
            return False, "Cloud sync is disabled (no Supabase config). Use guest mode."
        try:
            self.supabase.auth.sign_up({"email": email, "password": password})
            return True, "Registration successful. Please login."
        except Exception as e:
            return False, str(e)

    def logout(self):
        if self.cloud_enabled and self.supabase:
            try:
                self.supabase.auth.sign_out()
            except Exception:
                pass
        self.user = None
        self.session = None

    # ── local storage ─────────────────────────────────────
    def _local_read(self) -> dict:
        if not os.path.exists(LOCAL_CREDS):
            return {}
        try:
            with open(LOCAL_CREDS, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _local_write(self, data: dict):
        _ensure_lesh_dir()
        try:
            with open(LOCAL_CREDS, "w", encoding="utf-8") as f:
                json.dump(data, f)
            _restrict_permissions(LOCAL_CREDS)
        except OSError as e:
            print(f"[DB] Could not persist local credentials: {e}")

    # ── api keys ──────────────────────────────────────────
    def get_api_key(self, provider_name: str):
        # Cloud (only when logged in)
        if self.cloud_enabled and self.user:
            try:
                res = (
                    self.supabase.table("api_keys")
                    .select("api_key_encrypted")
                    .eq("user_id", self.user.id)
                    .eq("provider_name", provider_name)
                    .execute()
                )
                if res.data:
                    return self.decrypt(res.data[0]["api_key_encrypted"])
            except Exception:
                pass
            return None

        # Local
        data = self._local_read()
        enc = data.get(provider_name)
        if not enc:
            return None
        try:
            return self.decrypt(enc)
        except Exception:
            return None

    def set_api_key(self, provider_name: str, api_key: str):
        api_key = (api_key or "").strip()
        if not api_key:
            return False
        encrypted_key = self.encrypt(api_key)

        if self.cloud_enabled and self.user:
            try:
                self.supabase.table("api_keys").upsert(
                    {
                        "user_id": self.user.id,
                        "provider_name": provider_name,
                        "api_key_encrypted": encrypted_key,
                    },
                    on_conflict="user_id,provider_name",
                ).execute()
                return True
            except Exception as e:
                print(f"[DB] Cloud key save failed: {e}")
                return False

        data = self._local_read()
        data[provider_name] = encrypted_key
        self._local_write(data)
        return True


db = DBManager()
