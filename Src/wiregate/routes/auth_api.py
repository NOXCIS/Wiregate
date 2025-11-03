"""
FastAPI Auth Router
Migrated from auth_api.py Flask blueprint
Handles authentication, sessions, CSRF, and security checks
"""
import bcrypt
import pyotp
import re
import logging
from datetime import datetime
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException
from fastapi import APIRouter, Depends, Request, Response, Query
from typing import Dict, Any, Optional

from ..models.responses import StandardResponse, AuthenticationResponse
from ..models.requests import LoginRequest, WelcomeFinish
from ..modules.DashboardConfig import DashboardConfig
from ..modules.Config import SESSION_TIMEOUT
from ..modules.Logger import AllDashboardLogger
from ..modules.Security.fastapi_dependencies import (
    get_security_manager,
    check_brute_force,
    get_current_user,
    require_authentication,
    get_async_db
)

logger = logging.getLogger('wiregate')

# Create router
router = APIRouter()


def is_safari_webkit(request: Request) -> bool:
    """Detect if the request is from Safari WebKit"""
    user_agent = request.headers.get('user-agent', '').lower()
    return 'safari' in user_agent and 'webkit' in user_agent and 'chrome' not in user_agent


def escape_ldap_filter(value):
    """Escape special characters in LDAP filter to prevent injection"""
    if not value:
        return ""
    
    # Escape LDAP special characters
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("(", "\\28")
    escaped = escaped.replace(")", "\\29")
    escaped = escaped.replace("&", "\\26")
    escaped = escaped.replace("|", "\\7c")
    escaped = escaped.replace("=", "\\3d")
    escaped = escaped.replace("<", "\\3c")
    escaped = escaped.replace(">", "\\3e")
    escaped = escaped.replace(";", "\\3b")
    escaped = escaped.replace(",", "\\2c")
    escaped = escaped.replace("+", "\\2b")
    escaped = escaped.replace("*", "\\2a")
    escaped = escaped.replace("~", "\\7e")
    escaped = escaped.replace("!", "\\21")
    escaped = escaped.replace("#", "\\23")
    escaped = escaped.replace("$", "\\24")
    escaped = escaped.replace("%", "\\25")
    escaped = escaped.replace("^", "\\5e")
    escaped = escaped.replace("[", "\\5b")
    escaped = escaped.replace("]", "\\5d")
    escaped = escaped.replace("{", "\\7b")
    escaped = escaped.replace("}", "\\7d")
    escaped = escaped.replace("`", "\\60")
    escaped = escaped.replace("?", "\\3f")
    escaped = escaped.replace("/", "\\2f")
    
    return escaped


def authenticate_ldap(username, password):
    """Authenticate user against LDAP server"""
    if not DashboardConfig.GetConfig("LDAP", "enabled")[1]:
        return False, None, "LDAP authentication not enabled"
    
    conn = None
    user_conn = None
    
    def safe_get_attr(attrs: dict, key: str, default="") -> str:
        values = attrs.get(key, [])
        if isinstance(values, list) and len(values) > 0:
            return values[0]
        return default
    
    try:
        ldap_server = DashboardConfig.GetConfig("LDAP", "server")[1]
        ldap_port_str = DashboardConfig.GetConfig("LDAP", "port")[1]
        use_ssl = DashboardConfig.GetConfig("LDAP", "use_ssl")[1]
        
        try:
            ldap_port = int(ldap_port_str)
        except ValueError:
            AllDashboardLogger.log("", "", Message="LDAP Error: Source port must be an integer")
            return False, None, "LDAP Error: Source port must be an integer"
        
        server = Server(ldap_server, port=ldap_port, use_ssl=use_ssl, get_info=ALL)
        
        bind_dn = DashboardConfig.GetConfig("LDAP", "bind_dn")[1]
        bind_password = DashboardConfig.GetConfig("LDAP", "bind_password")[1]
        if bind_dn and bind_password:
            conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
        else:
            conn = Connection(server, auto_bind=True)
        
        search_base = DashboardConfig.GetConfig("LDAP", "search_base")[1]
        raw_search_filter = DashboardConfig.GetConfig("LDAP", "search_filter")[1]
        
        # Escape username to prevent LDAP injection
        escaped_username = escape_ldap_filter(username)
        search_filter = raw_search_filter % escaped_username
        
        conn.search(search_base, search_filter, search_scope=SUBTREE, attributes=['mail', 'givenName', 'sn'])
        if not conn.entries:
            return False, None, "User not found"
        
        user_dn = conn.entries[0].entry_dn
        user_attrs = conn.entries[0].entry_attributes_as_dict
        
        if DashboardConfig.GetConfig("LDAP", "require_group")[1]:
            group_dn = DashboardConfig.GetConfig("LDAP", "group_dn")[1]
            escaped_user_dn = escape_ldap_filter(user_dn)
            group_filter = f"(&(objectClass=group)(member={escaped_user_dn}))"
            conn.search(group_dn, group_filter, search_scope=SUBTREE)
            if not conn.entries:
                return False, None, "User not in required group"
        
        try:
            user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        except LDAPException:
            return False, None, "Invalid credentials"
        
        user_data = {
            "username": username,
            "email": safe_get_attr(user_attrs, 'mail'),
            "firstname": safe_get_attr(user_attrs, 'givenName'),
            "lastname": safe_get_attr(user_attrs, 'sn')
        }
        
        return True, user_data, None
        
    except LDAPException as e:
        return False, None, f"LDAP Error: {str(e)}"
    except Exception as e:
        return False, None, f"Error: {str(e)}"
    finally:
        if conn:
            conn.unbind()
        if user_conn:
            user_conn.unbind()


def generate_csrf_token(request: Request, security_mgr) -> str:
    """Generate a CSRF token for the session"""
    session_data = getattr(request.state, 'session', {})
    if 'csrf_token' not in session_data:
        session_data['csrf_token'] = security_mgr.generate_secure_token(32)
        request.state.session = session_data
    return session_data['csrf_token']


@router.get('/handshake', response_model=StandardResponse)
async def handshake():
    """API handshake endpoint"""
    return StandardResponse(status=True)


@router.get('/security-check', response_model=StandardResponse)
async def security_check():
    """Perform security startup checks"""
    try:
        # Import the function from Flask auth_api
        from . import auth_api
        success = auth_api.perform_security_startup_checks()
        if success:
            return StandardResponse(status=True, message="Security checks completed successfully")
        else:
            return StandardResponse(status=False, message="Security checks failed")
    except Exception as e:
        return StandardResponse(status=False, message=f"Security check error: {str(e)}")


@router.get('/validateAuthentication', response_model=StandardResponse)
async def validate_authentication(
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(get_current_user),
    security_mgr = Depends(get_security_manager)
):
    """Validate current authentication status"""
    if not DashboardConfig.GetConfig("Server", "auth_req")[1]:
        return StandardResponse(status=True)
    
    if user and user.get('authenticated'):
        return StandardResponse(status=True)
    
    # Track session expiration for grace period in rate limiting
    client_ip = request.client.host if request.client else "unknown"
    security_mgr.record_session_expiration(client_ip)
    
    return StandardResponse(status=False, message="Invalid authentication.")


@router.get('/requireAuthentication', response_model=StandardResponse)
async def require_auth_check():
    """Check if authentication is required"""
    auth_required = DashboardConfig.GetConfig("Server", "auth_req")[1]
    return StandardResponse(status=True, data=auth_required)


@router.post('/authenticate', response_model=StandardResponse)
async def authenticate_login(
    request: Request,
    response: Response,
    login_data: Dict[str, str],
    security_mgr = Depends(get_security_manager),
    brute_force_check = Depends(check_brute_force)
):
    """Authenticate user login"""
    if not DashboardConfig.GetConfig("Server", "auth_req")[1]:
        welcome_session = DashboardConfig.GetConfig("Other", "welcome_session")[1]
        
        # Return response with welcome_session data and include CSRF token
        response_data = welcome_session if isinstance(welcome_session, bool) else welcome_session
        # CSRF token is in session cookie, so we don't need to return it in response
        # The frontend will fetch it via /api/csrf-token endpoint
        
        return StandardResponse(
            status=True,
            data=response_data
        )
    
    # Sanitize username
    username = security_mgr.sanitize_input(login_data.get('username', ''), 30)
    password = login_data.get('password', '')
    
    # Validate username format
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return StandardResponse(
            status=False,
            message="Invalid username format"
        )
    
    client_ip = request.client.host if request.client else "unknown"
    
    # Check if LDAP is enabled
    ldap_enabled = DashboardConfig.GetConfig("LDAP", "enabled")[1]
    
    if ldap_enabled:
        success, user_data, error = authenticate_ldap(username, password)
        if not success:
            AllDashboardLogger.log(
                str(request.url),
                client_ip,
                Message=f"LDAP Login failed: {username}"
            )
            security_mgr.record_failed_attempt(client_ip)
            return StandardResponse(
                status=False,
                message="Authentication failed"
            )
        
        # LDAP authentication successful
        session_data = {}
        session_id = security_mgr.generate_secure_token(32)
        auth_token = security_mgr.generate_secure_token(32)
        csrf_token = security_mgr.generate_secure_token(32)  # Generate CSRF token at login
        
        # Store in request state for session middleware
        request.state.session = {
            'session_id': session_id,
            'username': username,
            'auth_token': auth_token,
            'csrf_token': csrf_token,  # Include CSRF token in session
            'user_data': user_data,
            'last_activity': datetime.now().timestamp(),
            'new_session': True
        }
        
        # Set cookies
        is_secure = request.url.scheme == "https"
        is_safari = is_safari_webkit(request)
        
        if is_safari and not is_secure:
            response.set_cookie(
                "authToken", auth_token,
                httponly=True, secure=False,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
            response.set_cookie(
                "sessionId", session_id,
                httponly=True, secure=False,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
        else:
            response.set_cookie(
                "authToken", auth_token,
                httponly=True, secure=is_secure,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
            response.set_cookie(
                "sessionId", session_id,
                httponly=True, secure=is_secure,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
        
        security_mgr.clear_failed_attempts(client_ip)
        
        AllDashboardLogger.log(
            str(request.url),
            client_ip,
            Message=f"LDAP Login success: {username}"
        )
        
        welcome_session = DashboardConfig.GetConfig("Other", "welcome_session")[1]
        
        # Return response with welcome_session data and include CSRF token
        response_data = welcome_session if isinstance(welcome_session, bool) else welcome_session
        # CSRF token is in session cookie, so we don't need to return it in response
        # The frontend will fetch it via /api/csrf-token endpoint
        
        return StandardResponse(
            status=True,
            data=response_data
        )
    
    # Local authentication
    stored_password = DashboardConfig.GetConfig("Account", "password")[1]
    
    # Verify password against hash
    if not stored_password.startswith('$2b$'):
        AllDashboardLogger.log(
            str(request.url),
            client_ip,
            Message="CRITICAL: Password is not in hashed format"
        )
        return StandardResponse(
            status=False,
            message="Authentication system error. Please contact administrator."
        )
    
    valid = security_mgr.verify_password(password, stored_password)
    
    totpEnabled = DashboardConfig.GetConfig("Account", "enable_totp")[1]
    totpValid = False
    if totpEnabled:
        totp_code = login_data.get('totp', '')
        if not totp_code:
            return StandardResponse(
                status=False,
                message="TOTP code is required when TOTP is enabled"
            )
        if not re.match(r'^[0-9]{6}$', totp_code):
            return StandardResponse(
                status=False,
                message="Invalid TOTP code format"
            )
        totpValid = pyotp.TOTP(
            DashboardConfig.GetConfig("Account", "totp_key")[1]
        ).verify(totp_code, valid_window=1)
    
    configured_username = DashboardConfig.GetConfig("Account", "username")[1]
    
    if (valid and username == configured_username and 
        ((totpEnabled and totpValid) or not totpEnabled)):
        
        # Create session
        session_id = security_mgr.generate_secure_token(32)
        auth_token = security_mgr.generate_secure_token(32)
        csrf_token = security_mgr.generate_secure_token(32)  # Generate CSRF token at login
        
        request.state.session = {
            'session_id': session_id,
            'username': username,
            'auth_token': auth_token,
            'csrf_token': csrf_token,  # Include CSRF token in session
            'last_activity': datetime.now().timestamp(),
            'new_session': True
        }
        
        # Set cookies
        is_secure = request.url.scheme == "https"
        is_safari = is_safari_webkit(request)
        
        if is_safari and not is_secure:
            response.set_cookie(
                "authToken", auth_token,
                httponly=True, secure=False,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
            response.set_cookie(
                "sessionId", session_id,
                httponly=True, secure=False,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
        else:
            response.set_cookie(
                "authToken", auth_token,
                httponly=True, secure=is_secure,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
            response.set_cookie(
                "sessionId", session_id,
                httponly=True, secure=is_secure,
                max_age=SESSION_TIMEOUT, samesite='lax'
            )
        
        security_mgr.clear_failed_attempts(client_ip)
        
        AllDashboardLogger.log(
            str(request.url),
            client_ip,
            Message=f"Login success: {username}"
        )
        
        welcome_session = DashboardConfig.GetConfig("Other", "welcome_session")[1]
        
        # Return response with welcome_session data and include CSRF token
        response_data = welcome_session if isinstance(welcome_session, bool) else welcome_session
        # CSRF token is in session cookie, so we don't need to return it in response
        # The frontend will fetch it via /api/csrf-token endpoint
        
        return StandardResponse(
            status=True,
            data=response_data
        )
    
    AllDashboardLogger.log(
        str(request.url),
        client_ip,
        Message=f"Login failed: {username}"
    )
    
    security_mgr.record_failed_attempt(client_ip)
    
    if totpEnabled:
        return StandardResponse(
            status=False,
            message="Sorry, your username, password or OTP is incorrect."
        )
    else:
        return StandardResponse(
            status=False,
            message="Sorry, your username or password is incorrect."
        )


@router.get('/signout', response_model=StandardResponse)
async def signout(request: Request, response: Response):
    """Sign out and clear session"""
    # Clear session data
    request.state.session = {}
    
    # Clear cookies
    is_secure = request.url.scheme == "https"
    is_safari = is_safari_webkit(request)
    
    if is_safari and not is_secure:
        response.delete_cookie("authToken", httponly=True, secure=False, samesite='lax')
        response.delete_cookie("sessionId", httponly=True, secure=False, samesite='lax')
    else:
        response.delete_cookie("authToken", httponly=True, secure=is_secure, samesite='lax')
        response.delete_cookie("sessionId", httponly=True, secure=is_secure, samesite='lax')
    
    return StandardResponse(
        status=True,
        message="Logged out successfully"
    )


@router.get('/csrf-token', response_model=StandardResponse)
async def get_csrf_token(
    request: Request,
    user: Dict[str, Any] = Depends(require_authentication),
    security_mgr = Depends(get_security_manager)
):
    """Get CSRF token for forms"""
    csrf_token = generate_csrf_token(request, security_mgr)
    return StandardResponse(
        status=True,
        data={"csrf_token": csrf_token}
    )


@router.get('/isTotpEnabled', response_model=StandardResponse)
async def is_totp_enabled():
    """Check if TOTP is enabled"""
    totp_enabled = (
        DashboardConfig.GetConfig("Account", "enable_totp")[1] and
        DashboardConfig.GetConfig("Account", "totp_verified")[1]
    )
    return StandardResponse(status=True, data=totp_enabled)


@router.get('/Welcome_GetTotpLink', response_model=StandardResponse)
async def welcome_get_totp_link():
    """Get TOTP provisioning link for welcome setup"""
    if not DashboardConfig.GetConfig("Account", "totp_verified")[1]:
        DashboardConfig.SetConfig("Account", "totp_key", pyotp.random_base32())
        provisioning_uri = pyotp.totp.TOTP(
            DashboardConfig.GetConfig("Account", "totp_key")[1]
        ).provisioning_uri(issuer_name="WireGate")
        return StandardResponse(status=True, data=provisioning_uri)
    return StandardResponse(status=False)


@router.post('/Welcome_VerifyTotpLink', response_model=StandardResponse)
async def welcome_verify_totp_link(
    verify_data: Dict[str, str]
):
    """Verify TOTP code during welcome setup"""
    totp = pyotp.TOTP(DashboardConfig.GetConfig("Account", "totp_key")[1]).now()
    is_valid = totp == verify_data.get('totp')
    
    if is_valid:
        DashboardConfig.SetConfig("Account", "totp_verified", "true")
        DashboardConfig.SetConfig("Account", "enable_totp", "true")
    
    return StandardResponse(status=is_valid)


@router.post('/Welcome_Finish', response_model=StandardResponse)
async def welcome_finish(
    welcome_data: Dict[str, str],
    security_mgr = Depends(get_security_manager)
):
    """Complete welcome setup"""
    if DashboardConfig.GetConfig("Other", "welcome_session")[1]:
        # Validate passwords match
        new_password = welcome_data.get('newPassword', '')
        if new_password != welcome_data.get('repeatNewPassword', ''):
            return StandardResponse(status=False, message="Passwords do not match")
        
        # Validate password policy
        is_valid, error_msg = security_mgr.validate_password_policy(new_password)
        if not is_valid:
            return StandardResponse(status=False, message=error_msg)
        
        updateUsername, updateUsernameErr = DashboardConfig.SetConfig(
            "Account", "username", welcome_data.get('username', '')
        )
        updatePassword, updatePasswordErr = DashboardConfig.SetConfig(
            "Account", "password",
            {
                "newPassword": new_password,
                "repeatNewPassword": welcome_data.get('repeatNewPassword', ''),
                "currentPassword": "admin"
            }
        )
        
        if not updateUsername or not updatePassword:
            return StandardResponse(
                status=False,
                message=f"{updateUsernameErr},{updatePasswordErr}".strip(",")
            )
        
        DashboardConfig.SetConfig("Other", "welcome_session", False)
    
    return StandardResponse(status=True)


@router.get('/rate-limit-status', response_model=StandardResponse)
async def get_rate_limit_status(
    request: Request,
    security_mgr = Depends(get_security_manager)
):
    """Get current rate limit status for the requesting IP"""
    identifier = request.client.host if request.client else "unknown"
    status_data = security_mgr.get_rate_limit_status(identifier)
    return StandardResponse(status=True, data=status_data)


@router.post('/reset-rate-limit', response_model=StandardResponse)
async def reset_rate_limit(
    reset_data: Dict[str, str],
    user: Dict[str, Any] = Depends(require_authentication),
    security_mgr = Depends(get_security_manager)
):
    """Reset rate limit for a specific identifier (admin function)"""
    identifier = reset_data.get('identifier', '')
    
    # Check authorization
    if not DashboardConfig.APIAccessed:
        return StandardResponse(
            status=False,
            message="Unauthorized"
        )
    
    success = security_mgr.reset_rate_limit(identifier)
    if success:
        return StandardResponse(
            status=True,
            message=f"Rate limit reset for {identifier}"
        )
    else:
        return StandardResponse(
            status=False,
            message="Failed to reset rate limit"
        )


@router.post('/validate-csrf', response_model=StandardResponse)
async def validate_csrf(
    csrf_data: Dict[str, str],
    request: Request,
    security_mgr = Depends(get_security_manager)
):
    """Validate CSRF token"""
    csrf_token = csrf_data.get('csrf_token', '')
    session_data = getattr(request.state, 'session', {})
    
    if 'csrf_token' not in session_data:
        return StandardResponse(status=False, message="No CSRF token in session")
    
    if not security_mgr.constant_time_compare(csrf_token, session_data['csrf_token']):
        return StandardResponse(status=False, message="Invalid CSRF token")
    
    return StandardResponse(status=True, message="CSRF token is valid")


@router.get('/distributed-rate-limit-test', response_model=StandardResponse)
async def test_distributed_rate_limit(
    request: Request,
    security_mgr = Depends(get_security_manager)
):
    """Test endpoint for distributed rate limiting"""
    identifier = request.client.host if request.client else "unknown"
    is_limited, info = security_mgr.is_distributed_rate_limited(identifier, limit=10, window=60)
    
    return StandardResponse(
        status=True,
        data={
            'is_limited': is_limited,
            'info': info,
            'identifier': identifier
        }
    )


@router.get('/rate-limit-metrics', response_model=StandardResponse)
async def get_rate_limit_metrics(
    request: Request,
    window: int = Query(default=3600, description="Time window in seconds"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get rate limiting metrics and statistics"""
    if not DashboardConfig.APIAccessed:
        return StandardResponse(status=False, message="Unauthorized")
    
    from ..modules.RateLimitMetrics import rate_limit_metrics
    metrics = rate_limit_metrics.get_metrics_summary(window)
    
    return StandardResponse(status=True, data=metrics)


@router.get('/rate-limit-health', response_model=StandardResponse)
async def get_rate_limit_health():
    """Get rate limiting system health status"""
    from ..modules.RateLimitMetrics import rate_limit_metrics
    health = rate_limit_metrics.get_health_status()
    return StandardResponse(status=True, data=health)


@router.get('/top-limited-identifiers', response_model=StandardResponse)
async def get_top_limited_identifiers(
    limit: int = Query(default=10, description="Number of top identifiers to return"),
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Get top identifiers that are being rate limited"""
    if not DashboardConfig.APIAccessed:
        return StandardResponse(status=False, message="Unauthorized")
    
    from ..modules.RateLimitMetrics import rate_limit_metrics
    top_limited = rate_limit_metrics.get_top_limited_identifiers(limit)
    
    return StandardResponse(status=True, data=top_limited)


@router.post('/cleanup-rate-limit-metrics', response_model=StandardResponse)
async def cleanup_rate_limit_metrics(
    user: Dict[str, Any] = Depends(require_authentication)
):
    """Clean up old rate limiting metrics data"""
    if not DashboardConfig.APIAccessed:
        return StandardResponse(status=False, message="Unauthorized")
    
    from ..modules.RateLimitMetrics import rate_limit_metrics
    cleaned_count = rate_limit_metrics.cleanup_old_metrics()
    
    return StandardResponse(
        status=True,
        message=f"Cleaned up {cleaned_count} old metrics entries"
    )

