from pynput import keyboard, mouse
from pynput.mouse import Controller as MouseController
from datetime import datetime
import subprocess
import json
import uuid

LOG_FILE = "input_events.jsonl"
mouse_controller = MouseController()

def get_active_app():
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of (processes where frontmost is true)'],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Unknown ({e})"

def log_event(event_type, key_or_button):
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

# Keyboard Handlers
def on_key_press(key):
    log_event("key_press", getattr(key, 'char', key))

def on_key_release(key):
    if key == keyboard.Key.esc:
        return False  # Stops both listeners

# Mouse Handlers
def on_click(x, y, button, pressed):
    if pressed:
        log_event("mouse_click", button)

# Start listeners
if __name__ == "__main__":
    print("Tracking keys and clicks. Press ESC to stop.")

    keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    mouse_listener = mouse.Listener(on_click=on_click)

    keyboard_listener.start()
    mouse_listener.start()

    keyboard_listener.join()
    mouse_listener.stop()
