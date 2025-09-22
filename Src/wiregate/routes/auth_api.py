import bcrypt
import pyotp
import html
import re
from datetime import datetime
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException
from flask import Flask, Blueprint, request, session, make_response, jsonify, g
from ..modules.DashboardConfig import DashboardConfig
from ..modules.App import ResponseObject
from ..modules.Core import  APP_PREFIX
from ..modules.App import app
from ..modules.Security import (
    security_manager, rate_limit, brute_force_protection, 
    validate_input, require_authentication, secure_headers
)
from ..modules.ConfigEnv import SESSION_TIMEOUT

from ..modules.Logger import AllDashboardLogger
auth_blueprint = Blueprint('auth', __name__)

@app.before_request
def auth_req():
    if request.method.lower() == 'options':
        return ResponseObject(True)

    DashboardConfig.APIAccessed = False
    if "api" in request.path:
        if str(request.method) == "GET":
            AllDashboardLogger.log(str(request.url), str(request.remote_addr), Message="API GET request")
        elif str(request.method) == "POST":
            content_type = request.headers.get('Content-Type', '')
            try:
                # Attempt to parse the JSON body of the request
                body = request.get_json()
                if body is None:
                    # If get_json() returns None, the body is empty or not JSON
                    raise ValueError("Empty or invalid JSON body")
                # Sanitize body for logging (remove sensitive fields)
                sanitized_body = {k: v for k, v in body.items() if k.lower() not in ['password', 'totp', 'token']}
                body_repr = str(sanitized_body)
            except Exception as e:
                # If parsing fails, check if Content-Type is multipart/form-data
                if 'multipart/form-data' in content_type:
                    try:
                        # Attempt to parse multipart/form-data
                        # This will not parse the body but ensures it's multipart
                        _ = request.form  # Accessing form to trigger parsing
                        body_repr = "multipart/form-data"
                    except Exception:
                        # If parsing multipart fails, respond with 415
                        response = make_response(jsonify({
                            "status": False,
                            "message": "Invalid multipart/form-data body",
                            "data": None
                        }), 415)
                        response = secure_headers(response)
                        return response
                else:
                    # If Content-Type is neither JSON nor multipart/form-data, respond with 415
                    response = make_response(jsonify({
                        "status": False,
                        "message": "Unsupported Media Type. Only application/json and multipart/form-data are supported.",
                        "data": None
                    }), 415)
                    response = secure_headers(response)
                    return response
            # Log the details of the POST request, including query parameters and body
            AllDashboardLogger.log(
                str(request.url),
                str(request.remote_addr),
                Message=f"Request Args: {str(request.args)} Body: {body_repr}"
            )

    authenticationRequired = DashboardConfig.GetConfig("Server", "auth_req")[1]
    d = request.headers
    if authenticationRequired:
        apiKey = d.get('wg-dashboard-apikey')
        apiKeyEnabled = DashboardConfig.GetConfig("Server", "dashboard_api_key")[1]

        # Use the security manager's constant time comparison
        def verify_api_key(provided_key: str, valid_keys: list) -> bool:
            """
            Verify API key in constant time to prevent timing attacks.
            Returns True if the key is valid, False otherwise.
            """
            return security_manager.verify_api_key(provided_key, [key.Key for key in valid_keys])

        if apiKey is not None and len(apiKey) > 0 and apiKeyEnabled:
            apiKeyExist = verify_api_key(apiKey, DashboardConfig.DashboardAPIKeys)
            
            AllDashboardLogger.log(str(request.url), str(request.remote_addr),
                               Message=f"API Key Access: {('true' if apiKeyExist else 'false')}")
            if not apiKeyExist:
                DashboardConfig.APIAccessed = False
                response = make_response(jsonify({
                    "status": False,
                    "message": "API Key does not exist",
                    "data": None
                }), 401)
                response = secure_headers(response)
                return response
            DashboardConfig.APIAccessed = True
        else:
            DashboardConfig.APIAccessed = False
            # Define allowed public endpoints
            public_endpoints = [
                '/static/',
                '/api/validateAuthentication',
                '/api/authenticate',
                '/api/getDashboardTheme',
                '/api/sharePeer/get',
                '/api/handshake',
                '/api/locale'
            ]
            
            # Check if current path is a public endpoint
            is_public = any(request.path.startswith(endpoint) for endpoint in public_endpoints)
            
            # Check for root path access
            root_paths = [
                f"{(APP_PREFIX if len(APP_PREFIX) > 0 else '')}/",
                f"{(APP_PREFIX if len(APP_PREFIX) > 0 else '')}"
            ]
            is_root = request.path in root_paths
            
            # Check if user is authenticated
            is_authenticated = "username" in session and "session_id" in session
            
            if not is_public and not is_root and not is_authenticated:
                response = make_response(jsonify({
                    "status": False,
                    "message": "Unauthorized access.",
                    "data": None
                }), 401)
                response = secure_headers(response)
                return response


@auth_blueprint.route('/handshake', methods=["GET", "OPTIONS"])
def API_Handshake():
    return ResponseObject(True)

@auth_blueprint.get('/security-check')
def API_SecurityCheck():
    """Perform security startup checks"""
    try:
        success = perform_security_startup_checks()
        if success:
            return secure_headers(ResponseObject(True, "Security checks completed successfully"))
        else:
            return secure_headers(ResponseObject(False, "Security checks failed"))
    except Exception as e:
        return secure_headers(ResponseObject(False, f"Security check error: {str(e)}"))


@auth_blueprint.get('/validateAuthentication')
def API_ValidateAuthentication():
    if not DashboardConfig.GetConfig("Server", "auth_req")[1]:
        return secure_headers(ResponseObject(True))
    
    # Check for proper session structure
    if "session_id" not in session or "username" not in session or "auth_token" not in session:
        return secure_headers(ResponseObject(False, "Invalid authentication."))
    
    # Validate session token
    token = request.cookies.get("authToken")
    if not token or not security_manager.constant_time_compare(token, session.get("auth_token", "")):
        return secure_headers(ResponseObject(False, "Invalid authentication."))
    
    # Check session timeout
    if 'last_activity' in session:
        last_activity = session['last_activity']
        if datetime.now().timestamp() - last_activity > SESSION_TIMEOUT:
            session.clear()
            return secure_headers(ResponseObject(False, "Session expired."))
    
    # Update last activity
    session['last_activity'] = datetime.now().timestamp()
    
    return secure_headers(ResponseObject(True))


@auth_blueprint.get('/requireAuthentication')
def API_RequireAuthentication():
    return ResponseObject(data=DashboardConfig.GetConfig("Server", "auth_req")[1])


def validate_ldap_filter_template(filter_template: str) -> tuple[bool, str]:
    """
    Validate LDAP search filter template to prevent injection.
    Returns (is_valid, error_message)
    """
    if not filter_template:
        return False, "Empty LDAP filter template"
    
    # Check for exactly one %s placeholder
    placeholder_count = filter_template.count('%s')
    if placeholder_count != 1:
        return False, f"LDAP filter must contain exactly one %s placeholder, found {placeholder_count}"
    
    # Check for dangerous LDAP filter characters that could be used for injection
    dangerous_chars = ['(', ')', '&', '|', '!', '=', '<', '>', '~', '*']
    
    # Split the template by %s to check both parts
    parts = filter_template.split('%s')
    for i, part in enumerate(parts):
        for char in dangerous_chars:
            if char in part:
                return False, f"Dangerous character '{char}' found in LDAP filter template part {i+1}"
    
    # Check for balanced parentheses (basic check)
    open_parens = filter_template.count('(')
    close_parens = filter_template.count(')')
    if open_parens != close_parens:
        return False, "Unbalanced parentheses in LDAP filter template"
    
    # Check for valid LDAP filter structure
    if not filter_template.strip().startswith('(') or not filter_template.strip().endswith(')'):
        return False, "LDAP filter template must be wrapped in parentheses"
    
    return True, ""

def escape_ldap_filter(value):
    """
    Escape special characters in LDAP filter to prevent injection.
    """
    if not value:
        return ""
    
    # Escape LDAP special characters
    escaped = value.replace("\\", "\\\\")  # Backslash
    escaped = escaped.replace("(", "\\28")    # Left parenthesis
    escaped = escaped.replace(")", "\\29")    # Right parenthesis
    escaped = escaped.replace("&", "\\26")    # Ampersand
    escaped = escaped.replace("|", "\\7c")    # Pipe
    escaped = escaped.replace("=", "\\3d")    # Equals
    escaped = escaped.replace("<", "\\3c")    # Less than
    escaped = escaped.replace(">", "\\3e")    # Greater than
    escaped = escaped.replace(";", "\\3b")    # Semicolon
    escaped = escaped.replace(",", "\\2c")    # Comma
    escaped = escaped.replace("+", "\\2b")    # Plus
    escaped = escaped.replace("*", "\\2a")    # Asterisk
    escaped = escaped.replace("~", "\\7e")    # Tilde
    escaped = escaped.replace("!", "\\21")    # Exclamation
    escaped = escaped.replace("#", "\\23")    # Hash
    escaped = escaped.replace("$", "\\24")    # Dollar
    escaped = escaped.replace("%", "\\25")    # Percent
    escaped = escaped.replace("^", "\\5e")    # Caret
    escaped = escaped.replace("[", "\\5b")    # Left bracket
    escaped = escaped.replace("]", "\\5d")    # Right bracket
    escaped = escaped.replace("{", "\\7b")    # Left brace
    escaped = escaped.replace("}", "\\7d")    # Right brace
    escaped = escaped.replace("`", "\\60")    # Backtick
    escaped = escaped.replace("?", "\\3f")    # Question mark
    escaped = escaped.replace("/", "\\2f")    # Forward slash
    escaped = escaped.replace("\\", "\\\\")  # Backslash (again for safety)
    
    return escaped

def authenticate_ldap(username, password):
    """
    Authenticate user against LDAP server using ldap3.
    Returns (success, user_data, error_message)
    """
    if not DashboardConfig.GetConfig("LDAP", "enabled")[1]:
        return False, None, "LDAP authentication not enabled"
    
    conn = None
    user_conn = None

    # Helper function to safely get an attribute from the entry dictionary.
    def safe_get_attr(attrs: dict, key: str, default="") -> str:
        # Get the attribute list from the dictionary; if missing, default to an empty list.
        values = attrs.get(key, [])
        if isinstance(values, list) and len(values) > 0:
            return values[0]
        return default

    try:
        ldap_server = DashboardConfig.GetConfig("LDAP", "server")[1]
        ldap_port_str = DashboardConfig.GetConfig("LDAP", "port")[1]
        use_ssl = DashboardConfig.GetConfig("LDAP", "use_ssl")[1]
        
        # Ensure that the LDAP port is an integer.
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
        
        # Validate LDAP filter template to prevent injection
        is_valid, error_msg = validate_ldap_filter_template(raw_search_filter)
        if not is_valid:
            AllDashboardLogger.log("", "", Message=f"LDAP Error: Invalid filter template - {error_msg}")
            return False, None, f"LDAP Error: Invalid filter template - {error_msg}"
        
        # Escape username to prevent LDAP injection
        escaped_username = escape_ldap_filter(username)
        search_filter = raw_search_filter % escaped_username
        
        conn.search(search_base, search_filter, search_scope=SUBTREE, attributes=['mail', 'givenName', 'sn'])
        if not conn.entries:
            return False, None, "User not found"
        
        # Retrieve the first entry and extract attributes safely.
        user_dn = conn.entries[0].entry_dn
        user_attrs = conn.entries[0].entry_attributes_as_dict
        
        if DashboardConfig.GetConfig("LDAP", "require_group")[1]:
            group_dn = DashboardConfig.GetConfig("LDAP", "group_dn")[1]
            # Escape user_dn to prevent injection
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

def generate_csrf_token():
    """Generate a CSRF token for the session"""
    if 'csrf_token' not in session:
        session['csrf_token'] = security_manager.generate_secure_token(32)
    return session['csrf_token']

def validate_csrf_token(token):
    """Validate CSRF token"""
    if 'csrf_token' not in session:
        return False
    return security_manager.constant_time_compare(token, session['csrf_token'])

def force_password_migration():
    """Force migration of plaintext passwords to hashed passwords"""
    stored_password = DashboardConfig.GetConfig("Account", "password")[1]
    
    # Check if password is still in plaintext (not starting with $2b$)
    if stored_password and not stored_password.startswith('$2b$'):
        AllDashboardLogger.log("", "", Message="WARNING: Plaintext password detected, forcing migration to hashed password")
        
        # Hash the plaintext password
        hashed_password = security_manager.hash_password(stored_password)
        
        # Update the configuration with the hashed password
        success, error = DashboardConfig.SetConfig("Account", "password", hashed_password, init=True)
        
        if success:
            AllDashboardLogger.log("", "", Message="SUCCESS: Password migrated to hashed format")
        else:
            AllDashboardLogger.log("", "", Message=f"ERROR: Failed to migrate password: {error}")
            # This is a critical security issue - we should not allow the system to run
            raise ValueError("CRITICAL: Failed to migrate plaintext password to hashed format")
    
    return True

def validate_ldap_configuration():
    """Validate LDAP configuration on startup"""
    ldap_enabled = DashboardConfig.GetConfig("LDAP", "enabled")[1]
    
    if ldap_enabled:
        # Validate LDAP filter template
        raw_search_filter = DashboardConfig.GetConfig("LDAP", "search_filter")[1]
        is_valid, error_msg = validate_ldap_filter_template(raw_search_filter)
        
        if not is_valid:
            AllDashboardLogger.log("", "", Message=f"LDAP Configuration Error: {error_msg}")
            # Reset to safe default
            safe_filter = "(sAMAccountName=%s)"
            DashboardConfig.SetConfig("LDAP", "search_filter", safe_filter, init=True)
            AllDashboardLogger.log("", "", Message=f"LDAP filter reset to safe default: {safe_filter}")
        
        # Validate other LDAP settings
        server = DashboardConfig.GetConfig("LDAP", "server")[1]
        if not server:
            AllDashboardLogger.log("", "", Message="LDAP Error: Server not configured")
        
        search_base = DashboardConfig.GetConfig("LDAP", "search_base")[1]
        if not search_base:
            AllDashboardLogger.log("", "", Message="LDAP Error: Search base not configured")
    
    return True

def perform_security_startup_checks():
    """Perform all security-related startup checks"""
    try:
        # Force password migration
        force_password_migration()
        
        # Validate LDAP configuration
        validate_ldap_configuration()
        
        AllDashboardLogger.log("", "", Message="Security startup checks completed successfully")
        return True
        
    except Exception as e:
        AllDashboardLogger.log("", "", Message=f"CRITICAL: Security startup check failed: {str(e)}")
        # In production, you might want to exit here
        # sys.exit(1)
        return False

@auth_blueprint.post('/authenticate')
@rate_limit(limit=20, window=300)  # 20 attempts per 5 minutes
@brute_force_protection(lambda: request.remote_addr)
@validate_input(required_fields=['username', 'password'])
def API_AuthenticateLogin():
    data = g.sanitized_data
    
    if not DashboardConfig.GetConfig("Server", "auth_req")[1]:
        resp = ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])
        return secure_headers(resp)

    # Validate input with stricter limits
    username = security_manager.sanitize_input(data['username'], 30)  # Reduced from 50
    password = data['password']
    
    # Additional password validation
    if not password or len(password) < 1 or len(password) > 128:
        return ResponseObject(False, "Invalid password length")
    
    if not username or len(username) < 1:
        return ResponseObject(False, "Username is required")
    
    # Validate username format (alphanumeric and common characters only)
    if not re.match(r'^[a-zA-Z0-9._-]+$', username):
        return ResponseObject(False, "Invalid username format")

    # Check if LDAP is enabled
    ldap_enabled = DashboardConfig.GetConfig("LDAP", "enabled")[1]
    
    if ldap_enabled:
        success, user_data, error = authenticate_ldap(username, password)
        if not success:
            AllDashboardLogger.log(str(request.url), str(request.remote_addr), 
                                 Message=f"LDAP Login failed: {username}")
            return ResponseObject(False, "Authentication failed")
            
        # LDAP authentication successful
        # Regenerate session to prevent session fixation
        session.clear()
        session['new_session'] = True
        
        session_id = security_manager.generate_secure_token(32)
        auth_token = security_manager.generate_secure_token(32)
        csrf_token = generate_csrf_token()
        
        session['session_id'] = session_id
        session['username'] = username  # Store actual username, not token
        session['auth_token'] = auth_token
        session['user_data'] = user_data
        session['last_activity'] = datetime.now().timestamp()
        
        resp = ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])
        resp.set_cookie("authToken", auth_token, httponly=True, secure=True, max_age=SESSION_TIMEOUT, samesite='Lax')
        resp.set_cookie("sessionId", session_id, httponly=True, secure=True, max_age=SESSION_TIMEOUT, samesite='Lax')
        session.permanent = True
        
        # Clear any failed attempts
        security_manager.clear_failed_attempts(request.remote_addr)
        
        AllDashboardLogger.log(str(request.url), str(request.remote_addr), 
                             Message=f"LDAP Login success: {username}")
        return secure_headers(resp)
        
    # Continue with existing local authentication if LDAP is not enabled
    # Force password migration on every authentication attempt
    try:
        force_password_migration()
    except ValueError as e:
        AllDashboardLogger.log(str(request.url), str(request.remote_addr), 
                             Message=f"CRITICAL SECURITY ERROR: {str(e)}")
        return ResponseObject(False, "System security error. Please contact administrator.")
    
    # Get stored password hash (should now be hashed)
    stored_password = DashboardConfig.GetConfig("Account", "password")[1]
    
    # Verify password against hash (all passwords should now be hashed)
    if not stored_password.startswith('$2b$'):
        AllDashboardLogger.log(str(request.url), str(request.remote_addr), 
                             Message="CRITICAL: Password is not in hashed format after migration")
        return ResponseObject(False, "Authentication system error. Please contact administrator.")
    
    valid = security_manager.verify_password(password, stored_password)
    
    totpEnabled = DashboardConfig.GetConfig("Account", "enable_totp")[1]
    totpValid = False
    if totpEnabled:
        totp_code = data.get('totp', '')
        if not totp_code:
            return ResponseObject(False, "TOTP code is required when TOTP is enabled")
        # Validate TOTP code format
        if not re.match(r'^[0-9]{6}$', totp_code):
            return ResponseObject(False, "Invalid TOTP code format")
        totpValid = pyotp.TOTP(DashboardConfig.GetConfig("Account", "totp_key")[1]).verify(totp_code, valid_window=1)

    # Get configured username for comparison
    configured_username = DashboardConfig.GetConfig("Account", "username")[1]
    
    if (valid
            and username == configured_username
            and ((totpEnabled and totpValid) or not totpEnabled)
    ):
        # Regenerate session to prevent session fixation
        session.clear()
        session['new_session'] = True
        
        session_id = security_manager.generate_secure_token(32)
        auth_token = security_manager.generate_secure_token(32)
        csrf_token = generate_csrf_token()
        
        session['session_id'] = session_id
        session['username'] = username  # Store actual username, not token
        session['auth_token'] = auth_token
        session['last_activity'] = datetime.now().timestamp()
        
        resp = ResponseObject(True, DashboardConfig.GetConfig("Other", "welcome_session")[1])
        resp.set_cookie("authToken", auth_token, httponly=True, secure=True, max_age=SESSION_TIMEOUT, samesite='Lax')
        resp.set_cookie("sessionId", session_id, httponly=True, secure=True, max_age=SESSION_TIMEOUT, samesite='Lax')
        session.permanent = True
        
        # Clear any failed attempts
        security_manager.clear_failed_attempts(request.remote_addr)
        
        AllDashboardLogger.log(str(request.url), str(request.remote_addr), Message=f"Login success: {username}")
        return secure_headers(resp)
    
    AllDashboardLogger.log(str(request.url), str(request.remote_addr), Message=f"Login failed: {username}")
    if totpEnabled:
        return ResponseObject(False, "Sorry, your username, password or OTP is incorrect.")
    else:
        return ResponseObject(False, "Sorry, your username or password is incorrect.")

@auth_blueprint.get('/signout')
def API_SignOut():
    # Clear session data
    session.clear()
    
    resp = ResponseObject(True, "Logged out successfully")
    resp.delete_cookie("authToken", httponly=True, secure=True, samesite='Lax')
    resp.delete_cookie("sessionId", httponly=True, secure=True, samesite='Lax')
    return secure_headers(resp)

@auth_blueprint.get('/csrf-token')
def API_GetCSRFToken():
    """Get CSRF token for forms"""
    if "username" not in session:
        return secure_headers(ResponseObject(False, "Authentication required"))
    
    csrf_token = generate_csrf_token()
    return secure_headers(ResponseObject(True, data={"csrf_token": csrf_token}))

@auth_blueprint.post('/validate-csrf')
@validate_input(required_fields=['csrf_token'])
def API_ValidateCSRF():
    """Validate CSRF token"""
    data = g.sanitized_data
    csrf_token = data.get('csrf_token', '')
    
    if not validate_csrf_token(csrf_token):
        return secure_headers(ResponseObject(False, "Invalid CSRF token"))
    
    return secure_headers(ResponseObject(True, "CSRF token is valid"))

@auth_blueprint.get('/rate-limit-status')
def API_GetRateLimitStatus():
    """Get current rate limit status for the requesting IP"""
    identifier = request.remote_addr
    status = security_manager.get_rate_limit_status(identifier)
    return secure_headers(ResponseObject(True, data=status))

@auth_blueprint.post('/reset-rate-limit')
@validate_input(required_fields=['identifier'])
def API_ResetRateLimit():
    """Reset rate limit for a specific identifier (admin function)"""
    data = g.sanitized_data
    identifier = data.get('identifier', '')
    
    # Basic authorization check (you might want to enhance this)
    if not DashboardConfig.APIAccessed:
        return secure_headers(ResponseObject(False, "Unauthorized"))
    
    success = security_manager.reset_rate_limit(identifier)
    if success:
        return secure_headers(ResponseObject(True, f"Rate limit reset for {identifier}"))
    else:
        return secure_headers(ResponseObject(False, "Failed to reset rate limit"))

@auth_blueprint.get('/distributed-rate-limit-test')
def API_TestDistributedRateLimit():
    """Test endpoint for distributed rate limiting"""
    identifier = request.remote_addr
    is_limited, info = security_manager.is_distributed_rate_limited(identifier, limit=10, window=60)
    
    return secure_headers(ResponseObject(True, data={
        'is_limited': is_limited,
        'info': info,
        'identifier': identifier
    }))

@auth_blueprint.get('/rate-limit-metrics')
def API_GetRateLimitMetrics():
    """Get rate limiting metrics and statistics"""
    if not DashboardConfig.APIAccessed:
        return secure_headers(ResponseObject(False, "Unauthorized"))
    
    from ..modules.RateLimitMetrics import rate_limit_metrics
    
    time_window = int(request.args.get('window', 3600))  # Default 1 hour
    metrics = rate_limit_metrics.get_metrics_summary(time_window)
    
    return secure_headers(ResponseObject(True, data=metrics))

@auth_blueprint.get('/rate-limit-health')
def API_GetRateLimitHealth():
    """Get rate limiting system health status"""
    from ..modules.RateLimitMetrics import rate_limit_metrics
    
    health = rate_limit_metrics.get_health_status()
    return secure_headers(ResponseObject(True, data=health))

@auth_blueprint.get('/top-limited-identifiers')
def API_GetTopLimitedIdentifiers():
    """Get top identifiers that are being rate limited"""
    if not DashboardConfig.APIAccessed:
        return secure_headers(ResponseObject(False, "Unauthorized"))
    
    from ..modules.RateLimitMetrics import rate_limit_metrics
    
    limit = int(request.args.get('limit', 10))
    top_limited = rate_limit_metrics.get_top_limited_identifiers(limit)
    
    return secure_headers(ResponseObject(True, data=top_limited))

@auth_blueprint.post('/cleanup-rate-limit-metrics')
def API_CleanupRateLimitMetrics():
    """Clean up old rate limiting metrics data"""
    if not DashboardConfig.APIAccessed:
        return secure_headers(ResponseObject(False, "Unauthorized"))
    
    from ..modules.RateLimitMetrics import rate_limit_metrics
    
    cleaned_count = rate_limit_metrics.cleanup_old_metrics()
    return secure_headers(ResponseObject(True, f"Cleaned up {cleaned_count} old metrics entries"))
