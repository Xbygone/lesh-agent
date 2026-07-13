from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Lesh Agent Web API")

class HealthCheck(BaseModel):
    status: str
    message: str

@app.get("/api/health", response_model=HealthCheck)
def health_check():
    return {"status": "ok", "message": "Lesh Agent API is running on Vercel!"}

@app.get("/api/info")
def info():
    return {
        "app": "Lesh Agent",
        "description": "This is the backend for Lesh Agent web services.",
        "database": "Supabase"
    }

# Not: Veritabanı ve kimlik doğrulama işlemleri doğrudan Masaüstü uygulamasındaki
# supabase-py istemcisi üzerinden (db_manager.py) güvenli bir şekilde (RLS ile) yapıldığı için 
# bu sunucu üzerinde kritik veritabanı şifresi tutmaya gerek kalmamıştır.
# Bu API'yi ileride Web Dashboard veya özel webhook'lar için kullanabilirsiniz.
