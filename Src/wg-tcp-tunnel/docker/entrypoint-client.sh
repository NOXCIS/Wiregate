#!/bin/bash
# wg-tcp-tunnel - Client Entrypoint Script
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Default values
UDP_PORT=${UDP_PORT:-51822}
SERVER_HOST=${SERVER_HOST:-server}
SERVER_PORT=${SERVER_PORT:-51820}
VERBOSE=${VERBOSE:-0}
TEST_MODE=${TEST_MODE:-false}
WEBSOCKET=${WEBSOCKET:-false}
WIREGUARD_MODE=${WIREGUARD_MODE:-false}
WG_KEYS_DIR=${WG_KEYS_DIR:-/wg-keys}

# Wait for server to be ready and resolve hostname to IP
echo "Waiting for server ${SERVER_HOST}:${SERVER_PORT} to be ready..."
until nc -z "${SERVER_HOST}" "${SERVER_PORT}" 2>/dev/null; do
    echo "  Server not ready, waiting..."
    sleep 1
done
echo "Server is ready!"

# Resolve hostname to IP address (wg-tcp-tunnel requires IP, not hostname)
echo "Resolving ${SERVER_HOST} to IP address..."
SERVER_IP=$(getent hosts "${SERVER_HOST}" | awk '{print $1}' | head -n1)
if [ -z "${SERVER_IP}" ]; then
    echo "Error: Failed to resolve ${SERVER_HOST} to IP address"
    exit 1
fi
echo "Resolved ${SERVER_HOST} to ${SERVER_IP}"
echo ""

# Build command arguments
ARGS=(
    "--src-udp=0.0.0.0:${UDP_PORT}"
    "--dst-tcp=${SERVER_IP}:${SERVER_PORT}"
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

# Add max connections if specified (environment variable is also supported directly)
if [ -n "${MAX_CONNECTIONS}" ]; then
    ARGS+=("--max-connections=${MAX_CONNECTIONS}")
fi

echo "Starting wg-tcp-tunnel client..."
echo "  UDP listen: 0.0.0.0:${UDP_PORT}"
echo "  TCP forward: ${SERVER_IP}:${SERVER_PORT} (${SERVER_HOST})"
if [ "${WEBSOCKET}" = "true" ]; then
    echo "  Transport: WebSocket"
else
    echo "  Transport: Raw TCP"
fi
echo "  Arguments: ${ARGS[*]}"
echo ""

# If in WireGuard mode, start WireGuard setup
if [ "${WIREGUARD_MODE}" = "true" ]; then
    echo "WireGuard mode: Starting WireGuard client setup..."
    
    # Create WireGuard keys directory if it doesn't exist
    mkdir -p "${WG_KEYS_DIR}"
    
    # Export environment variables for WireGuard setup script
    export WG_KEYS_DIR
    export WG_ENDPOINT="127.0.0.1:${UDP_PORT}"
    
    # Wait for tunnel to be ready before starting WireGuard
    echo "Waiting 3 seconds for tunnel to establish..."
    sleep 3
    
    # Start WireGuard setup script in background
    /wg-setup-client.sh &
    WG_SETUP_PID=$!
    echo "WireGuard setup started with PID ${WG_SETUP_PID}"
    echo ""
# If in test mode (not WireGuard), wait a bit then start UDP test client
elif [ "${TEST_MODE}" = "true" ]; then
    echo "Test mode: Waiting 2 seconds for tunnel to be ready..."
    sleep 2
    echo "Starting UDP test client..."
    /test-udp-client.sh "127.0.0.1" "${UDP_PORT}" &
    UDP_CLIENT_PID=$!
    echo "UDP test client started with PID ${UDP_CLIENT_PID}"
    echo ""
fi

# Start wg-tcp-tunnel
exec wg-tcp-tunnel "${ARGS[@]}"

