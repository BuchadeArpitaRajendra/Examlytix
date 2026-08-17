import logging
from datetime import datetime
from .connection import get_connection
from .session import update_integrity_score

logger = logging.getLogger(__name__)

def log_event(candidate_id, session_id, event_type, remarks, screenshot_path=None):
    con = get_connection()
    cur = con.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
INSERT INTO event_log(candidate_id, session_id, event_type, timestamp, remarks, screenshot_path)
VALUES(?,?,?,?,?,?)
    """, (candidate_id, session_id, event_type, timestamp, remarks,screenshot_path))
    update_integrity_score(cur, session_id, remarks)
    con.commit()
    con.close()

def get_events_for_session(session_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT event_id, candidate_id, session_id, event_type, timestamp, remarks, screenshot_path
FROM event_log
WHERE session_id=?
ORDER BY event_id
    """, (session_id,))
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]

def get_event(event_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT *
FROM event_log
WHERE event_id=?
    """, (event_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None