"""
Process Pool for CPU-intensive operations
Refactored to use ThreadPoolExecutor for PyInstaller compatibility
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import time
import json
import hashlib
import re
from typing import List, Dict, Any, Optional

# Use ThreadPoolExecutor instead of multiprocessing for PyInstaller compatibility
class ProcessPoolManager:
    def __init__(self, max_workers=None):
        import multiprocessing as mp
        self.max_workers = max_workers or max(4, mp.cpu_count() // 2)  # Use threads, not processes
        self.pool = None
        
    def start_pool(self):
        """Start the thread pool (using ThreadPoolExecutor for PyInstaller compatibility)"""
        if self.pool is None:
            try:
                self.pool = ThreadPoolExecutor(max_workers=self.max_workers)
                print(f"[ProcessPool] Started thread pool with {self.max_workers} workers")
            except Exception as e:
                print(f"[ProcessPool] Warning: Failed to start thread pool: {e}. Continuing without thread pool.")
                self.pool = None
    
    def stop_pool(self):
        """Stop the process pool"""
        if self.pool:
            self.pool.shutdown(wait=True) # ThreadPoolExecutor doesn't have a direct close/join
            self.pool = None
            print("[ProcessPool] Stopped")
    
    def submit_task(self, func, *args, **kwargs):
        """Submit a task to the process pool"""
        if self.pool is None:
            self.start_pool()
        if self.pool is None:
            # If pool still None after start attempt, run in main process
            return func(*args, **kwargs)
        return self.pool.submit(func, *args, **kwargs)
    
    def submit_batch(self, func, tasks):
        """Submit multiple tasks at once"""
        if self.pool is None:
            self.start_pool()
        if self.pool is None:
            # If pool still None after start attempt, run in main process
            return [func(*task) for task in tasks]
        return [self.pool.submit(func, *task) for task in tasks]

# WireGate-specific CPU-intensive functions
def process_peer_config(peer_data):
    """Process peer configuration in separate process"""
    import json
    import time
    import hashlib
    
    # Simulate heavy processing
    time.sleep(0.1)
    
    # Process peer data with CPU-intensive operations
    processed = {
        'id': peer_data.get('id'),
        'name': peer_data.get('name', 'Unknown'),
        'public_key': peer_data.get('public_key'),
        'public_key_hash': hashlib.sha256(peer_data.get('public_key', '').encode()).hexdigest(),
        'processed_at': time.time(),
        'config_checksum': hashlib.md5(json.dumps(peer_data, sort_keys=True).encode()).hexdigest()
    }
    
    return processed

def validate_peer_config(peer_data):
    """Validate peer configuration with CPU-intensive validation"""
    import re
    import hashlib
    import time
    
    # Simulate heavy validation
    time.sleep(0.05)
    
    validation_result = {
        'peer_id': peer_data.get('id'),
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Validate public key format
    public_key = peer_data.get('public_key', '')
    if not re.match(r'^[A-Za-z0-9+/]{43}=$', public_key):
        validation_result['valid'] = False
        validation_result['errors'].append('Invalid public key format')
    
    # Validate allowed IPs
    allowed_ips = peer_data.get('allowed_ips', '')
    if allowed_ips:
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}(\/\d{1,2})?$'
        for ip in allowed_ips.split(','):
            if not re.match(ip_pattern, ip.strip()):
                validation_result['warnings'].append(f'Invalid IP format: {ip}')
    
    # Calculate complexity score
    complexity_score = len(peer_data.get('name', '')) * 2 + len(public_key) + len(allowed_ips)
    validation_result['complexity_score'] = complexity_score
    
    return validation_result

def encrypt_peer_data(peer_data):
    """Encrypt peer data with CPU-intensive encryption"""
    import hashlib
    import time
    import json
    
    # Simulate heavy encryption
    time.sleep(0.1)
    
    # Simple encryption simulation (in real app, use proper encryption)
    data_str = json.dumps(peer_data, sort_keys=True)
    encrypted = hashlib.sha256(data_str.encode()).hexdigest()
    
    return {
        'original_id': peer_data.get('id'),
        'encrypted_data': encrypted,
        'encryption_time': time.time(),
        'data_size': len(data_str)
    }

def analyze_peer_usage(usage_data):
    """Analyze peer usage patterns with CPU-intensive analysis"""
    import time
    import statistics
    
    # Simulate heavy analysis
    time.sleep(0.2)
    
    if not usage_data:
        return {'peer_id': 'unknown', 'analysis': 'no_data'}
    
    # Calculate statistics
    bytes_sent = [entry.get('bytes_sent', 0) for entry in usage_data]
    bytes_received = [entry.get('bytes_received', 0) for entry in usage_data]
    
    analysis = {
        'peer_id': usage_data[0].get('peer_id', 'unknown'),
        'total_sent': sum(bytes_sent),
        'total_received': sum(bytes_received),
        'avg_sent': statistics.mean(bytes_sent) if bytes_sent else 0,
        'avg_received': statistics.mean(bytes_received) if bytes_received else 0,
        'max_sent': max(bytes_sent) if bytes_sent else 0,
        'max_received': max(bytes_received) if bytes_received else 0,
        'usage_trend': 'increasing' if len(bytes_sent) > 1 and bytes_sent[-1] > bytes_sent[0] else 'stable',
        'analysis_time': time.time()
    }
    
    return analysis

def generate_peer_qr_codes(peer_data_list):
    """Generate QR codes for multiple peers (CPU-intensive)"""
    import time
    import hashlib
    
    # Simulate QR code generation
    time.sleep(0.3)
    
    results = []
    for peer_data in peer_data_list:
        # Simulate QR code generation
        qr_data = f"wireguard://{peer_data.get('public_key', '')}@{peer_data.get('endpoint', '')}"
        qr_hash = hashlib.sha256(qr_data.encode()).hexdigest()
        
        results.append({
            'peer_id': peer_data.get('id'),
            'qr_data': qr_data,
            'qr_hash': qr_hash,
            'generated_at': time.time()
        })
    
    return results

def bulk_peer_processing(peers_data):
    """Process multiple peers in parallel using process pool"""
    pool_manager = ProcessPoolManager()
    
    try:
        # Submit all tasks
        tasks = [pool_manager.submit_task(process_peer_config, peer) for peer in peers_data]
        
        # Collect results
        results = [task.result() for task in as_completed(tasks)]
        
        return results
    finally:
        pool_manager.stop_pool()

def bulk_peer_validation(peers_data):
    """Validate multiple peers in parallel using process pool"""
    pool_manager = ProcessPoolManager()
    
    try:
        # Submit all tasks
        tasks = [pool_manager.submit_task(validate_peer_config, peer) for peer in peers_data]
        
        # Collect results
        results = [task.result() for task in as_completed(tasks)]
        
        return results
    finally:
        pool_manager.stop_pool()

def bulk_peer_encryption(peers_data):
    """Encrypt multiple peers in parallel using process pool"""
    pool_manager = ProcessPoolManager()
    
    try:
        # Submit all tasks
        tasks = [pool_manager.submit_task(encrypt_peer_data, peer) for peer in peers_data]
        
        # Collect results
        results = [task.result() for task in as_completed(tasks)]
        
        return results
    finally:
        pool_manager.stop_pool()

def bulk_usage_analysis(usage_data_list):
    """Analyze usage patterns for multiple peers in parallel using process pool"""
    pool_manager = ProcessPoolManager()
    
    try:
        # Submit all tasks
        tasks = [pool_manager.submit_task(analyze_peer_usage, usage_data) for usage_data in usage_data_list]
        
        # Collect results
        results = [task.result() for task in as_completed(tasks)]
        
        return results
    finally:
        pool_manager.stop_pool()

def bulk_qr_generation(peer_data_list):
    """Generate QR codes for multiple peers in parallel using process pool"""
    pool_manager = ProcessPoolManager()
    
    try:
        # Submit all tasks
        tasks = [pool_manager.submit_task(generate_peer_qr_codes, [peer_data]) for peer_data in peer_data_list]
        
        # Collect results
        results = [task.result() for task in as_completed(tasks)]
        
        return results
    finally:
        pool_manager.stop_pool()

# Global instance
process_pool = ProcessPoolManager(max_workers=4)  # Use 4 CPU cores
