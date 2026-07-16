import os
from supabase import create_client, Client
from cryptography.fernet import Fernet

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

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
ENCRYPTION_KEY_STR = os.environ.get("ENCRYPTION_KEY", "")

if ENCRYPTION_KEY_STR:
    ENCRYPTION_KEY = ENCRYPTION_KEY_STR.encode()
else:
    # Fallback
    ENCRYPTION_KEY = b'***REMOVED_FERNET***'

cipher_suite = Fernet(ENCRYPTION_KEY)

class DBManager:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.user = None
        self.session = None

    def encrypt(self, plain_text: str) -> str:
        return cipher_suite.encrypt(plain_text.encode()).decode()

    def decrypt(self, cipher_text: str) -> str:
        return cipher_suite.decrypt(cipher_text.encode()).decode()

    def login(self, email, password):
        try:
            response = self.supabase.auth.sign_in_with_password({"email": email, "password": password})
            self.user = response.user
            self.session = response.session
            return True, "Login successful"
        except Exception as e:
            return False, str(e)

    def register(self, email, password):
        try:
            response = self.supabase.auth.sign_up({"email": email, "password": password})
            return True, "Registration successful. Please login."
        except Exception as e:
            return False, str(e)

    def logout(self):
        self.supabase.auth.sign_out()
        self.user = None
        self.session = None

    def get_api_key(self, provider_name: str):
        if not self.user:
            return None
        
        try:
            res = self.supabase.table("api_keys").select("api_key_encrypted").eq("provider_name", provider_name).execute()
            if res.data and len(res.data) > 0:
                encrypted_key = res.data[0]['api_key_encrypted']
                return self.decrypt(encrypted_key)
        except:
            pass
        return None

    def set_api_key(self, provider_name: str, api_key: str):
        if not self.user:
            return False
            
        encrypted_key = self.encrypt(api_key)
        try:
            # Check if exists
            res = self.supabase.table("api_keys").select("id").eq("provider_name", provider_name).execute()
            if res.data and len(res.data) > 0:
                # Update
                self.supabase.table("api_keys").update({"api_key_encrypted": encrypted_key}).eq("provider_name", provider_name).execute()
            else:
                # Insert
                self.supabase.table("api_keys").insert({
                    "user_id": self.user.id,
                    "provider_name": provider_name,
                    "api_key_encrypted": encrypted_key
                }).execute()
            return True
        except Exception as e:
            print(f"Set API Key Error: {e}")
            return False

db = DBManager()
