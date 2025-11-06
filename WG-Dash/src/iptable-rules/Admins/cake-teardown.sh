#!/bin/bash
# CAKE Traffic Shaper Teardown Script for ADMINS Zone
# Removes CAKE qdisc from WireGuard interface
# Part of Wiregate CAKE integration

set -e

# Configuration
WIREGUARD_INTERFACE="${WIREGUARD_INTERFACE:-ADMINS}"
CAKE_ENABLED="${CAKE_ENABLED:-false}"

# Logging function
log() {
    echo "[CAKE-ADMINS] $1" >&2
}

# Check if CAKE was enabled
if [ "$CAKE_ENABLED" != "true" ]; then
    log "CAKE traffic shaping was disabled. Skipping teardown."
    exit 0
fi

log "Starting CAKE traffic shaper teardown..."

# Check if tc command is available
if ! command -v tc &> /dev/null; then
    log "WARNING: tc command not found. Skipping teardown."
    exit 0
fi

# Check if interface exists
if ! ip link show "$WIREGUARD_INTERFACE" &> /dev/null; then
    log "Interface $WIREGUARD_INTERFACE not found. Nothing to tear down."
    exit 0
fi

# Remove CAKE qdisc
log "Removing CAKE qdisc from $WIREGUARD_INTERFACE..."

if tc qdisc del dev "$WIREGUARD_INTERFACE" root 2>/dev/null; then
    log "✓ CAKE traffic shaper removed successfully!"
else
    log "No qdisc found on $WIREGUARD_INTERFACE or already removed."
fi

log "CAKE teardown completed for $WIREGUARD_INTERFACE."
