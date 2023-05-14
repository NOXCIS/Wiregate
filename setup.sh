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
                    @IAmStoxe for UnBound Config



'
sleep 5s



#sudo apt-get update -y && sudo apt-get upgrade -y

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
      sleep 2s
      echo ""
      echo "Enter password for Pihole Dashboard $(tput setaf 1)(Press enter to set password or wait 5 seconds for no password): $(tput sgr0)"  
      set_password &&
              sleep 1s

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
              sleep 1s
              
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
    echo -e "\033[32m$(docker run -d -p 8000:8000 -p 9000:9000 -e SERVER_IP=$(ip route get 8.8.8.8 | awk 'NR==1 {print $NF}') --name=portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce)\033[0m" "\n"

    #echo -e "\033[32m$(docker volume create portainer_data)\033[0m" "\n"
    #echo -e "\033[32m$(docker run -d -p 8000:8000 -p 9000:9000 --name=portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce)\033[0m" "\n"
fi
echo ""
echo ""  
sleep 1s
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
#nano docker-compose.yml 


docker-compose up -d --build  &&

sleep 1s
