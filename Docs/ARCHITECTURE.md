# Wiregate Architecture Documentation

This document describes the architecture of the Wiregate application, including middleware execution order, API prefix routing, async task lifecycle, database architecture, and health check endpoints.

## Table of Contents

1. [Middleware Execution Order](#middleware-execution-order)
2. [API Prefix Configuration](#api-prefix-configuration)
3. [Async Task Lifecycle](#async-task-lifecycle)
4. [Database Architecture](#database-architecture)
5. [Health Check Endpoint](#health-check-endpoint)

## Middleware Execution Order

FastAPI middleware is executed in **reverse order** of addition (last added = first executed). The middleware stack in Wiregate is configured as follows:

### Execution Flow

```
Request → CORS → Session → Rate Limit → Request Logging → Security Headers → CSRF → Bot Protection → HTTPS Redirect → Application
```

### Middleware Details

1. **CORS (Cross-Origin Resource Sharing)**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Handles cross-origin requests
   - **Execution**: First middleware (last added)
   - **Configuration**: Configured via `configure_cors()` function

2. **Session Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Manages user sessions and authentication state
   - **Execution**: Second middleware
   - **Features**: Session creation, validation, timeout handling

3. **Rate Limit Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Enforces rate limiting before authentication
   - **Execution**: Third middleware
   - **Features**: Per-identifier rate limiting, distributed rate limiting support

4. **Request Logging Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Logs all incoming requests
   - **Execution**: Fourth middleware
   - **Features**: Access logging, request/response logging

5. **Security Headers Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Adds security headers (CSP, HSTS, etc.)
   - **Execution**: Fifth middleware
   - **Features**: Content Security Policy, X-Frame-Options, etc.

6. **CSRF Protection Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Validates CSRF tokens for state-changing methods
   - **Execution**: Sixth middleware
   - **Features**: Token validation, exempt endpoints

7. **Bot Protection Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Blocks AI bots and scrapers
   - **Execution**: Seventh middleware
   - **Features**: User-Agent filtering, bot detection

8. **HTTPS Redirect Middleware**
   - **Location**: `Src/wiregate/modules/Security/fastapi_middleware.py`
   - **Purpose**: Redirects HTTP to HTTPS in production
   - **Execution**: Last middleware (first added, outermost)
   - **Features**: Production-only redirects

### Code Reference

The middleware is configured in `Src/wiregate/modules/App.py`:

```python
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
```

## API Prefix Configuration

Wiregate can serve every API route from a configurable prefix. This makes it easier to host the dashboard under sub-paths (for example `/wiregate`) or to run multiple instances behind the same domain.

### Configuration Source

- **Environment Variable**: `WGD_APP_PREFIX`
- **Default**: Empty string (`""`; routes are exposed under `/api`)
- **Definition**: Loaded in `Src/wiregate/modules/Config.py` as `wgd_app_prefix`
- **Imported As**: `APP_PREFIX` anywhere routing logic or middleware needs to know the prefix

### Runtime Usage

- In `Src/wiregate/modules/App.py`, every router is mounted under `f"{APP_PREFIX}/api"`.
- Middleware such as rate limiting, session management, and request logging check `request.url.path.startswith(f"{APP_PREFIX}/api")` to scope protections to API traffic.
- The prefix is evaluated once at startup, so updating the environment variable changes the prefix without code modifications.

### Example

```bash
export WGD_APP_PREFIX="/wiregate"
```

The above configuration exposes endpoints like `/wiregate/api/addPeers/{configName}`. Leaving the variable unset retains the historical behavior (`/api/...`).

## Async Task Lifecycle

Wiregate uses async background tasks instead of traditional threads for better performance and resource management.

### Task Startup

Tasks are created during application startup in the FastAPI lifespan event:

1. **Application Startup** (`Src/wiregate/modules/App.py::lifespan`)
   - Startup validation runs
   - Async database manager initialized
   - WireGuard configurations loaded
   - Background tasks started via `startThreads()`

2. **Task Creation** (`Src/wiregate/dashboard.py::startThreads()`)
   - Thread pools started (I/O and CPU-intensive operations)
   - Three async background tasks created:
     - `backGroundThread()` - WireGuard stats polling
     - `peerJobScheduleBackgroundThread()` - Peer job scheduling
     - `cpsAdaptationBackgroundThread()` - CPS pattern adaptation

### Task Execution

Each background task runs in an infinite loop with error handling:

1. **Task Loop Structure**
   ```python
   async def background_task():
       logger.info("Background Task Started (async)")
       await asyncio.sleep(initial_delay)
       
       while True:
           try:
               # Task work here
               await do_work()
           except asyncio.CancelledError:
               logger.info("Background Task cancelled")
               break
           except Exception as e:
               logger.error(f"Background Task error: {str(e)}")
           
           await asyncio.sleep(interval)
   ```

2. **Task Types**

   - **Task #1: WireGuard Stats Polling**
     - **Interval**: 10 seconds
     - **Purpose**: Polls WireGuard interface statistics
     - **Features**: Parallel config processing, update checks

   - **Task #2: Peer Job Scheduling**
     - **Interval**: 15 seconds
     - **Purpose**: Executes scheduled peer jobs
     - **Features**: Job execution, logging

   - **Task #3: CPS Pattern Adaptation**
     - **Interval**: 10 seconds (runs daily check)
     - **Purpose**: Periodic CPS pattern adaptation
     - **Features**: Daily adaptation runs, parallel processing

### Task Shutdown

Tasks are gracefully shut down during application shutdown:

1. **Application Shutdown** (`Src/wiregate/modules/App.py::lifespan`)
   - `stopThreads()` is called
   - All background tasks are cancelled
   - Tasks handle `asyncio.CancelledError` and exit cleanly
   - Thread pools are stopped
   - Database connections are closed

2. **Shutdown Sequence**
   ```python
   async def stopThreads():
       # Cancel async background tasks
       for task in _background_tasks:
           if not task.done():
               task.cancel()
               try:
                   await task
               except asyncio.CancelledError:
                   pass
       _background_tasks.clear()
       
       # Stop thread pools
       thread_pool.stop_pool()
       process_pool.stop_pool()
   ```

### Task Status Monitoring

Task status can be queried via the health check endpoint:

- **Endpoint**: `GET /api/health`
- **Function**: `get_background_task_status()` in `Src/wiregate/dashboard.py`
- **Returns**: Task running status, crash detection, exception information

## Database Architecture

Wiregate supports two database modes: **simple** (SQLite) and **scale** (PostgreSQL + Redis).

### Simple Mode (SQLite)

- **Manager**: `SQLiteDatabaseManager` in `Src/wiregate/modules/DataBase/DataBaseManager.py`
- **Technology**: `aiosqlite` (async SQLite)
- **Thread Safety**: All operations are async, ensuring thread-safe access
- **Connection**: Single async connection per manager instance
- **Initialization**: Connection initialized asynchronously via `_init_sqlite()`

**Key Features:**
- All database methods are async (`async def`)
- Automatic connection initialization on first use
- Thread-safe through async/await patterns
- No Redis caching (simple mode)

### Scale Mode (PostgreSQL + Redis)

- **Manager**: `DatabaseManager` in `Src/wiregate/modules/DataBase/DataBaseManager.py`
- **Technology**: `psycopg2` (PostgreSQL), `redis` (caching)
- **Connection**: PostgreSQL connection pool, Redis connection
- **Caching**: Redis cache layer with TTL

**Key Features:**
- PostgreSQL for persistent storage
- Redis for high-performance caching
- Cache invalidation on updates
- Connection pooling support

### Async Database Manager

For async operations, use `AsyncDataBaseManager`:

- **Location**: `Src/wiregate/modules/DataBase/AsyncDataBaseManager.py`
- **Simple Mode**: `AsyncSQLiteDatabaseManager` (uses `aiosqlite`)
- **Scale Mode**: `AsyncDatabaseManager` (uses `asyncpg` and `aioredis`)
- **Usage**: All async database operations should use this manager

### Database Thread Safety

**SQLite (Simple Mode):**
- Uses `aiosqlite` for async operations
- All methods are async, ensuring thread-safe access
- No `check_same_thread=False` needed (async handles concurrency)
- Connection initialized asynchronously

**PostgreSQL (Scale Mode):**
- Uses connection pooling
- Thread-safe through connection management
- Redis operations are thread-safe

### Migration Between Modes

- Automatic migration from SQLite to PostgreSQL when switching to scale mode
- Migration tracked in database to prevent duplicate migrations
- Backup of original SQLite files created

## Health Check Endpoint

The health check endpoint provides system status for Docker and monitoring tools.

### Endpoint Details

- **URL**: `GET /api/health`
- **Authentication**: None (public endpoint)
- **Response Codes**:
  - `200 OK`: Healthy or degraded
  - `503 Service Unavailable`: Unhealthy

### Health Checks Performed

1. **Database Connectivity**
   - SQLite: Executes `SELECT 1` query
   - PostgreSQL: Executes `SELECT 1` query
   - Response time included in response

2. **Redis Connectivity** (scale mode only)
   - Pings Redis server
   - Response time included in response
   - Returns "not_applicable" in simple mode

3. **Background Tasks Status**
   - Checks all 3 background tasks
   - Verifies tasks are running and not crashed
   - Includes task names and status

### Response Format

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "uptime_seconds": 12345.67,
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 2.5,
      "message": "SQLite database is accessible"
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1.2,
      "message": "Redis is accessible"
    },
    "background_tasks": {
      "status": "healthy",
      "response_time_ms": 0.1,
      "message": "All background tasks are running",
      "tasks": {
        "background_task_1": {
          "name": "WireGuard Stats Polling",
          "running": true,
          "crashed": false
        }
      }
    }
  },
  "timestamp": "2025-01-XX..."
}
```

### Usage

**Docker Health Check:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:10086/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

**Monitoring Tools:**
- Prometheus: Can scrape metrics from health endpoint
- Kubernetes: Use as liveness/readiness probe
- Load Balancers: Use for health checks

## Troubleshooting

### Middleware Issues

- **CORS errors**: Check `ALLOWED_ORIGINS` configuration
- **CSRF failures**: Verify CSRF token is included in requests
- **Rate limiting**: Check rate limit configuration and Redis (if scale mode)

### Task Issues

- **Task not running**: Check logs for exceptions
- **Task crashes**: Review exception details in health check endpoint
- **High CPU usage**: Check task execution times in metrics endpoint

### Database Issues

- **Connection errors**: Verify database configuration and network connectivity
- **SQLite errors**: Check file permissions and disk space
- **PostgreSQL errors**: Verify credentials and connection settings

### Health Check Issues

- **503 responses**: Check individual check statuses in response
- **Slow responses**: Review response times for each check
- **Missing checks**: Verify all services are running

## References

- FastAPI Middleware: https://fastapi.tiangolo.com/advanced/middleware/
- Async SQLite: https://aiosqlite.omnilib.dev/
- Async PostgreSQL: https://magicstack.github.io/asyncpg/
- Redis Python: https://redis-py.readthedocs.io/

