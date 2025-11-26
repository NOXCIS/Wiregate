"""
Health Check API Endpoint
Public endpoint for Docker health checks and monitoring tools
"""
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from ..models.responses import HealthCheckResponse
from ..modules.Config import DASHBOARD_TYPE

logger = logging.getLogger(__name__)

# Lazy import for PyInstaller compatibility
def _get_background_task_status():
    """Get background task status function with fallback for PyInstaller"""
    try:
        from ..dashboard import get_background_task_status
        return get_background_task_status
    except ImportError:
        try:
            from wiregate.dashboard import get_background_task_status
            return get_background_task_status
        except ImportError:
            # Stub function if module not available
            logger.warning("Dashboard module not available for background task status, using stub")
            def get_background_task_status():
                return {}
            return get_background_task_status

# Get the function (lazy loaded)
get_background_task_status = _get_background_task_status()

router = APIRouter()

# Track application start time for uptime calculation
_app_start_time = time.time()


def get_uptime() -> float:
    """Get application uptime in seconds"""
    return time.time() - _app_start_time


async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity"""
    check_start = time.time()
    try:
        from ..modules.DataBase import get_redis_manager
        manager = await get_redis_manager()
        
        if DASHBOARD_TYPE.lower() == 'simple':
            # SQLite - execute simple query (async)
            if hasattr(manager, 'execute_query'):
                result = await manager.execute_query("SELECT 1")
                if result:
                    return {
                        'status': 'healthy',
                        'response_time_ms': round((time.time() - check_start) * 1000, 2),
                        'message': 'SQLite database is accessible'
                    }
        else:
            # PostgreSQL - execute simple query (sync, run in thread)
            if hasattr(manager, 'postgres_conn'):
                def _check_postgres():
                    with manager.postgres_conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                        return True
                
                await asyncio.to_thread(_check_postgres)
                return {
                    'status': 'healthy',
                    'response_time_ms': round((time.time() - check_start) * 1000, 2),
                    'message': 'PostgreSQL database is accessible'
                }
        
        return {
            'status': 'unhealthy',
            'response_time_ms': round((time.time() - check_start) * 1000, 2),
            'message': 'Database check failed - unknown database type'
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'response_time_ms': round((time.time() - check_start) * 1000, 2),
            'message': f'Database connection error: {str(e)}'
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity (only in scale mode)"""
    check_start = time.time()
    
    if DASHBOARD_TYPE.lower() != 'scale':
        return {
            'status': 'not_applicable',
            'response_time_ms': 0,
            'message': 'Redis not used in simple mode'
        }
    
    try:
        from ..modules.DataBase import get_redis_manager
        manager = await get_redis_manager()
        
        if hasattr(manager, 'redis_client') and manager.redis_client:
            manager.redis_client.ping()
            return {
                'status': 'healthy',
                'response_time_ms': round((time.time() - check_start) * 1000, 2),
                'message': 'Redis is accessible'
            }
        else:
            return {
                'status': 'unhealthy',
                'response_time_ms': round((time.time() - check_start) * 1000, 2),
                'message': 'Redis client not available'
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            'status': 'unhealthy',
            'response_time_ms': round((time.time() - check_start) * 1000, 2),
            'message': f'Redis connection error: {str(e)}'
        }


async def check_background_tasks_health() -> Dict[str, Any]:
    """Check background task status"""
    check_start = time.time()
    try:
        task_status = get_background_task_status()
        
        if not task_status:
            return {
                'status': 'unhealthy',
                'response_time_ms': round((time.time() - check_start) * 1000, 2),
                'message': 'Background task status not available',
                'tasks': {}
            }
        
        # Check if all tasks are running
        all_running = all(
            task.get('running', False) and not task.get('crashed', False)
            for task in task_status.values()
        )
        
        status_str = 'healthy' if all_running else 'degraded'
        if not all_running:
            crashed_tasks = [
                name for name, task in task_status.items()
                if task.get('crashed', False) or not task.get('running', False)
            ]
            message = f"Some background tasks are not running: {', '.join(crashed_tasks)}"
        else:
            message = 'All background tasks are running'
        
        return {
            'status': status_str,
            'response_time_ms': round((time.time() - check_start) * 1000, 2),
            'message': message,
            'tasks': task_status
        }
    except Exception as e:
        logger.error(f"Background tasks health check failed: {e}")
        return {
            'status': 'unhealthy',
            'response_time_ms': round((time.time() - check_start) * 1000, 2),
            'message': f'Background task check error: {str(e)}',
            'tasks': {}
        }


@router.get('/health', response_model=HealthCheckResponse, status_code=200)
async def health_check(response: Response):
    """
    Health check endpoint for Docker and monitoring tools
    Public endpoint (no authentication required)
    Returns HTTP 200 for healthy, 503 for unhealthy
    """
    try:
        # Run all health checks in parallel
        db_check, redis_check, tasks_check = await asyncio.gather(
            check_database_health(),
            check_redis_health(),
            check_background_tasks_health(),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(db_check, Exception):
            db_check = {'status': 'unhealthy', 'message': str(db_check), 'response_time_ms': 0}
        if isinstance(redis_check, Exception):
            redis_check = {'status': 'unhealthy', 'message': str(redis_check), 'response_time_ms': 0}
        if isinstance(tasks_check, Exception):
            tasks_check = {'status': 'unhealthy', 'message': str(tasks_check), 'response_time_ms': 0}
        
        # Determine overall status
        check_statuses = [
            db_check.get('status'),
            tasks_check.get('status')
        ]
        
        # Redis is optional in simple mode
        if DASHBOARD_TYPE.lower() == 'scale':
            check_statuses.append(redis_check.get('status'))
        
        # Overall status logic
        if 'unhealthy' in check_statuses:
            overall_status = 'unhealthy'
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif 'degraded' in check_statuses or 'not_applicable' in check_statuses:
            overall_status = 'degraded'
            http_status = status.HTTP_200_OK
        else:
            overall_status = 'healthy'
            http_status = status.HTTP_200_OK
        
        # Build response
        health_data = {
            'status': overall_status,
            'uptime_seconds': round(get_uptime(), 2),
            'checks': {
                'database': db_check,
                'background_tasks': tasks_check
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add Redis check only if applicable
        if DASHBOARD_TYPE.lower() == 'scale':
            health_data['checks']['redis'] = redis_check
        
        response.status_code = http_status
        return HealthCheckResponse(**health_data)
        
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthCheckResponse(
            status='unhealthy',
            uptime_seconds=round(get_uptime(), 2),
            checks={
                'error': {
                    'status': 'unhealthy',
                    'message': f'Health check failed: {str(e)}'
                }
            },
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )

