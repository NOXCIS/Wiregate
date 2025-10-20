#!/bin/bash

# Test runner script for modular traffic-weir

echo "🧪 Running traffic-weir tests..."

# Build the application first
echo "Building traffic-weir..."
./build.sh

if [ $? -ne 0 ]; then
    echo "❌ Build failed, cannot run tests"
    exit 1
fi

# Run tests
echo "Running tests..."
cd tests
go test -v

if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed!"
    exit 1
fi
