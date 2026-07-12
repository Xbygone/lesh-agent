import json
import re
from ollama_client import chat_stream, chat_sync
from tools import read_file, write_file, search_web, list_directory, fetch_url

ROUTER_PROMPT = """Sen akıllı bir yönlendiricisin (Router). 
Görevin, kullanıcının talebini değerlendirmektir. 
Eğer talep sadece basit bir sohbet, merhaba deme veya kod gerektirmeyen çok basit bir soru ise, doğrudan sen cevap ver.
Eğer talep KODLAMA, DOSYA OKUMA/YAZMA, SİSTEM DEĞİŞİKLİĞİ, BUG ÇÖZME veya PROJE ÜZERİNDE İŞLEM gerektiriyorsa SADECE "[TRANSFER]" yaz. Başka hiçbir şey yazma.
"""

CODER_PROMPT = """Sen Otonom bir Kodlama Ajanısın (Autonomous Coding Agent). 
Kullanıcının projelerini inceleyebilir, dosyaları okuyabilir, düzenleyebilir ve otonom döngülerle hataları çözebilirsin.

Gerektiğinde aşağıdaki araçları (tools) kullanabilirsin. Araç kullanmak için çıktında tam olarak şu formata uymalısın:
<tool>{"action": "arac_adi", "parametreler"}</tool>

Kullanılabilir Araçlar (JSON formatları):
1. Dosya Okuma: <tool>{"action": "read_file", "filepath": "main.py"}</tool>
2. Dosya Yazma: <tool>{"action": "write_file", "filepath": "main.py", "content": "import os\n..."}</tool>
3. Klasör Listeleme: <tool>{"action": "list_directory", "filepath": "."}</tool>
4. Web Araması: <tool>{"action": "search_web", "query": "python fastapi error"}</tool>

KURALLAR:
1. Planlama yaparken veya düşünürken mutlaka <think> ... düşünceler ... </think> etiketlerini kullan. Bu kullanıcıya senin zihnini gösterir.
2. Bir araca ihtiyacın varsa, sadece tek bir <tool> JSON objesi bas ve cümleni/cevabını bitir. (Araç sonucu sana sistem tarafından gönderilecek).
3. Bir dosyayı değiştirmeden önce okuyup içeriğinden emin olman iyi bir pratiktir.
4. Dosyayı yazarken tüm içeriği (tam kodu) gönder, eksik kod gönderme.
5. Görevi tamamladığında kullanıcıya kısaca ne yaptığını açıkla ve döngüyü bitirmek için <tool> kullanma.
"""

def extract_tool_call(text):
    match = re.search(r'<tool>(.*?)</tool>', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None

class AgentState:
    def __init__(self, router_model, coder_model, workspace_path, ui_callback):
        self.router_model = router_model
        self.coder_model = coder_model
        self.workspace_path = workspace_path
        self.ui_callback = ui_callback
        self.messages = []
        
    def add_user_message(self, text):
        self.messages.append({"role": "user", "content": text})

    def process_input(self):
        # Router
        self.ui_callback("\n⚙️ [Yönlendirici Düşünüyor...]\n", is_system=True)
        router_msgs = [{"role": "system", "content": ROUTER_PROMPT}] + self.messages
        router_response = chat_sync(self.router_model, router_msgs)
        
        if "[TRANSFER]" in router_response or len(router_response.strip()) == 0:
            self.ui_callback("🚀 [Görev Ana Kodlama Ajanına (Coder) Devredildi]\n\n", is_system=True)
            self._run_coder_loop()
        else:
            self.ui_callback(f"🤖 Ajan (Router):\n{router_response}\n\n", is_system=False)
            self.messages.append({"role": "assistant", "content": router_response})

    def _run_coder_loop(self):
        coder_msgs = [{"role": "system", "content": CODER_PROMPT}] + self.messages
        max_steps = 15
        step = 0
        
        while step < max_steps:
            step += 1
            
            # Streaming the response
            def stream_hook(chunk):
                self.ui_callback(chunk, is_system=False)
                
            full_response = chat_stream(self.coder_model, coder_msgs, stream_hook)
            
            if not full_response:
                self.ui_callback("\n[HATA] Ajan cevap veremedi.\n", is_system=True)
                break
                
            self.messages.append({"role": "assistant", "content": full_response})
            coder_msgs.append({"role": "assistant", "content": full_response})
            self.ui_callback("\n\n", is_system=False)
            
            tool_call = extract_tool_call(full_response)
            if tool_call:
                action = tool_call.get("action")
                self.ui_callback(f"🛠️ [Araç Çalıştırılıyor: {action}]\n", is_system=True)
                
                result = ""
                try:
                    if action == "read_file":
                        result = read_file(tool_call.get("filepath", ""), self.workspace_path)
                    elif action == "write_file":
                        result = write_file(tool_call.get("filepath", ""), tool_call.get("content", ""), self.workspace_path)
                        self.ui_callback(f"💾 [Dosya Kaydedildi: {tool_call.get('filepath')}]\n", is_system=True)
                    elif action == "list_directory":
                        result = list_directory(tool_call.get("filepath", ""), self.workspace_path)
                    elif action == "search_web":
                        result = search_web(tool_call.get("query", ""))
                    else:
                        result = json.dumps({"error": f"Bilinmeyen araç: {action}"})
                except Exception as e:
                    result = json.dumps({"error": f"Araç çalışma hatası: {str(e)}"})
                
                # Aracı çağırdıktan sonra sonucu ajana geri besliyoruz
                tool_msg = f"Araç Sonucu:\n{result}"
                self.messages.append({"role": "user", "content": tool_msg})
                coder_msgs.append({"role": "user", "content": tool_msg})
                self.ui_callback(f"✅ [Araç Tamamlandı. Ajan devam ediyor...]\n\n", is_system=True)
            else:
                # Araç çağırmadıysa işlemi bitirmiş demektir
                self.ui_callback("🏁 [Döngü Tamamlandı]\n\n", is_system=True)
                break
