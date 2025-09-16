"""
Async module package for Wiregate
Contains thread pools, process pools, and Celery task queue for asynchronous operations
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

# Optional Celery imports
try:
    from .CeleryTasks import (
        celery_app,
        process_peer_configuration,
        send_notification_email,
        cleanup_old_logs
    )
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Mock functions for fallback
    def celery_app():
        return None
    def process_peer_configuration(*args, **kwargs):
        return None
    def send_notification_email(*args, **kwargs):
        return None
    def cleanup_old_logs(*args, **kwargs):
        return None

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
    'bulk_qr_generation',
    
    # Celery exports
    'celery_app',
    'process_peer_configuration',
    'send_notification_email',
    'cleanup_old_logs'
]
