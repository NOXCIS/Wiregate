"""
Peer Job Logger
"""
import os, uuid, json
import logging
from typing import List
from datetime import datetime
from ..Logger import Log
from ..Config import CONFIGURATION_PATH, DASHBOARD_TYPE
from ..DataBase import get_redis_manager, SQLiteDatabaseManager

# Set up logger
logger = logging.getLogger(__name__)

class PeerJobLogger:
    def __init__(self):
        self.db_manager = get_redis_manager()
        self._is_sqlite = isinstance(self.db_manager, SQLiteDatabaseManager)
        self.logs: List[Log] = []
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize database tables for logs"""
        try:
            # Ensure logs table exists
            if not self.db_manager.table_exists('PeerJobLogs'):
                logger.info("Creating PeerJobLogs table...")
                self.db_manager.create_logs_table()
            logger.debug("PeerJobLogs table ready")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def log(self, JobID: str, Status: bool = True, Message: str = "") -> bool:
        try:
            log_id = str(uuid.uuid4())
            log_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare log data
            log_data = {
                'id': log_id,  # Use LogID as the primary key
                'LogID': log_id,
                'JobID': JobID,
                'LogDate': log_date,
                'Status': Status,
                'Message': Message
            }
            
            # Save to database
            self.db_manager.insert_record('PeerJobLogs', log_id, log_data)
            
            return True
        except Exception as e:
            logger.error(f"Peer Job Log Error: {str(e)}")
            return False

    def getLogs(self, all: bool = False, configName=None) -> list[Log]:
        logs: list[Log] = []
        try:
            from ..Core import AllPeerJobs
            allJobs = AllPeerJobs.getAllJobs(configName)
            allJobsID = [x.JobID for x in allJobs]
            
            # Get all logs from database
            records = self.db_manager.get_all_records('PeerJobLogs')
            
            for record in records:
                try:
                    # Filter by job IDs if configName is specified
                    if not configName or record.get('JobID') in allJobsID:
                        status = record.get('Status')
                        # Handle both boolean and string representations
                        if isinstance(status, str):
                            status = status.lower() in ('true', '1', 'yes')
                        
                        logs.append(Log(
                            record.get('LogID'), 
                            record.get('JobID'), 
                            record.get('LogDate'), 
                            status, 
                            record.get('Message', '')
                        ))
                except Exception as e:
                    logger.warning(f"Failed to parse log record: {e}")
                    continue
            
            # Sort by date descending
            logs.sort(key=lambda x: x.LogDate, reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            return logs
        return logs


JobLogger: PeerJobLogger = PeerJobLogger()
