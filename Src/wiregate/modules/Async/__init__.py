"""
Async module package for Wiregate
Contains thread pools and process pools for asynchronous operations
"""

from .ThreadPool import (
    ThreadPoolManager,
    thread_pool,
    bulk_peer_status_check,
    redis_bulk_operations,
    file_operations,
    wg_command_operations
)

from .ProcessPool import (
    ProcessPoolManager,
    process_pool,
    bulk_peer_processing,
    bulk_peer_validation,
    bulk_peer_encryption,
    bulk_usage_analysis,
    bulk_qr_generation
)

__all__ = [
    # ThreadPool exports
    'ThreadPoolManager',
    'thread_pool',
    'bulk_peer_status_check',
    'redis_bulk_operations',
    'file_operations',
    'wg_command_operations',
    
    # ProcessPool exports
    'ProcessPoolManager',
    'process_pool',
    'bulk_peer_processing',
    'bulk_peer_validation',
    'bulk_peer_encryption',
    'bulk_usage_analysis',
    'bulk_qr_generation'
]
