"""Agent orchestration engine.

- Streams model output (with <think> tag handling) to the UI.
- Executes tools with workspace sandboxing.
- Terminal commands require explicit user approval (unless auto-approve is on).
- Runs can be cancelled between steps via cancel_event.
"""

import json
import threading

from tools import read_file, write_file, search_web, list_directory, run_terminal_command

SYSTEM_PROMPT = """You are 'Lesh Agent', an autonomous coding assistant with file-system and terminal access on the user's local machine.
You MUST use the tools provided to you (write_file, read_file, run_terminal_command, etc.) DIRECTLY.

GOLDEN RULES:
1. When the user asks you to build something, NEVER just print code as text. Always call write_file to actually save files to disk.
2. Before editing code, read the current file content with read_file, then write the complete working version.
3. Terminal commands go through user approval. If a command is rejected, do not insist; suggest an alternative or ask the user why.
4. Avoid destructive operations (deleting files, irreversible commands); consult the user first if needed.
5. Be transparent with the user: briefly explain what you are doing and never hide errors.
6. Respond in the language the user writes in.
"""

TOOLS_DEF = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Creates or overwrites a file with given content. ALWAYS USE THIS to save code files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "File path relative to workspace"},
                    "content": {"type": "string", "description": "Full content to write into the file"},
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "File path relative to workspace"}
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Runs a shell command (e.g. pip install, git status, mkdir). Requires user approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists files and folders in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": 'Directory path (use "." for workspace root)'}
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the web for documentation or solutions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
]

PROVIDER_BASE_URLS = {
    "GitHub Models": "https://models.github.ai/inference",
    "Groq Cloud": "https://api.groq.com/openai/v1",
    "Google AI Studio": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "NVIDIA Build": "https://integrate.api.nvidia.com/v1",
}


def resolve_model_id(provider: str, model: str) -> str:
    """GitHub Models' endpoint requires publisher-prefixed IDs."""
    if "GitHub" in provider and "/" not in model:
        return f"openai/{model}"
    return model


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
                    if idx > 0:
                        self.chat_callback(self.buffer[:idx], tag=None)
                    self.chat_callback("\n[THINKING...]\n", tag="think")
                    self.is_thinking = True
                    self.buffer = self.buffer[idx + 7:]
                else:
                    partial_idx = self._find_partial(self.buffer, "<think>")
                    if partial_idx != -1:
                        self.chat_callback(self.buffer[:partial_idx], tag=None)
                        self.buffer = self.buffer[partial_idx:]
                        break
                    self.chat_callback(self.buffer, tag=None)
                    self.buffer = ""
            else:
                idx = self.buffer.find("</think>")
                if idx != -1:
                    if idx > 0:
                        self.chat_callback(self.buffer[:idx], tag="think")
                    self.chat_callback("\n", tag=None)
                    self.is_thinking = False
                    self.buffer = self.buffer[idx + 8:]
                else:
                    partial_idx = self._find_partial(self.buffer, "</think>")
                    if partial_idx != -1:
                        self.chat_callback(self.buffer[:partial_idx], tag="think")
                        self.buffer = self.buffer[partial_idx:]
                        break
                    self.chat_callback(self.buffer, tag="think")
                    self.buffer = ""

    def flush(self):
        if self.buffer:
            self.chat_callback(self.buffer, tag="think" if self.is_thinking else None)
            self.buffer = ""

    @staticmethod
    def _find_partial(text, tag):
        for i in range(1, len(tag)):
            if text.endswith(tag[:i]):
                return len(text) - i
        return -1


def chat_cloud_streaming(model_name, messages, tools, token, base_url, chat_callback, log_callback):
    """Shared streaming + tool-calling driver for all OpenAI-compatible clouds."""
    import openai

    if log_callback:
        log_callback(f"[API] {base_url} → {model_name}")

    client = openai.OpenAI(api_key=token, base_url=base_url)
    parser = StreamingThinkParser(chat_callback)

    try:
        kwargs = {"model": model_name, "messages": messages, "stream": True}
        if tools:
            kwargs["tools"] = tools

        response = client.chat.completions.create(**kwargs)

        full_content = ""
        tool_calls_buffer = {}

        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                full_content += delta.content
                parser.add_chunk(delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_buffer:
                        tool_calls_buffer[idx] = {
                            "id": tc.id or f"call_{idx}",
                            "type": "function",
                            "function": {"name": tc.function.name or "", "arguments": ""},
                        }
                    if tc.function.arguments:
                        tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments

        parser.flush()

        tool_calls = list(tool_calls_buffer.values())
        if log_callback and tool_calls:
            names = [tc["function"]["name"] for tc in tool_calls]
            log_callback(f"[TOOLS] Requested: {names}")
        return full_content, tool_calls

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] API error: {str(e)}")
        return f"ERROR: {str(e)}", []


class AgentState:
    def __init__(self, provider, model, workspace_path, token,
                 chat_callback, log_callback, approval_callback=None):
        self.provider = provider
        self.model = model
        self.workspace_path = workspace_path
        self.token = token
        self.chat_callback = chat_callback
        self.log_callback = log_callback
        self.approval_callback = approval_callback
        self.auto_approve = False
        self.run_mode = "Standard"
        self.messages = []
        self.active_file_context = None
        self.cancel_event = threading.Event()
        self.is_running = False

    # ── helpers ───────────────────────────────────────────
    def add_user_message(self, text):
        self.messages.append({"role": "user", "content": text})

    def set_active_file(self, filepath, content):
        self.active_file_context = {"filepath": filepath, "content": content}
        self._log(f"Added to context: {filepath}")

    def cancel(self):
        self.cancel_event.set()

    def _log(self, text):
        if self.log_callback:
            self.log_callback(text)

    def _chat(self, text, tag=None):
        if self.chat_callback:
            self.chat_callback(text, tag=tag)

    def _approve(self, title, detail) -> bool:
        if self.auto_approve or not self.approval_callback:
            return True
        try:
            return bool(self.approval_callback(title, detail))
        except Exception:
            return False

    # ── tool execution ────────────────────────────────────
    def _execute_tool(self, tool_call):
        if isinstance(tool_call, dict):
            action = tool_call.get("function", {}).get("name", "")
            args_str = tool_call.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
            except ValueError:
                args = {}
        else:
            action = tool_call.function.name
            args = tool_call.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}

        target = args.get("filepath") or args.get("command") or args.get("query", "")
        self._log(f"▶ {action}: {target}")
        self._chat(f"\n🛠  {action}: {target}\n", tag="tool")

        try:
            if action == "write_file":
                result = write_file(args.get("filepath", ""), args.get("content", ""), self.workspace_path)
                ok = json.loads(result).get("success")
                self._log(("✅ Saved: " if ok else "❌ Write failed: ") + str(args.get("filepath")))

            elif action == "read_file":
                result = read_file(args.get("filepath", ""), self.workspace_path)

            elif action == "list_directory":
                result = list_directory(args.get("filepath", "."), self.workspace_path)

            elif action == "run_terminal_command":
                cmd = args.get("command", "")
                if not self._approve("Terminal Command Approval", cmd):
                    self._chat("⛔ Command rejected by user.\n", tag="system")
                    result = json.dumps({
                        "error": "The user REJECTED this command. Do not retry it; "
                                 "suggest an alternative or ask the user why."
                    })
                else:
                    self._log(f"$ {cmd}")
                    result = run_terminal_command(cmd, self.workspace_path)
                    parsed = json.loads(result)
                    if parsed.get("stdout"):
                        self._log(parsed["stdout"][:800])
                    if parsed.get("stderr"):
                        self._log(f"[stderr] {parsed['stderr'][:400]}")

            elif action == "search_web":
                result = search_web(args.get("query", ""))

            else:
                result = json.dumps({"error": f"Unknown tool: {action}"})
                self._log(f"❌ Unknown tool: {action}")

        except Exception as e:
            result = json.dumps({"error": str(e)})
            self._log(f"❌ Error ({action}): {str(e)}")

        return result

    # ── mode pre-processing ───────────────────────────────
    def _last_user_message(self):
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _autopilot_route(self):
        """Route easy tasks to the local model, hard ones to the cloud."""
        self._chat("\n🤖 Auto-Pilot: analyzing request difficulty...\n", tag="pilot")
        last_msg = self._last_user_message()

        verdict = None
        try:
            from ollama_client import check_ollama_status, chat_with_tools
            if check_ollama_status():
                analyzer_prompt = (
                    "Classify the following coding request. If it is a small fix or a simple "
                    "question, answer only 'EASY'. If it involves broad architecture or complex "
                    "logic, answer only 'HARD'.\n\n"
                    f"Request: {last_msg[:2000]}"
                )
                res, _ = chat_with_tools(
                    "qwen2.5-coder:7b",
                    [{"role": "user", "content": analyzer_prompt}],
                    [], lambda x: None,
                )
                if res and "EASY" in res.upper():
                    verdict = "EASY"
                elif res and "HARD" in res.upper():
                    verdict = "HARD"
        except Exception as e:
            self._log(f"[Auto-Pilot] Local analysis skipped: {e}")

        if verdict is None:  # heuristic fallback
            hard_words = ("architecture", "refactor", "design", "optimize", "from scratch",
                          "project", "mimari", "tasarla", "sıfırdan")
            verdict = "HARD" if (len(last_msg) > 400 or any(w in last_msg.lower() for w in hard_words)) else "EASY"

        if verdict == "EASY":
            self._chat("💡 Routine task → using local qwen2.5-coder:7b.\n", tag="pilot")
            self.provider = "Local (Ollama)"
            self.model = "qwen2.5-coder:7b"
        else:
            self._chat(f"🧠 Complex task → escalating to {self.provider} cloud model.\n", tag="pilot")
            if "NVIDIA" in self.provider:
                self.model = "meta/llama-3.3-70b-instruct"
            elif "Google" in self.provider:
                self.model = "gemini-2.5-flash"
            elif "Groq" in self.provider:
                self.model = "llama-3.3-70b-versatile"
            else:
                self.provider = "GitHub Models"
                self.model = "deepseek/DeepSeek-R1"

    def _software_office(self):
        """5-expert consensus pipeline. Builds extra context WITHOUT destroying
        the user's chat history."""
        self._chat("\n🏢 Software Office: 5 expert agents assembled for consensus...\n", tag="pilot")
        user_request = self._last_user_message()

        from db_manager import db
        nvidia_key = db.get_api_key("NVIDIA Build") or ""
        github_key = db.get_api_key("GitHub Models") or ""
        google_key = db.get_api_key("Google AI Studio") or ""

        missing = [n for n, k in (
            ("NVIDIA Build", nvidia_key), ("GitHub Models", github_key), ("Google AI Studio", google_key)
        ) if not k]
        if missing:
            self._chat(
                f"\n⚠️ Software Office is missing API keys for: {', '.join(missing)}. "
                "Switch to Standard mode, select those providers and enter the keys.\n",
                tag="system",
            )
            raise RuntimeError("Missing API keys for Software Office.")

        def _quiet(x, tag=None):
            pass

        # 1. Architect
        self._chat("🟢 [NVIDIA] Software Architect is designing the skeleton...\n", tag="pilot")
        mimar_res, _ = chat_cloud_streaming(
            "meta/llama-3.3-70b-instruct",
            [{"role": "system", "content": "You are a master Software Architect. Produce only the overall logic and skeleton of the code. Return markdown only."},
             {"role": "user", "content": user_request}],
            [], nvidia_key, PROVIDER_BASE_URLS["NVIDIA Build"], _quiet, self._log)
        if self.cancel_event.is_set():
            return None

        # 2. QA
        self._chat("🐙 [GitHub] Bug Hunter (o4-mini) is auditing...\n", tag="pilot")
        qa_res, _ = chat_cloud_streaming(
            "openai/o4-mini",
            [{"role": "system", "content": "You are a meticulous QA tester. Review the given design; find bugs and edge cases, write a revision plan."},
             {"role": "user", "content": mimar_res}],
            [], github_key, PROVIDER_BASE_URLS["GitHub Models"], _quiet, self._log)
        if self.cancel_event.is_set():
            return None

        # 3. Performance
        self._chat("🟢 [NVIDIA] Performance Expert (Codestral) is optimizing...\n", tag="pilot")
        perf_res, _ = chat_cloud_streaming(
            "mistralai/codestral-2501",
            [{"role": "system", "content": "You are a performance expert. Combine the design and QA findings into a lean, efficient implementation plan."},
             {"role": "user", "content": f"Architecture:\n{mimar_res}\n\nQA findings:\n{qa_res}"}],
            [], nvidia_key, PROVIDER_BASE_URLS["NVIDIA Build"], _quiet, self._log)
        if self.cancel_event.is_set():
            return None

        # 4. Infra
        self._chat("🟡 [Google] Git/Terminal Lead is planning...\n", tag="pilot")
        git_res, _ = chat_cloud_streaming(
            "gemini-2.5-flash",
            [{"role": "system", "content": "List briefly which files will change and which terminal commands will be needed."},
             {"role": "user", "content": f"Optimized plan:\n{perf_res}"}],
            [], google_key, PROVIDER_BASE_URLS["Google AI Studio"], _quiet, self._log)
        if self.cancel_event.is_set():
            return None

        # 5. Final judge runs the normal tool loop with the consensus as context
        self._chat("🐙 [GitHub] Chief Judge (DeepSeek-R1) is producing the final code...\n", tag="pilot")
        self.provider = "GitHub Models"
        self.token = github_key
        self.model = "deepseek/DeepSeek-R1"
        return (
            "\n\n[TEAM CONSENSUS REPORT — use this to implement the task with your tools]\n"
            f"## Architecture\n{mimar_res}\n\n## QA\n{qa_res}\n\n## Performance\n{perf_res}\n\n## Infra\n{git_res}\n"
        )

    # ── main loop ─────────────────────────────────────────
    def run(self):
        self.is_running = True
        self.cancel_event.clear()
        extra_context = ""

        try:
            self._log("═" * 40)
            self._log(f"Agent started | Mode: {self.run_mode} | Model: {self.model} ({self.provider})")

            if self.run_mode == "Auto-Pilot":
                self._autopilot_route()
            elif self.run_mode == "Software Office":
                extra_context = self._software_office() or ""
                if self.cancel_event.is_set():
                    self._chat("\n⏹ Task cancelled.\n", tag="system")
                    return

            system_prompt = SYSTEM_PROMPT + extra_context
            if self.active_file_context:
                system_prompt += (
                    f"\n\n[NOTE] File the user is focused on ({self.active_file_context['filepath']}):\n"
                    f"{self.active_file_context['content'][:20000]}\n"
                )

            coder_msgs = [{"role": "system", "content": system_prompt}] + self._normalized_history()
            max_steps = 15

            for step in range(max_steps):
                if self.cancel_event.is_set():
                    self._chat("\n⏹ Task stopped by user.\n", tag="system")
                    break

                self._log(f"[Step {step + 1}] Model is thinking...")
                content, tool_calls = self._call_model(coder_msgs)

                if isinstance(content, str) and content.startswith("ERROR:"):
                    self._chat(f"\n⚠️ Model error: {content[6:250]}\n", tag="system")
                    break

                assistant_msg = {"role": "assistant", "content": content or ""}
                if tool_calls:
                    assistant_msg["tool_calls"] = self._serialize_tool_calls(tool_calls)

                coder_msgs.append(assistant_msg)
                self.messages.append(assistant_msg)

                if not tool_calls:
                    self._chat("\n✅ Task completed.\n", tag="system")
                    break

                self._log(f"[Step {step + 1}] Executing {len(tool_calls)} tool(s)...")
                for tc in tool_calls:
                    if self.cancel_event.is_set():
                        break
                    result = self._execute_tool(tc)
                    tool_name = tc.get("function", {}).get("name") if isinstance(tc, dict) else tc.function.name
                    tool_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                    tool_result_msg = {"role": "tool", "content": result, "name": tool_name}
                    if tool_id:
                        tool_result_msg["tool_call_id"] = tool_id
                    coder_msgs.append(tool_result_msg)
                    self.messages.append(tool_result_msg)
            else:
                self._chat("\n⚠️ Maximum step count reached.\n", tag="system")

        finally:
            self.is_running = False
            self._log("═" * 40)

    # ── model call & formatting ───────────────────────────
    def _call_model(self, coder_msgs):
        if self.provider in PROVIDER_BASE_URLS or any(
            k in self.provider for k in ("GitHub", "Groq", "Google", "NVIDIA")
        ):
            base_url = None
            for key, url in PROVIDER_BASE_URLS.items():
                if key.split()[0] in self.provider:
                    base_url = url
                    break
            model_id = resolve_model_id(self.provider, self.model)
            return chat_cloud_streaming(
                model_id, coder_msgs, TOOLS_DEF, self.token, base_url, self._chat, self._log
            )

        # Local Ollama
        from ollama_client import chat_with_tools, ensure_model_exists
        ensure_model_exists(self.model, chat_callback=self._chat)
        content, tool_calls = chat_with_tools(self.model, coder_msgs, TOOLS_DEF, self._log)
        if content and not content.startswith("ERROR:"):
            parser = StreamingThinkParser(self._chat)
            parser.add_chunk(content + "\n")
            parser.flush()
        return content, tool_calls

    @staticmethod
    def _serialize_tool_calls(tool_calls):
        safe = []
        for i, tc in enumerate(tool_calls):
            if isinstance(tc, dict):
                safe.append(tc)
            else:
                args = getattr(tc.function, "arguments", "{}")
                if isinstance(args, dict):
                    args = json.dumps(args)
                safe.append({
                    "id": getattr(tc, "id", None) or f"call_{i}",
                    "type": "function",
                    "function": {"name": getattr(tc.function, "name", ""), "arguments": args},
                })
        return safe

    def _normalized_history(self):
        """Normalize past messages for the current provider (Ollama wants dict
        arguments; OpenAI-compatible APIs want JSON strings + ids)."""
        is_local = "Local" in self.provider
        normalized = []
        for msg in self.messages:
            new_msg = dict(msg)
            if new_msg.get("tool_calls"):
                formatted = []
                for i, tc in enumerate(new_msg["tool_calls"]):
                    fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                    name = fn.get("name", "")
                    args = fn.get("arguments", "{}")
                    tid = (tc.get("id") if isinstance(tc, dict) else None) or f"call_{i}"

                    if isinstance(args, str):
                        try:
                            args_dict = json.loads(args)
                        except ValueError:
                            args_dict = {}
                        args_str = args
                    else:
                        args_dict = args or {}
                        try:
                            args_str = json.dumps(args_dict)
                        except (TypeError, ValueError):
                            args_str = "{}"

                    if is_local:
                        formatted.append({"function": {"name": name, "arguments": args_dict}})
                    else:
                        formatted.append({
                            "id": tid, "type": "function",
                            "function": {"name": name, "arguments": args_str},
                        })
                new_msg["tool_calls"] = formatted
            normalized.append(new_msg)
        return normalized
