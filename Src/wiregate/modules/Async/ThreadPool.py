"""
Thread Pool for I/O-intensive operations
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Callable, Any, Optional
import subprocess
import os

class ThreadPoolManager:
    def __init__(self, max_workers=10):
        self.max_workers = max_workers
        self.executor = None
        
    def start_pool(self):
        """Start the thread pool"""
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            print(f"[ThreadPool] Started with {self.max_workers} workers")
    
    def stop_pool(self):
        """Stop the thread pool"""
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None
            print("[ThreadPool] Stopped")
    
    def submit_task(self, func: Callable, *args, **kwargs):
        """Submit a task to the thread pool"""
        if self.executor is None:
            self.start_pool()
        return self.executor.submit(func, *args, **kwargs)
    
    def submit_batch(self, func: Callable, tasks: List[tuple]) -> List[Any]:
        """Submit multiple tasks and return results"""
        if self.executor is None:
            self.start_pool()
        
        futures = [self.executor.submit(func, *task) for task in tasks]
        results = []
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[ThreadPool] Task failed: {e}")
                results.append(None)
        
        return results

# WireGate-specific I/O functions
def fetch_peer_status(peer_id: str, config_name: str = None) -> dict:
    """Fetch peer status from WireGuard (I/O operation)"""
    try:
        # Run wg show command
        if config_name:
            cmd = ['wg', 'show', config_name, 'dump']
        else:
            cmd = ['wg', 'show', 'all', 'dump']
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # Parse result to find peer
        status = {
            'peer_id': peer_id,
            'config': config_name,
            'status': 'connected' if result.returncode == 0 else 'error',
            'timestamp': time.time(),
            'raw_output': result.stdout if result.returncode == 0 else result.stderr
        }
        
        return status
    except Exception as e:
        return {'peer_id': peer_id, 'status': 'error', 'error': str(e)}

def bulk_peer_status_check(peer_ids: List[str], config_name: str = None) -> List[dict]:
    """Check status of multiple peers in parallel"""
    pool_manager = ThreadPoolManager()
    
    try:
        # Submit all tasks
        tasks = [(fetch_peer_status, peer_id, config_name) for peer_id in peer_ids]
        results = pool_manager.submit_batch(fetch_peer_status, tasks)
        
        return results
    finally:
        pool_manager.stop_pool()

def redis_bulk_operations(operations: List[tuple]) -> List[Any]:
    """Execute multiple Redis operations in parallel"""
    from ..DataBase import get_redis_manager
    
    def execute_redis_op(operation):
        op_type, key, value = operation
        redis_manager = get_redis_manager()
        
        try:
            if op_type == 'get':
                return redis_manager.redis_client.get(key)
            elif op_type == 'set':
                return redis_manager.redis_client.set(key, value)
            elif op_type == 'hget':
                return redis_manager.redis_client.hget(key, value)
            elif op_type == 'hset':
                return redis_manager.redis_client.hset(key, value[0], value[1])
            elif op_type == 'delete':
                return redis_manager.redis_client.delete(key)
            else:
                return None
        except Exception as e:
            return {'error': str(e)}
    
    pool_manager = ThreadPoolManager()
    
    try:
        results = pool_manager.submit_batch(execute_redis_op, operations)
        return results
    finally:
        pool_manager.stop_pool()

def file_operations(operations: List[tuple]) -> List[Any]:
    """Execute multiple file operations in parallel"""
    def execute_file_op(operation):
        op_type, path, data = operation
        
        try:
            if op_type == 'read':
                with open(path, 'r') as f:
                    return f.read()
            elif op_type == 'write':
                with open(path, 'w') as f:
                    f.write(data)
                return True
            elif op_type == 'exists':
                return os.path.exists(path)
            elif op_type == 'delete':
                os.remove(path)
                return True
            else:
                return None
        except Exception as e:
            return {'error': str(e)}
    
    pool_manager = ThreadPoolManager()
    
    try:
        results = pool_manager.submit_batch(execute_file_op, operations)
        return results
    finally:
        pool_manager.stop_pool()

def wg_command_operations(commands: List[tuple]) -> List[dict]:
    """Execute multiple WireGuard commands in parallel"""
    def execute_wg_command(command_data):
        command, args, timeout = command_data
        
        try:
            cmd = ['/WireGate/restricted_shell.sh', 'wg'] + [command] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            return {
                'command': ' '.join(cmd),
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                'command': ' '.join(cmd),
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out',
                'success': False
            }
        except Exception as e:
            return {
                'command': ' '.join(cmd),
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    pool_manager = ThreadPoolManager()
    
    try:
        results = pool_manager.submit_batch(execute_wg_command, commands)
        return results
    finally:
        pool_manager.stop_pool()

# Global instance
thread_pool = ThreadPoolManager(max_workers=20)  # Increased for WireGate operations
