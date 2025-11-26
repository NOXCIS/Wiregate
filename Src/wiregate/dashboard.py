"""
Dashboard module - Background tasks and thread management
Now uses async tasks instead of traditional threads for FastAPI

See Docs/ARCHITECTURE.md for detailed async task lifecycle documentation
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

from wiregate.modules.Async import thread_pool, process_pool
from wiregate.modules.Core import Configurations
from wiregate.modules.Jobs import AllPeerJobs


# Global list to track async background tasks
_background_tasks: List[asyncio.Task] = []

# Track metrics for each background task
_task_metrics: Dict[str, Dict[str, Any]] = {
    'background_task_1': {
        'iterations': 0,
        'last_success': None,
        'last_error': None,
        'error_count': 0,
        'start_time': None
    },
    'background_task_2': {
        'iterations': 0,
        'last_success': None,
        'last_error': None,
        'error_count': 0,
        'start_time': None
    },
    'background_task_3': {
        'iterations': 0,
        'last_success': None,
        'last_error': None,
        'error_count': 0,
        'start_time': None
    }
}

from wiregate.modules.Metrics.decorators import track_task_execution
from wiregate.modules.Logger import log_with_context

@track_task_execution("background_task_1_wireguard_stats")
async def backGroundThread() -> None:
    """Async background task for WireGuard stats polling with parallel config processing"""
    global Configurations
    task_key = 'background_task_1'
    _task_metrics[task_key]['start_time'] = datetime.utcnow().isoformat()
    
    logger.info("Background Task #1 Started (async)")
    await asyncio.sleep(10)
    
    update_check_counter = 0
    
    while True:
        try:
            # Get all active configurations
            active_configs = [c for c in Configurations.values() if c.getStatus()]
            
            if active_configs:
                # Process all configs in parallel for 3-5x performance improvement
                await asyncio.gather(
                    *[process_single_config(c) for c in active_configs],
                    return_exceptions=True
                )
            
            # Check for updates every hour (360 iterations * 10s = 1 hour)
            update_check_counter += 1
            if update_check_counter >= 360:
                try:
                    from .routes.utils_api import _background_update_check
                    # Run in thread pool to avoid blocking async loop
                    await asyncio.to_thread(_background_update_check)
                    logger.debug("Update check completed")
                except Exception as e:
                    logger.error(f"Update check error: {str(e)}")
                update_check_counter = 0
            
            # Update metrics on successful iteration
            _task_metrics[task_key]['iterations'] += 1
            _task_metrics[task_key]['last_success'] = datetime.utcnow().isoformat()
            _task_metrics[task_key]['last_error'] = None
                
        except asyncio.CancelledError:
            logger.info("Background Task #1 cancelled")
            log_with_context(
                logger, logging.INFO,
                "Background task cancelled",
                event_type="task_cancelled",
                task_name="background_task_1_wireguard_stats"
            )
            break
        except Exception as e:
            _task_metrics[task_key]['error_count'] += 1
            _task_metrics[task_key]['last_error'] = {
                'message': str(e),
                'type': type(e).__name__,
                'timestamp': datetime.utcnow().isoformat()
            }
            logger.error(f"Background Task #1 unexpected error: {str(e)}")
            log_with_context(
                logger, logging.ERROR,
                "Background task error",
                event_type="task_error",
                task_name="background_task_1_wireguard_stats",
                error=str(e),
                error_type=type(e).__name__
            )
        
        await asyncio.sleep(10)


async def process_single_config(config: Any) -> None:
    """Process a single config asynchronously for parallel execution with granular error handling"""
    config_name = getattr(config, 'name', 'unknown')
    
    # Use async versions if available, otherwise fall back to thread pool
    # Note: getPeersTransfer modifies database state, so we run it first
    # to avoid race conditions with other methods
    try:
        if hasattr(config, 'getPeersTransferAsync'):
            await config.getPeersTransferAsync()
        else:
            await asyncio.to_thread(config.getPeersTransfer)
    except Exception as e:
        logger.error(f"Error in getPeersTransfer for config {config_name}: {str(e)}")
        log_with_context(
            logger, logging.ERROR,
            "Error in getPeersTransfer",
            event_type="config_processing_error",
            config_name=config_name,
            method="getPeersTransfer",
            error=str(e),
            error_type=type(e).__name__
        )
        # Continue with other methods even if this one fails
    
    # Then run the other methods in parallel with individual error handling
    methods = [
        ('getPeersLatestHandshake', 
         config.getPeersLatestHandshakeAsync if hasattr(config, 'getPeersLatestHandshakeAsync') 
         else lambda: asyncio.to_thread(config.getPeersLatestHandshake)),
        ('getPeersEndpoint',
         config.getPeersEndpointAsync if hasattr(config, 'getPeersEndpointAsync')
         else lambda: asyncio.to_thread(config.getPeersEndpoint)),
        ('getPeersList',
         lambda: config.getPeersList()),  # Already async, no need for to_thread
        ('getRestrictedPeersList',
         lambda: config.getRestrictedPeersList())  # Already async, no need for to_thread
    ]
    
    # Execute all methods in parallel, but handle each exception individually
    results = await asyncio.gather(
        *[method() for _, method in methods],
        return_exceptions=True
    )
    
    # Log individual method errors without affecting other methods
    for (method_name, _), result in zip(methods, results):
        if isinstance(result, Exception):
            logger.error(f"Error in {method_name} for config {config_name}: {str(result)}")
            log_with_context(
                logger, logging.ERROR,
                f"Error in {method_name}",
                event_type="config_processing_error",
                config_name=config_name,
                method=method_name,
                error=str(result),
                error_type=type(result).__name__
            )


@track_task_execution("background_task_2_peer_jobs")
async def peerJobScheduleBackgroundThread() -> None:
    """Async background task for peer job scheduling"""
    task_key = 'background_task_2'
    _task_metrics[task_key]['start_time'] = datetime.utcnow().isoformat()
    
    logger.info("Background Task #2 Started (async)")
    await asyncio.sleep(10)
    
    while True:
        try:
            await AllPeerJobs.runJob()
            # Update metrics on successful iteration
            _task_metrics[task_key]['iterations'] += 1
            _task_metrics[task_key]['last_success'] = datetime.utcnow().isoformat()
            _task_metrics[task_key]['last_error'] = None
        except asyncio.CancelledError:
            logger.info("Background Task #2 cancelled")
            log_with_context(
                logger, logging.INFO,
                "Background task cancelled",
                event_type="task_cancelled",
                task_name="background_task_2_peer_jobs"
            )
            break
        except Exception as e:
            _task_metrics[task_key]['error_count'] += 1
            _task_metrics[task_key]['last_error'] = {
                'message': str(e),
                'type': type(e).__name__,
                'timestamp': datetime.utcnow().isoformat()
            }
            logger.error(f"Background Task #2 error: {str(e)}")
            log_with_context(
                logger, logging.ERROR,
                "Background task error",
                event_type="task_error",
                task_name="background_task_2_peer_jobs",
                error=str(e),
                error_type=type(e).__name__
            )
        
        await asyncio.sleep(15)


@track_task_execution("background_task_3_cps_adaptation")
async def cpsAdaptationBackgroundThread() -> None:
    """Async background task for periodic CPS pattern adaptation (daily)"""
    task_key = 'background_task_3'
    _task_metrics[task_key]['start_time'] = datetime.utcnow().isoformat()
    
    logger.info("Background Task #3 Started - CPS Pattern Adaptation (async)")
    await asyncio.sleep(60)  # Wait 1 minute after startup
    
    # Run every 24 hours (86400 seconds / 10 second intervals = 8640 iterations)
    adaptation_counter = 0
    daily_interval = 8640  # 24 hours
    
    while True:
        try:
            adaptation_counter += 1
            
            # Run periodic adaptation check daily
            if adaptation_counter >= daily_interval:
                try:
                    # Get all AWG configurations with CPS enabled
                    awg_configs = [
                        c for c in Configurations.values()
                        if c.get_iface_proto() == "awg" and 
                           (c.I1 or c.I2 or c.I3 or c.I4 or c.I5) and
                           c.cps_adaptation
                    ]
                    
                    if awg_configs:
                        logger.info(f"Running periodic CPS adaptation for {len(awg_configs)} configurations")
                        # Run adaptation for all configs in parallel
                        results = await asyncio.gather(
                            *[asyncio.to_thread(c.periodic_cps_adaptation) for c in awg_configs],
                            return_exceptions=True
                        )
                        
                        adapted_count = sum(1 for r in results if r and not isinstance(r, Exception))
                        if adapted_count > 0:
                            logger.info(f"Periodic CPS adaptation: {adapted_count} configurations adapted")
                        
                        # Log any errors
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.error(f"Error in periodic adaptation for {awg_configs[i].Name}: {result}")
                    
                    adaptation_counter = 0
                    # Update metrics on successful adaptation cycle
                    _task_metrics[task_key]['iterations'] += 1
                    _task_metrics[task_key]['last_success'] = datetime.utcnow().isoformat()
                    _task_metrics[task_key]['last_error'] = None
                except Exception as e:
                    _task_metrics[task_key]['error_count'] += 1
                    _task_metrics[task_key]['last_error'] = {
                        'message': str(e),
                        'type': type(e).__name__,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    logger.error(f"Periodic CPS adaptation error: {str(e)}")
            else:
                # Update metrics for each iteration (even if not running adaptation)
                _task_metrics[task_key]['iterations'] += 1
                _task_metrics[task_key]['last_success'] = datetime.utcnow().isoformat()
                    
        except asyncio.CancelledError:
            logger.info("Background Task #3 cancelled")
            log_with_context(
                logger, logging.INFO,
                "Background task cancelled",
                event_type="task_cancelled",
                task_name="background_task_3_cps_adaptation"
            )
            break
        except Exception as e:
            _task_metrics[task_key]['error_count'] += 1
            _task_metrics[task_key]['last_error'] = {
                'message': str(e),
                'type': type(e).__name__,
                'timestamp': datetime.utcnow().isoformat()
            }
            logger.error(f"Background Task #3 unexpected error: {str(e)}")
            log_with_context(
                logger, logging.ERROR,
                "Background task error",
                event_type="task_error",
                task_name="background_task_3_cps_adaptation",
                error=str(e),
                error_type=type(e).__name__
            )
        
        await asyncio.sleep(10)


async def startThreads() -> None:
    """Start thread pools and create async background tasks"""
    # Start thread pool for I/O operations
    thread_pool.start_pool()
    logger.info("Thread pool started with 20 workers")
    
    # Start process pool for CPU-intensive operations
    try:
        process_pool.start_pool()
        if process_pool.pool is not None:
            logger.info("Process pool (thread-based) started with workers")
        else:
            logger.warning("Process pool is disabled - will run tasks in main thread")
    except Exception as e:
        logger.error(f"Failed to start process pool: {e}")
        logger.warning("Continuing without process pool")
    
    # Create async background tasks
    loop = asyncio.get_running_loop()
    task1 = loop.create_task(backGroundThread())
    _background_tasks.append(task1)
    task2 = loop.create_task(peerJobScheduleBackgroundThread())
    _background_tasks.append(task2)
    task3 = loop.create_task(cpsAdaptationBackgroundThread())
    _background_tasks.append(task3)
    logger.info("Async background tasks created (3 tasks)")


async def stopThreads() -> None:
    """Stop async tasks, thread pool and process pool"""
    # Cancel async background tasks
    for task in _background_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    _background_tasks.clear()
    logger.info("Background tasks stopped")
    
    # Stop thread pool
    try:
        thread_pool.stop_pool()
        logger.info("Thread pool stopped")
    except Exception as e:
        logger.error(f"Error stopping thread pool: {e}")
    
    # Stop process pool
    try:
        process_pool.stop_pool()
        logger.info("Process pool stopped")
    except Exception as e:
        logger.error(f"Error stopping process pool: {e}")


def get_background_task_status() -> Dict[str, Any]:
    """Get status of all background tasks for health checks with detailed metrics"""
    task_status: Dict[str, Any] = {}
    
    task_configs = [
        (1, 'background_task_1', 'WireGuard Stats Polling'),
        (2, 'background_task_2', 'Peer Job Scheduling'),
        (3, 'background_task_3', 'CPS Pattern Adaptation')
    ]
    
    for idx, task_key, task_name in task_configs:
        if len(_background_tasks) >= idx:
            task = _background_tasks[idx - 1]
            metrics = _task_metrics.get(task_key, {})
            
            # Calculate uptime if start_time is available
            uptime_seconds: Optional[float] = None
            if metrics.get('start_time'):
                try:
                    start_dt = datetime.fromisoformat(metrics['start_time'])
                    uptime_seconds = (datetime.utcnow() - start_dt).total_seconds()
                except (ValueError, TypeError):
                    pass
            
            task_status[task_key] = {
                'name': task_name,
                'running': not task.done(),
                'crashed': task.done() and task.exception() is not None,
                'exception': str(task.exception()) if task.done() and task.exception() else None,
                'metrics': {
                    'iterations': metrics.get('iterations', 0),
                    'error_count': metrics.get('error_count', 0),
                    'last_success': metrics.get('last_success'),
                    'last_error': metrics.get('last_error'),
                    'start_time': metrics.get('start_time'),
                    'uptime_seconds': uptime_seconds
                }
            }
    
    return task_status


# Export what FastAPI needs
__all__ = ['startThreads', 'stopThreads', 'get_background_task_status']
