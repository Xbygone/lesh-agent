import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove workspace check in run()
content = content.replace("if not self.agent or not self.workspace_path:\n            self.ui.append_chat(\"Agent is not initialized or workspace not selected.\", tag=\"system\")\n            return", 
                          "if not self.agent:\n            self.ui.append_chat(\"Agent is not initialized.\", tag=\"system\")\n            return")

# 2. Update get_sessions_dir()
old_sess = '''    def get_sessions_dir(self):
        if not self.workspace_path:
            return None
        d = os.path.join(self.workspace_path, ".lesh", "sessions")
        os.makedirs(d, exist_ok=True)
        return d'''
new_sess = '''    def get_sessions_dir(self):
        if not self.workspace_path:
            d = os.path.expanduser("~/.lesh/sessions")
        else:
            d = os.path.join(self.workspace_path, ".lesh", "sessions")
        os.makedirs(d, exist_ok=True)
        return d'''
content = content.replace(old_sess, new_sess)

# 3. Remove workspace check in send_message()
old_send = '''    def send_message(self):
        msg = self.ui.chat_input.get().strip()
        if not msg:
            return
            
        if not self.workspace_path:
            self.ui.append_chat("Error: Select a workspace first.", tag="system")
            return'''
new_send = '''    def send_message(self):
        msg = self.ui.chat_input.get().strip()
        if not msg:
            return'''
content = content.replace(old_send, new_send)

# 4. Update refresh_diff()
old_diff = '''    def refresh_diff(self):
        if not self.workspace_path:
            return
        diff = get_diff(self.workspace_path) or "No changes detected."'''
new_diff = '''    def refresh_diff(self):
        if not self.workspace_path:
            self.ui.diff_text = "No workspace selected."
            if hasattr(self.ui, 'diff_textbox'):
                self.ui.diff_textbox.configure(state="normal")
                self.ui.diff_textbox.delete("1.0", "end")
                self.ui.diff_textbox.insert("1.0", self.ui.diff_text)
                self.ui.diff_textbox.configure(state="disabled")
            return
        diff = get_diff(self.workspace_path) or "No changes detected."'''
content = content.replace(old_diff, new_diff)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("main.py patched successfully")
