import json
from ollama_client import chat_stream, chat_sync
from tools import read_file, write_file, search_web, list_directory, fetch_url, run_terminal_command

ROUTER_PROMPT = """Sen akıllı bir Yönlendirici (Router) Ajansın.
Görevin, kullanıcının talebini değerlendirmektir. 
Eğer kullanıcının talebi, dosya oluşturma, proje kurma, kod yazma, terminal kullanma veya karmaşık bir geliştirme göreviyse SADECE "[TRANSFER]" yaz.
Eğer sadece basit bir soru, sohbet veya selamlaşmaysa, kendin doğrudan cevap ver. Başka hiçbir şey yapma.
"""

CODER_PROMPT = """Sen Profesyonel Otonom bir Yazılım Mühendisisin (Aider / OpenClaw seviyesinde).
Sana verilen araçları (tools) KULLANMAK ZORUNDASIN. Kullanıcı senden bir websitesi veya proje oluşturmanı isterse, sadece kodu ekrana yazmakla kalma; `write_file` aracını çağırarak o dosyaları (html, css, py vb.) gerçekten bilgisayara KAYDET!

KURALLAR:
1. Bir şey tasarlaman veya oluşturman istendiğinde, düşün ve sonra `write_file` aracı ile tüm gerekli dosyaları sırayla oluştur.
2. Bir kütüphane gerekiyorsa `run_terminal_command` aracı ile `pip install` yap.
3. Bir sorunla karşılaşırsan internette araştırmak için `search_web` kullan.
4. Dosya değiştirirken tüm dosyanın içeriğini ver.
5. Kullanıcıya uzun uzun açıklamalar yapmak yerine, doğrudan harekete geç (araçları çağır).
6. GÖREV BİTİNCE OTOMATİK PUSH: Tüm dosyaları yazdıktan sonra MUTLAKA `run_terminal_command` aracı ile `git add . && git commit -m "Auto update" && git push` komutunu çalıştır!
"""

TOOLS_DEF = [
    {
        'type': 'function',
        'function': {
            'name': 'read_file',
            'description': 'Reads the content of a specific file to understand existing code.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filepath': {'type': 'string', 'description': 'Path to the file to read (e.g. index.html)'}
                },
                'required': ['filepath']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'write_file',
            'description': 'Creates or overwrites a file. YOU MUST USE THIS to generate code files instead of just printing them to the user.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filepath': {'type': 'string', 'description': 'Path to the file to create/write (e.g. style.css, main.py)'},
                    'content': {'type': 'string', 'description': 'The complete code or text to write inside the file'}
                },
                'required': ['filepath', 'content']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_terminal_command',
            'description': 'Executes a command in the terminal (e.g. pip install requests, git add .).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {'type': 'string', 'description': 'The command string'}
                },
                'required': ['command']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'search_web',
            'description': 'Searches the internet for solutions or documentation.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'Search query'}
                },
                'required': ['query']
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
                    'filepath': {'type': 'string', 'description': 'Directory path to list'}
                },
                'required': ['filepath']
            }
        }
    }
]

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
        self.ui_callback("\n⚙️ [Yönlendirici Düşünüyor...]\n", is_system=True)
        router_msgs = [{"role": "system", "content": ROUTER_PROMPT}] + self.messages
        router_response = chat_sync(self.router_model, router_msgs)
        
        if "[TRANSFER]" in router_response or len(router_response.strip()) == 0:
            self.ui_callback("🚀 [Mühendis Ajan (Coder) Devreye Girdi]\n\n", is_system=True)
            self._run_coder_loop()
        else:
            self.ui_callback(f"🤖 Ajan:\n{router_response}\n\n", is_system=False)
            self.messages.append({"role": "assistant", "content": router_response})

    def _run_coder_loop(self):
        coder_msgs = [{"role": "system", "content": CODER_PROMPT}] + self.messages
        max_steps = 15
        step = 0
        
        while step < max_steps:
            step += 1
            
            # Buffer stream hook for better UI performance
            def stream_hook(chunk):
                self.ui_callback(chunk, is_system=False)
                
            full_response, tool_calls = chat_stream(self.coder_model, coder_msgs, tools=TOOLS_DEF, yield_callback=stream_hook)
            
            # Update messages with assistant response
            msg_to_append = {"role": "assistant", "content": full_response if full_response else ""}
            if tool_calls:
                msg_to_append["tool_calls"] = tool_calls
                
            self.messages.append(msg_to_append)
            coder_msgs.append(msg_to_append)
            
            if tool_calls:
                for tool in tool_calls:
                    action = tool['function']['name']
                    args = tool['function']['arguments']
                    self.ui_callback(f"\n🛠️ [Sistem Aracı Çalıştırılıyor: {action}]\n", is_system=True)
                    
                    result = ""
                    try:
                        if action == "read_file":
                            result = read_file(args.get("filepath", ""), self.workspace_path)
                        elif action == "write_file":
                            result = write_file(args.get("filepath", ""), args.get("content", ""), self.workspace_path)
                            self.ui_callback(f"💾 [Dosya Kaydedildi: {args.get('filepath')}]\n", is_system=True)
                        elif action == "list_directory":
                            result = list_directory(args.get("filepath", ""), self.workspace_path)
                        elif action == "search_web":
                            result = search_web(args.get("query", ""))
                        elif action == "run_terminal_command":
                            result = run_terminal_command(args.get("command", ""), self.workspace_path)
                            self.ui_callback(f"🖥️ [Terminal Çalıştı: {args.get('command')}]\n", is_system=True)
                        else:
                            result = json.dumps({"error": f"Bilinmeyen araç: {action}"})
                    except Exception as e:
                        result = json.dumps({"error": f"Araç çalışma hatası: {str(e)}"})
                    
                    # Send tool result back to the model
                    tool_msg = {"role": "tool", "content": result, "name": action}
                    self.messages.append(tool_msg)
                    coder_msgs.append(tool_msg)
                    
                self.ui_callback(f"✅ [Araçlar Tamamlandı. Ajan planlamaya devam ediyor...]\n\n", is_system=True)
            else:
                self.ui_callback("\n🏁 [Görev Tamamlandı]\n\n", is_system=True)
                break
