"""Ollama client wrapper. The `ollama` package is imported lazily so the app
can still start (cloud-only mode) when it isn't installed."""

OLLAMA_HOST = "http://localhost:11434"
_client = None


def _get_client():
    global _client
    if _client is None:
        from ollama import Client
        _client = Client(host=OLLAMA_HOST)
    return _client


def check_ollama_status():
    """Checks whether the Ollama service is running."""
    try:
        _get_client().list()
        return True
    except Exception:
        return False


def get_models():
    """Returns the list of installed models."""
    try:
        response = _get_client().list()
        return [m.model for m in response.models]
    except Exception:
        return []


def ensure_model_exists(model_name, progress_callback=None, chat_callback=None):
    """Pulls the model if it is not installed."""
    models = get_models()
    if model_name in models or f"{model_name}:latest" in models:
        return True
    try:
        cmd = f"ollama pull {model_name}"
        if chat_callback:
            chat_callback(f"\n[SYSTEM] Local model not found, downloading: `$ {cmd}`\n", tag="system")
        if progress_callback:
            progress_callback(f"Downloading: {model_name}...")

        import subprocess
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        for line in process.stdout:
            line = line.strip()
            if line:
                if progress_callback:
                    progress_callback(f"Downloading: {line[:50]}...")
                if chat_callback:
                    chat_callback(f"{line}\n", tag="system")

        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"ollama pull failed (code {process.returncode})")

        if chat_callback:
            chat_callback(f"✅ {model_name} downloaded!\n", tag="system")
        return True
    except Exception as e:
        if progress_callback:
            progress_callback(f"Download error: {str(e)}")
        if chat_callback:
            chat_callback(f"❌ Download error: {str(e)}\n", tag="system")
        return False


def chat_with_tools(model_name, messages, tools, log_callback=None):
    """Native tool calling (stream=False — most stable).
    Returns: (content: str, tool_calls: list)"""
    try:
        if log_callback:
            log_callback(f"[MODEL] Calling {model_name}... ({len(messages)} messages)")

        kwargs = {"model": model_name, "messages": messages, "stream": False}
        if tools:
            kwargs["tools"] = tools

        response = _get_client().chat(**kwargs)
        msg = response.message
        content = msg.content or ""
        tool_calls = msg.tool_calls or []

        if log_callback:
            if tool_calls:
                log_callback(f"[TOOLS] Requested: {[tc.function.name for tc in tool_calls]}")
            elif content:
                log_callback(f"[REPLY] Model responded ({len(content)} chars)")

        return content, tool_calls

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR] Ollama error: {str(e)}")
        return f"ERROR: {str(e)}", []


def chat_stream_simple(model_name, messages, chunk_callback=None):
    """Streaming chat without tools."""
    try:
        response = _get_client().chat(model=model_name, messages=messages, stream=True)
        full_content = ""
        for chunk in response:
            content = chunk.message.content or ""
            if content:
                full_content += content
                if chunk_callback:
                    chunk_callback(content)
        return full_content
    except Exception as e:
        err = f"\n[ERROR]: {str(e)}\n"
        if chunk_callback:
            chunk_callback(err)
        return err
