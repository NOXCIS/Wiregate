# Traffic-Weir Docker Testing

This directory contains Docker-based testing setup for the traffic-weir tool with CAKE traffic shaping support.

## Files

- `Dockerfile.traffic-weir` - Alpine Linux Docker image with traffic-weir and testing tools
- `docker-compose.traffic-weir.yml` - Docker Compose configuration for easy testing
- `Src/traffic_weir/test_traffic_weir_alpine.sh` - Main test runner script
- `alpine_test_script.sh` - Comprehensive test script that runs inside the container
- `Src/traffic_weir/traffic_weir_cake_test.go` - Go unit tests for CAKE functionality

## Quick Start

### Option 1: Using the test runner script (Recommended)

```bash
# Run all tests
./Src/traffic_weir/test_traffic_weir_alpine.sh

# Run interactive shell
./Src/traffic_weir/test_traffic_weir_alpine.sh interactive

# Clean up Docker images
./Src/traffic_weir/test_traffic_weir_alpine.sh clean
```

### Option 2: Using Docker Compose

```bash
# Build and run tests
docker-compose -f docker-compose.traffic-weir.yml up traffic-weir-test

# Run interactive container
docker-compose -f docker-compose.traffic-weir.yml run --rm traffic-weir-interactive
```

### Option 3: Using Docker directly

```bash
# Build the image
docker build -f Dockerfile.traffic-weir -t traffic-weir-alpine .

# Run tests
docker run --rm --privileged --cap-add=NET_ADMIN --cap-add=SYS_ADMIN \
    -v /proc:/host/proc:ro -v /sys:/host/sys:ro \
    traffic-weir-alpine

# Run interactive shell
docker run --rm -it --privileged --cap-add=NET_ADMIN --cap-add=SYS_ADMIN \
    -v /proc:/host/proc:ro -v /sys:/host/sys:ro \
    traffic-weir-alpine /bin/bash
```

## What's Tested

The Alpine container tests the following:

1. **System Capabilities**
   - tc command availability
   - traffic-weir binary functionality
   - Required network tools

2. **CAKE Scheduler**
   - CAKE scheduler validation
   - CAKE vs HTB/HFSC differences
   - CAKE rate limiting setup
   - CAKE rate limiting removal
   - CAKE interface nuking

3. **Cross-Scheduler Testing**
   - HTB scheduler functionality
   - HFSC scheduler functionality
   - Scheduler comparison

4. **Advanced Features**
   - IPv6 support
   - Performance characteristics
   - Error handling
   - Go unit tests

5. **Real Traffic Control**
   - Actual qdisc creation (if supported)
   - Traffic control verification
   - Cleanup operations

## Requirements

- Docker
- Docker Compose (optional)
- Linux/macOS host system

## Container Capabilities

The container runs with the following capabilities:
- `NET_ADMIN` - Required for network operations
- `SYS_ADMIN` - Required for system-level operations
- `--privileged` - Required for traffic control operations

## Troubleshooting

### Permission Issues
If you get permission errors, ensure Docker has the necessary capabilities:
```bash
sudo docker run --rm --privileged --cap-add=NET_ADMIN --cap-add=SYS_ADMIN ...
```

### tc Command Not Found
The Alpine container includes iproute2, but if you see "tc command not found", check:
1. The container is running with proper privileges
2. The host system supports the required network namespaces

### Test Failures
Some tests may fail in certain environments:
- Virtual machines may not support all traffic control features
- Some network operations require specific kernel modules
- Container networking limitations

## Expected Output

Successful test run should show:
```
==========================================
Traffic-Weir CAKE Testing in Alpine Linux
==========================================
[INFO] Checking system capabilities...
[SUCCESS] tc command is available
[SUCCESS] traffic-weir binary found
[SUCCESS] CAKE scheduler validation works
[SUCCESS] HTB scheduler works
[SUCCESS] HFSC scheduler works
[SUCCESS] CAKE and HTB produce different outputs (as expected)
[SUCCESS] CAKE removal works
[SUCCESS] CAKE nuke works
[SUCCESS] IPv6 support works
[SUCCESS] Go unit tests passed
[SUCCESS] Performance test completed in X.XXXs
[SUCCESS] Successfully created CAKE qdisc on lo interface
[SUCCESS] Cleaned up test qdisc

==========================================
Test Summary
==========================================
[SUCCESS] CAKE traffic shaping implementation tested in Alpine Linux
[SUCCESS] All major components verified:
  ✓ CAKE scheduler validation
  ✓ CAKE vs HTB/HFSC differences
  ✓ CAKE rate limiting setup
  ✓ CAKE rate limiting removal
  ✓ CAKE interface nuking
  ✓ IPv6 support
  ✓ Performance characteristics
  ✓ Go unit tests
  ✓ Actual traffic control (if supported)

[SUCCESS] CAKE traffic shaping is working correctly in Alpine Linux!
Use '-scheduler cake' with traffic-weir for modern traffic shaping.
```

## Development

To modify the tests:
1. Edit `alpine_test_script.sh` for container tests
2. Edit `Src/traffic_weir/traffic_weir_cake_test.go` for Go unit tests
3. Rebuild the Docker image: `docker build -f Dockerfile.traffic-weir -t traffic-weir-alpine .`
