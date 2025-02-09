"""
Dashboard Logger Class
"""
import sqlite3, os, uuid
from .config import (
    CONFIGURATION_PATH
)

class DashboardLogger:
    def __init__(self):
        self.loggerdb = sqlite3.connect(os.path.join(CONFIGURATION_PATH, 'db', 'wgdashboard_log.db'),
                                        check_same_thread=False)
        self.loggerdb.row_factory = sqlite3.Row
        self.__createLogDatabase()
        self.log(Message="WGDashboard started")

    def __createLogDatabase(self):
        with self.loggerdb:
            loggerdbCursor = self.loggerdb.cursor()
            existingTable = loggerdbCursor.execute("SELECT name from sqlite_master where type='table'").fetchall()
            existingTable = [t['name'] for t in existingTable]
            if "DashboardLog" not in existingTable:
                loggerdbCursor.execute(
                    "CREATE TABLE DashboardLog (LogID VARCHAR NOT NULL, LogDate DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now', 'localtime')), URL VARCHAR, IP VARCHAR, Status VARCHAR, Message VARCHAR, PRIMARY KEY (LogID))")
            if self.loggerdb.in_transaction:
                self.loggerdb.commit()

    def log(self, URL: str = "", IP: str = "", Status: str = "true", Message: str = "") -> bool:
        pass
        try:
            with self.loggerdb:
                loggerdbCursor = self.loggerdb.cursor()
                loggerdbCursor.execute(
                    "INSERT INTO DashboardLog (LogID, URL, IP, Status, Message) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), URL, IP, Status, Message,))
                if self.loggerdb.in_transaction:
                    self.loggerdb.commit()
                return True
        except Exception as e:
            print(f"[WGDashboard] Access Log Error: {str(e)}")
            return False
