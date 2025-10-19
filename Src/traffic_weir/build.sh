#!/bin/bash

# Build script for modular traffic-weir

echo "Building modular traffic-weir..."

# Clean previous builds
rm -f traffic-weir

# Build the application
go build -o traffic-weir .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "Binary: ./traffic-weir"
    echo ""
    echo "Usage examples:"
    echo "  ./traffic-weir -interface wg0 -peer <peer-key> -upload-rate 1000 -download-rate 2000"
    echo "  ./traffic-weir -interface wg0 -peer <peer-key> -remove"
    echo "  ./traffic-weir -interface wg0 -nuke"
else
    echo "❌ Build failed!"
    exit 1
fi
