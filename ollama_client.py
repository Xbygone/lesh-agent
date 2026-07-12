import requests
import json

OLLAMA_URL = "http://localhost:11434"

def check_ollama_status():
    """Ollama servisinin çalışıp çalışmadığını kontrol eder."""
    try:
        response = requests.get(OLLAMA_URL)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def get_models():
    """Yüklü olan modellerin listesini döndürür."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [model["name"] for model in models]
        return []
    except Exception:
        return []

def pull_model(model_name, progress_callback=None):
    """Belirtilen modeli Ollama üzerinden indirir."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/pull",
            json={"name": model_name},
            stream=True
        )
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if progress_callback:
                    progress_callback(data.get("status", ""))
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Hata: {str(e)}")
        return False

def chat_stream(model_name, messages, yield_callback):
    """
    Ollama API'sine chat isteği atar ve cevabı stream (parça parça) olarak döndürür.
    yield_callback: UI'ı güncellemek için çağrılacak fonksiyon (chunk alır).
    """
    try:
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True
        }
        
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True)
        if response.status_code != 200:
            if yield_callback:
                yield_callback(f"\n[API HATASI]: HTTP {response.status_code}")
            return None

        full_response = ""
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                if "message" in data and "content" in data["message"]:
                    chunk = data["message"]["content"]
                    full_response += chunk
                    if yield_callback:
                        yield_callback(chunk)
        return full_response
    except Exception as e:
        if yield_callback:
            yield_callback(f"\n[HATA]: Ollama ile iletişim kurulamadı. Lütfen modelin inmiş ve Ollama'nın açık olduğundan emin olun.\nDetay: {str(e)}")
        return None

def chat_sync(model_name, messages):
    """Senkron olarak (bekleyerek) Ollama'dan cevap alır."""
    try:
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False
        }
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload)
        if response.status_code == 200:
            return response.json().get("message", {}).get("content", "")
        return ""
    except Exception:
        return ""
