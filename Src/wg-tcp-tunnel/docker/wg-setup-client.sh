#!/bin/bash
# WireGuard Client Setup Script
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
WG_INTERFACE="wg0"
WG_SERVER_IP="${WG_SERVER_IP:-10.0.0.1}"
WG_CLIENT_IP="${WG_CLIENT_IP:-10.0.0.2}"
WG_ADDRESS="${WG_CLIENT_IP}/24"
WG_ENDPOINT="${WG_ENDPOINT:-127.0.0.1:51822}"
WG_KEYS_DIR="${WG_KEYS_DIR:-/wg-keys}"
WG_CONFIG_DIR="/etc/wireguard"
WG_CONFIG_FILE="${WG_CONFIG_DIR}/${WG_INTERFACE}.conf"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[WG-CLIENT]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WG-CLIENT]${NC} $1"; }
log_error() { echo -e "${RED}[WG-CLIENT]${NC} $1"; }

# Ensure required directories exist
mkdir -p "${WG_KEYS_DIR}"
mkdir -p "${WG_CONFIG_DIR}"

log_info "Starting WireGuard client setup..."

# Generate client keys if they don't exist
if [ ! -f "${WG_KEYS_DIR}/client.key" ]; then
    log_info "Generating client keys..."
    wg genkey > "${WG_KEYS_DIR}/client.key"
    wg pubkey < "${WG_KEYS_DIR}/client.key" > "${WG_KEYS_DIR}/client.pub"
    chmod 600 "${WG_KEYS_DIR}/client.key"
    log_info "Client public key: $(cat ${WG_KEYS_DIR}/client.pub)"
else
    log_info "Using existing client keys"
fi

CLIENT_PRIVATE_KEY=$(cat "${WG_KEYS_DIR}/client.key")
CLIENT_PUBLIC_KEY=$(cat "${WG_KEYS_DIR}/client.pub")

# Wait for server public key (timeout after 60 seconds)
log_info "Waiting for server public key..."
TIMEOUT=60
ELAPSED=0
while [ ! -f "${WG_KEYS_DIR}/server.pub" ]; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        log_error "Timeout waiting for server public key"
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ $((ELAPSED % 10)) -eq 0 ]; then
        log_info "Still waiting for server public key... (${ELAPSED}s)"
    fi
done

SERVER_PUBLIC_KEY=$(cat "${WG_KEYS_DIR}/server.pub")
log_info "Server public key received: ${SERVER_PUBLIC_KEY}"

# Wait for server to be ready
log_info "Waiting for server to be ready..."
TIMEOUT=60
ELAPSED=0
while [ ! -f "${WG_KEYS_DIR}/server.ready" ]; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        log_warn "Timeout waiting for server ready signal, proceeding anyway..."
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Create WireGuard configuration
log_info "Creating WireGuard client configuration..."
cat > "${WG_CONFIG_FILE}" << EOF
[Interface]
Address = ${WG_ADDRESS}
PrivateKey = ${CLIENT_PRIVATE_KEY}

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
Endpoint = ${WG_ENDPOINT}
AllowedIPs = ${WG_SERVER_IP}/32
PersistentKeepalive = 25
EOF

chmod 600 "${WG_CONFIG_FILE}"

log_info "Client configuration complete"

# Start WireGuard interface
log_info "Starting WireGuard interface ${WG_INTERFACE}..."
wg-quick up "${WG_INTERFACE}" || {
    log_error "Failed to start WireGuard interface"
    # Try manual setup if wg-quick fails
    log_info "Attempting manual interface setup..."
    ip link add dev "${WG_INTERFACE}" type wireguard || true
    ip addr add "${WG_ADDRESS}" dev "${WG_INTERFACE}" || true
    wg setconf "${WG_INTERFACE}" <(wg-quick strip "${WG_CONFIG_FILE}") || {
        log_error "Manual setup also failed"
        exit 1
    }
    ip link set up dev "${WG_INTERFACE}"
}

log_info "WireGuard interface status:"
wg show "${WG_INTERFACE}"

# Signal that client is ready
touch "${WG_KEYS_DIR}/client.ready"

log_info "WireGuard client setup complete"
log_info "Client IP: ${WG_CLIENT_IP}"
log_info "Connecting to endpoint: ${WG_ENDPOINT}"

# Test connectivity to server
log_info "Testing connectivity to WireGuard server (${WG_SERVER_IP})..."
sleep 2  # Wait for handshake

PING_SUCCESS=false
for i in 1 2 3 4 5; do
    if ping -c 1 -W 2 ${WG_SERVER_IP} > /dev/null 2>&1; then
        PING_SUCCESS=true
        log_info "Ping test successful!"
        break
    fi
    log_warn "Ping attempt $i failed, retrying..."
    sleep 2
done

if [ "$PING_SUCCESS" = false ]; then
    log_warn "Could not ping server, but WireGuard interface is up"
    log_warn "This may be normal if the tunnel is still establishing"
fi

# Keep script running to maintain logs
while true; do
    sleep 30
    if ip link show "${WG_INTERFACE}" > /dev/null 2>&1; then
        HANDSHAKE=$(wg show ${WG_INTERFACE} latest-handshakes 2>/dev/null | awk '{print $2}')
        if [ -n "$HANDSHAKE" ] && [ "$HANDSHAKE" != "0" ]; then
            log_info "WireGuard connected - last handshake: ${HANDSHAKE}s ago"
        else
            log_info "WireGuard interface up - waiting for handshake"
        fi
    else
        log_warn "WireGuard interface is down, attempting restart..."
        wg-quick up "${WG_INTERFACE}" 2>/dev/null || log_error "Failed to restart interface"
    fi
done

