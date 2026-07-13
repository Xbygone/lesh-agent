import re

with open("tools.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Patch read_file
old_read = '''def read_file(filepath, workspace_path):
    """
    Belirtilen dosyayı okur. Güvenlik için sadece workspace_path içindeki dosyalara izin verir.
    """
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return "Error: Permission denied. Can only read files inside the workspace."'''
new_read = '''def read_file(filepath, workspace_path):
    """
    Belirtilen dosyayı okur. Güvenlik için sadece workspace_path içindeki dosyalara izin verir.
    """
    if not workspace_path:
        return "Error: No workspace selected. File operations are disabled."
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return "Error: Permission denied. Can only read files inside the workspace."'''
content = content.replace(old_read, new_read)

# 2. Patch write_file
old_write = '''def write_file(filepath, content, workspace_path):
    """
    Belirtilen dosyaya (workspace_path içinde) içerik yazar.
    """
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return "Error: Permission denied. Can only write files inside the workspace."'''
new_write = '''def write_file(filepath, content, workspace_path):
    """
    Belirtilen dosyaya (workspace_path içinde) içerik yazar.
    """
    if not workspace_path:
        return "Error: No workspace selected. File operations are disabled."
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return "Error: Permission denied. Can only write files inside the workspace."'''
content = content.replace(old_write, new_write)

# 3. Patch list_directory
old_list = '''def list_directory(filepath, workspace_path):
    """
    Belirtilen klasörün içeriğini listeler.
    """
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return "Error: Permission denied."'''
new_list = '''def list_directory(filepath, workspace_path):
    """
    Belirtilen klasörün içeriğini listeler.
    """
    if not workspace_path:
        return "Error: No workspace selected. File operations are disabled."
    abs_path = os.path.abspath(os.path.join(workspace_path, filepath))
    if not abs_path.startswith(os.path.abspath(workspace_path)):
        return "Error: Permission denied."'''
content = content.replace(old_list, new_list)

# 4. Patch run_terminal_command
old_run = '''def run_terminal_command(command, workspace_path):
    """
    Güvenli (onaylı) terminal komutu çalıştırır.
    """
    try:
        # Popen ile komutu çalıştır'''
new_run = '''def run_terminal_command(command, workspace_path):
    """
    Güvenli (onaylı) terminal komutu çalıştırır.
    """
    if not workspace_path:
        return "Error: No workspace selected. Terminal operations are disabled."
    try:
        # Popen ile komutu çalıştır'''
content = content.replace(old_run, new_run)

with open("tools.py", "w", encoding="utf-8") as f:
    f.write(content)
print("tools.py patched successfully")
