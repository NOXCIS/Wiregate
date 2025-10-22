"""
FastAPI Dependencies for Security Features
Dependency injection functions for authentication, API keys, rate limiting, etc.
"""
import time
import logging
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import APIKeyHeader
from datetime import datetime

from ..Config import SESSION_TIMEOUT

logger = logging.getLogger(__name__)

# Defer DashboardConfig import to avoid circular dependency
def _get_dashboard_config():
    from ..DashboardConfig import DashboardConfig
    return DashboardConfig

# API Key header scheme
api_key_header = APIKeyHeader(name="wg-dashboard-apikey", auto_error=False)


async def get_security_manager():
    """Get the global security manager instance"""
    from .Security import security_manager
    return security_manager


async def verify_api_key_dependency(
    api_key: Optional[str] = Depends(api_key_header),
    security_mgr = Depends(get_security_manager)
) -> bool:
    """
    Verify API key from header
    Returns True if valid API key, False otherwise
    """
    if not api_key:
        return False
    
    DashboardConfig = _get_dashboard_config()
    
    # Check if API keys are enabled
    api_key_enabled = DashboardConfig.GetConfig("Server", "dashboard_api_key")[1]
    if not api_key_enabled:
        return False
    
    # Verify API key using security manager
    valid_keys = [key.Key for key in DashboardConfig.DashboardAPIKeys]
    is_valid = security_mgr.verify_api_key(api_key, valid_keys)
    
    if is_valid:
        DashboardConfig.APIAccessed = True
        return True
    
    return False


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from session
    Replaces Flask's require_authentication decorator
    Returns user data if authenticated, None otherwise
    """
    DashboardConfig = _get_dashboard_config()
    
    # Check if authentication is required
    auth_required = DashboardConfig.GetConfig("Server", "auth_req")[1]
    if not auth_required:
        configured_username = DashboardConfig.GetConfig("Account", "username")[1]
        return {"username": configured_username, "authenticated": True}  # No auth required
    
    # Get session data from request state (set by session middleware)
    session_data = getattr(request.state, 'session', {})
    
    # Check for proper session structure
    if "session_id" not in session_data or "username" not in session_data or "auth_token" not in session_data:
        return None
    
    # Validate session token from cookie
    auth_token = request.cookies.get("authToken")
    if not auth_token:
        return None
    
    # Import security manager
    from .Security import security_manager
    
    # Verify token matches session
    if not security_manager.constant_time_compare(auth_token, session_data.get("auth_token", "")):
        return None
    
    # Check session timeout
    if 'last_activity' in session_data:
        last_activity = session_data['last_activity']
        if datetime.now().timestamp() - last_activity > SESSION_TIMEOUT:
            # Session expired
            return None
    
    # Update last activity (will be saved by session middleware)
    session_data['last_activity'] = datetime.now().timestamp()
    request.state.session = session_data
    
    return {
        "username": session_data.get("username"),
        "session_id": session_data.get("session_id"),
        "authenticated": True,
        "user_data": session_data.get("user_data")
    }


async def require_authentication(
    request: Request,
    api_key_valid: bool = Depends(verify_api_key_dependency)
) -> Dict[str, Any]:
    """
    Dependency that requires authentication via session or API key
    Raises HTTPException if not authenticated
    """
    # Check if API key is valid first
    if api_key_valid:
        return {"username": "api_key", "authenticated": True, "api_key": True}
    
    # Check for session authentication
    user = await get_current_user(request)
    if user and user.get('authenticated'):
        return user
    
    # Not authenticated
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, but don't require it
    For endpoints that are public but can use auth if available
    """
    return await get_current_user(request)


async def check_brute_force(
    request: Request,
    security_mgr = Depends(get_security_manager)
) -> None:
    """
    Check for brute force lockout before allowing authentication attempts
    Raises HTTPException if locked
    """
    identifier = request.client.host if request.client else "unknown"
    
    is_locked, info = security_mgr.check_brute_force(identifier)
    
    if is_locked:
        remaining_time = info.get('remaining_time', 0)
        raise HTTPException(
            status_code=423,  # Locked
            detail={
                'status': False,
                'message': f'Account temporarily locked due to too many failed attempts. Try again in {remaining_time} seconds.',
                'data': {
                    'locked_until': info.get('locked_until', 0),
                    'remaining_time': remaining_time
                }
            }
        )


async def validate_csrf_token(
    request: Request,
    csrf_token: Optional[str] = Header(None, alias="X-CSRF-Token")
) -> bool:
    """
    Validate CSRF token from header
    Returns True if valid, raises HTTPException if invalid for protected methods
    """
    # Only validate CSRF for state-changing methods
    if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
        return True
    
    # Get session data
    session_data = getattr(request.state, 'session', {})
    
    if 'csrf_token' not in session_data:
        # No CSRF token in session, skip validation for now
        return True
    
    if not csrf_token:
        raise HTTPException(
            status_code=403,
            detail="CSRF token missing"
        )
    
    from .Security import security_manager
    
    if not security_manager.constant_time_compare(csrf_token, session_data['csrf_token']):
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token"
        )
    
    return True


async def get_async_db():
    """Get async database manager for dependency injection"""
    from ..DataBase.AsyncDataBaseManager import get_async_db_manager
    return await get_async_db_manager()


async def get_async_config_db(configuration_name: str):
    """Get async configuration database for a specific configuration"""
    from ..DataBase.AsyncDataBaseManager import AsyncConfigurationDatabase
    return AsyncConfigurationDatabase(configuration_name)

