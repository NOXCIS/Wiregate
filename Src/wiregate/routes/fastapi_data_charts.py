"""
FastAPI Data Charts Router
Migrated from data_charts_api.py Flask blueprint
"""
import logging
from fastapi import APIRouter, Query, Depends
from typing import Dict, Any

from ..models.responses import StandardResponse
from ..modules.Core import Configurations
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


@router.get('/getConfigurationRealtimeTraffic', response_model=StandardResponse)
async def get_configuration_realtime_traffic(
    configurationName: str = Query(..., description="Name of the configuration"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get real-time traffic data for a configuration"""
    logger.debug(f"API_getConfigurationRealtimeTraffic: Requested for configuration '{configurationName}'")
    
    if configurationName is None or configurationName not in Configurations.keys():
        logger.debug(f"API_getConfigurationRealtimeTraffic: Configuration '{configurationName}' does not exist")
        return StandardResponse(
            status=False,
            message="Configuration does not exist"
        )
    
    traffic_data = Configurations[configurationName].getRealtimeTrafficUsage()
    logger.debug(f"API_getConfigurationRealtimeTraffic: Retrieved traffic data for '{configurationName}': {traffic_data}")
    
    return StandardResponse(
        status=True,
        data=traffic_data
    )

