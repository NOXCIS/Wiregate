#!/bin/bash

echo '  





 █     █░ ▒█████   ██▀███   ███▄ ▄███▓ ██░ ██  ▒█████   ██▓    ▓█████ 
▓█░ █ ░█░▒██▒  ██▒▓██ ▒ ██▒▓██▒▀█▀ ██▒▓██░ ██▒▒██▒  ██▒▓██▒    ▓█   ▀ 
▒█░ █ ░█ ▒██░  ██▒▓██ ░▄█ ▒▓██    ▓██░▒██▀▀██░▒██░  ██▒▒██░    ▒███   
░█░ █ ░█ ▒██   ██░▒██▀▀█▄  ▒██    ▒██ ░▓█ ░██ ▒██   ██░▒██░    ▒▓█  ▄ 
░░██▒██▓ ░ ████▓▒░░██▓ ▒██▒▒██▒   ░██▒░▓█▒░██▓░ ████▓▒░░██████▒░▒████▒
░ ▓░▒ ▒  ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░░ ▒░   ░  ░ ▒ ░░▒░▒░ ▒░▒░▒░ ░ ▒░▓  ░░░ ▒░ ░
  ▒ ░ ░    ░ ▒ ▒░   ░▒ ░ ▒░░  ░      ░ ▒ ░▒░ ░  ░ ▒ ▒░ ░ ░ ▒  ░ ░ ░  ░
  ░   ░  ░ ░ ░ ▒    ░░   ░ ░      ░    ░  ░░ ░░ ░ ░ ▒    ░ ░      ░   
 ▄▄▄▄ ▓██   ██▓░   ███▄    █  ▒█████  ▒██ ░ ██▒ ▄████▄   ██▓  ██████ ░
▓█████▄▒██  ██▒    ██ ▀█   █ ▒██▒  ██▒▒▒ █ █ ▒░▒██▀ ▀█  ▓██▒▒██    ▒  
▒██▒ ▄██▒██ ██░   ▓██  ▀█ ██▒▒██░  ██▒░░  █   ░▒▓█    ▄ ▒██▒░ ▓██▄    
▒██░█▀  ░ ▐██▓░   ▓██▒  ▐▌██▒▒██   ██░ ░ █ █ ▒ ▒▓▓▄ ▄██▒░██░  ▒   ██▒ 
░▓█  ▀█▓░ ██▒▓░   ▒██░   ▓██░░ ████▓▒░▒██▒ ▒██▒▒ ▓███▀ ░░██░▒██████▒▒ 
░▒▓███▀▒ ██▒▒▒    ░ ▒░   ▒ ▒ ░ ▒░▒░▒░ ▒▒ ░ ░▓ ░░ ░▒ ▒  ░░▓  ▒ ▒▓▒ ▒ ░ 
▒░▒   ░▓██ ░▒░    ░ ░░   ░ ▒░  ░ ▒ ▒░ ░░   ░▒ ░  ░  ▒    ▒ ░░ ░▒  ░ ░ 
 ░    ░▒ ▒ ░░        ░   ░ ░ ░ ░ ░ ▒   ░    ░  ░         ▒ ░░  ░  ░   
 ░     ░ ░                 ░     ░ ░   ░    ░  ░ ░       ░        ░   
      ░░ ░                                     ░                      

                  Setup Script & Dockerization by 
                      Shamar Lee A.K.A NOXCIS

                              Thanks to

                    @donaldzou for WGDashboard
                  @klutchell for UnBound Config



'
sleep 5s

sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update
sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade



function check_docker_compose {
  local yml_file="docker-compose.yml"

  if [ -f "$(dirname "$0")/$yml_file" ]; then
    echo "Removing existing '$yml_file'..."
    rm "$(dirname "$0")/$yml_file"
    echo "Existing '$yml_file' removed."
  fi

  echo "Pulling '$yml_file' from GitHub..."
  curl -o "$(dirname "$0")/$yml_file" https://raw.githubusercontent.com/NOXCIS/Worm-Hole/nginx-%2B%2B/docker-compose.yml
  echo "File '$yml_file' successfully pulled from GitHub."
}

function disable_docker_iptables {
  # Check if Docker is installed
  if ! command -v docker > /dev/null 2>&1; then
    echo "Docker is not installed."
    return 1
  fi

  # Disable Docker iptables
  DOCKER_CONFIG="/etc/docker/daemon.json"
  if [[ -f "$DOCKER_CONFIG" ]]; then
    # Check if iptables configuration exists in daemon.json
    if grep -q '"iptables": false' "$DOCKER_CONFIG"; then
      echo "Docker iptables is already disabled."
      return 0
    fi

    # Disable iptables in daemon.json
    sed -i 's/\("iptables":\s*\)true/\1false/' "$DOCKER_CONFIG"
    echo "Docker iptables has been disabled. Restarting Docker daemon..."

    # Restart Docker daemon
    systemctl restart docker
    return $?
  else
    echo "Docker configuration file ($DOCKER_CONFIG) not found."
    return 1
  fi
}



function set_tz {
    local yml_file="docker-compose.yml"
    read -t 5 -p "Do you want to automatically get the host timezone? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    echo ""
    echo ""
    if [[ $answer == [Yy] || -z $answer ]]; then
        timezone=$(cat /etc/timezone)
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        
    else
        read -p "Enter timezone $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)America/New_York$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " timezone
        echo ""
        if [[ -z $timezone ]]; then
            timezone="America/New_York"
        fi
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        
    fi
    sed -i "s|TZ:.*|TZ: \"$timezone\"|" "$yml_file"
    echo ""
}


function update_server_ip() {
  local yml_file="docker-compose.yml"
  local ip

  read -t 5 -p "Do you want to automatically set the server IP address? $(tput setaf 1)(y/n)$(tput sgr0) " auto_ip
  echo ""
  echo ""
  if [[ $auto_ip =~ ^[Nn]$ ]]; then
    read -p "Please enter the server IP address $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)127.0.0.1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " ip
    ip=${ip:-127.0.0.1}
    echo ""
  else
    ip=$(hostname -I | awk '{print $1}')
  fi

  if [[ -f "$yml_file" ]]; then
    sed -i "s/SERVER_IP=.*/SERVER_IP=$ip/" "$yml_file"
    echo -e "Server IP address has been set to \033[32m$ip\033[0m"
    echo ""
  else
    echo "$yml_file not found."
  fi
}

function set_password {
    local yml_file="docker-compose.yml"
    local password=""
    local confirm_password=""
    local timer=5
    local user_activity=false

    # Wait for 5 seconds or until user activity is detected
    sleep $timer & PID=$!
    while true; do
        read -t 1 -n 1 && user_activity=true && break || true
        if ! ps -p $PID > /dev/null; then
            # Timer has expired and no user activity detected
            password=""
            echo ""
            sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
            echo -e "\033[31mNo user activity detected. Password has been set to null.\033[0m"
            echo ""
            break
        fi
    done

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Pihole Dashboard:$(tput sgr0)" password 
            echo ""
            echo ""

            if [[ -z "$password" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi

            read -sp "$(tput setaf 3)Confirm password for Pihole Dashboard:$(tput sgr0) " confirm_password
            echo ""
            echo ""

            if [[ "$password" != "$confirm_password" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, update the yml_file and exit the loop
                sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
                echo -e "\033[32mPASSWORD HAS BEEN SET\033[0m"
                echo ""
                break
            fi
        done
    fi
}


function config_count() {
  local yml_file="docker-compose.yml"
  local count=""
  read -t 10 -p "Enter # of WireGuard server configurations to generate $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " count
  echo ""
  echo ""
  if [[ -z "$count" ]]; then
    count=1
  fi
  sed -i "s/CONFIG_CT=.*/CONFIG_CT=$count/" "$yml_file"
  echo -e "WireGuard Server Configurations to be Generated has been set to \033[32m$count\033[0m"
  echo ""
}




#set -e
export DEBIAN_FRONTEND=noninteractive

# List of prerequisites
PREREQUISITES=(
    docker
    docker-compose
    curl
    git
    apt-transport-https
    ca-certificates
    gnupg
    gnupg-agent
    software-properties-common
    openssl
    firewalld
)

# Define ANSI color codes
GREEN=$(tput setaf 2)
RESET=$(tput sgr0)

# Check if each prerequisite is already installed
for prerequisite in "${PREREQUISITES[@]}"
do
    if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
        echo "${GREEN}$prerequisite is not installed. Installing...${RESET}"
        sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install "$prerequisite"
    else
        echo "${GREEN}$prerequisite is already installed. Skipping...${RESET}"
    fi
done

# Check if docker-compose is already installed
if ! command -v docker > /dev/null 2>&1; then
    echo "${GREEN}docker is not installed. Installing...${RESET}"
    # Install docker-compose
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
        "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo "${GREEN}docker is already installed. Skipping...${RESET}"
fi

check_docker_compose &&

clear

echo -e "\033[33m\n"
echo "#######################################################################"
echo ""
echo "                 SET TIMEZONE AND DASHBOARD PASSWORD"
echo ""
echo "              Input Prompt will timeout after 5s & 10s "
echo ""
echo "   The Time Zone will be set Automatically and The password left blank"
echo "                    When a timeout event occours"
echo ""
echo "#######################################################################"
echo -e "\n\033[0m"
sleep 0.1s

      set_tz &&
      sleep 0.1s
      echo ""
      echo "Enter password for Pihole Dashboard $(tput setaf 1)(Press enter to set password or wait 5 seconds for no password): $(tput sgr0)"  
      set_password &&
              sleep 0.1s




echo -e "\033[33m\n" 
echo "#######################################################################"
echo ""
echo "           SETTING SERVER IP & SERVER CONFIG FOR WIREGUARD"
echo ""
echo "                Input Prompt will timeout after 5s "
echo ""
echo "  The Server IP will be set Automatically and The Config Count set to 1"
echo "                    When a timeout event occours"
echo ""
echo "#######################################################################"
echo -e "\n\033[0m"
sleep 0.1s

      update_server_ip &&
      config_count &&
      set_nginx_Db &&
              sleep 0.1s
              
clear

systemctl enable --now firewalld &&
firewall-cmd --state &&
disable_docker_iptables &&

#Restart Docker
systemctl restart docker &&


# Masquerading allows for docker ingress and egress (this is the juicy bit)
firewall-cmd --zone=public --add-masquerade --permanent &&
# Reload firewall to apply permanent rules
firewall-cmd --reload &&

# Show interfaces to find out docker interface name
ip link show &&

# Assumes docker interface is docker0
firewall-cmd --permanent --zone=trusted --add-interface=docker0 &&
firewall-cmd --reload &&
systemctl restart docker &&


firewall-cmd --permanent --zone=public --add-interface=eth0 &&
firewall-cmd --reload &&


firewall-cmd --permanent --zone=public --add-port=9000/tcp
firewall-cmd --permanent --zone=public --add-port=10086/tcp
# Reload firewall to apply permanent rules
firewall-cmd --reload

#Uncomment to review the compose file before build.
#nano docker-compose.yml 


docker-compose up -d --build  &&



# Check if a swapfile already exists
if [[ -f /swapfile ]]; then
    echo "Swapfile already exists."
    exit 1
fi

# Create a swapfile
sudo fallocate -l 2G /swapfile

# Set permissions for the swapfile
sudo chmod 600 /swapfile

# Set up the swap space
sudo mkswap /swapfile

# Enable the swapfile
sudo swapon /swapfile

# Update the fstab file to make the swapfile persistent across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

echo "Swapfile created and enabled."

sleep 1s
#rm docker-compose.yml
