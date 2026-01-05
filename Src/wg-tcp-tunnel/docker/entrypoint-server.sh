#!/bin/bash
# wg-tcp-tunnel - Server Entrypoint Script
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Default values
TCP_PORT=${TCP_PORT:-51820}
UDP_PORT=${UDP_PORT:-51820}
VERBOSE=${VERBOSE:-0}
TEST_MODE=${TEST_MODE:-false}
WEBSOCKET=${WEBSOCKET:-false}
WIREGUARD_MODE=${WIREGUARD_MODE:-false}
WG_KEYS_DIR=${WG_KEYS_DIR:-/wg-keys}

# Build command arguments
ARGS=(
    "--src-tcp=0.0.0.0:${TCP_PORT}"
    "--dst-udp=127.0.0.1:${UDP_PORT}"
)

# Add WebSocket flag if requested
if [ "${WEBSOCKET}" = "true" ]; then
    ARGS+=("--web-socket")
fi

# Add verbose flag if requested
if [ "${VERBOSE}" -gt 0 ]; then
    ARGS+=("-v")
    if [ "${VERBOSE}" -gt 1 ]; then
        ARGS+=("-v")
    fi
    if [ "${VERBOSE}" -gt 2 ]; then
        ARGS+=("-v")
    fi
fi

# Add TCP keep-alive if specified
if [ -n "${TCP_KEEP_ALIVE}" ]; then
    ARGS+=("--tcp-keep-alive=${TCP_KEEP_ALIVE}")
fi

echo "Starting wg-tcp-tunnel server..."
echo "  TCP listen: 0.0.0.0:${TCP_PORT}"
echo "  UDP forward: 127.0.0.1:${UDP_PORT}"
if [ "${WEBSOCKET}" = "true" ]; then
    echo "  Transport: WebSocket"
else
    echo "  Transport: Raw TCP"
fi
echo "  Arguments: ${ARGS[*]}"
echo ""

# If in WireGuard mode, start WireGuard setup instead of test server
if [ "${WIREGUARD_MODE}" = "true" ]; then
    echo "WireGuard mode: Starting WireGuard server setup..."
    
    # Create WireGuard keys directory if it doesn't exist
    mkdir -p "${WG_KEYS_DIR}"
    
    # Export environment variables for WireGuard setup script
    export WG_KEYS_DIR
    export WG_LISTEN_PORT="${UDP_PORT}"
    
    # Start WireGuard setup script in background
    /wg-setup-server.sh &
    WG_SETUP_PID=$!
    echo "WireGuard setup started with PID ${WG_SETUP_PID}"
    
    # Wait a moment for WireGuard to initialize
    sleep 3
    echo ""
# If in test mode (not WireGuard), start UDP echo server in background
elif [ "${TEST_MODE}" = "true" ]; then
    echo "Test mode: Starting UDP echo server on port ${UDP_PORT}..."
    # Try Python script first, fallback to shell script
    # Use quiet mode to reduce log spam during stress tests
    if command -v python3 &> /dev/null; then
        python3 /test-udp-server.py "${UDP_PORT}" --quiet &
    else
        /test-udp-server.sh "${UDP_PORT}" &
    fi
    UDP_SERVER_PID=$!
    echo "UDP echo server started with PID ${UDP_SERVER_PID}"
    echo ""
fi

# Start wg-tcp-tunnel
exec wg-tcp-tunnel "${ARGS[@]}"

