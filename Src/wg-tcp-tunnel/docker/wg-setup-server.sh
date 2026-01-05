#!/bin/bash
# WireGuard Server Setup Script
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
WG_INTERFACE="wg0"
WG_SERVER_IP="${WG_SERVER_IP:-10.0.0.1}"
WG_CLIENT_IP="${WG_CLIENT_IP:-10.0.0.2}"
WG_ADDRESS="${WG_SERVER_IP}/24"
WG_LISTEN_PORT="${WG_LISTEN_PORT:-51820}"
WG_KEYS_DIR="${WG_KEYS_DIR:-/wg-keys}"
WG_CONFIG_DIR="/etc/wireguard"
WG_CONFIG_FILE="${WG_CONFIG_DIR}/${WG_INTERFACE}.conf"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[WG-SERVER]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WG-SERVER]${NC} $1"; }
log_error() { echo -e "${RED}[WG-SERVER]${NC} $1"; }

# Ensure required directories exist
mkdir -p "${WG_KEYS_DIR}"
mkdir -p "${WG_CONFIG_DIR}"

log_info "Starting WireGuard server setup..."

# Generate server keys if they don't exist
if [ ! -f "${WG_KEYS_DIR}/server.key" ]; then
    log_info "Generating server keys..."
    wg genkey > "${WG_KEYS_DIR}/server.key"
    wg pubkey < "${WG_KEYS_DIR}/server.key" > "${WG_KEYS_DIR}/server.pub"
    chmod 600 "${WG_KEYS_DIR}/server.key"
    log_info "Server public key: $(cat ${WG_KEYS_DIR}/server.pub)"
else
    log_info "Using existing server keys"
fi

SERVER_PRIVATE_KEY=$(cat "${WG_KEYS_DIR}/server.key")
SERVER_PUBLIC_KEY=$(cat "${WG_KEYS_DIR}/server.pub")

# Wait for client public key (timeout after 60 seconds)
log_info "Waiting for client public key..."
TIMEOUT=60
ELAPSED=0
while [ ! -f "${WG_KEYS_DIR}/client.pub" ]; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        log_error "Timeout waiting for client public key"
        exit 1
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ $((ELAPSED % 10)) -eq 0 ]; then
        log_info "Still waiting for client public key... (${ELAPSED}s)"
    fi
done

CLIENT_PUBLIC_KEY=$(cat "${WG_KEYS_DIR}/client.pub")
log_info "Client public key received: ${CLIENT_PUBLIC_KEY}"

# Create WireGuard configuration
log_info "Creating WireGuard server configuration..."
cat > "${WG_CONFIG_FILE}" << EOF
[Interface]
Address = ${WG_ADDRESS}
ListenPort = ${WG_LISTEN_PORT}
PrivateKey = ${SERVER_PRIVATE_KEY}

[Peer]
PublicKey = ${CLIENT_PUBLIC_KEY}
AllowedIPs = ${WG_CLIENT_IP}/32
EOF

chmod 600 "${WG_CONFIG_FILE}"

# Signal that server is ready
touch "${WG_KEYS_DIR}/server.ready"
log_info "Server configuration complete"

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

# Start iperf3 server in background
log_info "Starting iperf3 server..."
iperf3 -s -D --bind ${WG_SERVER_IP} 2>/dev/null || log_warn "iperf3 server may already be running"

log_info "WireGuard server setup complete"
log_info "Server IP: ${WG_SERVER_IP}"
log_info "Listening on UDP port: ${WG_LISTEN_PORT}"

# Keep script running to maintain logs
while true; do
    sleep 30
    if ip link show "${WG_INTERFACE}" > /dev/null 2>&1; then
        log_info "WireGuard interface is up - $(wg show ${WG_INTERFACE} latest-handshakes 2>/dev/null || echo 'no handshakes')"
    else
        log_warn "WireGuard interface is down, attempting restart..."
        wg-quick up "${WG_INTERFACE}" 2>/dev/null || log_error "Failed to restart interface"
    fi
done

