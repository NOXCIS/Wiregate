"""
Peer Job Logger
"""
import os, uuid, json
from typing import List
from datetime import datetime
from ..Logger import Log
from ..ConfigEnv import (
    CONFIGURATION_PATH
)
from ..DataBase import get_redis_manager

class MockRedisClient:
    """Mock Redis client for when Redis is not available"""
    def __init__(self):
        self._data = {}
    
    def exists(self, key):
        return key in self._data
    
    def set(self, key, value):
        self._data[key] = value
    
    def incr(self, key):
        if key not in self._data:
            self._data[key] = 0
        self._data[key] += 1
        return self._data[key]
    
    def hset(self, key, field, value):
        if key not in self._data:
            self._data[key] = {}
        self._data[key][field] = value
    
    def hgetall(self, key):
        return self._data.get(key, {})
    
    def lpush(self, key, value):
        if key not in self._data:
            self._data[key] = []
        self._data[key].insert(0, value)
    
    def lrange(self, key, start, end):
        data = self._data.get(key, [])
        if end == -1:
            return data[start:]
        return data[start:end+1]
    
    def hkeys(self, key):
        data = self._data.get(key, {})
        return list(data.keys())

class PeerJobLogger:
    def __init__(self):
        self.redis_manager = None
        self.job_logs_key = "wiregate:job_logs"
        self.log_counter_key = "wiregate:job_logs:counter"
        self.logs: List[Log] = []
        self._initialized = False
        
    def _ensure_redis_connection(self):
        """Ensure Redis connection is established"""
        if self.redis_manager is None:
            try:
                self.redis_manager = get_redis_manager()
                self.__initialize_redis()
                self._initialized = True
            except Exception as e:
                print(f"Warning: Could not connect to Redis: {e}")
                # Create a mock redis manager for fallback
                class MockRedisManager:
                    def __init__(self):
                        self.redis_client = MockRedisClient()
                self.redis_manager = MockRedisManager()
                self._initialized = True

    def __initialize_redis(self):
        """Initialize Redis with log counter if not exists"""
        if not self.redis_manager.redis_client.exists(self.log_counter_key):
            self.redis_manager.redis_client.set(self.log_counter_key, 0)

    def log(self, JobID: str, Status: bool = True, Message: str = "") -> bool:
        try:
            self._ensure_redis_connection()
            log_id = str(uuid.uuid4())
            log_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare log data
            log_data = {
                'LogID': log_id,
                'JobID': JobID,
                'LogDate': log_date,
                'Status': str(Status),
                'Message': Message
            }
            
            # Save to Redis
            self.redis_manager.redis_client.hset(
                self.job_logs_key, 
                log_id, 
                json.dumps(log_data)
            )
            
            return True
        except Exception as e:
            print(f"[WGDashboard] Peer Job Log Error: {str(e)}")
            return False

    def getLogs(self, all: bool = False, configName=None) -> list[Log]:
        logs: list[Log] = []
        try:
            from ..Core import AllPeerJobs
            allJobs = AllPeerJobs.getAllJobs(configName)
            allJobsID = [x.JobID for x in allJobs]
            
            # Get all job log keys
            log_keys = self.redis_manager.redis_client.hkeys(self.job_logs_key)
            
            for log_key in log_keys:
                log_data = self.redis_manager.redis_client.hget(self.job_logs_key, log_key)
                if log_data:
                    log_dict = json.loads(log_data)
                    # Filter by job IDs if configName is specified
                    if not configName or log_dict.get('JobID') in allJobsID:
                        logs.append(Log(
                            log_dict['LogID'], 
                            log_dict['JobID'], 
                            log_dict['LogDate'], 
                            log_dict['Status'] == 'True', 
                            log_dict['Message']
                        ))
            
            # Sort by date descending
            logs.sort(key=lambda x: x.LogDate, reverse=True)
            
        except Exception as e:
            print(f"[PeerJobLogger] Error getting logs: {e}")
            return logs
        return logs


JobLogger: PeerJobLogger = PeerJobLogger()
