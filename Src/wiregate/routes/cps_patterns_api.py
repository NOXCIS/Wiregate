"""
CPS Pattern Library API
API endpoints for accessing and managing CPS pattern library
"""
import logging
import os
import random
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from ..models.responses import StandardResponse
from ..modules.Security.fastapi_dependencies import require_authentication
from ..modules.AwgCPS.CPSPatternLibrary import CPSPatternLibrary
from ..modules.AwgCPS.CPSPatternExtractor import CPSPatternExtractor
from ..modules.Utilities import ValidateCPSFormat

logger = logging.getLogger('wiregate')

router = APIRouter()


def get_pattern_library() -> CPSPatternLibrary:
    """Get pattern library instance"""
    return CPSPatternLibrary()


@router.get('/cps-patterns/statistics', response_model=StandardResponse)
async def get_statistics(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """
    Get pattern library statistics
    
    Returns:
        StandardResponse with library statistics
    """
    try:
        library = get_pattern_library()
        stats = library.get_pattern_statistics()
        
        return StandardResponse(
            status=True,
            message="Statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get statistics: {str(e)}"
        )


@router.get('/cps-patterns/{protocol}', response_model=StandardResponse)
async def get_random_pattern(
    protocol: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """
    Get random CPS pattern for a protocol
    
    Args:
        protocol: Protocol type (http_get, http_response, dns, quic, json)
    
    Returns:
        StandardResponse with CPS pattern string
    """
    try:
        library = get_pattern_library()
        
        # Log library path for debugging
        logger.debug(f"Pattern library path: {library.library_path}")
        logger.debug(f"Patterns file: {library.patterns_file}")
        
        # Validate protocol
        valid_protocols = ['http_get', 'http_response', 'dns', 'quic', 'json']
        if protocol not in valid_protocols:
            return StandardResponse(
                status=False,
                message=f"Invalid protocol. Must be one of: {', '.join(valid_protocols)}"
            )
        
        # Get full pattern with ID
        try:
            patterns = library.load_patterns(protocol)
            logger.debug(f"Loaded {len(patterns) if patterns else 0} patterns for {protocol}")
        except Exception as load_error:
            logger.error(f"Error loading patterns for {protocol}: {load_error}")
            import traceback
            logger.error(traceback.format_exc())
            return StandardResponse(
                status=False,
                message=f"Failed to load patterns: {str(load_error)}"
            )
        
        if not patterns:
            logger.warning(f"No patterns available for protocol: {protocol} (library path: {library.library_path})")
            # Try to load all patterns to see what's available
            try:
                all_patterns = library.load_patterns()
                logger.debug(f"Total patterns in library: {len(all_patterns) if all_patterns else 0}")
                if all_patterns:
                    protocols_found = set(p.get('protocol') for p in all_patterns if p.get('protocol'))
                    logger.debug(f"Protocols found: {protocols_found}")
            except Exception as e:
                logger.warning(f"Failed to load patterns from library: {e}")
                pass
            return StandardResponse(
                status=False,
                message=f"No patterns available for protocol: {protocol}"
            )
        
        selected = random.choice(patterns)
        pattern = selected.get('cps_pattern', '')
        pattern_id = selected.get('id', '')
        
        # Validate that we have a pattern
        if not pattern or not pattern.strip():
            logger.warning(f"Selected pattern for {protocol} is empty (ID: {pattern_id})")
            return StandardResponse(
                status=False,
                message=f"Pattern retrieved but is empty for protocol: {protocol}"
            )
        
        logger.debug(f"Retrieved {protocol} pattern {pattern_id}: {len(pattern)} chars")
        
        return StandardResponse(
            status=True,
            message="Pattern retrieved successfully",
            data={
                'cps_pattern': pattern,
                'pattern_id': pattern_id,
                'protocol': protocol
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting random pattern: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get pattern: {str(e)}"
        )


@router.get('/cps-patterns/{protocol}/all', response_model=StandardResponse)
async def get_all_patterns(
    protocol: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """
    Get all CPS patterns for a protocol
    
    Args:
        protocol: Protocol type
    
    Returns:
        StandardResponse with list of all patterns
    """
    try:
        library = get_pattern_library()
        
        patterns = library.load_patterns(protocol)
        
        return StandardResponse(
            status=True,
            message=f"Retrieved {len(patterns)} patterns",
            data={'patterns': patterns, 'count': len(patterns)}
        )
        
    except Exception as e:
        logger.error(f"Error getting all patterns: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to get patterns: {str(e)}"
        )


@router.post('/cps-patterns', response_model=StandardResponse)
async def add_pattern(
    pattern_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """
    Add a CPS pattern to the library
    
    Request body:
        {
            "protocol": "http_get",
            "cps_pattern": "<b 0x47455420>...",
            "metadata": {...}
        }
    
    Returns:
        StandardResponse with success status
    """
    try:
        library = get_pattern_library()
        
        # Validate required fields
        if 'protocol' not in pattern_data or 'cps_pattern' not in pattern_data:
            return StandardResponse(
                status=False,
                message="Missing required fields: protocol and cps_pattern"
            )
        
        # Validate CPS format
        cps_pattern = pattern_data['cps_pattern']
        is_valid, error_msg = library.validate_pattern(cps_pattern)
        if not is_valid:
            return StandardResponse(
                status=False,
                message=f"Invalid CPS pattern format: {error_msg}"
            )
        
        # Prepare pattern dict
        pattern = {
            'protocol': pattern_data['protocol'],
            'cps_pattern': cps_pattern,
            'metadata': pattern_data.get('metadata', {})
        }
        
        # Save pattern
        success = library.save_pattern(pattern)
        
        if success:
            return StandardResponse(
                status=True,
                message="Pattern added successfully"
            )
        else:
            return StandardResponse(
                status=False,
                message="Failed to save pattern"
            )
        
    except Exception as e:
        logger.error(f"Error adding pattern: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to add pattern: {str(e)}"
        )


@router.delete('/cps-patterns/{pattern_id}', response_model=StandardResponse)
async def delete_pattern(
    pattern_id: str,
    user: Dict[str, Any] = Depends(require_authentication)
):
    """
    Delete a CPS pattern from the library
    
    Args:
        pattern_id: Pattern ID to delete
    
    Returns:
        StandardResponse with success status
    """
    try:
        library = get_pattern_library()
        
        success = library.delete_pattern(pattern_id)
        
        if success:
            return StandardResponse(
                status=True,
                message="Pattern deleted successfully"
            )
        else:
            return StandardResponse(
                status=False,
                message="Pattern not found or deletion failed"
            )
        
    except Exception as e:
        logger.error(f"Error deleting pattern: {e}")
        return StandardResponse(
            status=False,
            message=f"Failed to delete pattern: {str(e)}"
        )

