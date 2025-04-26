from pynput import keyboard, mouse
from pynput.mouse import Controller as MouseController, Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener
from datetime import datetime
import subprocess
import json
import uuid
import os
import shutil

LOG_FILE    = "input_events.jsonl"
BACKUP_FILE = "input_events_backup.jsonl"
MAX_INPUTS  = 10000

mouse_controller = MouseController()

# 1) Initialize line_counter at module scope
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r") as f:
        line_counter = sum(1 for _ in f)
else:
    line_counter = 0

def get_active_app():
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of (processes where frontmost is true)'],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Unknown ({e})"

def rotate_if_needed():
    global line_counter
    if line_counter < MAX_INPUTS:
        return
    # Delete old backup so only the latest is kept
    if os.path.exists(BACKUP_FILE):
        os.remove(BACKUP_FILE)
    # Copy and then truncate
    shutil.copy2(LOG_FILE, BACKUP_FILE)
    open(LOG_FILE, "w").close()
    print(f"[ROTATE] backed up {MAX_INPUTS} lines → {BACKUP_FILE}", flush=True)
    line_counter = 0

def log_event(event_type, key_or_button):
    """
    Append one event, bump counter, rotate if needed,
    and print a debug line so you can see it in real time.
    """
    global line_counter
    event_data = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "key_or_button": str(key_or_button),
        "position_x": mouse_controller.position[0],
        "position_y": mouse_controller.position[1],
        "active_app": get_active_app()
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event_data) + "\n")

    line_counter += 1
    print(f"[LOGGED] #{line_counter}: {event_type} → {key_or_button}", flush=True)
    rotate_if_needed()

# Keyboard Handlers
def on_key_press(key):
    log_event("key_press", getattr(key, 'char', key))

def on_key_release(key):
    if key == keyboard.Key.esc:
        # Return False to stop *both* listeners
        return False

# Mouse Handlers
def on_click(x, y, button, pressed):
    if pressed:
        log_event("mouse_click", button)

if __name__ == "__main__":
    print("Press ESC to stop")

    k_listener = KeyboardListener(on_press=on_key_press, on_release=on_key_release)
    m_listener = MouseListener(on_click=on_click)

    k_listener.start()
    m_listener.start()

    # Wait for both to finish
    k_listener.join()
    m_listener.join()

    print("Listeners stopped. Goodbye.", flush=True)
