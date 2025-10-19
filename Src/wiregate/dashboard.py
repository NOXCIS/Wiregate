"""
Dashboard module - Background tasks and thread management
Now uses async tasks instead of traditional threads for FastAPI
"""
import logging
import asyncio

logger = logging.getLogger(__name__)

from .modules.Async import thread_pool, process_pool
from .modules.Core import Configurations
from .modules.Jobs import AllPeerJobs


# Global list to track async background tasks
_background_tasks = []


async def backGroundThread():
    """Async background task for WireGuard stats polling with parallel config processing"""
    global Configurations
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
                    from .routes.fastapi_utils import _background_update_check
                    # Run in thread pool to avoid blocking async loop
                    await asyncio.to_thread(_background_update_check)
                    logger.debug("Update check completed")
                except Exception as e:
                    logger.error(f"Update check error: {str(e)}")
                update_check_counter = 0
                
        except asyncio.CancelledError:
            logger.info("Background Task #1 cancelled")
            break
        except Exception as e:
            logger.error(f"Background Task #1 unexpected error: {str(e)}")
        
        await asyncio.sleep(10)


async def process_single_config(config):
    """Process a single config asynchronously for parallel execution"""
    try:
        # Run all config methods in parallel using asyncio.to_thread
        # Note: getPeersTransfer modifies database state, so we run it first
        # to avoid race conditions with other methods
        await asyncio.to_thread(config.getPeersTransfer)
        
        # Then run the other methods in parallel
        await asyncio.gather(
            asyncio.to_thread(config.getPeersLatestHandshake),
            asyncio.to_thread(config.getPeersEndpoint),
            asyncio.to_thread(config.getPeersList),
            asyncio.to_thread(config.getRestrictedPeersList),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Error processing config {config.name}: {str(e)}")


async def peerJobScheduleBackgroundThread():
    """Async background task for peer job scheduling"""
    logger.info("Background Task #2 Started (async)")
    await asyncio.sleep(10)
    
    while True:
        try:
            AllPeerJobs.runJob()
        except asyncio.CancelledError:
            logger.info("Background Task #2 cancelled")
            break
        except Exception as e:
            logger.error(f"Background Task #2 error: {str(e)}")
        
        await asyncio.sleep(15)


def startThreads():
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
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(backGroundThread())
    _background_tasks.append(task1)
    task2 = loop.create_task(peerJobScheduleBackgroundThread())
    _background_tasks.append(task2)
    logger.info("Async background tasks created")


async def stopThreads():
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


# Export what FastAPI needs
__all__ = ['startThreads', 'stopThreads']
