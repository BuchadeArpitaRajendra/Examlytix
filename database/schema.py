import logging
from .connection import get_connection

logger = logging.getLogger(__name__)

CANDIDATE_TABLE = """
CREATE TABLE IF NOT EXISTS candidate(
    candidate_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL UNIQUE,
    password TEXT NOT NULL,
    age INTEGER,
    exam_subject TEXT,
    exam_date TEXT,
    exam_time TEXT,
    photo_path TEXT,
    created_at TEXT
)
"""

SESSION_TABLE = """
CREATE TABLE IF NOT EXISTS session(
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    total_absence_duration INTEGER DEFAULT 0,
    total_tab_switches INTEGER DEFAULT 0,
    current_absence_start INTEGER,
    face_present INTEGER DEFAULT 1,
    face_missing_logged INTEGER DEFAULT 0,
    prolonged_logged INTEGER DEFAULT 0,
    integrity_score INTEGER DEFAULT 100,
    FOREIGN KEY(candidate_id) REFERENCES candidate(candidate_id)
)
"""

EVENT_LOG = """
CREATE TABLE IF NOT EXISTS event_log(
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT,
    session_id INTEGER,
    event_type TEXT,
    timestamp TEXT,
    remarks TEXT,
    screenshot_path TEXT
)
"""

def create_tables():
    try:
        con = get_connection()
        logger.info("Connecting to Database")
        cur = con.cursor()
        logger.info("Creating Candidate Table")
        cur.execute(CANDIDATE_TABLE)
        logger.info("Creating Session Table")
        cur.execute(SESSION_TABLE)
        logger.info("Creating Event Log Table")
        cur.execute(EVENT_LOG)
        con.commit()
        con.close()
        logger.info("All Tables Created Successfully")
    except Exception:
        logger.exception("Failed while Creating Tables")
        raise