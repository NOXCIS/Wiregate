#!/bin/bash
#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

#trap "kill $TOP_PID"
export TOP_PID=$$
heavy_checkmark=$(printf "\xE2\x9C\x94")
heavy_crossmark=$(printf "\xE2\x9C\x97")
PID_FILE=./dashboard.pid
TORRC_PATH="/etc/tor/torrc"
DNS_TORRC_PATH="/etc/tor/dnstorrc"
INET_ADDR="$(hostname -i | awk '{print $1}')"
dashes='------------------------------------------------------------'
equals='============================================================'
log_dir="./log"
dnscrypt_conf=./dnscrypt/dnscrypt-proxy.toml



if [[ "$AMNEZIA_WG" == "true" ]]; then
    VPN_PROTO_TYPE="AmneziaWG"
else
    VPN_PROTO_TYPE="WireGuard"
fi
svr_config="${WGD_CONF_PATH}/ADMINS.conf"




get_obfs4_bridges() {
    BRIDGEDB_URL="https://bridges.torproject.org/bridges?transport=obfs4"
    
    printf "[TOR] Fetching obfs4 bridges from Tor's BridgeDB...\n"
    
    response=$(curl -s "$BRIDGEDB_URL")
    bridges=$(echo "$response" | sed -n 's/.*\(obfs4 [^<]*\)<br\/>.*/\1/p' | sed 's/&#43;/+/g')
    
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

    response=$(curl -s "$BRIDGEDB_URL")
    bridges=$(echo "$response" | sed -n 's/.*\(webtunnel [^<]*\)<br\/>.*/\1/p')
    
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
    rm "$TORRC_PATH" 
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
    echo -e "MaxMemInQueues 32 MB \n" >> "$TORRC_PATH"

    echo -e "ControlPort 9051 \n" >> "$TORRC_PATH"
    echo -e "HashedControlPassword $CTRL_P_PASS\n" >> "$TORRC_PATH"
    echo -e "User tor \n" >> "$TORRC_PATH"
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
    rm "$DNS_TORRC_PATH" 
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
    echo -e "MaxMemInQueues 32 MB \n" >> "$DNS_TORRC_PATH"
    echo -e "ControlPort 9054 \n" >> "$DNS_TORRC_PATH"
    echo -e "HashedControlPassword $CTRL_P_PASS\n" >> "$DNS_TORRC_PATH"
    echo -e "User tor \n" >> "$DNS_TORRC_PATH"
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
  TOR_HASH=$(sudo -u tor tor --hash-password "$PASSWORD")

  # Assign the Tor hash to VANGUARD
  export CTRL_P_PASS="$TOR_HASH"
  export VANGUARD="$PASSWORD"
  echo "[TOR] Generated Tor Hash: $CTRL_P_PASS"
  echo "[TOR] Generated Tor Password: $VANGUARD"
}
run_tor_flux() {
    # Start both Tor processes
    { date; tor -f /etc/tor/torrc; printf "\n\n"; } >> "$log_dir/tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &
    { date; tor -f /etc/tor/dnstorrc; printf "\n\n"; } >> "$log_dir/dns_tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &

    start_time=$(date +%s)
    retries=0
    max_retries=142  # 5 minutes with 3s intervals

    # Wait for Tor to be fully booted
    latest_log=$(ls "$log_dir/tor_startup_log_"*.txt | sort -V | tail -n 1)
    while ! grep -q 'Bootstrapped 100%' "$latest_log" && [ $retries -lt $max_retries ]; do
        sleep 3
        retries=$((retries + 1))
        latest_log=$(ls "$log_dir/tor_startup_log_"*.txt | sort -V | tail -n 1)
        
        elapsed_time=$(( $(date +%s) - start_time ))
        if [ $elapsed_time -ge 300 ]; then
            echo "[TOR] Bootstrap timeout. Restarting Tor..."
            pkill tor >/dev/null 2>&1
            sleep 0.5

            # Restart Tor processes and capture their PIDs
            { date; tor -f /etc/tor/torrc; printf "\n\n"; } >> "$log_dir/tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &
            { date; tor -f /etc/tor/dnstorrc; printf "\n\n"; } >> "$log_dir/dns_tor_startup_log_$(date +'%Y-%m-%d_%H-%M-%S').txt" &


            start_time=$(date +%s)
            retries=0
        fi
    done

    if [ $retries -ge $max_retries ]; then
        echo "[TOR] Exiting: Bootstrap unsuccessful."
        return
    fi

    # Main loop for periodic circuit renewal
    while true; do
        #sleep_time=$(( RANDOM % 30 + 12 ))
        sleep_time=$(( RANDOM % 600 + 142 ))
        printf "%s\n" "$dashes"
        #echo "[TOR] New circuit in $sleep_time seconds..."
        printf "%s\n" "$dashes"
        sleep "$sleep_time"
        printf "%s\n" "$dashes"
        echo "[TOR] Sending Signal for New Circuits..."
        ./torflux &
        printf "%s\n" "$dashes"
        echo "[TOR] New circuit in $sleep_time seconds..."
    done
}

generate_awgd_values() {
        # Random generator for a range
        rand_range() {
            local min=$1
            local max=$2
            echo $((RANDOM % (max - min + 1) + min))
        }

        # Generate WGD_JC (1 ≤ Jc ≤ 128; recommended 3 to 10)
        export WGD_JC=$(rand_range 3 10)

            # Generate WGD_JMIN and WGD_JMAX (Jmin < Jmax; Jmax ≤ 1280; recommended Jmin=50, Jmax=1000)
            export WGD_JMIN=$(rand_range 50 500)
            export WGD_JMAX=$(rand_range $((WGD_JMIN + 1)) 1000)

        # Generate WGD_S1 and WGD_S2 (S1 < 1280, S2 < 1280; S1 + 56 ≠ S2; recommended 15 ≤ S1, S2 ≤ 150)
        while :; do
            S1=$(rand_range 15 150)
            S2=$(rand_range 15 150)
            [ $((S1 + 56)) -ne $S2 ] && break
        done
        export WGD_S1=$S1
        export WGD_S2=$S2

        # Generate unique H1, H2, H3, and H4 (5 ≤ H ≤ 2147483647)
        declare -A unique_hashes
        for h in H1 H2 H3 H4; do
            while :; do
            val=$(rand_range 5 2147483647)
            if [[ -z ${unique_hashes[$val]} ]]; then
                unique_hashes[$val]=1
                export "WGD_$h=$val"
                break
            fi
            done
        done
}
_checkWireguard(){
	if ! wg -h > /dev/null 2>&1
	then
		printf "[WIREGATE] %s ${VPN_PROTO_TYPE} is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n" "$heavy_crossmark"
		kill  $TOP_PID
	fi
	if ! wg-quick -h > /dev/null 2>&1
	then
		printf "[WIREGATE] %s ${VPN_PROTO_TYPE} is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n" "$heavy_crossmark"
		kill  $TOP_PID
	fi
}
check_dashboard_status(){
  if test -f "$PID_FILE"; then
    # Check if the process ID in the dashboard.pid file is still running
    if ps aux | grep -v grep | grep "$(cat $PID_FILE)" > /dev/null; then
      return 0
    else
      return 1
    fi
  else
    # Check if any running dashboard process exists
    if ps aux | grep -v grep | grep '[.]\/dashboard' > /dev/null; then
      return 0
    else
      return 1
    fi
  fi
}

dashboard_start() {
    printf "%s\n" "$equals"
    # Start the dashboard executable in the background and capture its PID
    ./wiregate &
    echo $! > "$PID_FILE"

}
dashboard_stop () {
    if test -f "$PID_FILE"; then
        # Kill the process using the PID stored in dashboard.pid
        sudo kill $(cat "$PID_FILE")
        # Remove the PID file after stopping the process
        rm -f "$PID_FILE"
    else
        echo "No PID file found. Dashboard may not be running."
    fi
}
stop_wiregate() {
	if test -f "$PID_FILE"; then
        dashboard_stop
    else
        # Find the PID(s) of all running 'dashboard' processes
        PIDS=$(ps aux | grep "[.]\/dashboard" | awk '{print $2}')
        
        if [ -z "$PIDS" ]; then
            echo "No running dashboard processes found."
        else
            # Kill all running 'dashboard' processes by their PID
            echo "$PIDS" | xargs sudo kill
        fi
    fi
}
init() {
    _checkWireguard
    generate_awgd_values
    mkdir -p /etc/amnezia/amneziawg/
    if [[ ! -c /dev/net/tun ]]; then
    mkdir -p /dev/net && mknod /dev/net/tun c 10 200
    fi
    start_core
    #dashboard_start
	
	if [[ "$WGD_TOR_PROXY" == "true" ]]; then
		# Get the most recent log file based on the date in the filename
		latest_log=$(ls /WireGate/log/tor_startup_log_*.txt | sort -V | tail -n 1)
		printf "%s\n" "$equals"
		printf "[TOR] Starting Tor & VanGuards ...\n"
		printf "%s\n" "$equals"
		
		if [[ -z "$latest_log" ]]; then
			echo "[TOR-VANGUARDS] No Tor startup log file found. Skipping vanguards.py start."
			return
		fi

		# Wait for Tor to be fully booted by checking for "Bootstrapped" percentage in the latest log
		retries=0
		max_retries=300  # Max wait time is 15 minutes (300 retries * 3 seconds)
		bootstrapped_percent=0
		previous_percent=-1  # Track the previous percentage to update only on change

		while [ $bootstrapped_percent -lt 100 ] && [ $retries -lt $max_retries ]; do
			# Extract the latest bootstrapped percentage from the log file
			bootstrapped_percent=$(grep -o 'Bootstrapped [0-9]\{1,3\}%' "$latest_log" | tail -n 1 | grep -o '[0-9]\{1,3\}')
			bootstrapped_percent=${bootstrapped_percent:-0}  # Default to 0 if not found

			# Update the loading bar only if the percentage has changed
			if [ "$bootstrapped_percent" -ne "$previous_percent" ]; then
				previous_percent=$bootstrapped_percent

				# Generate a loading bar
				bar_length=25  # Adjusted bar length to fit better on screen
				filled_length=$(( (bootstrapped_percent * bar_length + 99) / 100 ))
				empty_length=$((bar_length - filled_length))

				# Display the loading bar with updated progress on a new line each time
				printf "%s\n" "$dashes"
				printf "[TOR-VANGUARDS] Bootstrapping TOR: ["
				printf "%0.s#" $(seq 1 $filled_length)
				
				# Only print "-" if not fully bootstrapped
				if [ "$bootstrapped_percent" -lt 100 ]; then
					printf "%0.s-" $(seq 1 $empty_length)
				fi
				
				printf "] %s%%\n" "$bootstrapped_percent"
			fi

			# Refresh the latest log file and retry count
			sleep 1  # Reduced sleep for faster updates
			retries=$((retries + 1))
			latest_log=$(ls /WireGate/log/tor_startup_log_*.txt | sort -V | tail -n 1)
		done

		if [ $bootstrapped_percent -lt 100 ]; then
			echo "[TOR-VANGUARDS] Tor did not bootstrap to 100% within the expected time. Exiting."
			printf "%s\n" "$dashes"
			return
		fi

		printf "%s\n" "$dashes"
		printf "[TOR-VANGUARDS] Tor is fully booted. Starting TOR Vanguards\n"
		printf "%s\n" "$dashes"
		sudo chown -R tor /etc/tor
		while true; do
        printf "%s\n" "$dashes"
        echo "[TOR-VANGUARDS] Updating Tor Vanguards..."
        printf "%s\n" "$dashes"
        sudo rm -r ./log/tor_circuit_refresh_log.txt > /dev/null 2>&1
		./vanguards --one_shot_vanguards &
		printf "%s\n" "$dashes"
        sleep 3600  #Sleep for 1 hour befored Updating Vanguards Again
		done
	fi    
	
}
start_core() {
	# Check if ADMINS.conf exists in ${WGD_CONF_PATH}
    if [ ! -f "$svr_config" ]; then
		printf "[WIREGATE] %s ${VPN_PROTO_TYPE} Configurations Missing, Creating ....\n" "$heavy_checkmark"
		set_proxy
		newconf_wgd
	else
		printf "[WIREGATE] %s Loading ${VPN_PROTO_TYPE} Configurations.\n" "$heavy_checkmark"
	fi
	
	# Re-assign config_files to ensure it includes any newly created configurations
	local config_files=$(find ${WGD_CONF_PATH} -type f -name "*.conf")
	local iptable_dir="/WireGate/iptable-rules"
	# Set file permissions
	find ${WGD_CONF_PATH} -type f -name "*.conf" -exec chmod 600 {} \;
	find "$iptable_dir" -type f -name "*.sh" -exec chmod +x {} \;
	
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
            tool="awg-quick"
            echo "Detected AmneziaWG parameters in $file. Using awg-quick for $config_name." >> "$log_file"
        else
            tool="wg-quick"
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

	AMDpostup="/WireGate/iptable-rules/Admins/${postType}up.sh"
	GSTpostup="/WireGate/iptable-rules/Guest/${postType}up.sh"
	LANpostup="/WireGate/iptable-rules/LAN-only-users/postup.sh"
	MEMpostup="/WireGate/iptable-rules/Members/${postType}up.sh"

	AMDpostdown="/WireGate/iptable-rules/Admins/${postType}down.sh"
	GSTpostdown="/WireGate/iptable-rules/Guest/${postType}down.sh"
	LANpostdown="/WireGate/iptable-rules/LAN-only-users/postdown.sh"
	MEMpostdown="/WireGate/iptable-rules/Members/${postType}down.sh"
}
generate_awgd_values() {
        # Random generator for a range
        rand_range() {
            local min=$1
            local max=$2
            echo $((RANDOM % (max - min + 1) + min))
        }

        # Generate WGD_JC (1 ≤ Jc ≤ 128; recommended 3 to 10)
        export WGD_JC=$(rand_range 3 10)

            # Generate WGD_JMIN and WGD_JMAX (Jmin < Jmax; Jmax ≤ 1280; recommended Jmin=50, Jmax=1000)
            export WGD_JMIN=$(rand_range 50 500)
            export WGD_JMAX=$(rand_range $((WGD_JMIN + 1)) 1000)

        # Generate WGD_S1 and WGD_S2 (S1 < 1280, S2 < 1280; S1 + 56 ≠ S2; recommended 15 ≤ S1, S2 ≤ 150)
        while :; do
            S1=$(rand_range 15 150)
            S2=$(rand_range 15 150)
            [ $((S1 + 56)) -ne $S2 ] && break
        done
        export WGD_S1=$S1
        export WGD_S2=$S2

        # Generate unique H1, H2, H3, and H4 (5 ≤ H ≤ 2147483647)
        declare -A unique_hashes
        for h in H1 H2 H3 H4; do
            while :; do
            val=$(rand_range 5 2147483647)
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
  local private_key=$(wg genkey)
  local public_key=$(echo "$private_key" | wg pubkey)
  
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
        echo "$private_key" | wg pubkey
    }

    # Generate the new peer's private key, public key, and preshared key
    wg_private_key=$(wg genkey)
    if [ -z "$wg_private_key" ]; then
        echo "[Error] Failed to generate ${VPN_PROTO_TYPE} private key."
        return 1
    fi

    peer_public_key=$(generate_public_key "$wg_private_key")
    preshared_key=$(wg genpsk)

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
    svrpublic_key=$(echo "$server_private_key" | wg pubkey)

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
    } > "/WireGate/master-key/master.conf"

	printf "[WIREGATE] %s ${VPN_PROTO_TYPE} Master configuration created successfully.\n" "$heavy_checkmark"
}


run_pre_install_setup(){
    sudo apk add --no-cache tor curl > /dev/null 2>&1
    sudo chmod -R 755 ${WGD_CONF_PATH}/

    # Load HFSC module at container startup and verify
    modprobe sch_hfsc
    if lsmod | grep -q sch_hfsc; then
        echo "[TRAFFIC] sch_hfsc module loaded successfully"
    else
        echo "[TRAFFIC] WARNING: Failed to load sch_hfsc module, Kernel may not support it"
    fi


   # Loop over each .sh file in the directory and its subdirectories
    find /WireGate/iptable-rules/ -type f -name "*.sh" | while read -r file; do
        # Check if the file contains the line with DNS_SERVER=${WGD_IPTABLES_DNS}
        if grep -q "DNS_SERVER=\${WGD_IPTABLES_DNS}" "$file"; then
            # Replace the line with the current value of WGD_IPTABLES_DNS
            sed -i "s|DNS_SERVER=\${WGD_IPTABLES_DNS}|DNS_SERVER=${WGD_IPTABLES_DNS}|" "$file"
        fi
    done



    if [[ "$WGD_TOR_PROXY" == "true" ]]; then
        sed -i "s/^#\(proxy = 'socks5:\/\/wiregate:9053'\)/\1/" "$dnscrypt_conf"
        else
            sed -i "s/^\(proxy = 'socks5:\/\/wiregate:9053'\)/#\1/" "$dnscrypt_conf"
    fi


    
    if [ ! -d "log" ]
	  then 
		printf "[WIREGATE] Creating WireGate Logs folder\n"
		mkdir "log"
	fi
    if [ ! -d "db" ] 
		then 
			mkdir "db"
    fi


}
run_pre_start_setup() {
    dashboard_start
    printf "%s\n" "$equals"
    printf "[WIREGATE] %s Dashboard Started\n" "$heavy_checkmark"
    printf "%s\n" "$equals"
    sleep 3
    make_torrc
    make_dns_torrc
    generate_vanguard_tor_ctrl_pass
    run_tor_flux &
    init 

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
    fi
fi
