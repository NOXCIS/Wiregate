#!/bin/bash

# Test script for traffic-weir in Alpine Docker container
# This script builds and runs the Docker container with proper network capabilities

set -e

echo "=========================================="
echo "Traffic-Weir Alpine Docker Testing"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_warning "Docker Compose not found, using docker build/run instead"
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# Build the Docker image
print_status "Building Alpine Docker image for traffic-weir..."
if [ "$USE_COMPOSE" = true ]; then
    docker-compose -f docker-compose.traffic-weir.yml build traffic-weir-test
else
    docker build -f Dockerfile.traffic-weir -t traffic-weir-alpine .
fi

if [ $? -eq 0 ]; then
    print_success "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# Run the tests
print_status "Running traffic-weir tests in Alpine container..."

if [ "$USE_COMPOSE" = true ]; then
    docker-compose -f docker-compose.traffic-weir.yml up traffic-weir-test
else
    docker run --rm --privileged --cap-add=NET_ADMIN --cap-add=SYS_ADMIN \
        -v /proc:/host/proc:ro -v /sys:/host/sys:ro \
        traffic-weir-alpine ./test_traffic_weir.sh
fi

if [ $? -eq 0 ]; then
    print_success "Tests completed successfully"
else
    print_warning "Some tests may have failed (check output above)"
fi

# Optionally run interactive container
echo ""
print_status "Available commands:"
echo "  Run tests: $0"
echo "  Interactive shell: $0 interactive"
echo "  Clean up: $0 clean"

if [ "$1" = "interactive" ]; then
    print_status "Starting interactive Alpine container..."
    if [ "$USE_COMPOSE" = true ]; then
        docker-compose -f docker-compose.traffic-weir.yml run --rm traffic-weir-interactive
    else
        docker run --rm -it --privileged --cap-add=NET_ADMIN --cap-add=SYS_ADMIN \
            -v /proc:/host/proc:ro -v /sys:/host/sys:ro \
            traffic-weir-alpine /bin/bash
    fi
elif [ "$1" = "clean" ]; then
    print_status "Cleaning up Docker images and containers..."
    docker rmi traffic-weir-alpine 2>/dev/null || true
    docker-compose -f docker-compose.traffic-weir.yml down 2>/dev/null || true
    print_success "Cleanup completed"
fi

echo ""
print_success "Traffic-weir Alpine testing completed!"
