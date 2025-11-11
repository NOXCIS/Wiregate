#!/bin/bash
#
# Cloudflare Warp PostUp Script for GUESTS Zone
# Routes zone traffic through Cloudflare Warp tunnel
#

set -e

# Configuration
WIREGUARD_INTERFACE="${WIREGUARD_INTERFACE:-GUESTS}"
WARP_INTERFACE="warp"
WARP_ENABLED="${WGD_WARP_ENABLED:-false}"
WARP_ZONES="${WGD_WARP_ZONES:-ADMINS,MEMBERS}"
WARP_TABLE=100
WARP_MARK=0x102

# Logging function
log() {
    echo "[WARP-POSTUP-GUESTS] $1" >&2
}

# Check if Warp is enabled globally
if [ "$WARP_ENABLED" != "true" ]; then
    log "Warp is disabled globally. Skipping Warp routing setup."
    exit 0
fi

# Check if this zone should use Warp
if ! echo "$WARP_ZONES" | grep -qE "(^|,)${WIREGUARD_INTERFACE}(,|$)"; then
    log "Zone $WIREGUARD_INTERFACE is not in WARP_ZONES. Skipping Warp routing setup."
    exit 0
fi

log "Setting up Warp routing for $WIREGUARD_INTERFACE zone..."

# Check if Warp interface exists
if ! ip link show "$WARP_INTERFACE" &> /dev/null; then
    log "ERROR: Warp interface not found. Please ensure warp-manager.sh setup has run."
    log "Skipping Warp routing setup. Traffic will use default routing."
    exit 0
fi

# Get Warp interface IP
WARP_IP=$(ip -4 addr show "$WARP_INTERFACE" | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
if [ -z "$WARP_IP" ]; then
    log "ERROR: Could not determine Warp interface IP address"
    exit 1
fi

log "Warp interface IP: $WARP_IP"

# Create custom routing table if it doesn't exist
if ! grep -q "^$WARP_TABLE warp" /etc/iproute2/rt_tables 2>/dev/null; then
    log "Creating custom routing table..."
    echo "$WARP_TABLE warp" >> /etc/iproute2/rt_tables
fi

# Add default route via Warp in custom table
log "Adding default route via Warp in custom table..."
ip route add default dev "$WARP_INTERFACE" table warp 2>/dev/null || true

# Mark packets from this WireGuard zone
log "Marking packets from $WIREGUARD_INTERFACE..."
iptables -t mangle -A PREROUTING -i "$WIREGUARD_INTERFACE" -j MARK --set-mark $WARP_MARK

# Route marked packets via custom table
log "Setting up policy routing for marked packets..."
ip rule add fwmark $WARP_MARK table warp priority 102 2>/dev/null || true

# Add source NAT for traffic going through Warp
log "Setting up NAT for Warp traffic..."
iptables -t nat -A POSTROUTING -o "$WARP_INTERFACE" -j MASQUERADE

# Allow forwarding to Warp interface
log "Allowing traffic forwarding to Warp..."
iptables -A FORWARD -i "$WIREGUARD_INTERFACE" -o "$WARP_INTERFACE" -j ACCEPT
iptables -A FORWARD -i "$WARP_INTERFACE" -o "$WIREGUARD_INTERFACE" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

log "✓ Warp routing configured successfully for $WIREGUARD_INTERFACE"
log "Traffic from $WIREGUARD_INTERFACE will now route through Cloudflare Warp"

# Display routing info
log "Routing configuration:"
log "  WireGuard Zone: $WIREGUARD_INTERFACE"
log "  Warp Interface: $WARP_INTERFACE ($WARP_IP)"
log "  Packet Mark: $WARP_MARK"
log "  Routing Table: warp (ID: $WARP_TABLE)"
