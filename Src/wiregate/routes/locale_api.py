"""
FastAPI Locale Router
Migrated from locale_api.py Flask blueprint
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any, Optional

from ..models.responses import StandardResponse
from ..modules.Locale.Locale import Locale
from ..modules.Security.fastapi_dependencies import require_authentication, get_async_db

# Create router
router = APIRouter()

# Create locale instance
locale_instance = Locale()


@router.get('/locale', response_model=StandardResponse)
async def get_current_language():
    """Get current dashboard language"""
    lang_data = locale_instance.getLanguage()
    return StandardResponse(
        status=True,
        data=lang_data
    )


@router.get('/locale/available', response_model=StandardResponse)
async def get_available_languages():
    """Get list of available languages"""
    return StandardResponse(
        status=True,
        data=locale_instance.activeLanguages
    )


@router.post('/locale/update', response_model=StandardResponse)
async def update_language(
    lang_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Update dashboard language"""
    if 'lang_id' not in lang_data:
        return StandardResponse(
            status=False,
            message="Please specify a lang_id"
        )
    
    locale_instance.updateLanguage(lang_data['lang_id'])
    
    return StandardResponse(
        status=True,
        data=locale_instance.getLanguage()
    )

