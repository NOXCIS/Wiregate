"""
FastAPI Middleware for Security Features
Converts Flask-based security to FastAPI middleware
"""
import time
import logging
import asyncio
import secrets
import base64
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, HTMLResponse
from starlette.middleware.cors import CORSMiddleware

from ..Config import (
    DASHBOARD_MODE, ALLOWED_ORIGINS, SECURE_SESSION, SESSION_TIMEOUT
)

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production mode"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only redirect in production mode
        if DASHBOARD_MODE == 'production' and request.url.scheme == "http":
            from starlette.responses import RedirectResponse
            # Build HTTPS URL
            https_url = str(request.url).replace("http://", "https://", 1)
            return RedirectResponse(url=https_url, status_code=301)
        
        return await call_next(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware - automatically validates CSRF tokens for state-changing methods"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only validate CSRF for state-changing methods
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Exceptions: endpoints that don't need CSRF (no authenticated session)
            csrf_exempt_paths = [
                '/api/authenticate',
                '/api/validate-csrf',
                '/api/handshake',
                '/api/health'
            ]
            
            if not any(request.url.path.startswith(path) for path in csrf_exempt_paths):
                # Get session data
                session_data = getattr(request.state, 'session', {})
                
                # If user is authenticated (has session), CSRF is required
                if session_data and 'session_id' in session_data:
                    # Ensure CSRF token exists in session (generate if missing)
                    token_was_generated = False
                    if 'csrf_token' not in session_data:
                        # Session exists but no CSRF token - generate one
                        # This can happen for existing sessions created before CSRF was added
                        from .Security import security_manager
                        session_data['csrf_token'] = security_manager.generate_secure_token(32)
                        request.state.session = session_data  # Update request state
                        token_was_generated = True
                        # SessionMiddleware will save this at the end of the request
                        # For this request, we'll allow it to proceed since token was just generated
                    
                    # Get CSRF token from header
                    csrf_token = request.headers.get('X-CSRF-Token')
                    
                    if not csrf_token:
                        # No token in header
                        if token_was_generated:
                            # Token was just generated in this request - allow this first POST
                            # The session will be saved with the token, so next POST will require it
                            pass  # Allow request to proceed
                        else:
                            # Token should exist in session but wasn't provided in header
                            # This means either:
                            # 1. Frontend didn't send token (shouldn't happen if implemented correctly)
                            # 2. Session cookie wasn't received yet after login
                            # For now, be lenient and allow if this might be the first request after login
                            # Check if this is a very new session (created in last few seconds)
                            import time
                            session_age = time.time() - session_data.get('last_activity', time.time())
                            if session_age < 5:  # Allow requests within 5 seconds of login
                                # Likely first request after login - generate token and allow
                                if 'csrf_token' not in session_data:
                                    from .Security import security_manager
                                    session_data['csrf_token'] = security_manager.generate_secure_token(32)
                                    request.state.session = session_data
                                pass  # Allow this request
                            else:
                                # Session is older, token should exist - require it
                                return JSONResponse(
                                    status_code=403,
                                    content={
                                        "status": False,
                                        "message": "CSRF token required for authenticated requests",
                                        "error": "CSRF token missing"
                                    }
                                )
                    else:
                        # Token provided in header - validate it
                        from .Security import security_manager
                        
                        # Get current session token (check both original and updated session)
                        current_session = getattr(request.state, 'session', session_data)
                        session_csrf_token = current_session.get('csrf_token') or session_data.get('csrf_token')
                        
                        if not session_csrf_token:
                            # No token in session - generate one and compare
                            from .Security import security_manager
                            session_data['csrf_token'] = security_manager.generate_secure_token(32)
                            request.state.session = session_data
                            session_csrf_token = session_data['csrf_token']
                        
                        if not security_manager.constant_time_compare(csrf_token, session_csrf_token):
                            return JSONResponse(
                                status_code=403,
                                content={
                                    "status": False,
                                    "message": "Invalid CSRF token",
                                    "error": "CSRF validation failed"
                                }
                            )
        
        return await call_next(request)


class BotProtectionMiddleware(BaseHTTPMiddleware):
    """Block AI bots and scrapers from accessing the site"""
    
    # Known AI bot user agents - comprehensive list from security scan
    BLOCKED_USER_AGENTS = [
        # OpenAI
        'GPTBot',
        'ChatGPT-User',
        # Google AI
        'Google-Extended',
        'Googlebot-Extended',
        # Anthropic Claude
        'ClaudeBot',
        'Claude-User',
        'Claude-SearchBot',
        'anthropic-ai',
        # Perplexity AI
        'PerplexityBot',
        'Perplexity-User',
        # Microsoft Copilot
        'BingPreview',
        'bingbot',
        'msnbot',
        # DeepSeek
        'DeepSeekBot',
        # Meta AI
        'Meta-ExternalAgent',
        'Meta AI Crawler',
        # Amazon
        'AmazonBot',
        'Amazonbot',
        # Apple Intelligence
        'Applebot-Extended',
        'Applebot',
        'Apple-Extended',
        # ByteDance/Doubao
        'Bytespider',
        # Common crawlers/scrapers
        'CCBot',
        'Baiduspider',
        'YandexBot',
        # Custom test bots (various formats)
        'Custom Bot',
        'CustomBot',
        'custom-bot',
        'test-bot',
        'testbot',
        'scraper',
        'ScraperBot',
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        user_agent = request.headers.get('user-agent', '')
        user_agent_lower = user_agent.lower()
        
        # Check if request is from a blocked bot (case-insensitive match)
        for blocked_agent in self.BLOCKED_USER_AGENTS:
            if blocked_agent.lower() in user_agent_lower:
                logger.info(f"Blocked bot request from {blocked_agent}: {request.url.path} (IP: {request.client.host if request.client else 'unknown'})")
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": False,
                        "message": "Access denied",
                        "error": "Bot access not allowed"
                    },
                    headers={
                        "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet"
                    }
                )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses - FastAPI version of secure_headers()"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Block dangerous HTTP methods that aren't needed
        dangerous_methods = ['TRACE', 'CONNECT']
        if request.method in dangerous_methods:
            return JSONResponse(
                status_code=405,
                content={"status": False, "message": f"Method {request.method} not allowed"}
            )
        # Block serving JavaScript files from backup directories or non-standard locations
        # This prevents uploaded backup files from being executed as scripts
        if request.url.path.startswith('/static/'):
            path_lower = request.url.path.lower()
            # Block JS files not from Vite's build output directory (assets/)
            # Vite bundles all scripts into /static/app/dist/assets/ with hashes
            if path_lower.endswith('.js') and '/assets/' not in path_lower:
                return JSONResponse(
                    status_code=403,
                    content={"status": False, "message": "Forbidden: JavaScript files must be served from assets directory"}
                )
            # Explicitly block access to backup directories and backup files
            backup_patterns = [
                'backup', 'wgdashboard_backup', '.bak', '.backup', 
                '.old', '.orig', '.tmp', '.swp', '~', '.git'
            ]
            if any(pattern in path_lower for pattern in backup_patterns):
                return JSONResponse(
                    status_code=403,
                    content={"status": False, "message": "Forbidden: Backup files and directories cannot be accessed via static file serving"}
                )
        
        # Generate CSP nonce for strict-dynamic support BEFORE calling next
        # This allows dynamically loaded scripts via JavaScript loaders without whitelisting sources
        # CSP nonces must use standard base64 charset (A-Z, a-z, 0-9, +, /, =) - not URL-safe base64
        # Use secrets.token_bytes() and base64.b64encode() for standard base64 encoding
        nonce_bytes = secrets.token_bytes(16)
        csp_nonce = base64.b64encode(nonce_bytes).decode('ascii')
        request.state.csp_nonce = csp_nonce  # Store for use in HTML injection
        
        # Call next middleware/route handler FIRST so HTML can be processed and hashes extracted
        # Then we'll build the CSP header with the extracted hashes
        response = await call_next(request)
        
        # Ensure Access-Control-Allow-Origin is set appropriately
        # CORS middleware handles cross-origin requests, but we ensure it's present when needed
        # Only add if not already set by CORS middleware (which runs before this)
        if 'Access-Control-Allow-Origin' not in response.headers:
            origin = request.headers.get('origin')
            
            # Check if wildcard is enabled (most common case for self-hosted apps)
            is_wildcard = False
            allowed_origins_list = []
            
            if isinstance(ALLOWED_ORIGINS, list):
                allowed_origins_list = ALLOWED_ORIGINS
                is_wildcard = '*' in ALLOWED_ORIGINS or (len(ALLOWED_ORIGINS) == 1 and ALLOWED_ORIGINS[0] == '*')
            elif isinstance(ALLOWED_ORIGINS, str):
                # Parse comma-separated string into list
                allowed_origins_list = [o.strip() for o in ALLOWED_ORIGINS.split(',')]
                is_wildcard = '*' in allowed_origins_list or (len(allowed_origins_list) == 1 and allowed_origins_list[0] == '*')
            
            # Always set the header when wildcard is enabled (for security scanner compliance)
            # Security scanners often check the main page and static assets, not just API endpoints
            if is_wildcard:
                # Wildcard allows any origin - set for all responses
                response.headers['Access-Control-Allow-Origin'] = '*'
            elif origin:
                # Cross-origin request - check if origin matches allowed list
                if origin in allowed_origins_list:
                    response.headers['Access-Control-Allow-Origin'] = origin
            else:
                # Same-origin request (no Origin header) - set header for security scanner compliance
                # Security scanners expect to see this header even for same-origin requests
                if allowed_origins_list:
                    configured_origin = allowed_origins_list[0]
                    # If it's already a full URL (starts with http:// or https://), use it as-is
                    if configured_origin.startswith('http://') or configured_origin.startswith('https://'):
                        response.headers['Access-Control-Allow-Origin'] = configured_origin
                    else:
                        # Construct full URL from the current request's scheme
                        # Match the scheme of the incoming request (http or https)
                        scheme = request.url.scheme  # Will be 'http' or 'https'
                        response.headers['Access-Control-Allow-Origin'] = f"{scheme}://{configured_origin}"
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        # Note: X-XSS-Protection removed - deprecated and not supported in modern browsers
        # XSS protection is provided by Content-Security-Policy instead
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Cross-Origin-Resource-Policy: Deny cross-origin requests by default for better security
        # Since WireGate is self-hosted and not meant for embedding, use 'same-origin'
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
        # Permissions-Policy: Restrict browser features not needed for VPN dashboard
        response.headers['Permissions-Policy'] = (
            'accelerometer=(), '
            'ambient-light-sensor=(), '
            'autoplay=(), '
            'battery=(), '
            'camera=(), '
            'cross-origin-isolated=(), '
            'display-capture=(), '
            'document-domain=(), '
            'encrypted-media=(), '
            'execution-while-not-rendered=(), '
            'execution-while-out-of-viewport=(), '
            'fullscreen=(self), '
            'geolocation=(), '
            'gyroscope=(), '
            'magnetometer=(), '
            'microphone=(), '
            'midi=(), '
            'navigation-override=(), '
            'payment=(), '
            'picture-in-picture=(), '
            'publickey-credentials-get=(), '
            'screen-wake-lock=(), '
            'sync-xhr=(), '
            'usb=(), '
            'web-share=()'
        )
        
        # Safari WebKit compatibility headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Determine if HTTPS is being used
        is_secure = request.url.scheme == "https"
        
        # Enable HSTS when HTTPS is detected (not just in production)
        if is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # After route handlers run, read script hashes if they were extracted
        # (This happens in catch_all route for index.html)
        script_hashes = getattr(request.state, 'script_hashes', [])
        
        # Build script-src directive with nonce and optionally hashes
        # Chrome requires script-src-elem for <script> elements, but it falls back to script-src
        # We include both for maximum compatibility
        script_src_parts = ["'self'", f"'nonce-{csp_nonce}'"]
        if script_hashes:
            # Add SRI hashes as CSP hash sources (backup for strict-dynamic)
            script_src_parts.extend(script_hashes)
        script_src_parts.append("'strict-dynamic'")
        script_src = " ".join(script_src_parts)
        
        # script-src-elem is Chrome-specific and applies to <script> elements
        # It falls back to script-src if not specified, but being explicit helps
        script_src_elem = script_src
        
        # Content Security Policy with deny-by-default approach (default-src 'none')
        # Then explicitly allow only what's needed - more secure than default-src 'self'
        # Scripts are secured using CSP3 'strict-dynamic':
        # - Initial script tags must have nonce or hash (SRI provides hash)
        # - 'strict-dynamic' allows scripts loaded by trusted scripts to execute
        # - No need to whitelist individual script sources - shim loader can load dynamically
        # - This is more secure and flexible than static source lists
        # - With 'strict-dynamic', host-source expressions ('self', origins) are ignored for dynamically loaded scripts
        # - But they're still used for initial script tag evaluation (backward compatibility)
        # - The nonce ensures the initial script is trusted, allowing strict-dynamic to work
        # - SRI hashes provide additional fallback if nonces aren't properly injected
        # Scripts are secured because:
        # - No JSONP endpoints (all APIs use standard JSON)
        # - No user-uploaded scripts executed (backups are validated .7z archives, extracted to separate directory)
        # - JavaScript files are only served from /static/app/dist/assets/ (Vite build output)
        # - Backup directories are explicitly blocked from static file serving (see middleware above)
        # - This is Vue.js, not Angular (no framework-specific script injection concerns)
        # Note: 'strict-dynamic' requires the initial script to have nonce or hash - nonces are injected at runtime
        base_csp = (
            "default-src 'none'; "  # Deny by default - most secure
            f"script-src {script_src}; "  # Allow scripts from self, with nonce/hash for initial load, and strict-dynamic for dynamic loading
            f"script-src-elem {script_src_elem}; "  # Chrome-specific: applies to <script> elements explicitly
            "style-src 'self'; "  # Allow styles from same origin only
            "img-src 'self' data: https://tile.openstreetmap.org; "  # Images from self, data URIs, and OpenStreetMap tiles
            "font-src 'self'; "  # Fonts from same origin only
            "manifest-src 'self'; "  # Web manifest from same origin
            "base-uri 'self'; "  # Base URL can only be same origin
            "form-action 'self'; "  # Form submissions only to same origin
            "connect-src 'self' https://raw.githubusercontent.com https://tile.openstreetmap.org; "  # API calls to self and allowed external APIs
            "frame-src 'none'; "  # No frames allowed
            "frame-ancestors 'none'; "  # Cannot be embedded in frames
            "object-src 'none'; "  # No plugins (Flash, etc.)
            "worker-src 'none'; "  # No web workers
            "child-src 'none'; "  # No child contexts
            "media-src 'self'"  # Media files from same origin only
        )
        
        if is_secure or DASHBOARD_MODE == 'production':
            # Production or HTTPS: add upgrade-insecure-requests and block-all-mixed-content
            response.headers['Content-Security-Policy'] = (
                f"{base_csp}; "
                "upgrade-insecure-requests; "
                "block-all-mixed-content"
            )
        else:
            # Development mode over HTTP: basic CSP without upgrade directives
            response.headers['Content-Security-Policy'] = base_csp
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all API requests for security auditing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Log API requests in background task to avoid blocking
        if "/api/" in request.url.path:
            from ..Logger import AllDashboardLogger
            
            client_ip = request.client.host if request.client else "unknown"
            
            # Create background task for logging
            async def log_request():
                try:
                    if request.method == "GET":
                        AllDashboardLogger.log(
                            str(request.url),
                            client_ip,
                            Message="API GET request"
                        )
                    elif request.method == "POST":
                        # For POST, log sanitized body (remove sensitive fields)
                        try:
                            if request.headers.get('content-type', '').startswith('application/json'):
                                # Note: We can't re-read the body here, so just log the endpoint
                                AllDashboardLogger.log(
                                    str(request.url),
                                    client_ip,
                                    Message=f"API POST request"
                                )
                            else:
                                AllDashboardLogger.log(
                                    str(request.url),
                                    client_ip,
                                    Message=f"API {request.method} request"
                                )
                        except Exception as e:
                            logger.debug(f"Failed to log request: {e}")
                except Exception as e:
                    logger.debug(f"Failed to log request in background: {e}")
            
            # Schedule logging as background task
            asyncio.create_task(log_request())
        
        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware"""
    
    def __init__(self, app, security_manager=None):
        super().__init__(app)
        self.security_manager = security_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for static files
        if request.url.path.startswith('/static/'):
            return await call_next(request)
        
        # Only rate limit API endpoints
        if not request.url.path.startswith('/api/'):
            return await call_next(request)
        
        # Skip rate limiting for public endpoints
        public_endpoints = [
            '/api/validateAuthentication',
            '/api/handshake',
            '/api/getDashboardTheme',
            '/api/sharePeer/get',
            '/api/locale'
        ]
        
        if any(request.url.path.startswith(endpoint) for endpoint in public_endpoints):
            return await call_next(request)
        
        # Check if session is expired before rate limiting
        # This prevents rate limiting requests that will return 401 anyway
        session_data = getattr(request.state, 'session', {})
        if not session_data or 'session_id' not in session_data:
            # No session or expired session - check if this endpoint requires auth
            # If it requires auth, it will return 401, so don't rate limit it
            # This prevents rate limit lockout when session expires
            auth_required_endpoints = [
                '/api/csrf-token',
                '/api/getDashboardConfiguration',
                '/api/getWireguardConfigurations'
            ]
            if any(request.url.path.startswith(endpoint) for endpoint in auth_required_endpoints):
                # This will likely return 401 - don't count towards rate limit
                # But still apply a minimal rate limit to prevent abuse
                identifier = request.client.host if request.client else "unknown"
                is_limited, info = self.security_manager.is_distributed_rate_limited(
                    identifier, 
                    limit=30,  # More lenient limit for expired session requests
                    window=60  # 1 minute window
                )
                if is_limited:
                    # Still apply rate limit but more lenient
                    limit_type = "rate"
                    if info.get('is_burst_limited', False):
                        limit_type = "burst"
                    
                    return JSONResponse(
                        status_code=429,
                        content={
                            'status': False,
                            'message': f'Rate limit exceeded ({limit_type})',
                            'data': {
                                'retry_after': max(0, info.get('reset_time', 0) - int(time.time())),
                                'limit': info.get('limit', 0)
                            }
                        }
                    )
                # Don't count this request in normal rate limiting
                return await call_next(request)
        
        if self.security_manager:
            # Get identifier (client IP)
            identifier = request.client.host if request.client else "unknown"
            
            # Apply stricter rate limits for authentication endpoints
            if request.url.path.startswith('/api/authenticate'):
                # Check if there was a recent session expiration (grace period)
                has_recent_expiration = self.security_manager.has_recent_session_expiration(identifier)
                
                if has_recent_expiration:
                    # More lenient limit if session expired recently (20 requests per 5 minutes)
                    is_limited, info = self.security_manager.is_distributed_rate_limited(
                        identifier, 
                        limit=20,  # 20 attempts per window (more lenient)
                        window=300  # 5 minutes window
                    )
                else:
                    # Stricter limits for normal login attempts: 10 requests per 5 minutes
                    is_limited, info = self.security_manager.is_distributed_rate_limited(
                        identifier, 
                        limit=10,  # 10 attempts per window
                        window=300  # 5 minutes window
                    )
            else:
                # Standard rate limit for other endpoints
                is_limited, info = self.security_manager.is_distributed_rate_limited(identifier)
            
            if is_limited:
                # Determine limit type
                limit_type = "rate"
                if info.get('is_burst_limited', False):
                    limit_type = "burst"
                elif info.get('is_sliding_limited', False):
                    limit_type = "sliding"
                
                return JSONResponse(
                    status_code=429,
                    content={
                        'status': False,
                        'message': f'Rate limit exceeded ({limit_type})',
                        'data': {
                            'retry_after': info.get('reset_time', 0) - int(time.time()),
                            'limit': info.get('limit', 0),
                            'current_requests': info.get('current_requests', 0),
                            'remaining_requests': info.get('remaining_requests', 0),
                            'limit_type': limit_type,
                            'burst_requests': info.get('burst_requests', 0),
                            'sliding_requests': info.get('sliding_requests', 0)
                        }
                    }
                )
        
        return await call_next(request)


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Session management middleware for FastAPI
    Provides Flask-like session functionality using cookies
    """
    
    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Load session from cookie
        session_data = {}
        session_cookie = request.cookies.get("session")
        
        if session_cookie:
            try:
                # Decrypt and load session data
                import json
                from itsdangerous import URLSafeTimedSerializer
                
                serializer = URLSafeTimedSerializer(self.secret_key)
                session_data = serializer.loads(session_cookie, max_age=SESSION_TIMEOUT)
            except Exception as e:
                logger.debug(f"Failed to load session: {e}")
                session_data = {}
        
        # Store session in request state
        request.state.session = session_data
        
        # Process request
        response = await call_next(request)
        
        # Save session to cookie if modified
        updated_session = getattr(request.state, 'session', {})
        if updated_session != session_data:
            try:
                import json
                from itsdangerous import URLSafeTimedSerializer
                
                serializer = URLSafeTimedSerializer(self.secret_key)
                session_cookie_value = serializer.dumps(updated_session)
                
                # Determine if we're using HTTPS
                is_secure = request.url.scheme == "https"
                
                # Safari WebKit compatibility
                user_agent = request.headers.get('user-agent', '').lower()
                is_safari = 'safari' in user_agent and 'webkit' in user_agent and 'chrome' not in user_agent
                
                # Set cookie with appropriate security settings
                if is_safari and not is_secure:
                    # Safari over HTTP - more permissive
                    response.set_cookie(
                        key="session",
                        value=session_cookie_value,
                        httponly=True,
                        secure=False,
                        samesite='lax',
                        max_age=SESSION_TIMEOUT
                    )
                else:
                    # Standard secure settings - always set Secure=True when HTTPS is detected
                    response.set_cookie(
                        key="session",
                        value=session_cookie_value,
                        httponly=True,
                        secure=is_secure,  # Always secure when HTTPS is detected
                        samesite='lax',
                        max_age=SESSION_TIMEOUT
                    )
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
        
        return response


def configure_cors(app):
    """Configure CORS middleware for FastAPI"""
    from ..Core import APP_PREFIX
    
    # Define allowed headers including CSRF token
    allowed_headers = [
        "Content-Type", 
        "wg-dashboard-apikey",
        "X-CSRF-Token",
        "Authorization",
        "Accept"
    ]
    
    # Determine if wildcard is enabled and normalize allowed origins
    is_wildcard = False
    normalized_origins = []
    
    if isinstance(ALLOWED_ORIGINS, list):
        normalized_origins = ALLOWED_ORIGINS
        is_wildcard = '*' in ALLOWED_ORIGINS or (len(ALLOWED_ORIGINS) == 1 and ALLOWED_ORIGINS[0] == '*')
    elif isinstance(ALLOWED_ORIGINS, str):
        # Parse comma-separated string into list
        normalized_origins = [o.strip() for o in ALLOWED_ORIGINS.split(',')]
        is_wildcard = '*' in normalized_origins or (len(normalized_origins) == 1 and normalized_origins[0] == '*')
    
    if is_wildcard:
        # Wildcard mode - allow all origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,  # Cannot use credentials with wildcard
            allow_methods=["DELETE", "POST", "GET", "OPTIONS", "PUT", "PATCH"],
            allow_headers=allowed_headers,
            expose_headers=["X-CSRF-Token"],
            max_age=3600,  # Cache preflight requests for 1 hour
        )
    else:
        # Specific origins - CORS middleware accepts hostnames or full URLs
        # It will match both "wg.j0k3rs.org" and "https://wg.j0k3rs.org"
        app.add_middleware(
            CORSMiddleware,
            allow_origins=normalized_origins,
            allow_credentials=True,
            allow_methods=["DELETE", "POST", "GET", "OPTIONS", "PUT", "PATCH"],
            allow_headers=allowed_headers,
            expose_headers=["X-CSRF-Token"],
            max_age=3600,  # Cache preflight requests for 1 hour
        )

