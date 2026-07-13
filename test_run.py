from main import MainApp
import tkinter as tk

root = tk.Tk()
app = MainApp()
# Initialize UI components that might be missing
app.ui.mode_selector.set('Standart')
app.ui.combo_provider.set('Yerel (Ollama)')
app.ui.combo_model.set('qwen2.5-coder:7b')
app.ui.entry_pat.delete(0, 'end')

app._make_agent()
app.agent.add_user_message('Merhaba')
app.agent.run()
print("Run completed successfully.")
