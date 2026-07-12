import json
import re
import requests
import openai
from tools import read_file, write_file, search_web, list_directory, run_terminal_command

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

class StreamingThinkParser:
    """Stateful parser to handle <think> tags in streaming chunks."""
    def __init__(self, chat_callback):
        self.chat_callback = chat_callback
        self.is_thinking = False
        self.buffer = ""

    def add_chunk(self, chunk: str):
        self.buffer += chunk
        
        while self.buffer:
            if not self.is_thinking:
                idx = self.buffer.find("<think>")
                if idx != -1:
                    # Output text before <think>
                    if idx > 0:
                        self.chat_callback(self.buffer[:idx], tag=None)
                    self.chat_callback("\n[DÜŞÜNÜYOR...]\n", tag="think")
                    self.is_thinking = True
                    self.buffer = self.buffer[idx+7:]
                else:
                    # Check for partial tag match at the end
                    partial_idx = self._find_partial(self.buffer, "<think>")
                    if partial_idx != -1:
                        self.chat_callback(self.buffer[:partial_idx], tag=None)
                        self.buffer = self.buffer[partial_idx:]
                        break
                    else:
                        self.chat_callback(self.buffer, tag=None)
                        self.buffer = ""
            else:
                idx = self.buffer.find("</think>")
                if idx != -1:
                    if idx > 0:
                        self.chat_callback(self.buffer[:idx], tag="think")
                    self.chat_callback("\n", tag=None)
                    self.is_thinking = False
                    self.buffer = self.buffer[idx+8:]
                else:
                    partial_idx = self._find_partial(self.buffer, "</think>")
                    if partial_idx != -1:
                        self.chat_callback(self.buffer[:partial_idx], tag="think")
                        self.buffer = self.buffer[partial_idx:]
                        break
                    else:
                        self.chat_callback(self.buffer, tag="think")
                        self.buffer = ""

    def _find_partial(self, text, tag):
        """Finds if text ends with a partial tag like '<', '<t', '</' etc."""
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return len(text) - i
        return -1


def chat_cloud_streaming(model_name, messages, tools, token, base_url, chat_callback, log_callback):
    """
    OpenAI, Groq, GitHub Models ve Google AI Studio (OpenAI API Compatibility) için
    ortak streaming ve tool calling yöneticisi.
    """
    if log_callback:
        log_callback(f"[API] Bağlanılan URL: {base_url}")
        
    client = openai.OpenAI(api_key=token, base_url=base_url)
    parser = StreamingThinkParser(chat_callback)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools,
            stream=True
        )
        
        full_content = ""
        tool_calls_buffer = {}
        
        for chunk in response:
            if not chunk.choices:
                continue
                
            delta = chunk.choices[0].delta
            
            # 1. Metin Akışı (Content Streaming)
            if delta.content:
                text = delta.content
                full_content += text
                parser.add_chunk(text)
                
            # 2. Araç Çağrıları Akışı (Tool Calls Buffer)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name or "", "arguments": ""}
                        }
                    if tc.function.arguments:
                        tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments
                        
        # Stream bittiğinde buffer'ı boşalt (eğer partial tag kaldıysa)
        if parser.buffer:
            parser.chat_callback(parser.buffer, tag="think" if parser.is_thinking else None)
            
        tool_calls = list(tool_calls_buffer.values())
        if log_callback and tool_calls:
            names = [tc['function']['name'] for tc in tool_calls]
            log_callback(f"[ARAÇ] Çağrılacak araçlar: {names}")
            
        return full_content, tool_calls
        
    except Exception as e:
        if log_callback:
            log_callback(f"[HATA] API Hatası: {str(e)}")
        return f"Hata: {str(e)}", []


class AgentState:
    def __init__(self, provider, model, workspace_path, token, chat_callback, log_callback):
        self.provider = provider
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
        self.active_file_context = {"filepath": filepath, "content": content}
        self._log(f"Bağlama eklendi: {filepath}")

    def _log(self, text):
        if self.log_callback:
            self.log_callback(text)

    def _chat(self, text, tag=None):
        if self.chat_callback:
            self.chat_callback(text, tag=tag)

    def _execute_tool(self, tool_call):
        if isinstance(tool_call, dict):
            action = tool_call.get('function', {}).get('name', '')
            args_str = tool_call.get('function', {}).get('arguments', '{}')
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except:
                args = {}
        else:
            action = tool_call.function.name
            args = tool_call.function.arguments

        self._log(f"▶ {action}({list(args.keys())})")
        self._chat(f"\n🛠️  {action}: {args.get('filepath') or args.get('command') or args.get('query', '')}\n", tag="system")

        try:
            if action == "write_file":
                result = write_file(args.get("filepath", ""), args.get("content", ""), self.workspace_path)
                self._log(f"✅ Dosya kaydedildi: {args.get('filepath')}")

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
            system_prompt += f"\n\n[DİKKAT] Kullanıcının odaklandığı dosya ({self.active_file_context['filepath']}) içeriği:\n{self.active_file_context['content']}\n"

        coder_msgs = [{"role": "system", "content": system_prompt}] + self.messages
        max_steps = 15

        for step in range(max_steps):
            self._log(f"\n[Adım {step + 1}] Model düşünüyor...")

            if "GitHub" in self.provider:
                base_url = "https://models.inference.ai.azure.com"
                content, tool_calls = chat_cloud_streaming(self.model, coder_msgs, TOOLS_DEF, self.token, base_url, self._chat, self._log)
            elif "Groq" in self.provider:
                base_url = "https://api.groq.com/openai/v1"
                content, tool_calls = chat_cloud_streaming(self.model, coder_msgs, TOOLS_DEF, self.token, base_url, self._chat, self._log)
            elif "Google" in self.provider:
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                content, tool_calls = chat_cloud_streaming(self.model, coder_msgs, TOOLS_DEF, self.token, base_url, self._chat, self._log)
            else:
                # Ollama Local Flow
                from ollama_client import chat_with_tools
                # Streaming for Ollama can be added similarly, but using previous logic for now
                content, tool_calls = chat_with_tools(self.model, coder_msgs, TOOLS_DEF, self._log)
                if content:
                    parser = StreamingThinkParser(self._chat)
                    parser.add_chunk(content + "\n")

            assistant_msg = {"role": "assistant", "content": content or ""}
            if tool_calls:
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
                tool_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                
                tool_result_msg = {
                    "role": "tool",
                    "content": result,
                    "name": tool_name
                }
                if tool_id:
                    tool_result_msg["tool_call_id"] = tool_id
                    
                coder_msgs.append(tool_result_msg)
                self.messages.append(tool_result_msg)

        else:
            self._log("[UYARI] Maksimum adım sayısına ulaşıldı!")
            self._chat("\n⚠️ Maksimum adım sayısına ulaşıldı.\n", tag="system")

        self._log("═══════════════════════════════")
