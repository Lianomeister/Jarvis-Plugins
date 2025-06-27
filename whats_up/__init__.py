import os
import sys

COMMANDS = ["whats up?", "what's up", "was geht ab", "was geht?"]

def run():
    text = "whaats upp!?"
    if sys.platform.startswith("win"):
        # Schreibe den Text in eine temporäre Datei
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        os.system(f'start notepad "{temp_path}"')
    else:
        # Für andere Systeme (z.B. Linux, macOS)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as f:
            f.write(text)
            temp_path = f.name
        os.system(f'xdg-open "{temp_path}"') 