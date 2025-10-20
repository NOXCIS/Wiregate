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
# 1. Security headers (outermost)
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
    logger.error(f"Internal server error: {exc}", exc_info=True)
    
    if request.url.path.startswith(f'{APP_PREFIX}/api'):
        return JSONResponse(
            status_code=500,
            content={
                "status": False,
                "message": "Internal server error",
                "data": None,
                "error": "500 Internal Server Error"
            }
        )
    
    return FileResponse(os.path.abspath("./static/app/dist/index.html"))


@fastapi_app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if request.url.path.startswith(f'{APP_PREFIX}/api'):
        error_detail = str(exc) if DASHBOARD_MODE == 'development' else "Internal Server Error"
        return JSONResponse(
            status_code=500,
            content={
                "status": False,
                "message": "An unexpected error occurred",
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

# Serve index.html for root and all non-API/non-static routes (Vue.js SPA routing)
@fastapi_app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch-all route to serve Vue.js SPA for all non-API routes"""
    # If it's an API route that doesn't exist, let the 404 handler deal with it
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # For all other routes, serve the Vue.js SPA
    return FileResponse(os.path.abspath("./static/app/dist/index.html"))

logger.info("FastAPI application initialized - Pure FastAPI mode (Flask disabled)")
