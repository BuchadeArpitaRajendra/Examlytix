import sqlite3
import logging

logger = logging.getLogger(__name__)
DATABASE = "exam.db"

def get_connection():
    try:
        con = sqlite3.connect(DATABASE, timeout = 15)
        con.row_factory = sqlite3.Row
        logger.info("Database Connection Opened")
        return con
    except Exception:
        logger.warning("Failed to Connect Database")
        raise