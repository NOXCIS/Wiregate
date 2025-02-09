"""
Dashboard Logger Class
"""
import sqlite3, os, uuid, threading, logging
from .config import (
    CONFIGURATION_PATH
)

class DashboardLogger:
    def __init__(self):
        self.lock = threading.Lock()
        self.db_path = os.path.join(CONFIGURATION_PATH, 'db', 'wgdashboard_log.db')
        self.__createLogDatabase()
        self.log(Message="WGDashboard started")

    def __get_connection(self):
        """Helper method to return a new SQLite connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def __createLogDatabase(self):
        """Create the DashboardLog table if it does not exist."""
        with self.__get_connection() as conn:
            cursor = conn.cursor()
            existingTables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            existingTables = [t['name'] for t in existingTables]
            if "DashboardLog" not in existingTables:
                cursor.execute(
                    "CREATE TABLE DashboardLog ("
                    "LogID VARCHAR NOT NULL, "
                    "LogDate DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')), "
                    "URL VARCHAR, IP VARCHAR, Status VARCHAR, Message VARCHAR, "
                    "PRIMARY KEY (LogID)"
                    ")"
                )
                conn.commit()

    def log(self, URL: str = "", IP: str = "", Status: str = "true", Message: str = "") -> bool:
        """
        Insert a log entry into the DashboardLog database table.
        """
        try:
            with self.lock:
                with self.__get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO DashboardLog (LogID, URL, IP, Status, Message) VALUES (?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), URL, IP, Status, Message)
                    )
                    conn.commit()
            return True

        except Exception as e:
            # Forward error details to the waitress logger so that they are output to the console.
            logging.getLogger('waitress').error(f"[WGDashboard] Access Log Error: {str(e)}")
            return False
