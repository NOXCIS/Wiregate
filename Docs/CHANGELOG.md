# WireGate Changelog

UNRELEASED:
  - Added CAKE (Common Applications Kept Enhanced) traffic shaping support
  - New Python traffic_control module for managing tc commands
  - CAKE setup/teardown scripts for all WireGuard zones (ADMINS, MEMBERS, GUESTS, LANP2P)
  - Added iproute2 package to Docker image for tc command support
  - Comprehensive CAKE documentation and example configurations
  - Per-zone bandwidth limits with sensible defaults (ADMINS: 1Gbit, MEMBERS: 100Mbit, GUESTS: 50Mbit, LANP2P: 100Mbit)
  - Optional CAKE feature - disabled by default, zero impact when not enabled
  - Automatic integration with existing PostUp/PostDown scripts
  - Environment variable-based configuration (CAKE_ENABLED, CAKE_BANDWIDTH_*, CAKE_OPTIONS)
  - Addresses upstream issue #77 - CAKE traffic shaper request

acid-rain-beta-v0.4:
  - Bug Fixes
  - Awg Kernel Module Support if installed on host
  - Rate Limits Fully Fuctional

## sol-beta-v2.5.2
- DO NOT USE IN PROD IS BETA
- Complete FastAPI Migration - All Flask routes migrated to FastAPI
- Enhanced Security Infrastructure - Comprehensive security middleware stack
- Async Database Architecture - Full async/await support with PostgreSQL + Redis
- Thread Pool & Process Pool Optimization - Parallel processing for bulk operations
- Bug Fixes (Traffic Shaping)
- Sqlite backwards Compatablitly via DASHBOARD_TYPE=scale  # simple (SQLite) or scale (PostgreSQL + Redis)

## sol-beta-v2.3.2
- DO NOT USE IN PROD IS BETA
- Auth Fixed
- K8 tested
- Stripped Img down to required tools and libs only
- 404 on the busybox
- More Bug Fixes
- You need a Redis & Postgress container to run,
- Check docker hub for more info.

## sol-beta-v2.3.1
- DO NOT USE IN PROD IS BETA
- Auth is Broken
- K8 tested
- Stripped Img down to required tools and libs only
- 404 on the busybox
- More Bug Fixes
- You need a Redis & Postgress container to run,
- Check docker hub for more info.

## sol-beta-v2.1.4
- DO NOT USE IN PROD IS BETA
- Auth is Broken
- K8 tested
- More Bug Fixes
- You need a Redis & Postgress container to run,
- Check docker hub for more info.

## sol-beta-v2.1.0
- DO NOT USE IN PROD IS BETA
- More Bug Fixes
- You need a Redis & Postgress container to run.

## sol-beta-v2.0.0
- DO NOT USE IN PROD IS BETA
- Bug Fixes
- You need a Redis & Postgress container to run.

## sol-beta-v0.2.0
- DO NOT USE IN PROD IS BETA
- Swaped to Redis DB Cache Layer
- Auto Migrates sqlite DB from previous versions or WGDashboard.
- Swapped to ASGI with better threading ARCH
- API Rate limits
- Public API reduction. Only Nessary
- Command Execution Hardending via Restricted Shell
- Minor Theme Changes
- Added 404 page.

## casper-beta-v0.1.1
- DO NOT USE IN PROD IS BETA
- Probably Broken

## casper-beta-v0.1.0
- DO NOT USE IN PROD IS BETA
- Probably Broken

## casper-beta-v0.0.4
- DO NOT USE IN PROD IS BETA
- Probably Broken

## casper-beta-v0.0.3
- DO NOT USE IN PROD IS BETA
- Probably Broken

## casper-beta-v0.0.2
- DO NOT USE IN PROD IS BETA
- Probably Broken

## casper-beta-v0.0.1
- DO NOT USE IN PROD IS BETA
- Probably Broken

## casper-beta
- DO NOT USE IN PROD IS BETA
- Probably Broken

## acid-rain-beta-v0.4.2
- Fixed Tor Save & Reload
- Added Tor Config Stop and Start Button
- Added Tor Log Viewer
- Added Tor Vanguards to Tor DNS
- Streamlined Tor Bootstrap Logging

## acid-rain-beta-v0.4.1
- Fixed Healtcheck

## acid-rain-beta-v0.4
- Bug Fixes
- Awg Kernel Module Support if installed on host
- Rate Limits Fully Fuctional
