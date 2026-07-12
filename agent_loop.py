import json
from ollama_client import chat_with_tools, chat_stream_simple
from tools import read_file, write_file, search_web, list_directory, run_terminal_command

AGENT_SYSTEM_PROMPT = """Sen profesyonel bir Otonom Yazılım Mühendisi Ajanısın.
Sana verilen araçları (write_file, read_file, run_terminal_command vb.) DOĞRUDAN KULLANMAK ZORUNDASIN.

ALTIN KURAL: Kullanıcı senden bir şey oluşturmanı istediğinde, KESİNLİKLE sadece metin olarak kod yazma.
Her zaman write_file aracını çağırarak dosyaları GERÇEKTEN bilgisayara KAYDET.

Örnek:
- "websitesi yap" → index.html, style.css, script.js dosyalarını write_file ile oluştur
- "python scripti yaz" → main.py dosyasını write_file ile oluştur
- "pip install" gerekliyse → run_terminal_command ile yükle

Görev bitince: run_terminal_command ile "git add . && git commit -m '...' && git push" çalıştır.
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
                    'filepath': {
                        'type': 'string',
                        'description': 'File path relative to workspace (e.g. index.html, src/app.py)'
                    },
                    'content': {
                        'type': 'string',
                        'description': 'Full content to write into the file'
                    }
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
                    'filepath': {
                        'type': 'string',
                        'description': 'File path relative to workspace'
                    }
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
                    'command': {
                        'type': 'string',
                        'description': 'Command to execute'
                    }
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
                    'filepath': {
                        'type': 'string',
                        'description': 'Directory path (use "." for workspace root)'
                    }
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
                    'query': {
                        'type': 'string',
                        'description': 'Search query'
                    }
                },
                'required': ['query']
            }
        }
    }
]


class AgentState:
    def __init__(self, model, workspace_path, chat_callback, log_callback):
        """
        chat_callback: UI sohbet penceresine metin yazar
        log_callback:  Sağ paneldeki Terminal Log'a yazar
        """
        self.model = model
        self.workspace_path = workspace_path
        self.chat_callback = chat_callback
        self.log_callback = log_callback
        self.messages = []

    def add_user_message(self, text):
        self.messages.append({"role": "user", "content": text})

    def _log(self, text):
        """Terminal log'a yazar."""
        if self.log_callback:
            self.log_callback(text)

    def _chat(self, text, tag=None):
        """Sohbet penceresine yazar."""
        if self.chat_callback:
            self.chat_callback(text, tag=tag)

    def _execute_tool(self, tool_call):
        """
        Tek bir tool_call nesnesini çalıştırır.
        tool_call.function.name  → araç adı
        tool_call.function.arguments → dict
        """
        # DÜZELTME: Pydantic nesnesi - dict değil, attribute erişimi
        action = tool_call.function.name
        args = tool_call.function.arguments  # Bu zaten dict

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
                result = run_terminal_command(cmd, self.workspace_path)
                # stdout'u log'a bas
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
        """
        Ana ajan döngüsü. Her zaman araç çağrısı modunda çalışır.
        """
        self._log("═══════════════════════════════")
        self._log(f"Ajan başlatıldı | Model: {self.model}")
        self._log("═══════════════════════════════")

        coder_msgs = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}] + self.messages
        max_steps = 20

        for step in range(max_steps):
            self._log(f"\n[Adım {step + 1}] Model düşünüyor...")

            content, tool_calls = chat_with_tools(
                model_name=self.model,
                messages=coder_msgs,
                tools=TOOLS_DEF,
                log_callback=self._log
            )

            # Modelden gelen metni sohbet penceresine yaz
            if content and content.strip():
                self._chat(content + "\n")

            # Mesaj geçmişine ekle
            assistant_msg = {"role": "assistant", "content": content or ""}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            coder_msgs.append(assistant_msg)
            self.messages.append(assistant_msg)

            # Araç çağrısı yoksa görev bitti
            if not tool_calls:
                self._log(f"\n[Adım {step + 1}] Araç çağrısı yok → Görev tamamlandı.")
                self._chat("\n✅ Görev tamamlandı.\n", tag="system")
                break

            # Araçları sırayla çalıştır
            self._log(f"[Adım {step + 1}] {len(tool_calls)} araç çalıştırılıyor...")
            for tc in tool_calls:
                result = self._execute_tool(tc)
                # Sonucu model geçmişine ekle
                tool_result_msg = {
                    "role": "tool",
                    "content": result,
                    "name": tc.function.name
                }
                coder_msgs.append(tool_result_msg)
                self.messages.append(tool_result_msg)

        else:
            self._log("[UYARI] Maksimum adım sayısına ulaşıldı!")
            self._chat("\n⚠️ Maksimum adım sayısına ulaşıldı.\n", tag="system")

        self._log("═══════════════════════════════")
