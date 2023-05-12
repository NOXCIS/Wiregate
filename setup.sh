#!/bin/bash
sleep 2s

function update_server_ip() {
  local yml_file="docker-compose.yml"
  local ip

  read -p "Do you want to automatically get the server IP address? (Y/n) " auto_ip
  echo ""
  if [[ $auto_ip =~ ^[Nn]$ ]]; then
    read -p "Please enter the server IP address (Press enter for default: 127.0.0.1 ): " ip
    ip=${ip:-127.0.0.1}
    echo ""
  else
    ip=$(hostname -I | awk '{print $1}')
  fi

  if [[ -f "$yml_file" ]]; then
    sed -i "s/SERVER_IP=.*/SERVER_IP=$ip/" "$yml_file"
    echo "SERVER_IP parameter in $yml_file has been updated to $ip"
    echo ""
  else
    echo "$yml_file not found."
  fi
}

function config_count() {
  local yml_file="docker-compose.yml"

  if [[ -f "$yml_file" ]]; then
    read -p "Enter # of WireGuard server configurations to generate (Press enter for default: 1 ): " count
    count=${count:-1} # set count to 1 if user enters nothing
    sed -i "s/CONFIG_CT=.*/CONFIG_CT=$count/" "$yml_file"
    echo ""
    echo "WireGuard Server Configurations to be Generated has been set to $count"
    echo ""
  else
    echo "$yml_file not found."

  fi
}



function set_password_and_tz {
    local yml_file="docker-compose.yml"
    read -p "Do you want to automatically get the host timezone? (y/n) " answer
    echo ""
    if [[ $answer == [Yy] ]]; then
        timezone=$(cat /etc/timezone)
    else
        read -p "Enter timezone (Press enter for default: America/New_York ): " timezone
        timezone=${timezone:-"America/New_York"} # set timezone to America/New_York if user enters nothing
        echo ""
    fi
    sed -i "s|TZ:.*|TZ: \"$timezone\"|" "$yml_file"
    read -sp "Enter password for Pihole Dashboard (Press enter for default: No Password ): " password
    sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
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

# Check if each prerequisite is already installed
for prerequisite in "${PREREQUISITES[@]}"
do
    if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
        echo "$prerequisite is not installed. Installing..."
        sudo apt-get update &&
        sudo apt-get install -yqq "$prerequisite"
    else
        echo "$prerequisite is already installed. Skipping..."
    fi
done

# Check if docker-compose is already installed
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "docker-compose is not installed. Installing..."
    # Install docker-compose
    sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose &&
    sudo chmod +x /usr/local/bin/docker-compose &&
    sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
else
    echo "docker-compose is already installed. Skipping..."
fi

echo ""
echo ""  
echo "#######################################################################"
echo ""
echo ""
echo "                        INSTALLING PORTAINER"
echo "                        RUNNING ON PORT :9000"
echo ""
echo ""
echo "#######################################################################"
echo ""
echo ""  
sleep 1s

   #docker rm -f portainer
if docker ps -a | grep portainer ; then
    echo "" 
    echo "Portainer is already running"
else
    echo "Portainer is not running, creating data volume and starting container"
    docker volume create portainer_data
    docker run -d -p 8000:8000 -p 9000:9000 --name=portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce
fi

sleep 2s
clear


echo ""
echo ""  
echo "#######################################################################"
echo ""
echo ""
echo "                 SET TIMEZONE AND DASHBOARD PASSWORD"
echo ""
echo ""
echo "#######################################################################"
echo ""
echo ""  
sleep 1s

    set_password_and_tz &&
        
        sleep 2s
        clear
echo ""
echo ""  
echo "#######################################################################"
echo ""
echo ""
echo "             SETTING SERVER IP & SERVER CONFIG FOR WIREGUARD"
echo ""
echo ""
echo "#######################################################################"
echo ""
echo ""  
sleep 1s
      update_server_ip &&
          sleep 1s

      config_count &&
          sleep 2s
          clear
echo ""
echo ""      
echo "#######################################################################"
echo ""
echo ""
echo "                        REVIEW COMPOSE FILE"
echo ""
echo ""
echo "#######################################################################"
echo ""
echo ""  
sleep 1s

      nano docker-compose.yml
      docker-compose up -d --build  &&

sleep 1s
