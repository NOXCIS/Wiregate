"""
FastAPI Middleware for Security Features
Converts Flask-based security to FastAPI middleware
"""
import time
import logging
import asyncio
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware

from ..Config import (
    DASHBOARD_MODE, ALLOWED_ORIGINS, SECURE_SESSION, SESSION_TIMEOUT
)

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses - FastAPI version of secure_headers()"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Safari WebKit compatibility headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Safari WebKit specific headers
        #response.headers['X-WebKit-CSP'] = "default-src 'self'"
        
        if DASHBOARD_MODE == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = (
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "media-src 'self'; "
                "object-src 'none'; "
                "frame-src 'none'; "
                "manifest-src 'self'; "
                "connect-src 'self' https://raw.githubusercontent.com https://tile.openstreetmap.org; "
                "frame-ancestors 'none'; "
                "form-action 'self'"
            )
        else:
            # Development mode - more permissive CSP
            response.headers['Content-Security-Policy'] = (
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "media-src 'self'; "
                "object-src 'none'; "
                "frame-src 'none'; "
                "manifest-src 'self'; "
                "connect-src 'self' https://raw.githubusercontent.com https://tile.openstreetmap.org; "
                "frame-ancestors 'none'; "
                "form-action 'self'"
            )
        
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
        
        if self.security_manager:
            # Get identifier (client IP)
            identifier = request.client.host if request.client else "unknown"
            
            # Check distributed rate limit
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
                    # Standard secure settings
                    response.set_cookie(
                        key="session",
                        value=session_cookie_value,
                        httponly=True,
                        secure=is_secure and SECURE_SESSION and DASHBOARD_MODE == 'production',
                        samesite='lax',
                        max_age=SESSION_TIMEOUT
                    )
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
        
        return response


def configure_cors(app):
    """Configure CORS middleware for FastAPI"""
    from ..Core import APP_PREFIX
    
    if DASHBOARD_MODE == 'production' and '*' not in ALLOWED_ORIGINS:
        # Production mode with specific allowed origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["DELETE", "POST", "GET", "OPTIONS"],
            allow_headers=["Content-Type", "wg-dashboard-apikey"],
        )
    else:
        # Development mode or wildcard allowed
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ['*'] else ["*"],
            allow_credentials=False if ALLOWED_ORIGINS == ['*'] else True,
            allow_methods=["DELETE", "POST", "GET", "OPTIONS"],
            allow_headers=["Content-Type", "wg-dashboard-apikey"],
        )

