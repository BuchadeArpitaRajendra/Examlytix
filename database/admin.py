import logging
from .connection import get_connection

logger = logging.getLogger(__name__)

def get_all_candidates():
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM candidate ORDER BY candidate_id")
    rows = cur.fetchall()
    con.close()
    # Convert to list of dicts
    return [dict(row) for row in rows]

def get_all_sessions():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT session.*, candidate.name AS candidate_name
FROM session
LEFT JOIN candidate ON candidate.candidate_id = session.candidate_id
ORDER BY session.session_id DESC
    """)
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]

def get_all_events():
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM event_log ORDER BY event_id DESC")
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]

def update_candidate_fields(candidate_id, fields):
    allowed = {"name", "email", "password", "age", "exam_subject"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    con = get_connection()
    cur = con.cursor()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    cur.execute(
        f"UPDATE candidate SET {set_clause} WHERE candidate_id=?",
        (*updates.values(), candidate_id)
    )
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed

def delete_candidate(candidate_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM event_log WHERE candidate_id=?", (candidate_id,))
    cur.execute("DELETE FROM session WHERE candidate_id=?", (candidate_id,))
    cur.execute("DELETE FROM candidate WHERE candidate_id=?", (candidate_id,))
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed

def update_session_fields(session_id, fields):
    allowed = {"status", "start_time", "end_time", "total_absence_duration", "total_tab_switches"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    con = get_connection()
    cur = con.cursor()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    cur.execute(
        f"UPDATE session SET {set_clause} WHERE session_id=?",
        (*updates.values(), session_id)
    )
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed

def delete_session(session_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM event_log WHERE session_id=?", (session_id,))
    cur.execute("DELETE FROM session WHERE session_id=?", (session_id,))
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed

def update_event_fields(event_id, fields):
    allowed = {"event_type", "remarks"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    con = get_connection()
    cur = con.cursor()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    cur.execute(
        f"UPDATE event_log SET {set_clause} WHERE event_id=?",
        (*updates.values(), event_id)
    )
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed

def delete_event(event_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM event_log WHERE event_id=?", (event_id,))
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed