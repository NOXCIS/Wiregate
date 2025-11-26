"""
System Metrics API Endpoint
Protected endpoint for viewing system performance metrics
"""
import logging
from typing import Optional
from fastapi import APIRouter, Query, Depends

from ..models.responses import StandardResponse
from ..modules.Security.fastapi_dependencies import require_authentication
from ..modules.Metrics import system_metrics

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/metrics', response_model=StandardResponse)
async def get_system_metrics(
    time_window: int = Query(default=3600, ge=60, le=86400, description="Time window in seconds (60-86400)"),
    task_name: Optional[str] = Query(default=None, description="Filter by specific task name"),
    table_name: Optional[str] = Query(default=None, description="Filter by specific table name"),
    user: dict = Depends(require_authentication)
):
    """
    Get system performance metrics
    Requires authentication
    """
    try:
        metrics_data = {}
        
        # Get task metrics
        task_metrics = system_metrics.get_task_metrics_summary(
            task_name=task_name,
            time_window=time_window
        )
        if task_metrics:
            metrics_data['tasks'] = task_metrics
        
        # Get database metrics
        db_metrics = system_metrics.get_db_metrics_summary(
            table_name=table_name,
            time_window=time_window
        )
        if db_metrics:
            metrics_data['database'] = db_metrics
        
        # Get system resource metrics
        system_resource_metrics = system_metrics.get_system_metrics_summary(
            time_window=time_window
        )
        if system_resource_metrics:
            metrics_data['system'] = system_resource_metrics
        
        metrics_data['time_window_seconds'] = time_window
        
        return StandardResponse(
            status=True,
            data=metrics_data
        )
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to retrieve metrics: {str(e)}"
        )


@router.get('/metrics/tasks', response_model=StandardResponse)
async def get_task_metrics(
    time_window: int = Query(default=3600, ge=60, le=86400, description="Time window in seconds"),
    task_name: Optional[str] = Query(default=None, description="Filter by specific task name"),
    user: dict = Depends(require_authentication)
):
    """Get background task execution metrics"""
    try:
        task_metrics = system_metrics.get_task_metrics_summary(
            task_name=task_name,
            time_window=time_window
        )
        
        return StandardResponse(
            status=True,
            data={
                'tasks': task_metrics,
                'time_window_seconds': time_window
            }
        )
    except Exception as e:
        logger.error(f"Error getting task metrics: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to retrieve task metrics: {str(e)}"
        )


@router.get('/metrics/database', response_model=StandardResponse)
async def get_database_metrics(
    time_window: int = Query(default=3600, ge=60, le=86400, description="Time window in seconds"),
    table_name: Optional[str] = Query(default=None, description="Filter by specific table name"),
    user: dict = Depends(require_authentication)
):
    """Get database query performance metrics"""
    try:
        db_metrics = system_metrics.get_db_metrics_summary(
            table_name=table_name,
            time_window=time_window
        )
        
        return StandardResponse(
            status=True,
            data={
                'database': db_metrics,
                'time_window_seconds': time_window
            }
        )
    except Exception as e:
        logger.error(f"Error getting database metrics: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to retrieve database metrics: {str(e)}"
        )


@router.post('/metrics/cleanup', response_model=StandardResponse)
async def cleanup_old_metrics(
    user: dict = Depends(require_authentication)
):
    """Clean up old metrics data"""
    try:
        cleaned_count = system_metrics.cleanup_old_metrics()
        
        return StandardResponse(
            status=True,
            message=f"Cleaned up {cleaned_count} old metric entries",
            data={'cleaned_count': cleaned_count}
        )
    except Exception as e:
        logger.error(f"Error cleaning up metrics: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to cleanup metrics: {str(e)}"
        )

