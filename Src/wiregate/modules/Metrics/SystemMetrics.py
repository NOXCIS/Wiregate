"""
System Metrics Collection
Tracks background task execution times, database query performance, and system metrics
Separate from RateLimitMetrics - focuses on system performance
"""
import time
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from ..Config import DASHBOARD_TYPE, redis_host, redis_port, redis_db, redis_password

logger = logging.getLogger(__name__)

# Try to import Redis for optional persistence
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class SystemMetrics:
    """
    System metrics collection class
    Tracks task execution times, database query performance, and system metrics
    Uses in-memory storage with optional Redis persistence (if scale mode)
    """
    
    def __init__(self, redis_client=None):
        """Initialize system metrics collector"""
        self.redis_client = redis_client
        self.use_redis = DASHBOARD_TYPE.lower() == 'scale' and redis_client is not None
        
        # In-memory storage for metrics
        self._task_metrics = defaultdict(lambda: deque(maxlen=1000))  # Last 1000 executions per task
        self._db_metrics = defaultdict(lambda: deque(maxlen=1000))  # Last 1000 queries per table
        self._system_metrics = deque(maxlen=3600)  # Last hour of system metrics (1 per second)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics configuration
        self.metrics_enabled = True
        self.retention_hours = 24  # Keep metrics for 24 hours
        
    def record_task_execution(self, task_name: str, execution_time: float, 
                            success: bool = True, error: Optional[str] = None) -> None:
        """Record a background task execution"""
        if not self.metrics_enabled:
            return
        
        try:
            timestamp = time.time()
            metric = {
                'task_name': task_name,
                'execution_time': execution_time,
                'success': success,
                'error': error,
                'timestamp': timestamp
            }
            
            with self._lock:
                self._task_metrics[task_name].append(metric)
            
            # Optionally persist to Redis
            if self.use_redis:
                try:
                    key = f"system_metrics:task:{task_name}:{int(timestamp)}"
                    self.redis_client.setex(key, self.retention_hours * 3600, json.dumps(metric))
                except Exception as e:
                    logger.debug(f"Failed to persist task metric to Redis: {e}")
                    
        except Exception as e:
            logger.error(f"Error recording task execution metric: {e}")
    
    def record_db_query(self, table_name: str, query_type: str, execution_time: float,
                       success: bool = True, error: Optional[str] = None) -> None:
        """Record a database query execution"""
        if not self.metrics_enabled:
            return
        
        try:
            timestamp = time.time()
            metric = {
                'table_name': table_name,
                'query_type': query_type,
                'execution_time': execution_time,
                'success': success,
                'error': error,
                'timestamp': timestamp
            }
            
            with self._lock:
                self._db_metrics[f"{table_name}:{query_type}"].append(metric)
            
            # Optionally persist to Redis
            if self.use_redis:
                try:
                    key = f"system_metrics:db:{table_name}:{query_type}:{int(timestamp)}"
                    self.redis_client.setex(key, self.retention_hours * 3600, json.dumps(metric))
                except Exception as e:
                    logger.debug(f"Failed to persist DB metric to Redis: {e}")
                    
        except Exception as e:
            logger.error(f"Error recording database query metric: {e}")
    
    def record_system_metric(self, cpu_percent: float, memory_percent: float,
                           disk_usage: Dict[str, float] = None) -> None:
        """Record system resource usage"""
        if not self.metrics_enabled:
            return
        
        try:
            timestamp = time.time()
            metric = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_usage': disk_usage or {},
                'timestamp': timestamp
            }
            
            with self._lock:
                self._system_metrics.append(metric)
            
            # Optionally persist to Redis
            if self.use_redis:
                try:
                    key = f"system_metrics:system:{int(timestamp)}"
                    self.redis_client.setex(key, self.retention_hours * 3600, json.dumps(metric))
                except Exception as e:
                    logger.debug(f"Failed to persist system metric to Redis: {e}")
                    
        except Exception as e:
            logger.error(f"Error recording system metric: {e}")
    
    def get_task_metrics_summary(self, task_name: Optional[str] = None, 
                                time_window: int = 3600) -> Dict[str, Any]:
        """Get task execution metrics summary"""
        try:
            current_time = time.time()
            start_time = current_time - time_window
            
            with self._lock:
                if task_name:
                    tasks_to_check = {task_name: self._task_metrics.get(task_name, deque())}
                else:
                    tasks_to_check = dict(self._task_metrics)
            
            summary = {}
            
            for task, metrics in tasks_to_check.items():
                # Filter by time window
                recent_metrics = [
                    m for m in metrics
                    if m['timestamp'] >= start_time
                ]
                
                if not recent_metrics:
                    continue
                
                execution_times = [m['execution_time'] for m in recent_metrics]
                successes = sum(1 for m in recent_metrics if m['success'])
                failures = len(recent_metrics) - successes
                
                summary[task] = {
                    'total_executions': len(recent_metrics),
                    'successful': successes,
                    'failed': failures,
                    'success_rate': (successes / len(recent_metrics) * 100) if recent_metrics else 0,
                    'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
                    'min_execution_time': min(execution_times) if execution_times else 0,
                    'max_execution_time': max(execution_times) if execution_times else 0,
                    'p95_execution_time': self._percentile(execution_times, 95) if execution_times else 0,
                    'p99_execution_time': self._percentile(execution_times, 99) if execution_times else 0
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting task metrics summary: {e}")
            return {}
    
    def get_db_metrics_summary(self, table_name: Optional[str] = None,
                               time_window: int = 3600) -> Dict[str, Any]:
        """Get database query metrics summary"""
        try:
            current_time = time.time()
            start_time = current_time - time_window
            
            with self._lock:
                if table_name:
                    db_metrics_to_check = {
                        k: v for k, v in self._db_metrics.items()
                        if k.startswith(f"{table_name}:")
                    }
                else:
                    db_metrics_to_check = dict(self._db_metrics)
            
            summary = {}
            
            for metric_key, metrics in db_metrics_to_check.items():
                # Filter by time window
                recent_metrics = [
                    m for m in metrics
                    if m['timestamp'] >= start_time
                ]
                
                if not recent_metrics:
                    continue
                
                execution_times = [m['execution_time'] for m in recent_metrics]
                successes = sum(1 for m in recent_metrics if m['success'])
                failures = len(recent_metrics) - successes
                
                summary[metric_key] = {
                    'total_queries': len(recent_metrics),
                    'successful': successes,
                    'failed': failures,
                    'success_rate': (successes / len(recent_metrics) * 100) if recent_metrics else 0,
                    'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
                    'min_execution_time': min(execution_times) if execution_times else 0,
                    'max_execution_time': max(execution_times) if execution_times else 0,
                    'p95_execution_time': self._percentile(execution_times, 95) if execution_times else 0,
                    'p99_execution_time': self._percentile(execution_times, 99) if execution_times else 0
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting DB metrics summary: {e}")
            return {}
    
    def get_system_metrics_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get system resource usage summary"""
        try:
            current_time = time.time()
            start_time = current_time - time_window
            
            with self._lock:
                recent_metrics = [
                    m for m in self._system_metrics
                    if m['timestamp'] >= start_time
                ]
            
            if not recent_metrics:
                return {}
            
            cpu_values = [m['cpu_percent'] for m in recent_metrics]
            memory_values = [m['memory_percent'] for m in recent_metrics]
            
            return {
                'cpu': {
                    'avg': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                    'min': min(cpu_values) if cpu_values else 0,
                    'max': max(cpu_values) if cpu_values else 0,
                    'p95': self._percentile(cpu_values, 95) if cpu_values else 0
                },
                'memory': {
                    'avg': sum(memory_values) / len(memory_values) if memory_values else 0,
                    'min': min(memory_values) if memory_values else 0,
                    'max': max(memory_values) if memory_values else 0,
                    'p95': self._percentile(memory_values, 95) if memory_values else 0
                },
                'sample_count': len(recent_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics summary: {e}")
            return {}
    
    def get_all_metrics(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get all metrics summary"""
        return {
            'tasks': self.get_task_metrics_summary(time_window=time_window),
            'database': self.get_db_metrics_summary(time_window=time_window),
            'system': self.get_system_metrics_summary(time_window=time_window),
            'time_window_seconds': time_window
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100.0))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]
    
    def cleanup_old_metrics(self) -> int:
        """Clean up old metrics data"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (self.retention_hours * 3600)
            cleaned_count = 0
            
            with self._lock:
                # Clean task metrics
                for task_name in list(self._task_metrics.keys()):
                    metrics = self._task_metrics[task_name]
                    original_len = len(metrics)
                    self._task_metrics[task_name] = deque(
                        [m for m in metrics if m['timestamp'] >= cutoff_time],
                        maxlen=1000
                    )
                    cleaned_count += original_len - len(self._task_metrics[task_name])
                
                # Clean DB metrics
                for metric_key in list(self._db_metrics.keys()):
                    metrics = self._db_metrics[metric_key]
                    original_len = len(metrics)
                    self._db_metrics[metric_key] = deque(
                        [m for m in metrics if m['timestamp'] >= cutoff_time],
                        maxlen=1000
                    )
                    cleaned_count += original_len - len(self._db_metrics[metric_key])
                
                # Clean system metrics
                original_len = len(self._system_metrics)
                self._system_metrics = deque(
                    [m for m in self._system_metrics if m['timestamp'] >= cutoff_time],
                    maxlen=3600
                )
                cleaned_count += original_len - len(self._system_metrics)
            
            # Clean Redis if enabled
            if self.use_redis:
                try:
                    pattern = "system_metrics:*"
                    keys = self.redis_client.keys(pattern)
                    for key in keys:
                        try:
                            data = self.redis_client.get(key)
                            if data:
                                metric = json.loads(data)
                                if metric.get('timestamp', 0) < cutoff_time:
                                    self.redis_client.delete(key)
                                    cleaned_count += 1
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"Error cleaning Redis metrics: {e}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old metrics: {e}")
            return 0


# Global system metrics instance
system_metrics = SystemMetrics()

# Initialize Redis client if in scale mode
if DASHBOARD_TYPE.lower() == 'scale' and REDIS_AVAILABLE:
    try:
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        redis_client.ping()
        system_metrics.redis_client = redis_client
        system_metrics.use_redis = True
        logger.info("System metrics initialized with Redis persistence")
    except Exception as e:
        logger.warning(f"Failed to connect Redis for system metrics, using in-memory only: {e}")
        system_metrics.use_redis = False

