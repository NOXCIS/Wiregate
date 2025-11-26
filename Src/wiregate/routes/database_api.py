"""
FastAPI Database Router
Migrated from database_api.py Flask blueprint
"""
import logging
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..models.responses import StandardResponse
from ..modules.DataBase.DataBaseManager import DatabaseAPI
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.get('/database/config', response_model=StandardResponse)
async def get_database_config(
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Get current database configuration"""
    try:
        config = DatabaseAPI.get_config()
        return StandardResponse(status=True, data=config)
    except Exception as e:
        logger.error(f"Failed to get database config: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get database configuration: {str(e)}"
        )


@router.post('/database/config', response_model=StandardResponse)
async def update_database_config(
    config_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Update database configuration"""
    try:
        if not config_data:
            return StandardResponse(
                status=False,
                message="No configuration data provided"
            )
        
        result = DatabaseAPI.update_config(config_data)
        if result:
            return StandardResponse(
                status=True,
                message="Database configuration updated successfully"
            )
        else:
            return StandardResponse(
                status=False,
                message="Failed to update database configuration"
            )
    except Exception as e:
        logger.error(f"Failed to update database config: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to update database configuration: {str(e)}"
        )


@router.get('/database/stats', response_model=StandardResponse)
async def get_database_stats(
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Get database statistics"""
    try:
        stats = await DatabaseAPI.get_stats()
        return StandardResponse(status=True, data=stats)
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get database statistics: {str(e)}"
        )


@router.post('/database/test', response_model=StandardResponse)
async def test_database_connections(
    test_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Test database connections"""
    try:
        if not test_data:
            return StandardResponse(
                status=False,
                message="No configuration data provided"
            )
        
        result = DatabaseAPI.test_connections(test_data)
        if result['success']:
            return StandardResponse(status=True, data=result['data'])
        else:
            return StandardResponse(status=False, message=result['message'])
    except Exception as e:
        logger.error(f"Failed to test database connections: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to test database connections: {str(e)}"
        )


@router.post('/database/clear-cache', response_model=StandardResponse)
async def clear_database_cache(
    user: Dict[str, Any] = Depends(require_authentication),
    async_db = Depends(get_async_db)
):
    """Clear database cache"""
    try:
        result = await DatabaseAPI.clear_cache()
        if result['success']:
            return StandardResponse(status=True, message=result['message'])
        else:
            return StandardResponse(status=False, message=result['message'])
    except Exception as e:
        logger.error(f"Failed to clear database cache: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to clear database cache: {str(e)}"
        )

