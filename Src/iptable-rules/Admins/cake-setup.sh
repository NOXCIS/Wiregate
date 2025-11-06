#!/bin/bash
# CAKE Traffic Shaper Setup Script for ADMINS Zone
# Applies CAKE (Common Applications Kept Enhanced) qdisc to WireGuard interface
# Part of Wiregate CAKE integration

set -e

# Configuration
WIREGUARD_INTERFACE="${WIREGUARD_INTERFACE:-ADMINS}"
CAKE_ENABLED="${CAKE_ENABLED:-false}"
CAKE_BANDWIDTH="${CAKE_BANDWIDTH_ADMINS:-1gbit}"
CAKE_OVERHEAD="${CAKE_OVERHEAD:-0}"
CAKE_MPU="${CAKE_MPU:-0}"
CAKE_MEMLIMIT="${CAKE_MEMLIMIT:-32m}"
CAKE_OPTIONS="${CAKE_OPTIONS:-besteffort triple-isolate nat nowash split-gso}"

# Logging function
log() {
    echo "[CAKE-ADMINS] $1" >&2
}

# Check if CAKE is enabled
if [ "$CAKE_ENABLED" != "true" ]; then
    log "CAKE traffic shaping is disabled. Skipping setup."
    exit 0
fi

log "Starting CAKE traffic shaper setup..."

# Check if tc command is available
if ! command -v tc &> /dev/null; then
    log "WARNING: tc command not found. Please install iproute2 package."
    log "Skipping CAKE setup."
    exit 0
fi

# Wait for interface to be available (max 10 seconds)
WAIT_COUNT=0
MAX_WAIT=10
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if ip link show "$WIREGUARD_INTERFACE" &> /dev/null; then
        log "Interface $WIREGUARD_INTERFACE is ready."
        break
    fi
    log "Waiting for interface $WIREGUARD_INTERFACE... ($WAIT_COUNT/$MAX_WAIT)"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    log "WARNING: Interface $WIREGUARD_INTERFACE not found after ${MAX_WAIT}s. Skipping CAKE setup."
    exit 0
fi

# Remove existing qdisc if present (ignore errors)
log "Removing any existing qdisc on $WIREGUARD_INTERFACE..."
tc qdisc del dev "$WIREGUARD_INTERFACE" root 2>/dev/null || true

# Apply CAKE qdisc
log "Applying CAKE qdisc to $WIREGUARD_INTERFACE..."
log "  Bandwidth: $CAKE_BANDWIDTH"
log "  Overhead: $CAKE_OVERHEAD bytes"
log "  MPU: $CAKE_MPU bytes"
log "  Memory Limit: $CAKE_MEMLIMIT"
log "  Options: $CAKE_OPTIONS"

# Build tc command
TC_CMD="tc qdisc add dev $WIREGUARD_INTERFACE root cake"
TC_CMD="$TC_CMD bandwidth $CAKE_BANDWIDTH"
TC_CMD="$TC_CMD overhead $CAKE_OVERHEAD"
TC_CMD="$TC_CMD mpu $CAKE_MPU"
TC_CMD="$TC_CMD memlimit $CAKE_MEMLIMIT"
TC_CMD="$TC_CMD $CAKE_OPTIONS"

# Execute tc command
if $TC_CMD; then
    log "✓ CAKE traffic shaper applied successfully!"

    # Show configuration
    log "Current qdisc configuration:"
    tc qdisc show dev "$WIREGUARD_INTERFACE" 2>&1 | while read -r line; do
        log "  $line"
    done
else
    log "ERROR: Failed to apply CAKE qdisc. Check if CAKE is available in kernel."
    log "You can verify with: tc qdisc add dev lo root cake help"
    exit 1
fi

log "CAKE setup completed for $WIREGUARD_INTERFACE."
