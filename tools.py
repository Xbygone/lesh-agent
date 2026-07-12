import os
import json
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests

def read_file(filepath, workspace_path):
    """
    Belirtilen dosyayı okur. Güvenlik için sadece workspace_path içindeki dosyalara izin verir.
    """
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return json.dumps({"error": "Güvenlik İhlali: Çalışma dizini dışına çıkılamaz."})
    
    if not os.path.exists(abs_path):
        return json.dumps({"error": f"Dosya bulunamadı: {filepath}"})
    
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps({"success": True, "content": content})
    except Exception as e:
        return json.dumps({"error": str(e)})

def write_file(filepath, content, workspace_path):
    """
    Belirtilen dosyaya (workspace_path içinde) içerik yazar.
    """
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return json.dumps({"error": "Güvenlik İhlali: Çalışma dizini dışına çıkılamaz."})
    
    # Klasör yoksa oluştur
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return json.dumps({"success": True, "message": f"{filepath} başarıyla kaydedildi."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def search_web(query, max_results=3):
    """
    DuckDuckGo üzerinden internet araması yapar ve ilk birkaç sonucun özetini/URL'ini döndürür.
    """
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title"),
                    "href": r.get("href"),
                    "body": r.get("body")
                })
        return json.dumps({"success": True, "results": results}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Arama yapılamadı: {str(e)}"})

def fetch_url(url):
    """
    Basitçe bir URL'den metin çeker. (Özellikle dokümantasyon veya github içerikleri okumak için)
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Gereksiz script vb sil
            for s in soup(['script', 'style', 'nav', 'footer', 'header']):
                s.decompose()
            text = ' '.join(soup.stripped_strings)
            # Çok uzun olmaması için kırp (LLM context limitini aşmamak için)
            return json.dumps({"success": True, "content": text[:5000] + ("..." if len(text) > 5000 else "")})
        else:
            return json.dumps({"error": f"HTTP Hatası: {response.status_code}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_directory(filepath, workspace_path):
    """
    Belirtilen klasörün içindeki dosyaları listeler.
    """
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return json.dumps({"error": "Güvenlik İhlali."})
    
    try:
        if os.path.isdir(abs_path):
            files = os.listdir(abs_path)
            return json.dumps({"success": True, "files": files})
        return json.dumps({"error": "Klasör değil."})
    except Exception as e:
        return json.dumps({"error": str(e)})
