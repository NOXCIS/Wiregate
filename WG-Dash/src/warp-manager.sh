#!/bin/bash
#
# Cloudflare Warp Manager for Wiregate
# Manages wgcf credentials and Warp interface configuration
#

set -e

# Configuration
WARP_DIR="/opt/wireguarddashboard/warp"
WARP_ACCOUNT_FILE="$WARP_DIR/wgcf-account.toml"
WARP_PROFILE_FILE="$WARP_DIR/wgcf-profile.conf"
WARP_WG_CONF="/etc/wireguard/warp.conf"
WARP_ENABLED="${WGD_WARP_ENABLED:-false}"
WARP_LICENSE_KEY="${WGD_WARP_LICENSE_KEY:-}"
WARP_MTU="${WGD_WARP_MTU:-1280}"
WARP_ENDPOINT="${WGD_WARP_ENDPOINT:-engage.cloudflareclient.com:2408}"

# Logging functions
log_info() {
    echo "[WARP-MANAGER] INFO: $1" >&2
}

log_error() {
    echo "[WARP-MANAGER] ERROR: $1" >&2
}

log_warn() {
    echo "[WARP-MANAGER] WARN: $1" >&2
}

# Check if wgcf is available
check_wgcf() {
    if ! command -v wgcf &> /dev/null; then
        log_error "wgcf command not found. Please install wgcf."
        return 1
    fi
    log_info "wgcf is available: $(wgcf --version 2>&1 || echo 'version unknown')"
    return 0
}

# Create Warp directory if it doesn't exist
setup_warp_directory() {
    if [ ! -d "$WARP_DIR" ]; then
        log_info "Creating Warp directory: $WARP_DIR"
        mkdir -p "$WARP_DIR"
    fi
    cd "$WARP_DIR" || exit 1
}

# Register a new Cloudflare Warp account
register_warp_account() {
    log_info "Registering new Cloudflare Warp account..."

    if [ -f "$WARP_ACCOUNT_FILE" ]; then
        log_info "Account file already exists. Skipping registration."
        return 0
    fi

    if wgcf register --accept-tos; then
        log_info "✓ Warp account registered successfully"
        return 0
    else
        log_error "Failed to register Warp account"
        return 1
    fi
}

# Apply Warp+ license key
apply_license_key() {
    if [ -z "$WARP_LICENSE_KEY" ]; then
        log_info "No Warp+ license key provided. Using free tier."
        return 0
    fi

    log_info "Applying Warp+ license key..."

    if wgcf update --license-key "$WARP_LICENSE_KEY"; then
        log_info "✓ Warp+ license key applied successfully"
        return 0
    else
        log_warn "Failed to apply Warp+ license key. Continuing with free tier."
        return 0
    fi
}

# Generate WireGuard profile
generate_warp_profile() {
    log_info "Generating WireGuard profile for Warp..."

    if [ ! -f "$WARP_ACCOUNT_FILE" ]; then
        log_error "Account file not found. Please register first."
        return 1
    fi

    if wgcf generate; then
        log_info "✓ WireGuard profile generated: $WARP_PROFILE_FILE"
        return 0
    else
        log_error "Failed to generate WireGuard profile"
        return 1
    fi
}

# Customize WireGuard configuration
customize_warp_config() {
    log_info "Customizing Warp WireGuard configuration..."

    if [ ! -f "$WARP_PROFILE_FILE" ]; then
        log_error "Profile file not found: $WARP_PROFILE_FILE"
        return 1
    fi

    # Create /etc/wireguard directory if it doesn't exist
    mkdir -p /etc/wireguard

    # Copy profile and customize
    cp "$WARP_PROFILE_FILE" "$WARP_WG_CONF"

    # Set custom MTU
    if ! grep -q "^MTU" "$WARP_WG_CONF"; then
        sed -i "/^\[Interface\]/a MTU = $WARP_MTU" "$WARP_WG_CONF"
    else
        sed -i "s/^MTU.*/MTU = $WARP_MTU/" "$WARP_WG_CONF"
    fi

    # Update endpoint if custom one is provided
    if [ "$WARP_ENDPOINT" != "engage.cloudflareclient.com:2408" ]; then
        sed -i "s|^Endpoint.*|Endpoint = $WARP_ENDPOINT|" "$WARP_WG_CONF"
    fi

    # Remove any Table directive (we'll use custom routing)
    sed -i '/^Table/d' "$WARP_WG_CONF"

    # Add Table = off to prevent automatic route creation
    sed -i "/^\[Interface\]/a Table = off" "$WARP_WG_CONF"

    log_info "✓ Configuration customized: $WARP_WG_CONF"
    return 0
}

# Start Warp interface
start_warp_interface() {
    log_info "Starting Warp interface (warp)..."

    if [ ! -f "$WARP_WG_CONF" ]; then
        log_error "Warp configuration not found: $WARP_WG_CONF"
        return 1
    fi

    # Check if interface is already up
    if ip link show warp &> /dev/null; then
        log_info "Warp interface already exists. Bringing it down first..."
        wg-quick down warp 2>/dev/null || true
    fi

    # Bring up the interface
    if wg-quick up warp; then
        log_info "✓ Warp interface started successfully"

        # Verify interface is up
        if wg show warp &> /dev/null; then
            log_info "✓ Warp interface verified"
            return 0
        else
            log_error "Warp interface failed verification"
            return 1
        fi
    else
        log_error "Failed to start Warp interface"
        return 1
    fi
}

# Stop Warp interface
stop_warp_interface() {
    log_info "Stopping Warp interface..."

    if ip link show warp &> /dev/null; then
        if wg-quick down warp; then
            log_info "✓ Warp interface stopped successfully"
            return 0
        else
            log_error "Failed to stop Warp interface"
            return 1
        fi
    else
        log_info "Warp interface is not running"
        return 0
    fi
}

# Check Warp connectivity
check_warp_connectivity() {
    log_info "Checking Warp connectivity..."

    if ! ip link show warp &> /dev/null; then
        log_error "Warp interface is not up"
        return 1
    fi

    # Use wgcf trace to verify connection
    if wgcf trace 2>&1 | grep -q "warp=on"; then
        log_info "✓ Warp is connected and working"
        return 0
    else
        log_warn "Warp interface is up but connectivity check failed"
        return 1
    fi
}

# Get Warp status
get_warp_status() {
    if ! ip link show warp &> /dev/null; then
        echo "stopped"
        return 0
    fi

    if wg show warp &> /dev/null; then
        echo "running"
        return 0
    else
        echo "error"
        return 1
    fi
}

# Main setup function
setup_warp() {
    log_info "===== Cloudflare Warp Setup ====="

    # Check if Warp is enabled
    if [ "$WARP_ENABLED" != "true" ]; then
        log_info "Warp is disabled (WGD_WARP_ENABLED=$WARP_ENABLED). Skipping setup."
        return 0
    fi

    # Check dependencies
    if ! check_wgcf; then
        log_error "Missing dependencies. Cannot setup Warp."
        return 1
    fi

    # Setup directory
    setup_warp_directory

    # Register account if needed
    if [ ! -f "$WARP_ACCOUNT_FILE" ]; then
        if ! register_warp_account; then
            log_error "Failed to register Warp account"
            return 1
        fi
    else
        log_info "Using existing Warp account"
    fi

    # Apply license key if provided
    apply_license_key

    # Generate profile if needed
    if [ ! -f "$WARP_PROFILE_FILE" ]; then
        if ! generate_warp_profile; then
            log_error "Failed to generate Warp profile"
            return 1
        fi
    else
        log_info "Using existing Warp profile"
    fi

    # Customize configuration
    if ! customize_warp_config; then
        log_error "Failed to customize Warp configuration"
        return 1
    fi

    # Start Warp interface
    if ! start_warp_interface; then
        log_error "Failed to start Warp interface"
        return 1
    fi

    # Check connectivity
    if check_warp_connectivity; then
        log_info "===== Warp Setup Complete ====="
        return 0
    else
        log_warn "Warp setup complete but connectivity check failed"
        return 0
    fi
}

# Cleanup function
cleanup_warp() {
    log_info "===== Cleaning up Warp ====="

    # Stop interface
    stop_warp_interface

    # Optionally remove configuration files
    if [ "$1" == "--remove-config" ]; then
        log_info "Removing Warp configuration files..."
        rm -rf "$WARP_DIR"
        rm -f "$WARP_WG_CONF"
        log_info "✓ Configuration files removed"
    fi

    log_info "===== Warp Cleanup Complete ====="
}

# Main command handler
case "${1:-}" in
    setup)
        setup_warp
        ;;
    start)
        start_warp_interface
        ;;
    stop)
        stop_warp_interface
        ;;
    restart)
        stop_warp_interface
        sleep 2
        start_warp_interface
        ;;
    status)
        STATUS=$(get_warp_status)
        echo "Warp status: $STATUS"
        if [ "$STATUS" == "running" ]; then
            wg show warp
        fi
        ;;
    check)
        check_warp_connectivity
        ;;
    cleanup)
        cleanup_warp "$2"
        ;;
    register)
        setup_warp_directory
        register_warp_account
        ;;
    generate)
        setup_warp_directory
        generate_warp_profile
        ;;
    *)
        echo "Usage: $0 {setup|start|stop|restart|status|check|cleanup|register|generate}"
        echo ""
        echo "Commands:"
        echo "  setup       - Full Warp setup (register, generate, start)"
        echo "  start       - Start Warp interface"
        echo "  stop        - Stop Warp interface"
        echo "  restart     - Restart Warp interface"
        echo "  status      - Show Warp status"
        echo "  check       - Check Warp connectivity"
        echo "  cleanup     - Stop Warp and optionally remove config (--remove-config)"
        echo "  register    - Register new Warp account"
        echo "  generate    - Generate WireGuard profile"
        echo ""
        echo "Environment Variables:"
        echo "  WGD_WARP_ENABLED         - Enable/disable Warp (true/false, default: false)"
        echo "  WGD_WARP_LICENSE_KEY     - Warp+ license key (optional)"
        echo "  WGD_WARP_MTU             - MTU size (default: 1280)"
        echo "  WGD_WARP_ENDPOINT        - Warp endpoint (default: engage.cloudflareclient.com:2408)"
        exit 1
        ;;
esac
