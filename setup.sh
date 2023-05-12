#!/bin/bash
sleep 2s

function update_server_ip() {
  local yml_file="docker-compose.yml"
  local ip

  read -p "Do you want to automatically get the server IP address? $(tput setaf 1)(y/n)$(tput sgr0) " auto_ip
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

function config_count() {
  local yml_file="docker-compose.yml"

  if [[ -f "$yml_file" ]]; then
                                                                   
    read -p "Enter # of WireGuard server configurations to generate  $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " count
    count=${count:-1} # set count to 1 if user enters nothing
    sed -i "s/CONFIG_CT=.*/CONFIG_CT=$count/" "$yml_file"
    echo ""
    echo -e "WireGuard Server Configurations to be Generated has been set to \033[32m$count\033[0m"
    echo ""
  else
    echo "$yml_file not found."

  fi
}



function set_password_and_tz {
    local yml_file="docker-compose.yml"
    read -p "Do you want to automatically get the host timezone? $(tput setaf 1)(y/n)$(tput sgr0) " answer
    echo ""
    if [[ $answer == [Yy] ]]; then
        timezone=$(cat /etc/timezone)
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        echo ""
    else
        #read -p "Enter timezone ($(tput setaf 1)Press enter for default: America/New_York$(tput sgr0)): " timezone
        read -p "Enter timezone $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)America/New_York$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " timezone

        echo ""
        timezone=${timezone:-"America/New_York"} # set timezone to America/New_York if user enters nothing
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        echo ""
    fi
    sed -i "s|TZ:.*|TZ: \"$timezone\"|" "$yml_file"
    read -sp "Enter password for Pihole Dashboard $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)No Password$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " password && echo -e "\n"
    sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
    echo -e "\033[32mPASSWORD HAS BEEN SET\033[0m"
    echo ""


}


set -e

# List of prerequisites
PREREQUISITES=(
    docker
    curl
    git
    apt-transport-https
    ca-certificates
    gnupg-agent
    software-properties-common
)

# Define ANSI color codes
GREEN=$(tput setaf 2)
RESET=$(tput sgr0)

# Check if each prerequisite is already installed
for prerequisite in "${PREREQUISITES[@]}"
do
    if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
        echo "${GREEN}$prerequisite is not installed. Installing...${RESET}"
        sudo apt-get update &&
        sudo apt-get install -yqq "$prerequisite"
    else
        echo "${GREEN}$prerequisite is already installed. Skipping...${RESET}"
    fi
done

# Check if docker-compose is already installed
if ! command -v docker > /dev/null 2>&1; then
    echo "${GREEN}docker is not installed. Installing...${RESET}"
    # Install docker-compose
    sudo apt-get remove docker docker-engine docker.io containerd runc
    sudo apt-get update
    sudo apt-get install ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
        "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
    echo "${GREEN}docker is already installed. Skipping...${RESET}"
fi

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
        sleep 2s
        clear



echo -e "\033[33m\n"
echo "#######################################################################"
echo ""
echo ""
echo "                 SET TIMEZONE AND DASHBOARD PASSWORD"
echo ""
echo ""
echo "#######################################################################"
echo -e "\n\033[0m"
sleep 0.5s

set_password_and_tz &&
        sleep 2s
        clear



echo -e "\033[33m\n" 
echo "#######################################################################"
echo ""
echo ""
echo "             SETTING SERVER IP & SERVER CONFIG FOR WIREGUARD"
echo ""
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
sleep 1s

nano docker-compose.yml
docker-compose up -d --build  &&

sleep 1s
