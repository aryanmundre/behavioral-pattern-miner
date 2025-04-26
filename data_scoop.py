import csv
import datetime
import threading

from pynput import keyboard, mouse
from AppKit import NSWorkspace  # pip install pyobjc

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def utc_now():
    """ISO-format UTC timestamp with millisecond precision."""
    return datetime.datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

def get_active_app_name():
    """
    Returns the name of the frontmost application (e.g. 'Safari', 'Visual Studio Code').
    """
    return NSWorkspace.sharedWorkspace().frontmostApplication().localizedName()

# ----------------------------------------------------------------------------
# CSV Logger setup
# ----------------------------------------------------------------------------
csv_file = open('events_mac.csv', 'w', newline='', encoding='utf-8')
writer   = csv.writer(csv_file)
writer.writerow([
    'id',
    'timestamp',
    'event_type',
    'key_or_button',
    'position_x',
    'position_y',
    'active_app',
])

event_id = 0
lock     = threading.Lock()

def log_event(event_type, key_or_button, x=None, y=None):
    global event_id
    with lock:
        event_id += 1
        writer.writerow([
            event_id,
            utc_now(),
            event_type,
            key_or_button,
            x if x is not None else 'NULL',
            y if y is not None else 'NULL',
            get_active_app_name(),
        ])
        csv_file.flush()

# ----------------------------------------------------------------------------
# Keyboard listener
# ----------------------------------------------------------------------------
def on_key_press(key):
    try:
        k = key.char  # single‐character keys
    except AttributeError:
        k = str(key)  # special keys, e.g. 'Key.enter'
    log_event('keypress', k)

kb_listener = keyboard.Listener(on_press=on_key_press)
kb_listener.start()

# ----------------------------------------------------------------------------
# Mouse listener
# ----------------------------------------------------------------------------
def on_click(x, y, button, pressed):
    if pressed:
        # button.name is 'left', 'right', 'middle'
        log_event('click', button.name, x, y)

mouse_listener = mouse.Listener(on_click=on_click)
mouse_listener.start()

# ----------------------------------------------------------------------------
# Keep the script alive until Ctrl-C
# ----------------------------------------------------------------------------
print("Logging to events_mac.csv. Press Ctrl-C to stop.")
try:
    kb_listener.join()
    mouse_listener.join()
except KeyboardInterrupt:
    print("\nStopped.")
    csv_file.close()
