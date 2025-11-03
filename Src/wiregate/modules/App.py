"""
FastAPI Application for Wiregate
Main FastAPI app with lifespan events for background threads
"""
import logging
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

logger = logging.getLogger(__name__)

# Import only what we need for background threads (no Flask app needed)
from ..dashboard import startThreads, stopThreads

# Import security components
from .Security import (
    security_manager,
    HTTPSRedirectMiddleware,
    BotProtectionMiddleware,
    CSRFProtectionMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SessionMiddleware,
    configure_cors
)

# Import core modules
from .Core import APP_PREFIX, InitWireguardConfigurationsList, InitRateLimits
from .Config import DASHBOARD_MODE
from .DataBase import check_and_migrate_sqlite_databases


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager
    Handles startup and shutdown events for background threads
    """
    logger.info("FastAPI application starting up...")
    
    try:
        # Initialize async database manager
        from .DataBase.AsyncDataBaseManager import init_async_db
        await init_async_db()
        logger.info("✓ Async database manager initialized")
        
        # Database migration check (only in scale mode)
        from .Config import DASHBOARD_TYPE
        if DASHBOARD_TYPE.lower() == 'scale':
            logger.info("Checking for SQLite databases to migrate...")
            if check_and_migrate_sqlite_databases():
                logger.info("✓ SQLite databases migrated to PostgreSQL + Redis")
            else:
                logger.info("✓ No SQLite databases found to migrate")
        else:
            logger.info(f"✓ Using SQLite database (simple mode: DASHBOARD_TYPE={DASHBOARD_TYPE})")
        
        # Initialize WireGuard configurations
        InitWireguardConfigurationsList(startup=True)
        await InitRateLimits()
        
        # Start background threads
        startThreads()
        logger.info("✓ Background threads started")
        
        yield  # Application is running
        
    finally:
        # Shutdown: stop async tasks and thread pools
        logger.info("FastAPI application shutting down...")
        try:
            await stopThreads()
            logger.info("✓ Background tasks and thread pools stopped")
        except Exception as e:
            logger.error(f"Error stopping background tasks: {e}")
        
        # Close async database connections
        try:
            from .DataBase.AsyncDataBaseManager import get_async_db_manager
            async_db = await get_async_db_manager()
            if hasattr(async_db, 'close_connections'):
                await async_db.close_connections()
            logger.info("✓ Async database connections closed")
        except Exception as e:
            logger.error(f"Error closing async database connections: {e}")


# Create FastAPI application
fastapi_app = FastAPI(
    title="Wiregate Dashboard API",
    description="WireGuard VPN Management Dashboard with FastAPI",
    version="2.5.1",
    lifespan=lifespan,
    docs_url="/api/docs" if DASHBOARD_MODE == 'development' else None,
    redoc_url="/api/redoc" if DASHBOARD_MODE == 'development' else None,
    openapi_url="/api/openapi.json" if DASHBOARD_MODE == 'development' else None
)

# Generate secret key for session middleware
SESSION_SECRET_KEY = secrets.token_urlsafe(64)

# Add middleware in reverse order (last added = first executed)
# 0. HTTPS redirect (first - redirects HTTP to HTTPS in production)
fastapi_app.add_middleware(HTTPSRedirectMiddleware)
# 1. Bot protection (block AI bots and scrapers)
fastapi_app.add_middleware(BotProtectionMiddleware)
# 2. CSRF protection (validates CSRF tokens for state-changing methods)
fastapi_app.add_middleware(CSRFProtectionMiddleware)
# 3. Security headers (outermost)
fastapi_app.add_middleware(SecurityHeadersMiddleware)

# 2. Request logging
fastapi_app.add_middleware(RequestLoggingMiddleware)

# 3. Rate limiting (before authentication)
fastapi_app.add_middleware(RateLimitMiddleware, security_manager=security_manager)

# 4. Session management
fastapi_app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# 5. CORS (must be last middleware added = first executed)
configure_cors(fastapi_app)


# Exception handlers
@fastapi_app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors - serve Vue.js SPA for non-API routes"""
    if request.url.path.startswith(f'{APP_PREFIX}/api'):
        return JSONResponse(
            status_code=404,
            content={
                "status": False,
                "message": "API endpoint not found",
                "data": None,
                "error": "404 Not Found"
            }
        )
    
    # For non-API requests, serve the frontend (let Vue router handle 404)
    return FileResponse(os.path.abspath("./static/app/dist/index.html"))


@fastapi_app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    # Log detailed error server-side only
    logger.error(f"Internal server error: {exc}", exc_info=True)
    
    if request.url.path.startswith(f'{APP_PREFIX}/api'):
        # Production: generic error message, no path disclosure
        error_message = "Internal server error"
        error_detail = "500 Internal Server Error"
        
        # Development: include error details for debugging
        if DASHBOARD_MODE == 'development':
            error_detail = str(exc)
        
        return JSONResponse(
            status_code=500,
            content={
                "status": False,
                "message": error_message,
                "data": None,
                "error": error_detail
            }
        )
    
    return FileResponse(os.path.abspath("./static/app/dist/index.html"))


@fastapi_app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    # Log detailed error server-side only (includes full traceback)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if request.url.path.startswith(f'{APP_PREFIX}/api'):
        # Production: generic error, no path or stack trace disclosure
        error_message = "An unexpected error occurred"
        error_detail = "Internal Server Error"
        
        # Development: include error details for debugging
        if DASHBOARD_MODE == 'development':
            error_detail = str(exc)
            # In development, also log the traceback
            import traceback
            logger.debug(f"Exception traceback:\n{traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={
                "status": False,
                "message": error_message,
                "data": None,
                "error": error_detail
            }
        )
    
    return FileResponse(os.path.abspath("./static/app/dist/index.html"))


# Health check endpoint
@fastapi_app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {"status": "ok", "message": "Wiregate is running"}


# Import and register FastAPI routers as they are created
from ..routes.locale_api import router as locale_router
fastapi_app.include_router(locale_router, prefix=f"{APP_PREFIX}/api", tags=["locale"])

from ..routes.data_charts_api import router as data_charts_router
fastapi_app.include_router(data_charts_router, prefix=f"{APP_PREFIX}/api", tags=["data_charts"])

from ..routes.utils_api import router as utils_router
fastapi_app.include_router(utils_router, prefix=f"{APP_PREFIX}/api", tags=["utils"])

from ..routes.peer_jobs_api import router as peer_jobs_router
fastapi_app.include_router(peer_jobs_router, prefix=f"{APP_PREFIX}/api", tags=["peer_jobs"])

from ..routes.traffic_weir_api import router as traffic_weir_router
fastapi_app.include_router(traffic_weir_router, prefix=f"{APP_PREFIX}/api", tags=["traffic_weir"])

from ..routes.email_api import router as email_router
fastapi_app.include_router(email_router, prefix=f"{APP_PREFIX}/api", tags=["email"])

from ..routes.ldap_auth_api import router as ldap_auth_router
fastapi_app.include_router(ldap_auth_router, prefix=f"{APP_PREFIX}/api", tags=["ldap_auth"])

from ..routes.database_api import router as database_router
fastapi_app.include_router(database_router, prefix=f"{APP_PREFIX}/api", tags=["database"])

from ..routes.tor_api import router as tor_router
fastapi_app.include_router(tor_router, prefix=f"{APP_PREFIX}/api", tags=["tor"])

from ..routes.snapshot_api import router as snapshot_router
fastapi_app.include_router(snapshot_router, prefix=f"{APP_PREFIX}/api", tags=["snapshot"])

from ..routes.auth_api import router as auth_router
fastapi_app.include_router(auth_router, prefix=f"{APP_PREFIX}/api", tags=["auth"])

from ..routes.core_api import router as main_api_router
fastapi_app.include_router(main_api_router, prefix=f"{APP_PREFIX}/api", tags=["main"])

# All Flask blueprints have been migrated to FastAPI routers!
logger.info("All FastAPI routers registered successfully")

# Mount static files FIRST (before catch-all)
try:
    fastapi_app.mount(
        "/static",
        StaticFiles(directory="./static"),
        name="static"
    )
    logger.info("Static files mounted at /static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Serve robots.txt at root level
@fastapi_app.get("/robots.txt")
async def robots_txt():
    """Serve robots.txt file"""
    robots_path = os.path.abspath("./static/app/public/robots.txt")
    if os.path.exists(robots_path):
        return FileResponse(robots_path, media_type="text/plain")
    # Return default robots.txt if file doesn't exist
    from fastapi.responses import Response as FastAPIResponse
    return FastAPIResponse(
        content="User-agent: *\nDisallow: /",
        media_type="text/plain"
    )

# Serve index.html for root and all non-API/non-static routes (Vue.js SPA routing)
@fastapi_app.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str):
    """Catch-all route to serve Vue.js SPA for all non-API routes"""
    # If it's an API route that doesn't exist, let the 404 handler deal with it
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # Get CSP nonce from request state (set by SecurityHeadersMiddleware)
    csp_nonce = getattr(request.state, 'csp_nonce', None)
    
    # Read the HTML file
    html_path = os.path.abspath("./static/app/dist/index.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # If we have a nonce, inject it into script tags for strict-dynamic support
        # Also extract SRI hashes from script tags for CSP hash-based fallback
        script_hashes = []
        if csp_nonce:
            import re
            # Add nonce to all script tags that don't already have one
            # Also extract integrity hashes for CSP hash-based allowlist (backup method)
            def add_nonce(match):
                script_tag = match.group(0)
                # Extract integrity hash if present (from SRI plugin)
                integrity_match = re.search(r'integrity=["\']([^"\']+)["\']', script_tag)
                if integrity_match:
                    hash_value = integrity_match.group(1)
                    # CSP uses 'sha256-', 'sha384-', or 'sha512-' format
                    # SRI plugin uses 'sha384-' - extract just the hash part
                    if hash_value.startswith('sha384-'):
                        script_hashes.append(f"'{hash_value}'")
                
                # Skip if nonce already present
                if 'nonce=' in script_tag:
                    return script_tag
                # Insert nonce attribute before closing >
                # Find the position of the closing > or />
                if script_tag.rstrip().endswith('/>'):
                    # Self-closing tag
                    return script_tag.rstrip()[:-2] + f' nonce="{csp_nonce}" />'
                else:
                    # Regular closing tag
                    # Insert nonce before the final >
                    return script_tag[:-1] + f' nonce="{csp_nonce}">'
            
            # Match all script tags (including type="module", inline scripts, etc.)
            # This pattern matches <script followed by any attributes and >
            html_content = re.sub(r'<script[^>]*>', add_nonce, html_content)
            
            # Store hashes in request state for CSP header generation
            if script_hashes:
                request.state.script_hashes = script_hashes
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
    
    # Fallback to FileResponse if HTML file doesn't exist
    return FileResponse(html_path)

logger.info("FastAPI application initialized - Pure FastAPI mode (Flask disabled)")
