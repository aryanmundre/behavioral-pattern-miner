import sqlite3
import datetime

IDLE_THRESHOLD_MINUTES = 5

def load_events(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT timestamp, app_name FROM events ORDER BY timestamp ASC')
    events = c.fetchall()
    conn.close()
    return events

def build_sessions(events):
    sessions = []
    current_session = []
    last_time = None

    for timestamp_str, app_name in events:
        timestamp = datetime.datetime.fromisoformat(timestamp_str)

        if last_time and (timestamp - last_time).total_seconds() > IDLE_THRESHOLD_MINUTES * 60:
            if current_session:
                sessions.append(current_session)
            current_session = []

        current_session.append(app_name)
        last_time = timestamp

    if current_session:
        sessions.append(current_session)

    return sessions
