#!/bin/bash


sudo apt-get update -y && sudo apt-get upgrade -y

function set_tz {
    local yml_file="docker-compose.yml"
    read -t 5 -p "Do you want to automatically get the host timezone? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    echo ""
    echo ""
    if [[ $answer == [Yy] || -z $answer ]]; then
        timezone=$(cat /etc/timezone)
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        
    else
        read -t 5 -p "Enter timezone $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)America/New_York$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " timezone
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

  read -t 10 -p "Do you want to automatically set the server IP address? $(tput setaf 1)(y/n)$(tput sgr0) " auto_ip
  echo ""
  echo ""
  if [[ $auto_ip =~ ^[Nn]$ ]]; then
    read -t 10 -p "Please enter the server IP address $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)127.0.0.1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " ip
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
    
    # Set a timeout of 10 seconds for user input
    trap 'password=""' USR1
    read -t 10 -sp "Enter password for Pihole Dashboard $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)No Password$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " password 
    echo ""
    echo ""
    sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
    echo -e "\033[32mPASSWORD HAS BEEN SET\033[0m"
    echo ""
}


function config_count() {
  local yml_file="docker-compose.yml"

  if [[ -f "$yml_file" ]]; then
    local count=""
    
    # Set a timeout of 5 seconds for user input
    count=$(timeout 5 bash -c 'read -e -p "Enter # of WireGuard server configurations to generate $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " count && echo "$count"')
    
    count=${count:-1} # set count to 1 if user enters nothing
    sed -i "s/CONFIG_CT=.*/CONFIG_CT=$count/" "$yml_file"
    echo -e "WireGuard Server Configurations to be Generated has been set to \033[32m$count\033[0m"
    echo ""
  else
    echo "$yml_file not found."

  fi
}


set -e

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
)

#!/bin/bash

# Define ANSI color codes
GREEN=$(tput setaf 2)
RESET=$(tput sgr0)

# Update package manager
echo "${GREEN}Updating package manager...${RESET}"
sudo apt-get update -yqq

# Check if each prerequisite is already installed
PREREQUISITES=("git" "curl" "wget" "jq" "gnupg2" "python3-pip")
for prerequisite in "${PREREQUISITES[@]}"
do
    if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
        echo "${GREEN}$prerequisite is not installed. Installing...${RESET}"
        sudo apt-get install -yqq "$prerequisite"
    else
        echo "${GREEN}$prerequisite is already installed. Skipping...${RESET}"
    fi
done

# Check for outdated libraries
if ldconfig -p | grep -qE 'libssl.*(1.0.|1.1.[0-9])'; then
    echo "${GREEN}The following libraries are outdated:${RESET}"
    ldconfig -p | grep -E 'libssl.*(1.0.|1.1.[0-9])'
    echo "${GREEN}Restarting services that use these libraries...${RESET}"
    systemctl --no-pager list-units --type service | awk '{print $1}' | xargs systemctl restart
    echo "${GREEN}Services restarted.${RESET}"
else
    echo "${GREEN}No outdated libraries found.${RESET}"
fi



clear

echo -e "\033[33m\n"
echo "#######################################################################"
echo ""
echo "                        INSTALLING PORTAINER"
echo "                        RUNNING ON PORT :9000"
echo ""
echo "#######################################################################"
echo -e "\n\033[0m"
sleep 1s

   #docker rm -f portainer
if docker ps -a | grep portainer ; then
    echo "" 
    echo -e "\033[32mPortainer is already running\033[0m"
else
    echo -e "\033[31mPortainer is not running, creating data volume and starting container\033[0m" "\n"
    echo -e "\033[32m$(docker volume create portainer_data)\033[0m" "\n"
    echo -e "\033[32m$(docker run -d -p 8000:8000 -p 9000:9000 --name=portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce)\033[0m" "\n"
fi
echo ""
echo ""  
              sleep 1s
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
sleep 0.5s

      set_tz &&
      set_password &&
              sleep 2s

clear


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
sleep 0.5s

      update_server_ip &&
      config_count &&
              sleep 2s
              
clear

echo -e "\033[33m\n"   
echo "#######################################################################"
echo ""
echo ""
echo "                        REVIEW COMPOSE FILE"
echo ""
echo ""
echo "#######################################################################"
echo -e "\n\033[0m"
sleep 2s

#Uncomment to review the compose file before build.
# nano docker-compose.yml 

docker-compose up -d --build  &&

sleep 1s
