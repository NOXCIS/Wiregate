#!/bin/bash

# wgd.sh - Copyright(C) 2024 Donald Zou [https://github.com/donaldzou]
# Under Apache-2.0 License
app_name="dashboard.py"
app_official_name="WGDashboard"
venv_python="./venv/bin/python3"
venv_gunicorn="./venv/bin/gunicorn"

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
        { python3 -m venv --system-site-packages $VIRTUAL_ENV; } >> ./log/install.txt
    fi
    printf "[WGDashboard] Activate Python Virtual Environment under ./venv\n"
    . ${VIRTUAL_ENV}/bin/activate
}

_determineOS() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/redhat-release ]; then
        OS="redhat"
    elif [ -f /etc/alpine-release ]; then
        OS="alpine"
    else
        printf "[WGDashboard] Sorry, your OS is not supported. Currently, the install script only supports Debian-based, Red Hat-based, and Alpine OS.\n"
        printf "%s\n" "$helpMsg"
        exit 1
    fi
}


_installPython() {
    case "$OS" in
        ubuntu|debian)
            { apt update; apt-get install -y python3; printf "\n\n"; } &>> ./log/install.txt
        ;;
        centos|fedora|redhat)
            if command -v dnf &> /dev/null; then
                { dnf install -y python3; printf "\n\n"; } >> ./log/install.txt
            else
                { yum install -y python3; printf "\n\n"; } >> ./log/install.txt
            fi
        ;;
        alpine)
            { apk add --no-cache python3; printf "\n\n"; } &>> ./log/install.txt
        ;;
        *)
            printf "[WGDashboard] Sorry, your OS is not supported. Currently, the install script only supports Debian-based, Red Hat-based, and Alpine OS.\n"
            printf "%s\n" "$helpMsg"
            exit 1
        ;;
    esac
    
    if ! python3 --version > /dev/null 2>&1; then
        printf "[WGDashboard] Python is still not installed, halting script now.\n"
        printf "%s\n" "$helpMsg"
        exit 1
    else
        printf "[WGDashboard] \xE2\x9C\x94 Python is installed\n"
    fi
}


_installPythonVenv(){
	case "$OS" in
		ubuntu|debian)
			{
				apt update 
				apt-get install -y python3-venv
				printf "\n\n"
			} &>> ./log/install.txt 
			;;
		centos|fedora|redhat)
			if command -v dnf &> /dev/null; then
				{
					dnf install -y python3-virtualenv
					printf "\n\n"
				} >> ./log/install.txt
			else
				{
					yum install -y python3-virtualenv
					printf "\n\n"
				} >> ./log/install.txt
			fi
			;;
		alpine)
			{
				apk update
				apk add --no-cache python3 py3-virtualenv
				printf "\n\n"
			} >> ./log/install.txt
			;;
		*)
			printf "[WGDashboard] Sorry, your OS is not supported. Currently the install script only supports Debian-based, Red Hat-based, and Alpine OS.\n"
			printf "%s\n" "$helpMsg"
			exit 1
			;;
	esac
	
	if ! python3 -m venv -h > /dev/null 2>&1
	then
		printf "[WGDashboard] Python Virtual Environment is still not installed, halting script now.\n"
		printf "%s\n" "$helpMsg"
		exit 1
	else
		printf "[WGDashboard] \xE2\x9C\x94 Python Virtual Environment is installed\n"
	fi
}


_installPythonPip() {
    case "$OS" in
        ubuntu|debian)
            { apt update; apt-get install -y python3-pip; printf "\n\n"; } &>> ./log/install.txt
        ;;
        centos|fedora|redhat)
            if command -v dnf &> /dev/null; then
                { dnf install -y python3-pip; printf "\n\n"; } >> ./log/install.txt
            else
                { yum install -y python3-pip; printf "\n\n"; } >> ./log/install.txt
            fi
        ;;
        alpine)
            { apk add --no-cache py3-pip; printf "\n\n"; } &>> ./log/install.txt
        ;;
        *)
            printf "[WGDashboard] Sorry, your OS is not supported for auto install. Currently, the install script only supports Debian-based, Red Hat-based, and Alpine OS.\n"
            printf "%s\n" "$helpMsg"
            exit 1
        ;;
    esac

    if ! python3 -m pip -h > /dev/null 2>&1; then
        printf "[WGDashboard] Python Package Manager (PIP) is still not installed, halting script now.\n"
        printf "%s\n" "$helpMsg"
        exit 1
    else
        printf "[WGDashboard] \xE2\x9C\x94 Python Package Manager (PIP) is installed\n"
    fi
}


_checkWireguard(){
	if ! wg -h > /dev/null 2>&1
	then
		printf "[WGDashboard] WireGuard is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n"
		exit 1
	fi
	if ! wg-quick -h > /dev/null 2>&1
	then
		printf "[WGDashboard] WireGuard is not installed. Please follow instruction on https://www.wireguard.com/install/ to install. \n"
		exit 1
	fi
}

install_wgd(){
    printf "[WGDashboard] Starting to install WGDashboard\n"
    _checkWireguard
     chmod -R 755 /etc/wireguard/
    
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
    	printf "[WGDashboard] \xE2\x9C\x94 Python is installed\n"
    fi
    _installPythonVenv
    _installPythonPip
  
    version_pass=$(python3 -c 'import sys; print("1") if (sys.version_info.major == 3 and sys.version_info.minor >= 10) else print("0");')
    if [ $version_pass == "0" ]
      then 
        printf "[WGDashboard] WGDashboard required Python 3.7 or above\n"
        exit 1
    fi

    if [ ! -d "db" ] 
      then 
        printf "[WGDashboard] Creating ./db folder\n"
        mkdir "db"
    fi
    _check_and_set_venv
    printf "[WGDashboard] Upgrading Python Package Manage (PIP)\n"
    { date; python3 -m pip install --upgrade pip; printf "\n\n"; } >> ./log/install.txt
    printf "[WGDashboard] Installing latest Python dependencies\n"
    { date; python3 -m pip install -r requirements.txt ; printf "\n\n"; } >> ./log/install.txt
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

zone_setup () {
  local config_files=$(find /etc/wireguard -type f -name "*.conf")
  local iptable_dir="/home/app/Iptables/fowarding-rules"

  newconf_wgd
    find /etc/wireguard -type f -name "*.conf" -exec chmod 600 {} \;
    find "$iptable_dir" -type f -name "*.sh" -exec chmod +x {} \;
  
  
      for file in $config_files; do
        config_name=$(basename "$file" ".conf")
        { date; wg-quick up "$config_name"; printf "\n\n"; } >> ./log/install.txt 2>&1
      done
}

gunicorn_start () {
  printf "%s\n" "$dashes"
  printf "[WGDashboard] Starting WGDashboard with Gunicorn in the background.\n"
  d=$(date '+%Y%m%d%H%M%S')

  is_alpine() {
    grep -q "Alpine" /etc/os-release 2>/dev/null
  }
  if [[ $USER == root ]]; then
    if is_alpine; then
      export PATH=$PATH:/usr/local/bin:$HOME/.local/bin:/sbin:/usr/sbin
    else
      export PATH=$PATH:/usr/local/bin:$HOME/.local/bin
    fi
  fi

  _check_and_set_venv
  
  if [ ! -x "$venv_gunicorn" ]; then
    printf "[ERROR] Gunicorn executable not found or not executable.\n"
    return 1
  fi

  zone_setup

  gunicorn -c ./gunicorn.conf.py 
  # line below exsits after execution when using docker
  #"$venv_gunicorn" --config ./gunicorn.conf.py &

  sleep 5
  
  checkPIDExist=0
  while [ $checkPIDExist -eq 0 ]; do
    if test -f './gunicorn.pid'; then
      checkPIDExist=1
      printf "[WGDashboard] Checking if WGDashboard w/ Gunicorn started successfully\n"
    else
      printf "[INFO] Waiting for Gunicorn PID file to be created...\n"
    fi
    sleep 2
  done

  printf "[WGDashboard] WGDashboard w/ Gunicorn started successfully\n"
  printf "%s\n" "$dashes"
}

gunicorn_stop () {
   kill $(cat ./gunicorn.pid)
}

start_wgd () {
	_checkWireguard
  zone_setup
    gunicorn_start
}

stop_wgd() {
  if test -f "$PID_FILE"; then
    gunicorn_stop
  else
    kill "$(ps aux | grep "[p]ython3 $app_name" | awk '{print $2}')"
  fi
}

start_wgd_debug() {
  printf "%s\n" "$dashes"
  zone_setup
  _checkWireguard
  printf "[WGDashboard] Starting WGDashboard in the foreground.\n"
   "$venv_python" "$app_name"
  printf "%s\n" "$dashes"
}

update_wgd() {
  new_ver=$(python3 -c "import json; import urllib.request; data = urllib.request.urlopen('https://api.github.com/repos/donaldzou/WGDashboard/releases/latest').read(); output = json.loads(data);print(output['tag_name'])")
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
     ./wgd.sh install
    printf "[WGDashboard] Update completed!\n"
    printf "%s\n" "$dashes"
    rm wgd.sh.old
  else
    printf "%s\n" "$dashes"
    printf "| Update Canceled.                                         |\n"
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


newconf_wgd0() {
    local port_wg0=$WG_DASH_PORT_RANGE_STARTPORT
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)
    cat <<EOF >"/etc/wireguard/ADMINS.conf"
[Interface]
PrivateKey = $private_key
Address = 10.0.0.1/24
ListenPort = $port_wg0
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/Admins/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/Admins/postdown.sh

EOF
    if [ ! -f "/master-key/master.conf" ]; then
        make_master_config  # Only call make_master_config if master.conf doesn't exist
    fi 
}


newconf_wgd1() {
    local port_wg1=$WG_DASH_PORT_RANGE_STARTPORT
    local port_wg1=$((port_wg1 + 1))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/MEMBERS.conf"
[Interface]
PrivateKey = $private_key
Address = 192.168.10.1/24
ListenPort = $port_wg1
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/Members/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/Members/postdown.sh

EOF
}

newconf_wgd2() {
    local port_wg2=$WG_DASH_PORT_RANGE_STARTPORT
    local port_wg2=$((port_wg2 + 2))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/LANP2P.conf"
[Interface]
PrivateKey = $private_key
Address = 172.16.0.1/24
ListenPort = $port_wg2
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/LAN-only-users/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/LAN-only-users/postdown.sh

EOF
}

newconf_wgd3() {
    local port_wg3=$WG_DASH_PORT_RANGE_STARTPORT
    local port_wg3=$((port_wg3 + 3))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/GUESTS.conf"
[Interface]
PrivateKey = $private_key
Address = 192.168.20.1/24
ListenPort = $port_wg3
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/Guest/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/Guest/postdown.sh

EOF
}


make_master_config() {
        local svr_config="/etc/wireguard/ADMINS.conf"
        # Check if the specified config file exists
        if [ ! -f "$svr_config" ]; then
            echo "Error: Config file $svr_config not found."
            exit 1
        fi


        #Function to generate a new peer's public key
        generate_public_key() {
            local private_key="$1"
            echo "$private_key" | wg pubkey
        }

        # Function to generate a new preshared key
        generate_preshared_key() {
            wg genpsk
        }   



    # Generate the new peer's public key, preshared key, and allowed IP
    wg_private_key=$(wg genkey)
    peer_public_key=$(generate_public_key "$wg_private_key")
    preshared_key=$(generate_preshared_key)

    # Add the peer to the WireGuard config file with the preshared key
    echo -e "\n[Peer]" >> "$svr_config"
    echo "PublicKey = $peer_public_key" >> "$svr_config"
    echo "PresharedKey = $preshared_key" >> "$svr_config"
    echo "AllowedIPs = 10.0.0.254/32" >> "$svr_config"


    server_public_key=$(grep -E '^PrivateKey' "$svr_config" | awk '{print $NF}')
    svrpublic_key=$(echo "$server_public_key" | wg pubkey)


    # Generate the client config file
    cat <<EOF >"/home/app/master-key/master.conf"
[Interface]
PrivateKey = $wg_private_key
Address = 10.0.0.254/32
DNS = 10.2.0.100,10.2.0.100
MTU = 1420

[Peer]
PublicKey = $svrpublic_key
AllowedIPs = 0.0.0.0/0
Endpoint = $WG_DASH_SERVER_IP:$WG_DASH_PORT_RANGE_STARTPORT
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
           printf "| WGDashboard is stopped.                                  |\n"
           sleep 4
           start_wgd
        else
          start_wgd
        fi
      elif [ "$1" = "debug" ]; then
        if check_wgd_status; then
          printf "| WGDashboard is already running.                          |\n"
          else
            start_wgd_debug
        fi
      else
        help
    fi
fi
