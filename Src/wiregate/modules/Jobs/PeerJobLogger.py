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
        self.db_manager = None
        self._is_sqlite = False
        self.logs: List[Log] = []
        self._init_done = False
        
    async def _ensure_initialized(self):
        """Ensure database manager is initialized"""
        if not self._init_done:
            self.db_manager = await get_redis_manager()
            self._is_sqlite = isinstance(self.db_manager, SQLiteDatabaseManager)
            await self._initialize_database()
            self._init_done = True
        
    async def _initialize_database(self):
        """Initialize database tables for logs"""
        try:
            # Ensure logs table exists
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                if not await self.db_manager.table_exists('PeerJobLogs'):
                    logger.info("Creating PeerJobLogs table...")
                    await self.db_manager.create_logs_table()
            else:
                if not self.db_manager.table_exists('PeerJobLogs'):
                    logger.info("Creating PeerJobLogs table...")
                    self.db_manager.create_logs_table()
            logger.debug("PeerJobLogs table ready")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    async def log(self, JobID: str, Status: bool = True, Message: str = "") -> bool:
        await self._ensure_initialized()
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
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                await self.db_manager.insert_record('PeerJobLogs', log_id, log_data)
            else:
                self.db_manager.insert_record('PeerJobLogs', log_id, log_data)
            
            return True
        except Exception as e:
            logger.error(f"Peer Job Log Error: {str(e)}")
            return False

    async def getLogs(self, all: bool = False, configName=None) -> list[Log]:
        await self._ensure_initialized()
        logs: list[Log] = []
        try:
            from ..Core import AllPeerJobs
            allJobs = AllPeerJobs.getAllJobs(configName)
            allJobsID = [x.JobID for x in allJobs]
            
            # Get all logs from database
            if isinstance(self.db_manager, SQLiteDatabaseManager):
                records = await self.db_manager.get_all_records('PeerJobLogs')
            else:
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
