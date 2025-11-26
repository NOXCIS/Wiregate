"""
Decorators for automatic metrics collection
"""
import time
import functools
import logging
from typing import Callable, Any

from .SystemMetrics import system_metrics

logger = logging.getLogger(__name__)


def track_task_execution(task_name: str = None):
    """
    Decorator to track background task execution times
    Usage:
        @track_task_execution("task_name")
        async def my_task():
            ...
    """
    def decorator(func: Callable) -> Callable:
        nonlocal task_name
        if task_name is None:
            task_name = func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                system_metrics.record_task_execution(
                    task_name=task_name,
                    execution_time=execution_time,
                    success=success,
                    error=error
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                system_metrics.record_task_execution(
                    task_name=task_name,
                    execution_time=execution_time,
                    success=success,
                    error=error
                )
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def track_db_query(table_name: str = None, query_type: str = "query"):
    """
    Decorator to track database query execution times
    Usage:
        @track_db_query("peers", "select")
        async def get_peer(peer_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        nonlocal table_name
        if table_name is None:
            # Try to infer from function name or args
            table_name = "unknown"
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                system_metrics.record_db_query(
                    table_name=table_name,
                    query_type=query_type,
                    execution_time=execution_time,
                    success=success,
                    error=error
                )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                system_metrics.record_db_query(
                    table_name=table_name,
                    query_type=query_type,
                    execution_time=execution_time,
                    success=success,
                    error=error
                )
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

