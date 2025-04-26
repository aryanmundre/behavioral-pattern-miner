from pynput import keyboard
from pynput.mouse import Controller as MouseController
from datetime import datetime
import json
import uuid
import os
import subprocess

mouse = MouseController()
LOG_FILE = "keystrokes.jsonl"  # Each line is a separate JSON object

def get_active_app():
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of (processes where frontmost is true)'],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Unknown ({e})"

def log_event(key):
    event_data = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "event_type": "key_press",
        "key_or_button": str(getattr(key, 'char', key)),  # Fallback for special keys
        "position_x": mouse.position[0],
        "position_y": mouse.position[1],
        "active_app": get_active_app()
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event_data) + "\n")

def on_press(key):
    log_event(key)

def on_release(key):
    if key == keyboard.Key.esc:
        return False  # Stop the logger

if __name__ == "__main__":
    print("Keylogger started. Press ESC to stop.")
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
