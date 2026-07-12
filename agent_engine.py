import json
import requests
from tools import read_file, write_file, search_web, list_directory, run_terminal_command
import re

AGENT_SYSTEM_PROMPT = """Sen profesyonel bir Otonom Yazılım Mühendisi Ajanısın.
Sana verilen araçları (write_file, read_file, run_terminal_command vb.) DOĞRUDAN KULLANMAK ZORUNDASIN.

ALTIN KURAL: Kullanıcı senden bir şey oluşturmanı istediğinde, KESİNLİKLE sadece metin olarak kod yazma.
Her zaman write_file aracını çağırarak dosyaları GERÇEKTEN bilgisayara KAYDET.

Örnek:
- "websitesi yap" → index.html, style.css, script.js dosyalarını write_file ile oluştur
- "python scripti yaz" → main.py dosyasını write_file ile oluştur
- "pip install" gerekliyse → run_terminal_command ile yükle

Görev bitince: Tüm dosyaları oluşturduktan sonra run_terminal_command ile "git add . && git commit -m 'AI Update' && git push" çalıştır.
"""

TOOLS_DEF = [
    {
        'type': 'function',
        'function': {
            'name': 'write_file',
            'description': 'Creates or overwrites a file with given content. ALWAYS USE THIS to save code files.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filepath': {'type': 'string', 'description': 'File path relative to workspace'},
                    'content': {'type': 'string', 'description': 'Full content to write into the file'}
                },
                'required': ['filepath', 'content']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_file',
            'description': 'Reads the content of an existing file.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filepath': {'type': 'string', 'description': 'File path relative to workspace'}
                },
                'required': ['filepath']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_terminal_command',
            'description': 'Runs a shell command (e.g. pip install, git push, mkdir).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {'type': 'string', 'description': 'Command to execute'}
                },
                'required': ['command']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'list_directory',
            'description': 'Lists files and folders in a directory.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filepath': {'type': 'string', 'description': 'Directory path (use "." for workspace root)'}
                },
                'required': ['filepath']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_web',
            'description': 'Searches the web for documentation or solutions.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'Search query'}
                },
                'required': ['query']
            }
        }
    }
]

def chat_github_models(model_name, messages, tools, token, log_callback=None):
    """GitHub Models API'ye requests ile OpenAI uyumlu istek atar (Bağımlılığı artırmamak için)"""
    url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "tools": tools,
        "stream": False # Tool calling daha stabil çalışsın diye False
    }
    
    try:
        if log_callback:
            log_callback(f"[MODEL] GitHub Models ({model_name}) çağrılıyor...")
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        msg = data['choices'][0]['message']
        content = msg.get('content', '')
        tool_calls = msg.get('tool_calls', [])
        
        if log_callback:
            if tool_calls:
                names = [tc['function']['name'] for tc in tool_calls]
                log_callback(f"[ARAÇ] Çağrılacak araçlar: {names}")
            elif content:
                log_callback(f"[CEVAP] Model yanıt verdi.")
                
        return content, tool_calls
    except Exception as e:
        if log_callback:
            log_callback(f"[HATA] GitHub Models hatası: {str(e)}")
        return f"Hata: {str(e)}", []


def parse_think_tags(text, chat_callback):
    """<think> etiketlerini ayırarak UI'a doğru renklerle gönderir."""
    if not text:
        return
        
    parts = re.split(r'(</?think>)', text)
    is_thinking = False
    
    for part in parts:
        if part == '<think>':
            is_thinking = True
            chat_callback("\n[DÜŞÜNÜYOR...]\n", tag="think")
            continue
        elif part == '</think>':
            is_thinking = False
            chat_callback("\n", tag=None)
            continue
            
        if part:
            if is_thinking:
                chat_callback(part, tag="think")
            else:
                chat_callback(part, tag=None)


class AgentState:
    def __init__(self, provider, model, workspace_path, token, chat_callback, log_callback):
        self.provider = provider # 'Yerel (Ollama)' veya 'GitHub Models (Bulut)'
        self.model = model
        self.workspace_path = workspace_path
        self.token = token
        self.chat_callback = chat_callback
        self.log_callback = log_callback
        self.messages = []
        self.active_file_context = None

    def add_user_message(self, text):
        self.messages.append({"role": "user", "content": text})

    def set_active_file(self, filepath, content):
        """Kullanıcı ağaçtan bir dosya seçtiğinde context'i günceller"""
        self.active_file_context = {"filepath": filepath, "content": content}
        self._log(f"Bağlama eklendi: {filepath}")

    def _log(self, text):
        if self.log_callback:
            self.log_callback(text)

    def _chat(self, text, tag=None):
        if self.chat_callback:
            self.chat_callback(text, tag=tag)

    def _execute_tool(self, tool_call):
        # GitHub ve Ollama API'leri tool call objesini farklı dict formatlarında döndürebilir
        if isinstance(tool_call, dict):
            action = tool_call.get('function', {}).get('name', '')
            args_str = tool_call.get('function', {}).get('arguments', '{}')
            if isinstance(args_str, str):
                try:
                    args = json.loads(args_str)
                except:
                    args = {}
            else:
                args = args_str
        else:
            # Ollama Pydantic
            action = tool_call.function.name
            args = tool_call.function.arguments

        self._log(f"▶ {action}({list(args.keys())})")
        self._chat(f"\n🛠️  {action}: {args.get('filepath') or args.get('command') or args.get('query', '')}\n", tag="system")

        try:
            if action == "write_file":
                filepath = args.get("filepath", "")
                content = args.get("content", "")
                result = write_file(filepath, content, self.workspace_path)
                self._log(f"✅ Dosya kaydedildi: {filepath}")
                self._chat(f"💾 Kaydedildi: {filepath}\n", tag="system")

            elif action == "read_file":
                result = read_file(args.get("filepath", ""), self.workspace_path)
                self._log(f"📖 Okundu: {args.get('filepath')}")

            elif action == "list_directory":
                result = list_directory(args.get("filepath", "."), self.workspace_path)
                self._log(f"📂 Listelendi: {args.get('filepath')}")

            elif action == "run_terminal_command":
                cmd = args.get("command", "")
                self._log(f"$ {cmd}")
                
                # Sadece ajan çağırırken git push içerisinde PAT token kullanması için komutu değiştirme:
                # Ancak bunu git_manager üzerinden yapmıyoruz, doğrudan komut çalıştırıyoruz.
                # Terminal command güvenliği için komut timeout içerebilir (tools.py'yi ona göre güncelleyebiliriz)
                result = run_terminal_command(cmd, self.workspace_path)
                
                parsed = json.loads(result)
                if parsed.get("stdout"):
                    self._log(parsed["stdout"][:500])
                if parsed.get("stderr"):
                    self._log(f"[stderr] {parsed['stderr'][:200]}")

            elif action == "search_web":
                result = search_web(args.get("query", ""))
                self._log(f"🌐 Arandı: {args.get('query')}")

            else:
                result = json.dumps({"error": f"Bilinmeyen araç: {action}"})
                self._log(f"❌ Bilinmeyen araç: {action}")

        except Exception as e:
            result = json.dumps({"error": str(e)})
            self._log(f"❌ Hata ({action}): {str(e)}")

        return result

    def run(self):
        self._log("═══════════════════════════════")
        self._log(f"Ajan başlatıldı | Model: {self.model} ({self.provider})")
        self._log("═══════════════════════════════")

        system_prompt = AGENT_SYSTEM_PROMPT
        if self.active_file_context:
            system_prompt += f"\n\n[DİKKAT] Kullanıcının şu an odaklandığı/seçtiği dosya ({self.active_file_context['filepath']}) içeriği:\n{self.active_file_context['content']}\n"

        coder_msgs = [{"role": "system", "content": system_prompt}] + self.messages
        max_steps = 15

        for step in range(max_steps):
            self._log(f"\n[Adım {step + 1}] Model düşünüyor...")

            if "GitHub" in self.provider:
                content, tool_calls = chat_github_models(
                    model_name=self.model,
                    messages=coder_msgs,
                    tools=TOOLS_DEF,
                    token=self.token,
                    log_callback=self._log
                )
            else:
                from ollama_client import chat_with_tools
                content, tool_calls = chat_with_tools(
                    model_name=self.model,
                    messages=coder_msgs,
                    tools=TOOLS_DEF,
                    log_callback=self._log
                )

            if content and content.strip():
                parse_think_tags(content + "\n", self._chat)

            assistant_msg = {"role": "assistant", "content": content or ""}
            if tool_calls:
                # GitHub modelleri JSON formatında dict döndürür, OpenAI standardına uyumlu hale getir
                # Ollama ise objeler kullanır. Burada mesaja format uyumlu eklemek zorundayız.
                if "GitHub" in self.provider:
                    assistant_msg["tool_calls"] = tool_calls
                else:
                    assistant_msg["tool_calls"] = tool_calls

            coder_msgs.append(assistant_msg)
            self.messages.append(assistant_msg)

            if not tool_calls:
                self._log(f"\n[Adım {step + 1}] Görev tamamlandı.")
                self._chat("\n✅ Görev tamamlandı.\n", tag="system")
                break

            self._log(f"[Adım {step + 1}] {len(tool_calls)} araç çalıştırılıyor...")
            for tc in tool_calls:
                result = self._execute_tool(tc)
                
                tool_name = tc.get('function', {}).get('name') if isinstance(tc, dict) else tc.function.name
                
                tool_result_msg = {
                    "role": "tool",
                    "content": result,
                    "name": tool_name
                }
                # Ollama tool responses need special role matching, usually 'tool' is fine for both.
                coder_msgs.append(tool_result_msg)
                self.messages.append(tool_result_msg)

        else:
            self._log("[UYARI] Maksimum adım sayısına ulaşıldı!")
            self._chat("\n⚠️ Maksimum adım sayısına ulaşıldı.\n", tag="system")

        self._log("═══════════════════════════════")
