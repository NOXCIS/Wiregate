#!/bin/bash
#
# Cloudflare Warp PostDown Script for MEMBERS Zone
# Removes Warp routing configuration
#

set -e

# Configuration
WIREGUARD_INTERFACE="${WIREGUARD_INTERFACE:-MEMBERS}"
WARP_INTERFACE="warp"
WARP_ENABLED="${WGD_WARP_ENABLED:-false}"
WARP_ZONES="${WGD_WARP_ZONES:-ADMINS,MEMBERS}"
WARP_TABLE=100
WARP_MARK=0x101

# Logging function
log() {
    echo "[WARP-POSTDOWN-MEMBERS] $1" >&2
}

# Check if Warp was enabled
if [ "$WARP_ENABLED" != "true" ]; then
    log "Warp was disabled. Skipping cleanup."
    exit 0
fi

# Check if this zone was using Warp
if ! echo "$WARP_ZONES" | grep -qE "(^|,)${WIREGUARD_INTERFACE}(,|$)"; then
    log "Zone $WIREGUARD_INTERFACE was not using Warp. Skipping cleanup."
    exit 0
fi

log "Cleaning up Warp routing for $WIREGUARD_INTERFACE zone..."

# Remove policy routing rule
log "Removing policy routing rule..."
ip rule del fwmark $WARP_MARK table warp 2>/dev/null || true

# Remove packet marking
log "Removing packet marking..."
iptables -t mangle -D PREROUTING -i "$WIREGUARD_INTERFACE" -j MARK --set-mark $WARP_MARK 2>/dev/null || true

# Remove NAT rule
log "Removing NAT rule..."
iptables -t nat -D POSTROUTING -o "$WARP_INTERFACE" -j MASQUERADE 2>/dev/null || true

# Remove forwarding rules
log "Removing forwarding rules..."
iptables -D FORWARD -i "$WIREGUARD_INTERFACE" -o "$WARP_INTERFACE" -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i "$WARP_INTERFACE" -o "$WIREGUARD_INTERFACE" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

# Remove default route from custom table
log "Removing routes from custom table..."
ip route del default dev "$WARP_INTERFACE" table warp 2>/dev/null || true

log "✓ Warp routing cleaned up for $WIREGUARD_INTERFACE"
