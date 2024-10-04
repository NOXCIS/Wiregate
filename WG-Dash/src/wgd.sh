#!/bin/bash

# wgd.sh - Copyright(C) 2024 Donald Zou [https://github.com/donaldzou]
# Under Apache-2.0 License
#trap "kill $TOP_PID"
export TOP_PID=$$


app_name="dashboard.py"
app_official_name="WGDashboard"
venv_python="./venv/bin/python3"
venv_gunicorn="./venv/bin/gunicorn"
pythonExecutable="python3"
svr_config="/etc/wireguard/ADMINS.conf"

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

_check_and_set_venv(){
    VIRTUAL_ENV="./venv"
    if [ ! -d $VIRTUAL_ENV ]; then
    	printf "[WGDashboard] Creating Python Virtual Environment under ./venv\n"
        { $pythonExecutable -m venv $VIRTUAL_ENV; } >> ./log/install.txt
    fi
    
    if ! $venv_python --version > /dev/null 2>&1
    then
    	printf "[WGDashboard] %s Python Virtual Environment under ./venv failed to create. Halting now.\n" "$heavy_crossmark"	
    	kill  $TOP_PID
    fi
    
    . ${VIRTUAL_ENV}/bin/activate
}

_determineOS(){
  if [ -f /etc/os-release ]; then
      . /etc/os-release
      OS=$ID
  elif [ -f /etc/redhat-release ]; then
      OS="redhat"
  else
      printf "[WGDashboard] %s Sorry, your OS is not supported. Currently the install script only support Debian-based, Red Hat-based OS." "$heavy_crossmark"
      printf "%s\n" "$helpMsg"
      kill  $TOP_PID
  fi
   printf "[WGDashboard] OS: %s\n" "$OS"
}

_installPython(){
	case "$OS" in
		ubuntu|debian)
			{ sudo apt update ; sudo apt-get install -y python3 net-tools; printf "\n\n"; } &>> ./log/install.txt 
		;;
		centos|fedora|redhat|rehl)
			if command -v dnf &> /dev/null; then
				{ sudo dnf install -y python3 net-tools; printf "\n\n"; } >> ./log/install.txt
			else
				{ sudo yum install -y python3 net-tools ; printf "\n\n"; } >> ./log/install.txt
			fi
		;;
		alpine)
			{ apk update; apk add --no-cache python3 net-tools certbot; printf "\n\n"; } &>> ./log/install.txt 
		;;
	esac
	
	if ! python3 --version > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Python is still not installed, halting script now.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
		kill  $TOP_PID
	else
		printf "[WGDashboard] %s Python is installed\n" "$heavy_checkmark"
	fi
}

_installPythonVenv(){
	if [ "$pythonExecutable" = "python3" ]; then
		case "$OS" in
			ubuntu|debian)
				{ sudo apt update ; sudo apt-get install -y python3-venv; printf "\n\n"; } &>> ./log/install.txt
			;;
			centos|fedora|redhat|rhel)
				if command -v dnf &> /dev/null; then
					{ sudo dnf install -y python3-virtualenv; printf "\n\n"; } >> ./log/install.txt
				else
					{ sudo yum install -y python3-virtualenv; printf "\n\n"; } >> ./log/install.txt
				fi
			;;
			alpine)
				{ apk add --no-cache py3-virtualenv; printf "\n\n"; } &>> ./log/install.txt 
			;;
			*)
				printf "[WGDashboard] %s Sorry, your OS is not supported. Currently the install script only support Debian-based, Red Hat-based OS.\n" "$heavy_crossmark"
				printf "%s\n" "$helpMsg"
				kill  $TOP_PID
			;;
		esac
	else
		case "$OS" in
			ubuntu|debian)
				{ sudo apt-get update; sudo apt-get install ${pythonExecutable}-venv;  } &>> ./log/install.txt
			;;
		esac
	fi
	
	if ! $pythonExecutable -m venv -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Python Virtual Environment is still not installed, halting script now.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
	else
		printf "[WGDashboard] %s Python Virtual Environment is installed\n" "$heavy_checkmark"
	fi
}

_installPythonPip(){
	
	if ! $pythonExecutable -m pip -h > /dev/null 2>&1
	then
		case "$OS" in
			ubuntu|debian)
				if [ "$pythonExecutable" = "python3" ]; then
					{ sudo apt update ; sudo apt-get install -y python3-pip; printf "\n\n"; } &>> ./log/install.txt
				else
					{ sudo apt update ; sudo apt-get install -y ${pythonExecutable}-distutil python3-pip; printf "\n\n"; } &>> ./log/install.txt
				fi
			;;
			centos|fedora|redhat|rhel)
				if [ "$pythonExecutable" = "python3" ]; then
					{ sudo dnf install -y python3-pip; printf "\n\n"; } >> ./log/install.txt
				else
					{ sudo dnf install -y ${pythonExecutable}-pip; printf "\n\n"; } >> ./log/install.txt
				fi
			;;
			alpine)
				{ apk add --no-cache py3-pip; printf "\n\n"; } &>> ./log/install.txt 
			;;
			*)
				printf "[WGDashboard] %s Sorry, your OS is not supported. Currently the install script only support Debian-based, Red Hat-based OS.\n" "$heavy_crossmark"
				printf "%s\n" "$helpMsg"
				kill  $TOP_PID
			;;
		esac
    fi
    	
	if ! $pythonExecutable -m pip -h > /dev/null 2>&1
	then
		printf "[WGDashboard] %s Python Package Manager (PIP) is still not installed, halting script now.\n" "$heavy_crossmark"
		printf "%s\n" "$helpMsg"
		kill  $TOP_PID
	else
		printf "[WGDashboard] %s Python Package Manager (PIP) is installed\n" "$heavy_checkmark"
	fi
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

_checkPythonVersion(){
	version_pass=$($pythonExecutable -c 'import sys; print("1") if (sys.version_info.major == 3 and sys.version_info.minor >= 10) else print("0");')
	version=$($pythonExecutable --version)
	if [ $version_pass == "1" ]
	  	then 
			return;
	elif python3.10 --version > /dev/null 2>&1
		then
	 		printf "[WGDashboard] %s Found Python 3.10. Will be using [python3.10] to install WGDashboard.\n" "$heavy_checkmark"
	 		pythonExecutable="python3.10"
	elif python3.11 --version > /dev/null 2>&1
    	 then
    	 	printf "[WGDashboard] %s Found Python 3.11. Will be using [python3.11] to install WGDashboard.\n" "$heavy_checkmark"
    	 	pythonExecutable="python3.11"
    elif python3.12 --version > /dev/null 2>&1
    	 then
    	 	printf "[WGDashboard] %s Found Python 3.12. Will be using [python3.12] to install WGDashboard.\n" "$heavy_checkmark"
    	 	pythonExecutable="python3.12"
	else
		printf "[WGDashboard] %s Could not find a compatible version of Python. Current Python is %s.\n" "$heavy_crossmark" "$version"
		printf "[WGDashboard] WGDashboard required Python 3.10, 3.11 or 3.12. Halting install now.\n"
		kill $TOP_PID
	fi
}

install_wgd(){
    printf "[WGDashboard] Starting to install WGDashboard\n"
    _checkWireguard
    sudo chmod -R 755 /etc/wireguard/
    
    if [ ! -d "log" ]
	  then 
		printf "[WGDashboard] Creating ./log folder\n"
		mkdir "log"
	fi
    _determineOS
    if ! python3 --version > /dev/null 2>&1
    then
    	printf "[WGDashboard] Python is not installed, trying to install now\n"
    	_installPython
    else
    	printf "[WGDashboard] %s Python is installed\n" "$heavy_checkmark"
    fi
    
    _checkPythonVersion
    _installPythonVenv
    _installPythonPip

    if [ ! -d "db" ] 
		then 
			printf "[WGDashboard] Creating ./db folder\n"
			mkdir "db"
    fi
	if [ ! -d "dashboard_config" ] 
		then 
			printf "[WGDashboard] Creating ./dashboard_config folder\n"
			mkdir "dashboard_config"
    fi
    _check_and_set_venv
    printf "[WGDashboard] Upgrading Python Package Manage (PIP)\n"
	{ date; python3 -m ensurepip --upgrade; printf "\n\n"; } >> ./log/install.txt
    { date; python3 -m pip install --no-cache-dir --upgrade pip; printf "\n\n"; } >> ./log/install.txt
    printf "[WGDashboard] Installing latest Python dependencies\n"
    { date; python3 -m pip install --no-cache-dir -r requirements.txt ; printf "\n\n"; } >> ./log/install.txt
	{ date; pip cache purge ; printf "\n\n"; } >> ./log/install.txt
    printf "[WGDashboard] WGDashboard installed successfully!\n"
    printf "[WGDashboard] Enter ./wgd.sh start to start the dashboard\n"
}

check_wgd_status(){
  if test -f "$PID_FILE"; then
    if ps aux | grep -v grep | grep $(cat ./gunicorn.pid)  > /dev/null; then
    return 0
    else
      return 1
    fi
  else
    if ps aux | grep -v grep | grep '[p]ython3 '$app_name > /dev/null; then
      return 0
    else
      return 1
    fi
  fi
}

certbot_create_ssl () {
	certbot certonly --config ./certbot.ini --email "$EMAIL" --work-dir $cb_work_dir --config-dir $cb_config_dir --domain "$SERVERURL"
}

certbot_renew_ssl () {
	certbot renew --work-dir $cb_work_dir --config-dir $cb_config_dir
}

gunicorn_start () {
  printf "%s\n" "$dashes"
  printf "[WGDashboard] Starting WGDashboard with Gunicorn in the background.\n"
  d=$(date '+%Y%m%d%H%M%S')
  if [[ $USER == root ]]; then
    export PATH=$PATH:/usr/local/bin:$HOME/.local/bin
  fi
  _check_and_set_venv
  . .env
	export WGD_IPTABLES_DNS
  sudo "$venv_gunicorn" --config ./gunicorn.conf.py
  sleep 5
  checkPIDExist=0
  while [ $checkPIDExist -eq 0 ]
  do
  		if test -f './gunicorn.pid'; then
  			checkPIDExist=1
  			printf "[WGDashboard] Checking if WGDashboard w/ Gunicorn started successfully\n"
  		fi
  		sleep 2
  done
  printf "[WGDashboard] WGDashboard w/ Gunicorn started successfully\n"
  printf "%s\n" "$dashes"
}

gunicorn_stop () {
	sudo kill $(cat ./gunicorn.pid)
}

start_wgd () {
	_checkWireguard
	set_env regular
    gunicorn_start
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
	printf "[WGDashboard][Docker] %s WGD Docker Started\n" "$heavy_checkmark"
    set_env docker 
    start_core
    gunicorn_start
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
    printf "WGD_WELCOME_SESSION=%s\n" "${WGD_WELCOME_SESSION}" >> "$env_file"
    printf "WGD_REMOTE_ENDPOINT_PORT=%s\n" "${WGD_REMOTE_ENDPOINT_PORT}" >> "$env_file"
    printf "WGD_USER=%s\n" "${WGD_USER}" >> "$env_file"
    printf "WGD_PASS=%s\n" "${WGD_PASS}" >> "$env_file"
    printf "WGD_REMOTE_ENDPOINT=%s\n" "${WGD_REMOTE_ENDPOINT}" >> "$env_file"
    printf "WGD_DNS=%s\n" "${WGD_DNS}" >> "$env_file"
    printf "WGD_IPTABLES_DNS=%s\n" "${WGD_IPTABLES_DNS}" >> "$env_file"
    printf "WGD_PEER_ENDPOINT_ALLOWED_IP=%s\n" "${WGD_PEER_ENDPOINT_ALLOWED_IP}" >> "$env_file"
    printf "WGD_KEEP_ALIVE=%s\n" "${WGD_KEEP_ALIVE}" >> "$env_file"
    printf "WGD_MTU=%s\n" "${WGD_MTU}" >> "$env_file"
    printf "WGD_PORT_RANGE_STARTPORT=%s\n" "${WGD_PORT_RANGE_STARTPORT}" >> "$env_file"

  elif [[ "$env_type" == "regular" ]]; then
    printf "WGD_WELCOME_SESSION=true\n" >> "$env_file"
    printf "WGD_REMOTE_ENDPOINT_PORT=10086\n" >> "$env_file"
    printf "WGD_USER=admin\n" >> "$env_file"
    printf "WGD_PASS=admin\n" >> "$env_file"
    printf "WGD_REMOTE_ENDPOINT=0.0.0.0\n" >> "$env_file"
    printf "WGD_DNS=1.1.1.1\n" >> "$env_file"
    printf "WGD_IPTABLES_DNS=%s\n" "${WGD_IPTABLES_DNS}" >> "$env_file"
    printf "WGD_PEER_ENDPOINT_ALLOWED_IP=0.0.0.0/0\n" >> "$env_file"
    printf "WGD_KEEP_ALIVE=21\n" >> "$env_file"
    printf "WGD_MTU=1420\n" >> "$env_file"
    printf "WGD_PORT_RANGE_STARTPORT=%s\n" "${WGD_PORT_RANGE_STARTPORT}" >> "$env_file"
  else
    echo "Error: Invalid environment type. Use 'docker' or 'regular'."
    return 1
  fi
}


start_core() {
	# Check if wg0.conf exists in /etc/wireguard
    if [ ! -f "$svr_config" ]; then
		printf "[WGDashboard][Docker] %s Wireguard Configuration Missing, Creating ....\n" "$heavy_checkmark"
		set_proxy
		newconf_wgd
	else
		printf "[WGDashboard][Docker] %s Loading Wireguard Configuartions.\n" "$heavy_checkmark"
	fi
	# Re-assign config_files to ensure it includes any newly created configurations
	local config_files=$(find /etc/wireguard -type f -name "*.conf")
	local iptable_dir="/opt/wireguarddashboard/src/iptable-rules"
	# Set file permissions
	find /etc/wireguard -type f -name "*.conf" -exec chmod 600 {} \;
	find "$iptable_dir" -type f -name "*.sh" -exec chmod +x {} \;
	
	# Start WireGuard for each config file
  printf "[WGDashboard][Docker] %s Starting Wireguard Configuartions.\n" "$heavy_checkmark"
  printf "%s\n" "$dashes"
  set_proxy
	for file in $config_files; do
		config_name=$(basename "$file" ".conf")  
		wg-quick up "$config_name"
	done
}


start_wgd_debug() {
	printf "%s\n" "$dashes"
	_checkWireguard
	printf "[WGDashboard] Starting WGDashboard in the foreground.\n"
	sudo "$venv_python" "$app_name"
	printf "%s\n" "$dashes"
}

update_wgd() {
	_determineOS
	if ! python3 --version > /dev/null 2>&1
	then
		printf "[WGDashboard] Python is not installed, trying to install now\n"
		_installPython
	else
		printf "[WGDashboard] %s Python is installed\n" "$heavy_checkmark"
	fi
	
	_checkPythonVersion
	_installPythonVenv
	_installPythonPip	
	
	new_ver=$($venv_python -c "import json; import urllib.request; data = urllib.request.urlopen('https://api.github.com/repos/donaldzou/WGDashboard/releases/latest').read(); output = json.loads(data);print(output['tag_name'])")
	printf "%s\n" "$dashes"
	printf "[WGDashboard] Are you sure you want to update to the %s? (Y/N): " "$new_ver"
	read up
	if [ "$up" = "Y" ] || [ "$up" = "y" ]; then
		printf "[WGDashboard] Shutting down WGDashboard\n"
		if check_wgd_status; then
			stop_wgd
		fi
		mv wgd.sh wgd.sh.old
		printf "[WGDashboard] Downloading %s from GitHub..." "$new_ver"
		{ date; git stash; git pull https://github.com/donaldzou/WGDashboard.git $new_ver --force; } >> ./log/update.txt
		chmod +x ./wgd.sh
		sudo ./wgd.sh install
		printf "[WGDashboard] Update completed!\n"
		printf "%s\n" "$dashes"
		rm wgd.sh.old
	else
		printf "%s\n" "$dashes"
		printf "[WGDashboard] Update Canceled.\n"
		printf "%s\n" "$dashes"
	fi
}


newconf_wgd () {
  newconf_wgd0
  newconf_wgd1
  newconf_wgd2
  newconf_wgd3
  return
}

set_proxy () {
    if [[ "$WGD_TOR_PROXY" == "true" ]]; then
        postType="tor-post"
    elif [[ "$WGD_TOR_PROXY" == "false" ]]; then
        postType="post"
    fi

AMDpostup="/opt/wireguarddashboard/src/iptable-rules/Admins/${postType}up.sh"
GSTpostup="/opt/wireguarddashboard/src/iptable-rules/Members/${postType}up.sh"
LANpostup="/opt/wireguarddashboard/src/iptable-rules/Guest/${postType}up.sh"
MEMpostup="/opt/wireguarddashboard/src/iptable-rules/LAN-only-users/postup.sh"

AMDpostdown="/opt/wireguarddashboard/src/iptable-rules/Admins/${postType}down.sh"
GSTpostdown="/opt/wireguarddashboard/src/iptable-rules/Members/${postType}down.sh"
LANpostdown="/opt/wireguarddashboard/src/iptable-rules/Guest/${postType}down.sh"
MEMpostdown="/opt/wireguarddashboard/src/iptable-rules/LAN-only-users/postdown.sh"

}



newconf_wgd0() {
    local port_wg0=$WGD_PORT_RANGE_STARTPORT
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)
    cat <<EOF >"/etc/wireguard/ADMINS.conf"
[Interface]
PrivateKey = $private_key
Address = 10.0.0.1/24
ListenPort = $port_wg0
SaveConfig = true
PostUp =  $AMDpostup
PreDown = $AMDpostdown

EOF

        make_master_config
}


newconf_wgd1() {
    local port_wg1=$WGD_PORT_RANGE_STARTPORT
    local port_wg1=$((port_wg1 + 1))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/MEMBERS.conf"
[Interface]
PrivateKey = $private_key
Address = 192.168.10.1/24
ListenPort = $port_wg1
SaveConfig = true
PostUp =  $MEMpostup
PreDown = $MEMpostdown

EOF
}

newconf_wgd2() {
    local port_wg2=$WGD_PORT_RANGE_STARTPORT
    local port_wg2=$((port_wg2 + 2))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/LANP2P.conf"
[Interface]
PrivateKey = $private_key
Address = 172.16.0.1/24
ListenPort = $port_wg2
SaveConfig = true
PostUp =  $LANpostup
PreDown = $LANpostdown

EOF
}

newconf_wgd3() {
    local port_wg3=$WGD_PORT_RANGE_STARTPORT
    local port_wg3=$((port_wg3 + 3))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/GUESTS.conf"
[Interface]
PrivateKey = $private_key
Address = 192.168.20.1/24
ListenPort = $port_wg3
SaveConfig = true
PostUp =  $GSTpostup
PreDown = $GSTpostdown

EOF
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
            
            
            { date; python3 -m pip install --upgrade pip; printf "\n\n"; } >> ./log/install.txt
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
    cat <<EOF >"/opt/wireguarddashboard/src/master-key/master.conf"
[Interface]
PrivateKey = $wg_private_key
Address = 10.0.0.254/32
DNS = 10.2.0.100,10.2.0.100
MTU = 1420

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
		if [ "$1" = "start" ]; then
			if check_wgd_status; then
				printf "%s\n" "$dashes"
				printf "[WGDashboard] WGDashboard is already running.\n"
				printf "%s\n" "$dashes"
				else
					start_wgd
			fi
			elif [ "$1" = "docker_start" ]; then
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