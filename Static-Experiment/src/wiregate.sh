#!/bin/bash
# Copyright 2024 NOXCIS [https://github.com/NOXCIS]



#trap "kill $TOP_PID"
export TOP_PID=$$


app_name="dashboard.py"
app_official_name="WGDashboard"
venv_python="./venv/bin/python3"
venv_gunicorn="./venv/bin/gunicorn"
pythonExecutable="python3"
svr_config="${WGD_CONF_PATH}/ADMINS.conf"

heavy_checkmark=$(printf "\xE2\x9C\x94")
heavy_crossmark=$(printf "\xE2\x9C\x97")

PID_FILE=./gunicorn.pid
environment=$(if [[ $ENVIRONMENT ]]; then echo $ENVIRONMENT; else echo 'develop'; fi)
if [[ $CONFIGURATION_PATH ]]; then
  cb_work_dir=$CONFIGURATION_PATH/letsencrypt/work-dir
  cb_config_dir=$CONFIGURATION_PATH/letsencrypt/config-dir
else
  cb_work_dir=/etc/letsencrypt
  cb_config_dir=/var/lib/letsencrypt
fi

dashes='------------------------------------------------------------'
equals='============================================================'
helpMsg="[WGDashboard] Please check ./log/install.txt for more details. For further assistance, please open a ticket on https://github.com/donaldzou/WGDashboard/issues/new/choose, I'm more than happy to help :)"
help () {
  printf "=================================================================================\n"
  printf "+          <WGDashboard> by Donald Zou - https://github.com/donaldzou           +\n"
  printf "=================================================================================\n"
  printf "| Usage: ./wgd.sh <option>                                                      |\n"
  printf "|                                                                               |\n"
  printf "| Available options:                                                            |\n"
  printf "|    start: To start WGDashboard.                                               |\n"
  printf "|    stop: To stop WGDashboard.                                                 |\n"
  printf "|    debug: To start WGDashboard in debug mode (i.e run in foreground).         |\n"
  printf "|    update: To update WGDashboard to the newest version from GitHub.           |\n"
  printf "|    install: To install WGDashboard.                                           |\n"
  printf "| Thank you for using! Your support is my motivation ;)                         |\n"
  printf "=================================================================================\n"
}



_checkWireguard(){
	if ! wg -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s WireGuard is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n" "$heavy_crossmark"
		kill  $TOP_PID
	fi
	if ! wg-quick -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s WireGuard is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n" "$heavy_crossmark"
		kill  $TOP_PID
	fi
}


install_wgd(){
    printf "[WGDashboard] Starting to install WGDashboard\n"
    sudo chmod -R 755 ${WGD_CONF_PATH}/

	if [ ! -d "${WGD_CONF_PATH}/WGDashboard_Backup" ]
    	then
    		printf "[WGDashboard] Creating ${WGD_CONF_PATH}/WGDashboard_Backup folder\n"
            mkdir "${WGD_CONF_PATH}/WGDashboard_Backup"
    fi
    
    if [ ! -d "log" ]
	  then 
		printf "[WGDashboard] Creating ./log folder\n"
		mkdir "log"
	fi
    if [ ! -d "db" ] 
		then 
			printf "[WGDashboard] Creating ./db folder\n"
			mkdir "db"
    fi
}

gunicorn_start () {
  	printf "%s\n" "$equals"
	./dashboard &
  	tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 42000 > .env
	sed -i '1,42s/^/#/' .env
	
}
gunicorn_stop () {
	sudo kill $(cat ./gunicorn.pid)
}
stop_wgd() {
	if test -f "$PID_FILE"; then
		gunicorn_stop
	else
		kill "$(ps aux | grep "[p]ython3 $app_name" | awk '{print $2}')"
	fi
}
startwgd_docker() {
    _checkWireguard
	printf "%s\n" "$equals"
    printf "[WIREGATE] %s Started\n" "$heavy_checkmark"
    printf "%s\n" "$equals"
	set_env docker 
    gunicorn_start
	start_core
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
				printf "[TOR-VANGUARDS] Bootstrapping: ["
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

		# Ensure the loading bar ends with a newline
		echo ""

		if [ $bootstrapped_percent -lt 100 ]; then
			echo "[TOR-VANGUARDS] Tor did not bootstrap to 100% within the expected time. Exiting."
			printf "%s\n" "$dashes"
			return
		fi

		printf "[TOR-VANGUARDS] Tor is fully booted. Starting TOR Vanguards\n"
		printf "%s\n" "$dashes"
		sudo chown -R tor /etc/tor
		while true; do
		./vanguards --one_shot_vanguards &
		wait
		sleep 3600  # Sleep for 1 hour (3600 seconds)
		done
	fi    
	
}
set_env() {
  local env_file=".env"
  local env_type="$1"

  # Check if the env_file exists and is not empty
  if [[ -f "$env_file" && -s "$env_file" ]]; then
    printf "[WGDashboard][Docker] %s Loading Enviornment File.\n" "$heavy_checkmark"
    return 0
  fi

  # Create the env_file if it doesn't exist
  if [[ ! -f "$env_file" ]]; then
    touch "$env_file"
    printf "[WGDashboard][Docker] %s Enviornment File Missing, Creating ...\n" "$heavy_checkmark" 
  fi

  # Clear the file to ensure it's updated with the latest values
  > "$env_file"

  if [[ "$env_type" == "docker" ]]; then
    printf "AMNEZIA_WG=%s\n" "${AMNEZIA_WG}" >> "$env_file"
	printf "WGD_CONF_PATH=%s\n" "${WGD_CONF_PATH}" >> "$env_file"
    printf "WGD_WELCOME_SESSION=%s\n" "${WGD_WELCOME_SESSION}" >> "$env_file"
    printf "WGD_REMOTE_ENDPOINT_PORT=%s\n" "${WGD_REMOTE_ENDPOINT_PORT}" >> "$env_file"
	printf "WGD_AUTH_REQ=%s\n" "${WGD_AUTH_REQ}" >> "$env_file"
    printf "WGD_USER=%s\n" "${WGD_USER}" >> "$env_file"
    printf "WGD_PASS=%s\n" "${WGD_PASS}" >> "$env_file"
    printf "WGD_REMOTE_ENDPOINT=%s\n" "${WGD_REMOTE_ENDPOINT}" >> "$env_file"
    printf "WGD_DNS=%s\n" "${WGD_DNS}" >> "$env_file"
    printf "WGD_IPTABLES_DNS=%s\n" "${WGD_IPTABLES_DNS}" >> "$env_file"
    printf "WGD_PEER_ENDPOINT_ALLOWED_IP=%s\n" "${WGD_PEER_ENDPOINT_ALLOWED_IP}" >> "$env_file"
    printf "WGD_KEEP_ALIVE=%s\n" "${WGD_KEEP_ALIVE}" >> "$env_file"
    printf "WGD_MTU=%s\n" "${WGD_MTU}" >> "$env_file"
    printf "WGD_PORT_RANGE_STARTPORT=%s\n" "${WGD_PORT_RANGE_STARTPORT}" >> "$env_file"
	printf "WGD_JC=%s\n" "${WGD_JC}" >> "$env_file"
	printf "WGD_JMIN=%s\n" "${WGD_JMIN}" >> "$env_file"
	printf "WGD_JMAX=%s\n" "${WGD_JMAX}" >> "$env_file"
	printf "WGD_S1=%s\n" "${WGD_S1}" >> "$env_file"
	printf "WGD_S2=%s\n" "${WGD_S2}" >> "$env_file"
	printf "WGD_H1=%s\n" "${WGD_H1}" >> "$env_file"
	printf "WGD_H2=%s\n" "${WGD_H2}" >> "$env_file"
	printf "WGD_H3=%s\n" "${WGD_H3}" >> "$env_file"
	printf "WGD_H4=%s\n" "${WGD_H4}" >> "$env_file"
  else
    echo "Error: Invalid environment type. Use 'docker' or 'regular'."
    return 1
  fi
}
start_core() {
	log_dir="./log"
	printf "%s\n" "$equals"
	# Check if wg0.conf exists in ${WGD_CONF_PATH}
    if [ ! -f "$svr_config" ]; then
		printf "[WGDashboard][Docker] %s Wireguard Configuration Missing, Creating ....\n" "$heavy_checkmark"
		set_proxy
		newconf_wgd
	else
		printf "[WGDashboard][Docker] %s Loading Wireguard Configuartions.\n" "$heavy_checkmark"
	fi
	
	# Re-assign config_files to ensure it includes any newly created configurations
	local config_files=$(find ${WGD_CONF_PATH} -type f -name "*.conf")
	local iptable_dir="/WireGate/iptable-rules"
	# Set file permissions
	find ${WGD_CONF_PATH} -type f -name "*.conf" -exec chmod 600 {} \;
	find "$iptable_dir" -type f -name "*.sh" -exec chmod +x {} \;
	
	# Start WireGuard for each config file
	
	printf "[WGDashboard][Docker] %s Starting Wireguard Configuartions.\n" "$heavy_checkmark"
	printf "%s\n" "$equals"



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

	# Loop over each .conf file in the specified directory
	for file in "$wg_conf_path"/*.conf; do
		# Get the configuration name (without the .conf extension)
		config_name=$(basename "$file" .conf)

		# Extract the IPv6 address from the configuration file
		ipv6_address=$(grep -E 'Address\s*=\s*.*,\s*([a-fA-F0-9:]+)' "$file" | sed -E 's/.*,\s*([a-fA-F0-9:]+)\/.*/\1/')

		# Bring the WireGuard interface up
		echo "Bringing up interface: $config_name" >> "$log_file"
		wg-quick up "$config_name" >> "$log_file" 2>&1

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
start_wgd_debug() {
	printf "%s\n" "$dashes"
	_checkWireguard
	printf "[WGDashboard] Starting WGDashboard in the foreground.\n"
	sudo "$venv_python" "$app_name"
	printf "%s\n" "$dashes"
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
    # Create the master-key directory if it doesn't exist
    if [ ! -d "master-key" ]; then
        mkdir "master-key"
    fi

    # Check if the specified config file exists
    if [ -f "$svr_config" ]; then
        # Check if the master peer with IP 10.0.0.254/32 is already configured
        if grep -q "AllowedIPs = 10.0.0.254/32" "$svr_config"; then
            echo "[WGDashboard][Docker] Master Peer Already Exists, Skipping..."
            return 0
        fi
    fi

    # Function to generate a new peer's public key
    generate_public_key() {
        local private_key="$1"
        echo "$private_key" | wg pubkey
    }

    # Function to generate a new preshared key
    generate_preshared_key() {
        wg genpsk
    }

    # Generate the new peer's private key, public key, and preshared key
    wg_private_key=$(wg genkey)
    peer_public_key=$(generate_public_key "$wg_private_key")
    preshared_key=$(generate_preshared_key)

    # Add the peer to the WireGuard config file with the preshared key
    echo -e "\n[Peer]" >> "$svr_config"
    echo "#Name# = Master Key" >> "$svr_config"
    echo "PublicKey = $peer_public_key" >> "$svr_config"
    echo "PresharedKey = $preshared_key" >> "$svr_config"
    echo "AllowedIPs = 10.0.0.254/32" >> "$svr_config"

    server_private_key=$(grep -E '^PrivateKey' "$svr_config" | awk '{print $NF}')
    svrpublic_key=$(echo "$server_private_key" | wg pubkey)

    # Generate the client config file
    cat <<EOF >"/WireGate/master-key/master.conf"
[Interface]
PrivateKey = $wg_private_key
Address = 10.0.0.254/32
DNS = 10.2.0.100,10.2.0.100
MTU = 1420
Jc = $WGD_JC
Jmin = $WGD_JMIN
Jmax = $WGD_JMAX
S1 = $WGD_S1
S2 = $WGD_S2
H1 = $WGD_H1
H2 = $WGD_H2
H3 = $WGD_H3
H4 = $WGD_H4

[Peer]
PublicKey = $svrpublic_key
AllowedIPs = 0.0.0.0/0
Endpoint = $WGD_REMOTE_ENDPOINT:$WGD_PORT_RANGE_STARTPORT
PersistentKeepalive = 21
PresharedKey = $preshared_key
EOF
}












if [ "$#" != 1 ];
	then
		help
	else
		if [ "$1" = "docker_start" ]; then
				printf "%s\n" "$dashes"
				startwgd_docker 
				printf "%s\n" "$dashes"
			elif [ "$1" = "stop" ]; then
				if check_wgd_status; then
					printf "%s\n" "$dashes"
					stop_wgd
					printf "[WGDashboard] WGDashboard is stopped.\n"
					printf "%s\n" "$dashes"
					else
						printf "%s\n" "$dashes"
						printf "[WGDashboard] WGDashboard is not running.\n"
						printf "%s\n" "$dashes"
				fi
			elif [ "$1" = "update" ]; then
				update_wgd
			elif [ "$1" = "install" ]; then
				printf "%s\n" "$dashes"
				install_wgd
				printf "%s\n" "$dashes"
			elif [ "$1" = "restart" ]; then
				if check_wgd_status; then
					printf "%s\n" "$dashes"
					stop_wgd
					printf "[WGDashboard] WGDashboard is stopped.\n"
					sleep 4
					start_wgd
				else
					start_wgd
				fi
			elif [ "$1" = "debug" ]; then
				if check_wgd_status; then
					printf "[WGDashboard] WGDashboard is already running.\n"
				else
					start_wgd_debug
				fi
			else
				help
		fi
fi