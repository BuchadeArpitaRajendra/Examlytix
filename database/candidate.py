import logging
from datetime import datetime
from .connection import get_connection

logger = logging.getLogger(__name__)

def create_candidate(candidate_id, name, email, password, age, exam_subject, exam_date, exam_time, photo_path):
    con = get_connection()
    cur = con.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("Creating Candidate %s with ID %s and Mail %s at %s", name, candidate_id, email, created_at)
    cur.execute("""
INSERT INTO candidate(candidate_id, name, email, password, age, exam_subject, exam_date, exam_time, photo_path, created_at)
VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (candidate_id, name, email, password, age, exam_subject, exam_date, exam_time, photo_path, created_at))
    con.commit()
    con.close()

def get_candidate_by_email(email):
    con = get_connection()
    cur = con.cursor()
    logger.info("Fetching Candidate with Mail %s", email)
    cur.execute("""
SELECT *
FROM candidate
WHERE email=?
    """, (email,))
    row = cur.fetchone()
    con.close()
    return row

def get_candidate_by_id(candidate_id):
    con = get_connection()
    cur = con.cursor()
    logger.info("Fetching Candidate with ID %s", candidate_id)
    cur.execute("""
SELECT *
FROM candidate
WHERE candidate_id=?
    """, (candidate_id,))
    row = cur.fetchone()
    con.close()
    return row

def login(email, password):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""
SELECT candidate_id, name
FROM candidate
WHERE email=? AND password=?
    """, (email, password))
    user = cur.fetchone()
    con.close()
    return user