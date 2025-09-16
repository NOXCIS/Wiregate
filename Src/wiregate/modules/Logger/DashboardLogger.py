"""
Dashboard Logger Class
"""
import os, uuid, threading, logging, json
from ...modules.ConfigEnv import CONFIGURATION_PATH
from ..DataBase.DataBaseManager import get_redis_manager

class DashboardLogger:
    def __init__(self, CONFIGURATION_PATH):
        self.redis_manager = get_redis_manager()
        self.logs_key = "wiregate:dashboard_logs"
        self.log_counter_key = "wiregate:dashboard_logs:counter"
        self.__initialize_redis()
        self.log(Message="WireGate started")
    def __initialize_redis(self):
        """Initialize Redis with log counter if not exists"""
        if not self.redis_manager.redis_client.exists(self.log_counter_key):
            self.redis_manager.redis_client.set(self.log_counter_key, 0)

    def __get_next_log_id(self) -> str:
        """Generate next log ID using Redis counter"""
        return str(self.redis_manager.redis_client.incr(self.log_counter_key))

    def log(self, URL: str = "", IP: str = "", Status: str = "true", Message: str = "") -> bool:
        try:
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
