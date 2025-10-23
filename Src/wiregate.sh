#!/bin/bash
#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Execute commands through restricted shell for security
secure_exec() {
    /WireGate/restricted_shell.sh "$@"
}

# Set up signal handling for the main script
export TOP_PID=$$
trap 'cleanup_and_exit' SIGTERM SIGINT SIGQUIT

# Array to store child process PIDs
declare -a CHILD_PIDS=()

cleanup_and_exit() {
    echo "[WIREGATE] Received stop signal. Cleaning up child processes..."
    echo "[WIREGATE] DEBUG: Cleanup signal received at $(date)"
    
    # Set timeout for graceful shutdown (5 seconds)
    timeout=5
    start_time=$(date +%s)
    
    # Send TERM signal to all child processes
    for pid in "${CHILD_PIDS[@]}"; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "[WIREGATE] Stopping child process $pid"
            secure_exec kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    
    # Wait for graceful shutdown with timeout
    while true; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -ge $timeout ]; then
            echo "[WIREGATE] Graceful shutdown timeout reached. Force killing processes..."
            break
        fi
        
        # Check if any child processes are still running
        all_stopped=true
        for pid in "${CHILD_PIDS[@]}"; do
            if ps -p "$pid" > /dev/null 2>&1; then
                all_stopped=false
                break
            fi
        done
        
        if [ "$all_stopped" = true ]; then
            echo "[WIREGATE] All child processes stopped gracefully"
            break
        fi
        
        sleep 0.1
    done
    
    # Force kill any remaining child processes
    for pid in "${CHILD_PIDS[@]}"; do
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "[WIREGATE] Force killing child process $pid"
            secure_exec kill -KILL "$pid" 2>/dev/null || true
        fi
    done
    
    # Clean up any remaining processes immediately
    # Since we don't have ps, we'll rely on the process tracking we already have
    # The CHILD_PIDS array should contain most processes we need to kill
    
    echo "[WIREGATE] Cleanup complete. Exiting."
    exit 0
}
heavy_checkmark=$(printf "\xE2\x9C\x94")
heavy_crossmark=$(printf "\xE2\x9C\x97")
PID_FILE=./dashboard.pid
TORRC_PATH="/etc/tor/torrc"
DNS_TORRC_PATH="/etc/tor/dnstorrc"
# Get IPv4 address instead of IPv6
INET_ADDR="$(ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1)"
dashes='------------------------------------------------------------'
equals='============================================================'
log_dir="./log"
export WGD_IPTABLES_DNS=1.1.1.1
WGD_TOR_PROXY="${WGD_TOR_PROXY:-false}"


# Default configuration paths and settings
WGD_CONF_PATH="${WGD_CONF_PATH:-/etc/wireguard}"
WGD_TOR_PLUGIN="${WGD_TOR_PLUGIN:-obfs4}"
WGD_TOR_BRIDGES="${WGD_TOR_BRIDGES:-false}"
WGD_TOR_EXIT_NODES="${WGD_TOR_EXIT_NODES:-{US}}"



if [[ "$AMNEZIA_WG" == "true" ]]; then
    VPN_PROTO_TYPE="AmneziaWG"
else
    VPN_PROTO_TYPE="WireGuard"
fi
svr_config="${WGD_CONF_PATH}/ADMINS.conf"


help() {
    echo "Usage: ./wiregate.sh [command]"
    echo "Commands:"
    echo "  install"
    echo "  start"
    echo "  stop"
}

get_obfs4_bridges() {
    BRIDGEDB_URL="https://bridges.torproject.org/bridges?transport=obfs4"
    
    printf "[TOR] Fetching obfs4 bridges from Tor's BridgeDB...\n"
    
    response=$(secure_exec wget -qO- "$BRIDGEDB_URL")
    bridges=$(echo "$response" | secure_exec sed -n 's/.*\(obfs4 [^<]*\)<br\/>.*/\1/p' | secure_exec sed 's/&#43;/+/g')
    
    if [[ $response == *"obfs4"* ]]; then
        printf "[TOR] Bridges fetched successfully!\n"
        echo "[TOR-BRIDGE] $bridges"
    else
        echo "[TOR] No obfs4 bridges found or request failed."
    fi
}
get_webtunnel_bridges() {
    BRIDGEDB_URL="https://bridges.torproject.org/bridges?transport=webtunnel"
    
    printf "[TOR] Fetching WebTunnel bridges from Tor's BridgeDB...\n"

    response=$(secure_exec wget -qO- "$BRIDGEDB_URL")
    bridges=$(echo "$response" | secure_exec sed -n 's/.*\(webtunnel [^<]*\)<br\/>.*/\1/p')
    
    if [[ $response == *"webtunnel"* ]]; then
        printf "[TOR] Bridges fetched successfully!\n"
        echo "[TOR-BRIDGE] $bridges"
    else
        echo "[TOR] No WebTunnel bridges found or request failed."
    fi
}
make_torrc() {
    printf "%s\n" "$dashes"
    printf "[TOR] Generating torrc to $TORRC_PATH...\n"
    if [ -f "$TORRC_PATH" ]; then
    secure_exec rm "$TORRC_PATH" 
    fi

    if [[ "$WGD_TOR_PLUGIN" == "webtunnel" ]]; then
    get_webtunnel_bridges
    elif [[ "$WGD_TOR_PLUGIN" == "obfs4" ]]; then
    get_obfs4_bridges
    fi
    
    if [[ "$WGD_TOR_BRIDGES" == "true" ]]; then
    echo -e "UseBridges 1\n" >> "$TORRC_PATH"
    printf "[TOR] Adding bridges to $TORRC_PATH...\n"
    printf "[TOR] Bridges added to $TORRC_PATH successfully!\n"
    fi

    echo -e "AutomapHostsOnResolve 1 \n" >> "$TORRC_PATH"
    echo -e "VirtualAddrNetwork 10.192.0.0/10 \n" >> "$TORRC_PATH"
    echo -e "MaxMemInQueues 128 MB \n" >> "$TORRC_PATH"

    echo -e "ControlPort 9051 \n" >> "$TORRC_PATH"
    echo -e "HashedControlPassword $CTRL_P_PASS\n" >> "$TORRC_PATH"
    echo -e "User tor \n" >> "$TORRC_PATH"
    echo -e "Log notice file /var/log/tor/log \n" >> "$TORRC_PATH"
    echo -e "DataDirectory /var/lib/tor \n" >> "$TORRC_PATH"
    echo -e "TransPort ${INET_ADDR}:59040 IsolateClientAddr IsolateClientProtocol IsolateDestAddr IsolateDestPort \n" >> "$TORRC_PATH"

    echo -e "ClientTransportPlugin ${WGD_TOR_PLUGIN} exec /usr/local/bin/${WGD_TOR_PLUGIN} \n" >> "$TORRC_PATH"
    
    if [[ "$WGD_TOR_EXIT_NODES" == "default" ]]; then
    echo "Using Default"
    elif [[ -n "$WGD_TOR_EXIT_NODES" ]]; then
    echo -e "ExitNodes $WGD_TOR_EXIT_NODES \n" >> "$TORRC_PATH"
    else
    echo "Invalid input. Please use the correct format: {US},{GB},{AU}, etc."
    fi

    if [[ "$WGD_TOR_PLUGIN" == "snowflake" ]]; then
    echo -e "Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn \n" >> "$TORRC_PATH"
    echo -e "Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.net:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn \n" >> "$TORRC_PATH"
  
    else
    echo "$bridges" | while read -r bridge; do
        echo "Bridge $bridge" >> "$TORRC_PATH"
    done
    fi
    printf "%s\n" "$dashes"
}
make_dns_torrc() {
    printf "%s\n" "$dashes"
    printf "[TOR-DNS] Generating DNS-torrc to $DNS_TORRC_PATH...\n"
    if [ -f "$DNS_TORRC_PATH" ]; then
    secure_exec rm "$DNS_TORRC_PATH" 
    fi

    if [[ "$WGD_TOR_PLUGIN" == "webtunnel" ]]; then
    get_webtunnel_bridges
    elif [[ "$WGD_TOR_PLUGIN" == "obfs4" ]]; then
    get_obfs4_bridges
    fi

    if [[ "$WGD_TOR_BRIDGES" == "true" ]]; then
    echo -e "UseBridges 1\n" >> "$DNS_TORRC_PATH"
    printf "[TOR-DNS] Adding bridges to $DNS_TORRC_PATH...\n"
    printf "[TOR-DNS] Bridges added to $DNS_TORRC_PATH successfully!\n"
    fi

    echo -e "AutomapHostsOnResolve 1 \n" >> "$DNS_TORRC_PATH"
    echo -e "VirtualAddrNetwork 10.193.0.0/10 \n" >> "$DNS_TORRC_PATH"
    echo -e "MaxMemInQueues 128 MB \n" >> "$DNS_TORRC_PATH"
    echo -e "ControlPort 9054 \n" >> "$DNS_TORRC_PATH"
    echo -e "HashedControlPassword $CTRL_P_PASS\n" >> "$DNS_TORRC_PATH"
    echo -e "User tor \n" >> "$DNS_TORRC_PATH"
    echo -e "Log notice file /var/log/tor/dnslog \n" >> "$DNS_TORRC_PATH"
    echo -e "DataDirectory /var/lib/tor/dns \n" >> "$DNS_TORRC_PATH"
    echo -e "ClientTransportPlugin ${WGD_TOR_PLUGIN} exec /usr/local/bin/${WGD_TOR_PLUGIN} \n" >> "$DNS_TORRC_PATH"
    if [[ "$WGD_TOR_DNS_EXIT_NODES" == "default" ]]; then
    echo "Using Default"
    elif [[ -n "$WGD_TOR_DNS_EXIT_NODES" ]]; then
    echo -e "ExitNodes $WGD_TOR_DNS_EXIT_NODES \n" >> "$DNS_TORRC_PATH"
    else
    echo "Invalid input. Please use the correct format: {US},{GB},{AU}, etc."
    fi

    echo -e "SocksPort ${INET_ADDR}:9053 \n" >> "$DNS_TORRC_PATH"

    if [[ "$WGD_TOR_PLUGIN" == "snowflake" ]]; then
    echo -e "Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 fingerprint=2B280B23E1107BB62ABFC40DDCC8824814F80A72 url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn \n" >> "$DNS_TORRC_PATH"
    echo -e "Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA fingerprint=8838024498816A039FCBBAB14E6F40A0843051FA url=https://1098762253.rsc.cdn77.org/ fronts=www.cdn77.com,www.phpmyadmin.net ice=stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.net:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn \n" >> "$DNS_TORRC_PATH"
  

    
    else
    echo "$bridges" | while read -r bridge; do
        echo "Bridge $bridge" >> "$DNS_TORRC_PATH"
    done
    fi

    printf "%s\n" "$dashes"
}
generate_vanguard_tor_ctrl_pass() {
  # Generate a 42-character long random password using /dev/urandom and base64
  PASSWORD=$(head -c 32 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 42)
  # Generate the Tor password hash while suppressing the warning message if running as root
  TOR_HASH=$(tor --hash-password "$PASSWORD" 2>&1 | sed -n '/^16/p')
  # Assign the Tor hash to VANGUARD
  export CTRL_P_PASS="$TOR_HASH"
  export VANGUARD="$PASSWORD"
  echo "[TOR] Generated Tor Hash: $CTRL_P_PASS"
  #echo "[TOR] Generated Tor Password: $VANGUARD"
}
run_tor_flux() {
    # Start both Tor processes
    { date; tor -f /etc/tor/torrc; printf "\n\n"; } >> "$log_dir/tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &
    local tor_pid1=$!
    { date; tor -f /etc/tor/dnstorrc; printf "\n\n"; } >> "$log_dir/dns_tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &
    local tor_pid2=$!
    
    # Store Tor PIDs for cleanup
    echo "$tor_pid1" > "$log_dir/tor_pid1.txt" 2>/dev/null || true
    echo "$tor_pid2" > "$log_dir/tor_pid2.txt" 2>/dev/null || true

    start_time=$(date +%s)
    retries=0
    max_retries=142  # 5 minutes with 3s intervals

    # Wait for log files to be created
    while [ ! -f "/var/log/tor/log" ] || [ ! -f "/var/log/tor/dnslog" ]; do
        sleep 1
        retries=$((retries + 1))
        if [ $retries -ge 30 ]; then # Wait up to 30 seconds for log files
            echo "[TOR] Error: One or both log files were not created"
            return 1
        fi
    done

    retries=0 # Reset retries for bootstrap check
    main_bootstrapped=false
    dns_bootstrapped=false
    
    # Wait for both Tor instances to be fully booted
    while ([ "$main_bootstrapped" != "true" ] || [ "$dns_bootstrapped" != "true" ]) && [ $retries -lt $max_retries ]; do
        sleep 3
        retries=$((retries + 1))
        
        # Check main Tor bootstrap status
        if [ "$main_bootstrapped" != "true" ] && grep -q 'Bootstrapped 100%' "/var/log/tor/log"; then
            main_bootstrapped=true
            echo "[TOR] Main Tor instance bootstrapped 100%"
        fi
        
        # Check DNS Tor bootstrap status
        if [ "$dns_bootstrapped" != "true" ] && grep -q 'Bootstrapped 100%' "/var/log/tor/dnslog"; then
            dns_bootstrapped=true
            echo "[TOR] DNS Tor instance bootstrapped 100%"
        fi
        
        elapsed_time=$(( $(date +%s) - start_time ))
        if [ $elapsed_time -ge 300 ]; then
            echo "[TOR] Bootstrap timeout. Restarting Tor processes..."
            secure_exec pkill tor >/dev/null 2>&1
            sleep 0.5

            # Restart Tor processes and capture their PIDs
            { date; tor -f /etc/tor/torrc; printf "\n\n"; } >> "$log_dir/tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &
            tor_pid1=$!
            { date; tor -f /etc/tor/dnstorrc; printf "\n\n"; } >> "$log_dir/dns_tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &
            tor_pid2=$!
            
            # Update stored PIDs
            echo "$tor_pid1" > "$log_dir/tor_pid1.txt" 2>/dev/null || true
            echo "$tor_pid2" > "$log_dir/tor_pid2.txt" 2>/dev/null || true

            start_time=$(date +%s)
            retries=0
            main_bootstrapped=false
            dns_bootstrapped=false
        fi
    done

    if [ $retries -ge $max_retries ]; then
        echo "[TOR] Exiting: Bootstrap unsuccessful for one or both Tor instances."
        return
    fi

    echo "[TOR] Both Tor instances bootstrapped successfully!"

    # Main loop for periodic circuit renewal
    while true; do
        # Use cryptographically secure random for sleep time
        sleep_time=$(secure_exec od -An -N2 -tu2 /dev/urandom | secure_exec tr -d ' ')
        sleep_time=$(( (sleep_time % 600) + 142 ))
        printf "%s\n" "$dashes"
        printf "%s\n" "$dashes"
        sleep "$sleep_time"
        printf "%s\n" "$dashes"
        echo "[TOR] Sending Signal for New Circuits..."
        ./torflux &
        local torflux_pid=$!
        CHILD_PIDS+=("$torflux_pid")
        printf "%s\n" "$dashes"
        echo "[TOR] New circuit in $sleep_time seconds..."
    done
}
generate_awgd_values() {
        # Cryptographically secure random generator for a range
        secure_rand_range() {
            local min=$1
            local max=$2
            local range=$((max - min + 1))
            local bytes_needed=4  # Use 4 bytes for good entropy
            local random_bytes=$(od -An -N$bytes_needed -tu4 /dev/urandom | tr -d ' ')
            local random_value=$((random_bytes % range))
            echo $((min + random_value))
        }

        # Generate WGD_JC (1 ≤ Jc ≤ 128; recommended 3 to 10)
        export WGD_JC=$(secure_rand_range 3 10)

            # Generate WGD_JMIN and WGD_JMAX (Jmin < Jmax; Jmax ≤ 1280; recommended Jmin=50, Jmax=1000)
            export WGD_JMIN=$(secure_rand_range 50 500)
            export WGD_JMAX=$(secure_rand_range $((WGD_JMIN + 1)) 1000)

        # Generate WGD_S1 and WGD_S2 (S1 < 1280, S2 < 1280; S1 + 56 ≠ S2; recommended 15 ≤ S1, S2 ≤ 150)
        while :; do
            S1=$(secure_rand_range 15 150)
            S2=$(secure_rand_range 15 150)
            [ $((S1 + 56)) -ne $S2 ] && break
        done
        export WGD_S1=$S1
        export WGD_S2=$S2

        # Generate unique H1, H2, H3, and H4 (5 ≤ H ≤ 2147483647)
        declare -A unique_hashes
        for h in H1 H2 H3 H4; do
            while :; do
            val=$(secure_rand_range 5 2147483647)
            if [[ -z ${unique_hashes[$val]} ]]; then
                unique_hashes[$val]=1
                export "WGD_$h=$val"
                break
            fi
            done
        done
}
_checkWireguard(){
	if ! secure_exec wg -h > /dev/null 2>&1
	then
		printf "[WIREGATE] %s ${VPN_PROTO_TYPE} is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n" "$heavy_crossmark"
		kill  $TOP_PID
	fi
	if ! secure_exec wg-quick -h > /dev/null 2>&1
	then
		printf "[WIREGATE] %s ${VPN_PROTO_TYPE} is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n" "$heavy_crossmark"
		kill  $TOP_PID
	fi
}
check_dashboard_status(){
  # Use netstat to find listening port and wget to test connectivity
  # This method works in Docker containers that don't have ps
  PORT=$(netstat -tulpn 2>/dev/null | grep ":80 " | head -n1 | awk "{print \$4}" | cut -d: -f2)
  
  if [ -n "$PORT" ]; then
    # Try to connect to the port using wget
    if wget -q --spider http://127.0.0.1:$PORT/ 2>/dev/null; then
      return 0
    fi
  fi
  
  # Fallback: check for HTTPS on port 443
  if netstat -tulpn 2>/dev/null | grep -q ":443 "; then
    return 0
  fi
  
  return 1
}

dashboard_start() {
    printf "%s\n" "$equals"
    
    # Check if we should use SSL based on DASHBOARD_MODE environment variable
    # Default to HTTP unless DASHBOARD_MODE is set to "production"
    if [[ "$DASHBOARD_MODE" == "production" ]]; then
        # Check for SSL certificates in both possible locations
        SSL_CERT_PATH=""
        if [ -f "./SSL_CERT/cert.pem" ] && [ -f "./SSL_CERT/key.pem" ]; then
            SSL_CERT_PATH="./SSL_CERT"
        elif [ -f "/WireGate/SSL_CERT/cert.pem" ] && [ -f "/WireGate/SSL_CERT/key.pem" ]; then
            SSL_CERT_PATH="/WireGate/SSL_CERT"
        fi
        
        if [ -n "$SSL_CERT_PATH" ]; then
            echo "[WIREGATE] SSL mode enabled, starting HTTPS-only (production mode)..."
            
            # Start HTTPS server on port 443 only (production best practice)
            WGD_REMOTE_ENDPOINT_PORT=443 ./wiregate --ssl --certfile ${SSL_CERT_PATH}/cert.pem --keyfile ${SSL_CERT_PATH}/key.pem &
            local https_pid=$!
            echo "$https_pid" > "$PID_FILE"
            CHILD_PIDS+=("$https_pid")
            echo "[WIREGATE] Started HTTPS server on port 443 (PID: $https_pid)"
            echo "[WIREGATE] Access via: https://your-domain:8443"
        else
            echo "[WIREGATE] Production mode enabled but no SSL certificates found!"
            echo "[WIREGATE] Falling back to HTTP mode..."
            echo "[WIREGATE] To enable HTTPS, mount SSL certificates to ./configs/ssl/ or /WireGate/SSL_CERT/ directory inside container"
            echo "[WIREGATE] Required files: cert.pem and key.pem"
            
            # Start the dashboard executable in the background and capture its PID
            ./wiregate &
            local wiregate_pid=$!
            echo "$wiregate_pid" > "$PID_FILE"
            CHILD_PIDS+=("$wiregate_pid")
            echo "[WIREGATE] Started wiregate process with HTTP on port 80 (PID: $wiregate_pid)"
            echo "[WIREGATE] Access via: http://your-domain:8080"
        fi
    else
        echo "[WIREGATE] Starting in development mode (HTTP only)..."
        echo "[WIREGATE] To enable HTTPS, set DASHBOARD_MODE=production and mount SSL certificates"
        echo "[WIREGATE] SSL certificates should be placed in ./SSL_CERT/ or /WireGate/SSL_CERT/ directory"
        
        # Start the dashboard executable in the background and capture its PID
        ./wiregate &
        local wiregate_pid=$!
        echo "$wiregate_pid" > "$PID_FILE"
        CHILD_PIDS+=("$wiregate_pid")
        echo "[WIREGATE] Started wiregate process with HTTP on port 80 (PID: $wiregate_pid)"
        echo "[WIREGATE] Access via: http://your-domain:8080"
    fi
}
dashboard_stop () {
    printf "%s\n" "$equals"  
    echo "[WIREGATE] Stopping WireGuard Dashboard and Tor."

    # Set timeout for graceful shutdown (3 seconds)
    timeout=3
    start_time=$(date +%s)

    # Stop main process
    if test -f "$PID_FILE"; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "[WIREGATE] Stopping main process (PID: $pid)"
            sudo kill -TERM "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown with timeout
            while ps -p "$pid" > /dev/null 2>&1; do
                current_time=$(date +%s)
                elapsed=$((current_time - start_time))
                if [ $elapsed -ge $timeout ]; then
                    echo "[WIREGATE] Force killing main process"
                    sudo kill -KILL "$pid" 2>/dev/null || true
                    break
                fi
                sleep 0.1
            done
        fi
        secure_exec rm -f "$PID_FILE"
    else
        echo "[WIREGATE] No PID file found. Looking for running processes..."
    fi
    
    # Kill all remaining processes immediately
    # Since we don't have ps, we'll rely on the PID file and process tracking
    # The main process should handle most cleanup through the PID file
    
    printf "[WIREGATE] All processes stopped.\n"
    printf "%s\n" "$equals"
    exit 0
}
stop_wiregate() {
	if test -f "$PID_FILE"; then
        dashboard_stop
    else
        # Find the PID(s) of all running 'wiregate' processes
        PIDS=$(ps aux | grep "[.]\/wiregate" | awk '{print $2}')
        
        if [ -z "$PIDS" ]; then
            echo "[WIREGATE] No running wiregate processes found."
        else
            echo "[WIREGATE] Found running wiregate processes: $PIDS"
            # Set timeout for graceful shutdown (2 seconds)
            timeout=2
            start_time=$(date +%s)
            
            # Send TERM signal to all processes
            echo "$PIDS" | xargs sudo kill -TERM 2>/dev/null || true
            
            # Wait for graceful shutdown with timeout
            while true; do
                current_time=$(date +%s)
                elapsed=$((current_time - start_time))
                if [ $elapsed -ge $timeout ]; then
                    echo "[WIREGATE] Force killing remaining processes"
                    echo "$PIDS" | xargs sudo kill -KILL 2>/dev/null || true
                    break
                fi
                
                # Check if any processes are still running
                remaining_pids=$(ps aux | grep "[.]\/wiregate" | awk '{print $2}')
                if [ -z "$remaining_pids" ]; then
                    echo "[WIREGATE] All processes stopped gracefully"
                    break
                fi
                
                sleep 0.1
            done
        fi
        
        # Clean up any remaining processes immediately
        # Since we don't have ps, we'll rely on the process tracking we already have
        # The main process should handle most cleanup through the PID file
    fi
}
init_tor_vanguards() {
    printf "%s\n" "$equals"
    printf "[TOR] Starting Tor & VanGuards ...\n"
    printf "%s\n" "$equals"
    
    # Wait for both Tor log files to be created
    retries=0
    max_file_wait=60  # Wait up to 60 seconds for log files to appear
    
    while ([[ ! -f "/var/log/tor/log" ]] || [[ ! -f "/var/log/tor/dnslog" ]]) && [ $retries -lt $max_file_wait ]; do
        echo "[TOR-VANGUARDS] Waiting for Tor log files to be created... ($retries/$max_file_wait)"
        sleep 1
        retries=$((retries + 1))
    done
    
    if [[ ! -f "/var/log/tor/log" ]] || [[ ! -f "/var/log/tor/dnslog" ]]; then
        echo "[TOR-VANGUARDS] One or both Tor log files not found after waiting. Skipping vanguards.py start."
        return
    fi

    # Wait for both Tor instances to be fully booted
    retries=0
    max_retries=300  # Max wait time is 15 minutes (300 retries * 3 seconds)
    main_bootstrapped_percent=0
    dns_bootstrapped_percent=0
    previous_main_percent=-1
    previous_dns_percent=-1

    while ([ $main_bootstrapped_percent -lt 100 ] || [ $dns_bootstrapped_percent -lt 100 ]) && [ $retries -lt $max_retries ]; do
        # Extract the latest bootstrapped percentage from both log files
        main_bootstrapped_percent=$(grep -o 'Bootstrapped [0-9]\{1,3\}%' "/var/log/tor/log" | tail -n 1 | grep -o '[0-9]\{1,3\}')
        main_bootstrapped_percent=${main_bootstrapped_percent:-0}  # Default to 0 if not found
        
        dns_bootstrapped_percent=$(grep -o 'Bootstrapped [0-9]\{1,3\}%' "/var/log/tor/dnslog" | tail -n 1 | grep -o '[0-9]\{1,3\}')
        dns_bootstrapped_percent=${dns_bootstrapped_percent:-0}  # Default to 0 if not found

        # Update the loading bars only if the percentages have changed
        if [ "$main_bootstrapped_percent" -ne "$previous_main_percent" ] || [ "$dns_bootstrapped_percent" -ne "$previous_dns_percent" ]; then
            previous_main_percent=$main_bootstrapped_percent
            previous_dns_percent=$dns_bootstrapped_percent

            # Generate loading bars
            bar_length=25  # Adjusted bar length to fit better on screen
            
            # Main Tor loading bar
            main_filled_length=$(( (main_bootstrapped_percent * bar_length + 99) / 100 ))
            main_empty_length=$((bar_length - main_filled_length))
            
            # DNS Tor loading bar
            dns_filled_length=$(( (dns_bootstrapped_percent * bar_length + 99) / 100 ))
            dns_empty_length=$((bar_length - dns_filled_length))

            # Display the loading bars with updated progress
            printf "%s\n" "$dashes"
            printf "[TOR-VANGUARDS] Main Tor: ["
            # Create filled bar using while loop
            i=1
            while [ $i -le $main_filled_length ]; do
                printf "#"
                i=$((i + 1))
            done
            
            # Only print "-" if not fully bootstrapped
            if [ "$main_bootstrapped_percent" -lt 100 ]; then
                # Create empty bar using while loop
                i=1
                while [ $i -le $main_empty_length ]; do
                    printf "-"
                    i=$((i + 1))
                done
            fi
            
            printf "] %s%%\n" "$main_bootstrapped_percent"
            
            printf "[TOR-VANGUARDS] DNS Tor: ["
            # Create filled bar using while loop
            i=1
            while [ $i -le $dns_filled_length ]; do
                printf "#"
                i=$((i + 1))
            done
            
            # Only print "-" if not fully bootstrapped
            if [ "$dns_bootstrapped_percent" -lt 100 ]; then
                # Create empty bar using while loop
                i=1
                while [ $i -le $dns_empty_length ]; do
                    printf "-"
                    i=$((i + 1))
                done
            fi
            
            printf "] %s%%\n" "$dns_bootstrapped_percent"
        fi

        # Retry count
        sleep 1  # Reduced sleep for faster updates
        retries=$((retries + 1))
    done

    if [ $main_bootstrapped_percent -lt 100 ] || [ $dns_bootstrapped_percent -lt 100 ]; then
        echo "[TOR-VANGUARDS] One or both Tor instances did not bootstrap to 100% within the expected time. Exiting."
        printf "%s\n" "$dashes"
        return
    fi

    printf "%s\n" "$dashes"
    printf "[TOR-VANGUARDS] Both Tor instances are fully booted. Starting TOR Vanguards\n"
    printf "%s\n" "$dashes"
    sudo chown -R tor /etc/tor
    while true; do
        printf "%s\n" "$dashes"
        echo "[TOR-VANGUARDS] Updating Tor Vanguards..."
        printf "%s\n" "$dashes"
        sudo rm -r ./log/tor_circuit_refresh_log.txt > /dev/null 2>&1
        printf "%s\n" "$dashes"
        # Run vanguards for the first control port (9051)
        echo "[TOR-VANGUARDS] Running vanguards for control port 9051..."
        printf "%s\n" "$dashes"
        export VANGUARD_CTRL_PORT=9051
        ./vanguards --one_shot_vanguards &
        local vanguards_pid1=$!
        CHILD_PIDS+=("$vanguards_pid1")
        sleep 5  # Short delay between runs
        printf "%s\n" "$dashes"
        # Run vanguards for the second control port (9054)
        echo "[TOR-VANGUARDS] Running vanguards for control port 9054..."
        printf "%s\n" "$dashes"
        export VANGUARD_CTRL_PORT=9054
        ./vanguards --one_shot_vanguards &
        local vanguards_pid2=$!
        CHILD_PIDS+=("$vanguards_pid2")
        
        printf "%s\n" "$dashes"
        sleep 3600  # Sleep for 1 hour before updating Vanguards again
    done  
}
start_core() {
    _checkWireguard
    generate_awgd_values
	# Check if ADMINS.conf exists in ${WGD_CONF_PATH}
    if [ ! -f "$svr_config" ]; then
		printf "[WIREGATE] %s ${VPN_PROTO_TYPE} Configurations Missing, Creating ....\n" "$heavy_checkmark"
		set_proxy
		newconf_wgd
	else
		printf "[WIREGATE] %s Loading ${VPN_PROTO_TYPE} Configurations.\n" "$heavy_checkmark"
	fi
	
	# Re-assign config_files to ensure it includes any newly created configurations
	local config_files=$(secure_exec find ${WGD_CONF_PATH} -type f -name "*.conf")
	local iptable_dir="./iptable-rules"
	# Set file permissions
	secure_exec find ${WGD_CONF_PATH} -type f -name "*.conf" -exec chmod 600 {} \;
	secure_exec find "$iptable_dir" -type f -name "*.sh" -exec chmod +x {} \;
	
	printf "[WIREGATE] %s Starting ${VPN_PROTO_TYPE} Configurations.\n" "$heavy_checkmark"
	printf "%s\n" "$equals"

    #Creating Symbolic Links For AmneziaWG if Enabled
    
	for file in ${WGD_CONF_PATH}/*; do
    # Check if the symbolic link already exists
    if [ -L "/etc/amnezia/amneziawg/$(basename "$file")" ]; then
        echo "AmneziaWG Symbolic Links for $(basename "$file") already exists, skipping..."
        continue
    fi
    # Create the symbolic link if it doesn't exist
    sudo ln -s "$file" /etc/amnezia/amneziawg/
	done


	log_file="$log_dir/interface_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt"
	wg_conf_path="${WGD_CONF_PATH}"

    # Start WireGuard for each config file
	# Loop over each .conf file in the specified directory
    for file in "$wg_conf_path"/*.conf; do
        # Get the configuration name (without the .conf extension)
        config_name=$(basename "$file" .conf)

        # Check if the config file contains AmneziaWG parameters
        if grep -q -E '^\s*(Jc|Jmin|Jmax|S1|S2|H1|H2|H3|H4)\s*=' "$file"; then
            tool="secure_exec awg-quick"
            echo "Detected AmneziaWG parameters in $file. Using awg-quick for $config_name." >> "$log_file"
        else
            tool="secure_exec wg-quick"
            echo "No AmneziaWG parameters detected in $file. Using wg-quick for $config_name." >> "$log_file"
        fi

        # Extract the IPv6 address from the configuration file
        ipv6_address=$(grep -E 'Address\s*=\s*.*,\s*([a-fA-F0-9:]+)' "$file" | sed -E 's/.*,\s*([a-fA-F0-9:]+)\/.*/\1/')

        # Bring the WireGuard interface up
        echo "Bringing up interface: $config_name using $tool" >> "$log_file"
        $tool up "$config_name" >> "$log_file" 2>&1

        # Patching for AmneziaWG IPv6
        # Check if an IPv6 address was found in the config
        if [ -n "$ipv6_address" ]; then
            echo "IPv6 address found: $ipv6_address for $config_name" >> "$log_file"

            # Remove any existing IPv6 addresses for the interface
            ip -6 addr flush dev "$config_name" >> "$log_file" 2>&1

            # Add the new IPv6 address to the interface
            echo "Adding IPv6 address $ipv6_address to $config_name" >> "$log_file"
            ip -6 addr add "$ipv6_address" dev "$config_name" >> "$log_file" 2>&1
        else
            echo "No IPv6 address found for $config_name, skipping IPv6 configuration." >> "$log_file"
        fi
    done
}
set_proxy () {
    if [[ "$WGD_TOR_PROXY" == "true" ]]; then
        postType="tor-post"
    elif [[ "$WGD_TOR_PROXY" == "false" ]]; then
        postType="post"
    fi

	AMDpostup="./iptable-rules/Admins/${postType}up.sh"
	GSTpostup="./iptable-rules/Guest/${postType}up.sh"
	LANpostup="./iptable-rules/LAN-only-users/postup.sh"
	MEMpostup="./iptable-rules/Members/${postType}up.sh"

	AMDpostdown="./iptable-rules/Admins/${postType}down.sh"
	GSTpostdown="./iptable-rules/Guest/${postType}down.sh"
	LANpostdown="./iptable-rules/LAN-only-users/postdown.sh"
	MEMpostdown="./iptable-rules/Members/${postType}down.sh"
}
generate_awgd_values() {
        # Cryptographically secure random generator for a range
        secure_rand_range() {
            local min=$1
            local max=$2
            local range=$((max - min + 1))
            local bytes_needed=4  # Use 4 bytes for good entropy
            local random_bytes=$(od -An -N$bytes_needed -tu4 /dev/urandom | tr -d ' ')
            local random_value=$((random_bytes % range))
            echo $((min + random_value))
        }

        # Generate WGD_JC (1 ≤ Jc ≤ 128; recommended 3 to 10)
        export WGD_JC=$(secure_rand_range 3 10)

            # Generate WGD_JMIN and WGD_JMAX (Jmin < Jmax; Jmax ≤ 1280; recommended Jmin=50, Jmax=1000)
            export WGD_JMIN=$(secure_rand_range 50 500)
            export WGD_JMAX=$(secure_rand_range $((WGD_JMIN + 1)) 1000)

        # Generate WGD_S1 and WGD_S2 (S1 < 1280, S2 < 1280; S1 + 56 ≠ S2; recommended 15 ≤ S1, S2 ≤ 150)
        while :; do
            S1=$(secure_rand_range 15 150)
            S2=$(secure_rand_range 15 150)
            [ $((S1 + 56)) -ne $S2 ] && break
        done
        export WGD_S1=$S1
        export WGD_S2=$S2

        # Generate unique H1, H2, H3, and H4 (5 ≤ H ≤ 2147483647)
        declare -A unique_hashes
        for h in H1 H2 H3 H4; do
            while :; do
            val=$(secure_rand_range 5 2147483647)
            if [[ -z ${unique_hashes[$val]} ]]; then
                unique_hashes[$val]=1
                export "WGD_$h=$val"
                break
            fi
            done
        done
}
newconf_wgd() {
  for i in {0..3}; do
    wg_config_zones "$i"
  done
}
wg_config_zones() {
  local index=$1
  local port=$((WGD_PORT_RANGE_STARTPORT + index))
  local private_key=$(secure_exec wg genkey)
  local public_key=$(echo "$private_key" | secure_exec wg pubkey)
  
  case $index in
    0)
      local config_file="${WGD_CONF_PATH}/ADMINS.conf"
      local address="10.0.0.1/24"
      local post_up="$AMDpostup"
      local pre_down="$AMDpostdown"
      ;;
    1)
      local config_file="${WGD_CONF_PATH}/MEMBERS.conf"
      local address="192.168.10.1/24"
      local post_up="$MEMpostup"
      local pre_down="$MEMpostdown"
      ;;
    2)
      local config_file="${WGD_CONF_PATH}/LANP2P.conf"
      local address="172.16.0.1/24"
      local post_up="$LANpostup"
      local pre_down="$LANpostdown"
      ;;
    3)
      local config_file="${WGD_CONF_PATH}/GUESTS.conf"
      local address="192.168.20.1/24"
      local post_up="$GSTpostup"
      local pre_down="$GSTpostdown"
      ;;
  esac

  cat <<EOF >"$config_file"
[Interface]
SaveConfig = true
PostUp =  $post_up
PreDown = $pre_down
ListenPort = $port
PrivateKey = $private_key
Address = $address
EOF

  if [[ "$AMNEZIA_WG" == "true" ]]; then
    echo "Jc = $WGD_JC" >> "$config_file"
    echo "Jmin = $WGD_JMIN" >> "$config_file"
    echo "Jmax = $WGD_JMAX" >> "$config_file"
    echo "S1 = $WGD_S1" >> "$config_file"
    echo "S2 = $WGD_S2" >> "$config_file"
    echo "H1 = $WGD_H1" >> "$config_file"
    echo "H2 = $WGD_H2" >> "$config_file"
    echo "H3 = $WGD_H3" >> "$config_file"
    echo "H4 = $WGD_H4" >> "$config_file"
  fi

  [ "$index" -eq 0 ] && make_master_config
}
make_master_config() {
    # Ensure necessary variables are set
    if [ -z "$svr_config" ]; then
        echo "[Error] Server configuration file path (\$svr_config) is not set."
        return 1
    fi

    # Create the master-key directory if it doesn't exist
    mkdir -p "master-key"

    # Check if the specified config file exists
    if [ -f "$svr_config" ]; then
        # Check if the master peer with IP 10.0.0.254/32 is already configured
        if grep -q "AllowedIPs = 10.0.0.254/32" "$svr_config"; then
            echo "[WIREGATE] Master Peer Already Exists, Skipping..."
            return 0
        fi
    else
        echo "[Error] Server configuration file ($svr_config) does not exist."
        return 1
    fi

    # Function to generate a new peer's public key
    generate_public_key() {
        local private_key="$1"
        echo "$private_key" | secure_exec wg pubkey
    }

    # Generate the new peer's private key, public key, and preshared key
    wg_private_key=$(secure_exec wg genkey)
    if [ -z "$wg_private_key" ]; then
        echo "[Error] Failed to generate ${VPN_PROTO_TYPE} private key."
        return 1
    fi

    peer_public_key=$(generate_public_key "$wg_private_key")
    preshared_key=$(secure_exec wg genpsk)

    # Add the peer to the WireGuard config file with the preshared key
    {
        echo -e "\n[Peer]"
        echo "#Name# = Master Key"
        echo "PublicKey = $peer_public_key"
        echo "PresharedKey = $preshared_key"
        echo "AllowedIPs = 10.0.0.254/32"
    } >> "$svr_config"

    # Extract the server's private key and generate its public key
    server_private_key=$(grep -E '^PrivateKey' "$svr_config" | awk '{print $NF}')
    if [ -z "$server_private_key" ]; then
        echo "[Error] Failed to extract server private key from configuration."
        return 1
    fi
    svrpublic_key=$(echo "$server_private_key" | secure_exec wg pubkey)

    # Generate the client config file
    {
        echo "[Interface]"
        echo "PrivateKey = $wg_private_key"
        echo "Address = 10.0.0.254/32"
        echo "DNS = 10.2.0.100,10.2.0.100"
        echo -e "MTU = 1420\n" 

        # Conditional block for AMNEZIA_WG
        if [ "$AMNEZIA_WG" == "true" ]; then
            echo "Jc = $WGD_JC"
            echo "Jmin = $WGD_JMIN"
            echo "Jmax = $WGD_JMAX"
            echo "S1 = $WGD_S1"
            echo "S2 = $WGD_S2"
            echo "H1 = $WGD_H1"
            echo "H2 = $WGD_H2"
            echo "H3 = $WGD_H3"
            echo -e "H4 = $WGD_H4\n"
        fi

        echo "[Peer]"
        echo "PublicKey = $svrpublic_key"
        echo "AllowedIPs = 0.0.0.0/0"
        echo "Endpoint = $WGD_REMOTE_ENDPOINT:$WGD_PORT_RANGE_STARTPORT"
        echo "PersistentKeepalive = 21"
        echo "PresharedKey = $preshared_key"
    } > "./master-key/master.conf"

	printf "[WIREGATE] %s ${VPN_PROTO_TYPE} Master configuration created successfully.\n" "$heavy_checkmark"
}
run_pre_install_setup(){

    # Create and set ownership for Tor directories

    sudo chmod -R 755 ${WGD_CONF_PATH}/

    # Load HFSC module at container startup and verify
    secure_exec modprobe sch_hfsc
    if secure_exec lsmod | secure_exec grep -q sch_hfsc; then
        echo "[TRAFFIC] sch_hfsc module loaded successfully"
    else
        echo "[TRAFFIC] WARNING: Failed to load sch_hfsc module, Kernel may not support it"
    fi


   # Loop over each .sh file in the directory and its subdirectories
    secure_exec find ./iptable-rules/ -type f -name "*.sh" | while read -r file; do
        # Check if the file contains the line with DNS_SERVER=${WGD_IPTABLES_DNS}
        if secure_exec grep -q "DNS_SERVER=\${WGD_IPTABLES_DNS}" "$file"; then
            # Replace the line with the current value of WGD_IPTABLES_DNS
            secure_exec sed -i "s|DNS_SERVER=\${WGD_IPTABLES_DNS}|DNS_SERVER=${WGD_IPTABLES_DNS}|" "$file"
        fi
    done

    secure_exec mkdir -p /etc/amnezia/amneziawg/
    if [[ ! -c /dev/net/tun ]]; then
    secure_exec mkdir -p /dev/net && secure_exec mknod /dev/net/tun c 10 200
    fi

    exit 0

}
run_pre_start_setup() {

	# Create and set ownership for Tor directories
	secure_exec mkdir -p /var/lib/tor /var/log/tor
	secure_exec chown -R tor:tor /var/lib/tor/
	secure_exec chown -R tor:tor /var/log/tor/
	secure_exec chmod 700 /var/lib/tor/
	secure_exec chmod 700 /var/log/tor/

    start_core
    generate_vanguard_tor_ctrl_pass
    dashboard_start
    printf "%s\n" "$equals"
    printf "[WIREGATE] %s Dashboard Starting\n" "$heavy_checkmark"
    printf "%s\n" "$equals"
    sleep 3
    make_torrc
    make_dns_torrc
    run_tor_flux &
    init_tor_vanguards

}
metal_install() {
    printf "%s\n" "$equals"
    printf "[WIREGATE] Metal Install\n"
    printf "%s\n" "$equals"
    sudo make install
    sudo make clean
    printf "%s\n" "$equals"
    printf "[WIREGATE] Metal Install Complete\n"
    printf "%s\n" "$equals"
    run_pre_install_setup
}

if [ "$#" != 1 ]; then
    help
else
    if [ "$1" = "start" ]; then
        printf "%s\n" "$dashes"
        run_pre_start_setup
        printf "%s\n" "$dashes"
    elif [ "$1" = "stop" ]; then
        if check_dashboard_status; then
            printf "%s\n" "$dashes"
            stop_wiregate
            printf "[WIREGATE] Dashboard EXITED.\n"
            printf "%s\n" "$dashes"
        else
            printf "%s\n" "$dashes"
            printf "[WIREGATE] Dashboard is not running.\n"
            printf "%s\n" "$dashes"
        fi
    elif [ "$1" = "install" ]; then
        run_pre_install_setup 
    elif [ "$1" = "metal_install" ]; then
        metal_install
    fi
fi

