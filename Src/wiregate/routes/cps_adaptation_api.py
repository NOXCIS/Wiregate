"""
FastAPI CPS Pattern Adaptation Router
Handles ML auto-adaptation of I1-I5 CPS patterns for DPI evasion
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


@router.get('/cps/adaptation/stats/{configurationName}', response_model=StandardResponse)
async def get_cps_adaptation_stats(
    configurationName: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get CPS pattern adaptation statistics for a configuration"""
    try:
        if configurationName not in Configurations:
            return StandardResponse(
                status=False,
                message="Configuration not found"
            )
        
        config = Configurations[configurationName]
        stats = config.get_cps_adaptation_stats()
        
        return StandardResponse(
            status=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"Failed to get CPS adaptation stats: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get adaptation stats: {str(e)}"
        )


@router.post('/cps/adaptation/trigger/{configurationName}', response_model=StandardResponse)
async def trigger_cps_adaptation(
    configurationName: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Manually trigger CPS pattern adaptation for a configuration"""
    try:
        if configurationName not in Configurations:
            return StandardResponse(
                status=False,
                message="Configuration not found"
            )
        
        config = Configurations[configurationName]
        
        if not config.cps_adaptation:
            return StandardResponse(
                status=False,
                message="CPS adaptation not available for this configuration"
            )
        
        adapted_patterns = config.periodic_cps_adaptation()
        
        if adapted_patterns:
            return StandardResponse(
                status=True,
                message="CPS patterns adapted successfully",
                data={
                    "adapted": True,
                    "patterns": adapted_patterns
                }
            )
        else:
            return StandardResponse(
                status=True,
                message="No adaptation needed at this time",
                data={
                    "adapted": False
                }
            )
    except Exception as e:
        logger.error(f"Failed to trigger CPS adaptation: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to trigger adaptation: {str(e)}"
        )


@router.get('/cps/adaptation/patterns/{configurationName}', response_model=StandardResponse)
async def get_cps_pattern_performance(
    configurationName: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of patterns to return"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get best performing CPS patterns for a configuration"""
    try:
        if configurationName not in Configurations:
            return StandardResponse(
                status=False,
                message="Configuration not found"
            )
        
        config = Configurations[configurationName]
        
        if not config.cps_adaptation:
            return StandardResponse(
                status=False,
                message="CPS adaptation not available for this configuration"
            )
        
        best_patterns = config.cps_adaptation.metrics.get_best_patterns(limit=limit)
        poor_patterns = config.cps_adaptation.metrics.get_poor_patterns()
        
        return StandardResponse(
            status=True,
            data={
                "best_patterns": best_patterns,
                "poor_patterns": poor_patterns,
                "total_best": len(best_patterns),
                "total_poor": len(poor_patterns)
            }
        )
    except Exception as e:
        logger.error(f"Failed to get CPS pattern performance: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get pattern performance: {str(e)}"
        )

