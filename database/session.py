import logging
from datetime import datetime
from .connection import get_connection

logger = logging.getLogger(__name__)

INTEGRITY_RULES = {
    "Candidate's Face is Not Visible": 2,
    "Multiple Faces are Visible": 5,
    "Face Detection Violation for Over 5s": 8,
    "Candidate Switched to Another Tab": 5,  # This is for the FIRST switch
    "Exam Window Lost Focus": 3,  # This is for focus loss events
    "Candidate Paused the Exam": 8,
}

# Note: "Tab Returned" events do NOT deduct points

def get_latest_session(candidate_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT *
FROM session
WHERE candidate_id=?
ORDER BY session_id DESC
LIMIT 1
    """, (candidate_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None

def start_session(candidate_id):
    con = get_connection()
    cur = con.cursor()
    start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
INSERT INTO session(candidate_id, start_time, status, total_absence_duration, total_tab_switches, current_absence_start, face_present, face_missing_logged, prolonged_logged)
VALUES(?,?,?,0,0,NULL,1,0,0)
    """, (candidate_id, start, "Running"))
    con.commit()
    session_id = cur.lastrowid
    con.close()
    return session_id

def update_session_status(session_id, status):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
UPDATE session
SET status=?
WHERE session_id=?
    """, (status, session_id))
    con.commit()
    con.close()

def end_session(session_id, total_absence_duration, total_tab_switches):
    con = get_connection()
    cur = con.cursor()
    end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
UPDATE session
SET end_time=?, status=?, total_absence_duration=?, total_tab_switches=?
WHERE session_id=?
    """, (end, "Completed", total_absence_duration, total_tab_switches, session_id))
    con.commit()
    con.close()

def get_session(session_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM session WHERE session_id=?", (session_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None

def update_monitor_state(session_id, total_absence_duration, current_absence_start, total_tab_switches, face_present, face_missing_logged, prolonged_logged):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
UPDATE session
SET
    total_absence_duration=?,
    current_absence_start=?,
    total_tab_switches=?,
    face_present=?,
    face_missing_logged=?,
    prolonged_logged=?
WHERE session_id=?
    """,(
        total_absence_duration,
        current_absence_start,
        total_tab_switches,
        face_present,
        face_missing_logged,
        prolonged_logged,
        session_id
    ))
    con.commit()
    con.close()

def get_monitor_state(session_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT total_absence_duration, total_tab_switches, current_absence_start, face_present, face_missing_logged, prolonged_logged
FROM session
WHERE session_id=?
    """,(session_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None

def increment_tab_switch(session_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
UPDATE session
SET total_tab_switches = total_tab_switches + 1
WHERE session_id=?
    """,(session_id,))
    con.commit()
    con.close()

def update_total_absence(session_id, total):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
UPDATE session
SET total_absence_duration=?
WHERE session_id=?
    """,(total, session_id))
    con.commit()
    con.close()

def get_session_summary(session_id):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT status, total_absence_duration, total_tab_switches
FROM session
WHERE session_id=?
    """,(session_id,))
    row = cur.fetchone()
    con.close()
    return dict(row) if row else None

def update_integrity_score(cur, session_id, remarks):
    deduction = INTEGRITY_RULES.get(remarks)
    if deduction is None:
        return
    cur.execute(
        "SELECT integrity_score FROM session WHERE session_id=?",
        (session_id,)
    )
    row = cur.fetchone()
    if row:
        score = row["integrity_score"]
        score = max(0, score - deduction)
        cur.execute(
            "UPDATE session SET integrity_score=? WHERE session_id=?",
            (score, session_id)
        )

def get_sessions_by_candidate(candidate_id):
    """Get all sessions for a specific candidate"""
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
        SELECT *
        FROM session
        WHERE candidate_id=?
        ORDER BY session_id DESC
    """, (candidate_id,))
    rows = cur.fetchall()
    con.close()
    return [dict(row) for row in rows]