import ollama
from ollama import Client

client = Client(host='http://localhost:11434')

def check_ollama_status():
    """Ollama servisinin çalışıp çalışmadığını kontrol eder."""
    try:
        client.list()
        return True
    except Exception:
        return False

def get_models():
    """Yüklü olan modellerin listesini döndürür."""
    try:
        response = client.list()
        return [m['name'] for m in response.get('models', [])]
    except Exception:
        return []

def ensure_model_exists(model_name, progress_callback=None):
    """Model yoksa indirir."""
    models = get_models()
    if model_name not in models:
        try:
            if progress_callback:
                progress_callback(f"İndiriliyor: {model_name}...")
            client.pull(model_name)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"İndirme Hatası: {str(e)}")
            return False
    return True

def chat_stream(model_name, messages, tools=None, yield_callback=None):
    """
    Ollama API'sine chat isteği atar. Native tool calling destekler.
    Döndürdüğü değer: (full_content, tool_calls_list)
    """
    try:
        # Tool kullanıldığında ollama bazen content'i boş döndürüp sadece tool_calls atar.
        # Stream=False yaparsak tool_calls çok daha kararlı çalışır ancak biz stream=True istiyoruz.
        # Stream açıkken tool çağırdığında chunk'larda tool_call objeleri parça parça gelir.
        
        # Otonom tool calling'in en kararlı hali stream=False'tur.
        # Arayüzdeki donmayı engellemek için fonksiyon zaten thread içinde çağrılmaktadır.
        # Eğer tools gönderildiyse (Coder modeli), daha güvenilir tool parsing için stream=False kullanıyoruz.
        if tools:
            if yield_callback:
                yield_callback("\n[Ajan Düşünüyor... Lütfen bekleyin]\n")
                
            response = client.chat(
                model=model_name,
                messages=messages,
                tools=tools,
                stream=False
            )
            msg = response.get('message', {})
            content = msg.get('content', '')
            if content and yield_callback:
                yield_callback(content)
                
            return content, msg.get('tool_calls', [])
            
        else:
            # Sadece sohbet ediliyorsa (Router veya tools yoksa) Stream=True
            response = client.chat(
                model=model_name,
                messages=messages,
                stream=True
            )
            full_content = ""
            for chunk in response:
                msg = chunk.get('message', {})
                content = msg.get('content', '')
                if content:
                    full_content += content
                    if yield_callback:
                        yield_callback(content)
            return full_content, []
            
    except Exception as e:
        if yield_callback:
            yield_callback(f"\n[HATA]: Ollama ile iletişim kurulamadı. ({str(e)})\n")
        return None, []

def chat_sync(model_name, messages):
    """Senkron olarak (bekleyerek) Ollama'dan cevap alır."""
    try:
        response = client.chat(model=model_name, messages=messages, stream=False)
        return response.get('message', {}).get('content', '')
    except Exception:
        return ""
