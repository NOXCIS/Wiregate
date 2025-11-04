acid-rain-beta-v0.4:
  - Bug Fixes
  - Awg Kernel Module Support if installed on host
  - Rate Limits Fully Fuctional

acid-rain-beta-v0.4.1:
  - Fixed Healtcheck

acid-rain-beta-v0.4.2:
  - Fixed Tor Save & Reload
  - Added Tor Config Stop and Start Button
  - Added Tor Log Viewer
  - Added Tor Vanguards to Tor DNS
  - Streamlined Tor Bootstrap Logging

casper-beta:
  - DO NOT USE IN PROD IS BETA
  - Probably Broken

casper-beta-v0.0.1:
  - DO NOT USE IN PROD IS BETA
  - Probably Broken

casper-beta-v0.0.2:
  - DO NOT USE IN PROD IS BETA
  - Probably Broken

casper-beta-v0.0.3:
  - DO NOT USE IN PROD IS BETA
  - Probably Broken

casper-beta-v0.0.4:
  - DO NOT USE IN PROD IS BETA
  - Probably Broken

casper-beta-v0.1.0:
  - - DO NOT USE IN PROD IS BETA
  - Probably Broken

casper-beta-v0.1.1:
  - - DO NOT USE IN PROD IS BETA
  - Probably Broken

sol-beta-v0.2.0:
  - DO NOT USE IN PROD IS BETA
  - Swaped to Redis DB Cache Layer
  - Auto Migrates sqlite DB from previous versions or       WGDashboard.
  - Swapped to ASGI with better threading ARCH
  - API Rate limits
  - Public API reduction. Only Nessary
  - Command Execution Hardending via Restricted Shell
  - Minor Theme Changes
  - Added 404 page.


sol-beta-v2.0.0:
  - DO NOT USE IN PROD IS BETA
  - Bug Fixes
  - You need a Redis & Postgress container to run.

sol-beta-v2.1.0:
  - DO NOT USE IN PROD IS BETA
  - More Bug Fixes
  - You need a Redis & Postgress container to run.

sol-beta-v2.1.4:
  - DO NOT USE IN PROD IS BETA
  - Auth is Broken
  - K8 tested
  - More Bug Fixes
  - You need a Redis & Postgress container to run,
  - Check docker hub for more info.

sol-beta-v2.3.1:
  - DO NOT USE IN PROD IS BETA
  - Auth is Broken
  - K8 tested
  - Stripped Img down to required tools and libs only
  - 404 on the busybox
  - More Bug Fixes
  - You need a Redis & Postgress container to run,
  - Check docker hub for more info.

sol-beta-v2.3.2:
  - DO NOT USE IN PROD IS BETA
  - Auth Fixed
  - K8 tested
  - Stripped Img down to required tools and libs only
  - 404 on the busybox
  - More Bug Fixes
  - You need a Redis & Postgress container to run,
  - Check docker hub for more info.

sol-beta-v2.5.2:
  - DO NOT USE IN PROD IS BETA
  - Complete FastAPI Migration - All Flask routes migrated to FastAPI
  - Enhanced Security Infrastructure - Comprehensive security middleware stack
  - Async Database Architecture - Full async/await support with PostgreSQL + Redis
  - Thread Pool & Process Pool Optimization - Parallel processing for bulk operations
  - Bug Fixes (Traffic Shaping) (Unsafe Inline css) (Public keys)
  - Sqlite backwards Compatablitly via DASHBOARD_TYPE=scale  # simple (SQLite) or scale (PostgreSQL + Redis)

sol-beta-v2.5.3:
  - DO NOT USE IN PROD IS BETA
  - theme updates 
  - logo update
  - ui bug fixes
  - added Tor Protocol Badge
  - fixed tor proxy config generation
  - move uvicorn options to .env
  - bug fixes


flat-bridge-v0.0.1:
  - STABLE BETA (USE AT OWN RISK)
  - Dockerfile & Nuitka.Dockerfile: Auto-fetch latest Go version (removed hardcoded 1.24.x)
  - Security (CSP) - fastapi_middleware.py:
  - Added default-src, base-uri, worker-src, child-src directives
  - Added upgrade-insecure-requests & block-all-mixed-content (prod)
  - Removed redundant script-src 'self'
  - Added middleware to block JS files outside /assets/ and backup directories
  - Frontend:
  - Converted 5 Vue components to dynamic imports (defineAsyncComponent)
  - Fixed Vite code-splitting warnings, reduced initial bundle size


flat-bridge-v0.0.2:
  - Bug Fixes
  - Security hardening with CSP
  - SRI (Subresource Integrity) is a security feature that verifies external resources (scripts, stylesheets) haven't been tampered with.
  - infrastructure updates for deployment and management.

flat-bridge-v0.0.3:
  - Bug Fixes
  - Security hardening with CSP
  - SRI (Subresource Integrity) is a security feature that verifies external resources (scripts, stylesheets) haven't been tampered with.
  - infrastructure updates for deployment and management.

flat-bridge-v1.5.0:
  - AmneziaWG 1.5 Implimentation.
  - Adaptive AWG decoy packets
  - Bug Fixes
