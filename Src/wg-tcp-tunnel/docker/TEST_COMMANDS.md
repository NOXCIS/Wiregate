# Docker Test Commands Reference

This document provides all Docker build and run commands for testing `wg-tcp-tunnel` with various configurations.

## Prerequisites

All commands should be run from the `wg-tcp-tunnel` directory:

```bash
cd /Users/nemo/Documents/Wiregate.org/wg-tcp-tunnel
```

## Quick Reference

| Test Type | Build Command | Run Command |
|-----------|--------------|-------------|
| **Quick TCP Test** | `docker-compose -f docker-compose.stress.yml build server-tcp client-tcp stress-tester` | `docker-compose -f docker-compose.stress.yml up server-tcp client-tcp stress-tester` |
| **Full TCP Stress Test** | `docker-compose -f docker-compose.stress.yml build server-tcp client-tcp stress-tester-full` | `docker-compose -f docker-compose.stress.yml --profile stress-full up server-tcp client-tcp stress-tester-full` |
| **Full Stress Test (TCP + WebSocket)** | `docker-compose -f docker-compose.stress.yml --profile stress-full --profile websocket build server-tcp client-tcp server-ws client-ws stress-tester-full` | `docker-compose -f docker-compose.stress.yml --profile stress-full --profile websocket up server-tcp client-tcp server-ws client-ws stress-tester-full` |
| **WebSocket Quick Test** | `docker-compose -f docker-compose.stress.yml --profile websocket build server-ws client-ws stress-tester-ws-quick` | `docker-compose -f docker-compose.stress.yml --profile websocket up server-ws client-ws stress-tester-ws-quick` |
| **WebSocket Full Test** | `docker-compose -f docker-compose.stress.yml --profile websocket build server-ws client-ws stress-tester-ws` | `docker-compose -f docker-compose.stress.yml --profile websocket up server-ws client-ws stress-tester-ws` |
| **WireGuard Quick Test (TCP)** | `docker-compose -f docker-compose.stress.yml --profile wireguard build server-wg client-wg wg-tester-quick` | `docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg client-wg wg-tester-quick` |
| **WireGuard Full Test (TCP)** | `docker-compose -f docker-compose.stress.yml --profile wireguard build server-wg client-wg wg-tester` | `docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg client-wg wg-tester` |
| **WireGuard Full Test (WebSocket)** | `docker-compose -f docker-compose.stress.yml --profile wireguard build server-wg-ws client-wg-ws wg-tester-ws` | `docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg-ws client-wg-ws wg-tester-ws` |

## TCP Transport Tests

### Quick TCP Test (30 seconds)
Fast test with basic throughput measurement.

**Build:**
```bash
docker-compose -f docker-compose.stress.yml build server-tcp client-tcp stress-tester
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml up server-tcp client-tcp stress-tester
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml up -d server-tcp client-tcp stress-tester
docker logs -f wg-tcp-tunnel-stress-tester
```

### Full TCP Stress Test Suite (35-50 minutes)
Comprehensive test suite including:
- Throughput tests
- Reconnection tests
- Concurrent connection tests
- Network conditions simulation
- Long-running stability tests

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile stress-full build server-tcp client-tcp stress-tester-full
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile stress-full up server-tcp client-tcp stress-tester-full
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile stress-full up -d server-tcp client-tcp stress-tester-full
docker logs -f wg-tcp-tunnel-stress-full
```

### Full Stress Test Suite WITH WebSocket Tests (40-60 minutes)
Run the complete test suite including both TCP and WebSocket transport tests.

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile stress-full --profile websocket build server-tcp client-tcp server-ws client-ws stress-tester-full
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile stress-full --profile websocket up server-tcp client-tcp server-ws client-ws stress-tester-full
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile stress-full --profile websocket up -d server-tcp client-tcp server-ws client-ws stress-tester-full
docker logs -f wg-tcp-tunnel-stress-full
```

**Note:** This includes all TCP tests plus WebSocket-specific tests (throughput, reconnection, network conditions, stability).

## WebSocket Transport Tests

### Quick WebSocket Test (handshakes, frames, ping/pong)
Fast WebSocket-specific functionality test.

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile websocket build server-ws client-ws stress-tester-ws-quick
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile websocket up server-ws client-ws stress-tester-ws-quick
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile websocket up -d server-ws client-ws stress-tester-ws-quick
docker logs -f wg-tcp-tunnel-stress-ws-quick
```

### Full WebSocket Stress Test
Complete WebSocket test suite.

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile websocket build server-ws client-ws stress-tester-ws
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile websocket up server-ws client-ws stress-tester-ws
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile websocket up -d server-ws client-ws stress-tester-ws
docker logs -f wg-tcp-tunnel-stress-ws
```

## WireGuard Live Tests

### Quick WireGuard Test (TCP) (~30-40 seconds)
Fast WireGuard tunnel test with raw TCP transport:
- Handshake verification
- Ping test (10 packets)
- TCP throughput (5 seconds)

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard build server-wg client-wg wg-tester-quick
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg client-wg wg-tester-quick
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard up -d server-wg client-wg wg-tester-quick
docker logs -f wg-tcp-tunnel-wg-tester-quick
```

### Full WireGuard Stress Test (TCP) (several minutes)
Complete WireGuard test suite with raw TCP transport:
- Handshake verification
- Ping connectivity tests
- Sustained ping (60 seconds)
- TCP throughput (30 seconds)
- UDP throughput (30 seconds)

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard build server-wg client-wg wg-tester
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg client-wg wg-tester
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard up -d server-wg client-wg wg-tester
docker logs -f wg-tcp-tunnel-wg-tester
```

### Full WireGuard Stress Test (WebSocket) (several minutes)
Complete WireGuard test suite with WebSocket transport:
- Handshake verification
- Ping connectivity tests
- Sustained ping (60 seconds)
- TCP throughput (30 seconds)
- UDP throughput (30 seconds)

**Build:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard build server-wg-ws client-wg-ws wg-tester-ws
```

**Run:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg-ws client-wg-ws wg-tester-ws
```

**Detached Mode:**
```bash
docker-compose -f docker-compose.stress.yml --profile wireguard up -d server-wg-ws client-wg-ws wg-tester-ws
docker logs -f wg-tcp-tunnel-wg-tester-ws
```

**Note:** WebSocket WireGuard tests use IP range `10.0.1.0/24` (server: `10.0.1.1`, client: `10.0.1.2`) to avoid conflicts with TCP WireGuard tests which use `10.0.0.0/24`.

## Build Options

### Build with No Cache
Force a complete rebuild (useful after code changes):

```bash
docker-compose -f docker-compose.stress.yml build --no-cache server-tcp client-tcp
```

### Build All Services
Build all services at once:

```bash
docker-compose -f docker-compose.stress.yml --profile all build
```

## Running Individual Test Scripts

### Manual Test Execution
You can also run tests manually inside containers:

**TCP Tests:**
```bash
# Start services
docker-compose -f docker-compose.stress.yml up -d server-tcp client-tcp

# Run individual test script
docker exec wg-tcp-tunnel-stress-full bash -c "cd /tests && bash stress-test-throughput.sh client-tcp 51822 tcp 15"
```

**WireGuard Tests:**
```bash
# Start services
docker-compose -f docker-compose.stress.yml --profile wireguard up -d server-wg client-wg

# Run manual tests
docker exec wg-tcp-tunnel-client-wg ping -c 10 10.0.0.1
docker exec wg-tcp-tunnel-client-wg iperf3 -c 10.0.0.1 -t 10
```

## Viewing Results

### Access Test Results
Test results are stored in Docker volumes. To access them:

**List volumes:**
```bash
docker volume ls | grep wg-tcp-tunnel
```

**Inspect volume:**
```bash
docker volume inspect wg-tcp-tunnel_stress-results
```

**Copy results from container:**
```bash
docker cp wg-tcp-tunnel-stress-full:/results ./local-results
```

**View results in container:**
```bash
docker exec wg-tcp-tunnel-stress-full ls -la /results
docker exec wg-tcp-tunnel-stress-full cat /results/results.json
```

## Cleanup Commands

### Stop All Services
```bash
docker-compose -f docker-compose.stress.yml --profile all down
```

### Stop Specific Profile
```bash
# Stop WireGuard tests
docker-compose -f docker-compose.stress.yml --profile wireguard down

# Stop WebSocket tests
docker-compose -f docker-compose.stress.yml --profile websocket down
```

### Remove Containers and Volumes
```bash
# Remove containers, networks, and volumes
docker-compose -f docker-compose.stress.yml --profile all down -v
```

### Remove Images
```bash
# Remove all wg-tcp-tunnel images
docker images | grep wg-tcp-tunnel | awk '{print $3}' | xargs docker rmi
```

### Complete Cleanup
```bash
# Stop everything
docker-compose -f docker-compose.stress.yml --profile all down -v

# Remove images
docker images | grep wg-tcp-tunnel | awk '{print $3}' | xargs docker rmi -f

# Prune system
docker system prune -a
```

## Common Issues and Solutions

### Port Already in Use
If you get port conflicts, stop existing containers first:
```bash
docker-compose -f docker-compose.stress.yml --profile all down
```

### Container Won't Start
Check logs for errors:
```bash
docker-compose -f docker-compose.stress.yml logs server-tcp
docker-compose -f docker-compose.stress.yml logs client-tcp
```

### Rebuild After Code Changes
Always rebuild after modifying source code:
```bash
docker-compose -f docker-compose.stress.yml build --no-cache server-tcp client-tcp
```

### WireGuard Test Fails
If WireGuard tests fail, ensure WireGuard kernel module is available:
```bash
# Check if WireGuard is available in container
docker exec wg-tcp-tunnel-server-wg modprobe wireguard
```

## Test Duration Estimates

| Test Type | Estimated Duration |
|-----------|-------------------|
| Quick TCP Test | ~30 seconds |
| Full TCP Stress Test | 35-50 minutes |
| Quick WebSocket Test | ~30 seconds |
| Full WebSocket Test | 10-15 minutes |
| Quick WireGuard Test | ~30-40 seconds |
| Full WireGuard Test | 5-10 minutes |

## Environment Variables

You can override default settings using environment variables:

```bash
# Custom UDP port
UDP_PORT=51823 docker-compose -f docker-compose.stress.yml up server-tcp client-tcp

# Custom test duration
RESULTS_DIR=/custom/path docker-compose -f docker-compose.stress.yml --profile stress-full up stress-tester-full
```

## Tips

1. **Use detached mode** (`-d`) for long-running tests to keep your terminal free
2. **Follow logs** with `docker logs -f <container-name>` to monitor progress
3. **Rebuild after code changes** to ensure you're testing the latest version
4. **Check disk space** - test results and Docker images can use significant space
5. **Use `--no-cache`** when you suspect build cache issues

## Example Workflow

```bash
# 1. Build everything
docker-compose -f docker-compose.stress.yml --profile all build

# 2. Run quick WireGuard test first
docker-compose -f docker-compose.stress.yml --profile wireguard up server-wg client-wg wg-tester-quick

# 3. If successful, run full TCP stress test
docker-compose -f docker-compose.stress.yml --profile stress-full up -d server-tcp client-tcp stress-tester-full

# 4. Monitor progress
docker logs -f wg-tcp-tunnel-stress-full

# 5. Check results when complete
docker exec wg-tcp-tunnel-stress-full ls -la /results

# 6. Cleanup
docker-compose -f docker-compose.stress.yml --profile all down
```

