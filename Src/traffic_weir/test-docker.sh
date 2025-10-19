#!/bin/bash

# Test Docker script for traffic-weir
# This script builds and runs the test Docker container

set -e

echo "🐳 Building traffic-weir test Docker container..."

# Build the test image
docker build -f Dockerfile.test -t traffic-weir-test .

if [ $? -eq 0 ]; then
    echo "✅ Test image built successfully!"
    echo ""
    echo "Available test commands:"
    echo "  ./test-docker.sh run          - Run comprehensive test suite"
    echo "  ./test-docker.sh go-tests     - Run only Go unit tests"
    echo "  ./test-docker.sh tc-verify    - Verify tc commands only"
    echo "  ./test-docker.sh all-tests    - Run all test suites"
    echo "  ./test-docker.sh coverage     - Generate test coverage report"
    echo "  ./test-docker.sh shell        - Open interactive shell"
    echo ""
    
    # If no arguments, run comprehensive tests
    if [ $# -eq 0 ]; then
        echo "🚀 Running comprehensive test suite..."
        docker run --rm --privileged traffic-weir-test
    else
        case "$1" in
            "run")
                echo "🚀 Running comprehensive test suite..."
                docker run --rm --privileged traffic-weir-test
                ;;
            "go-tests")
                echo "🧪 Running Go unit tests..."
                docker run --rm --privileged traffic-weir-test ./run-go-tests.sh
                ;;
            "tc-verify")
                echo "🔍 Verifying tc commands..."
                docker run --rm --privileged traffic-weir-test ./verify-tc-commands.sh
                ;;
            "all-tests")
                echo "🧪 Running all test suites..."
                docker run --rm --privileged traffic-weir-test ./run-all-tests.sh
                ;;
            "coverage")
                echo "📊 Generating test coverage report..."
                docker run --rm --privileged traffic-weir-test ./test-coverage.sh
                ;;
            "shell")
                echo "🐚 Opening interactive shell..."
                docker run --rm --privileged -it traffic-weir-test /bin/bash
                ;;
            *)
                echo "❌ Unknown command: $1"
                echo "Available commands: run, go-tests, tc-verify, all-tests, coverage, shell"
                exit 1
                ;;
        esac
    fi
else
    echo "❌ Failed to build test image!"
    exit 1
fi
