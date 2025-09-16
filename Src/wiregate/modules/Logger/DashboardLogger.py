"""
Dashboard Logger Class
"""
import os, uuid, threading, logging, json
from ...modules.ConfigEnv import CONFIGURATION_PATH
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

class DashboardLogger:
    def __init__(self, CONFIGURATION_PATH):
        self.CONFIGURATION_PATH = CONFIGURATION_PATH
        self.redis_manager = None
        self.logs_key = "wiregate:dashboard_logs"
        self.log_counter_key = "wiregate:dashboard_logs:counter"
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

    def __get_next_log_id(self) -> str:
        """Generate next log ID using Redis counter"""
        self._ensure_redis_connection()
        return str(self.redis_manager.redis_client.incr(self.log_counter_key))

    def log(self, URL: str = "", IP: str = "", Status: str = "true", Message: str = "") -> bool:
        try:
            self._ensure_redis_connection()
            from datetime import datetime
            
            log_id = str(uuid.uuid4())
            log_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare log data
            log_data = {
                'LogID': log_id,
                'LogDate': log_date,
                'URL': URL,
                'IP': IP,
                'Status': Status,
                'Message': Message
            }
            
            # Save to Redis
            self.redis_manager.redis_client.hset(
                self.logs_key, 
                log_id, 
                json.dumps(log_data)
            )
            
            return True
        except Exception as e:
            print(f"[WireGate] Access Log Error: {str(e)}")
            return False
        

AllDashboardLogger: DashboardLogger = DashboardLogger(CONFIGURATION_PATH)
