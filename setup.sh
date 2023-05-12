#!/bin/bash
sleep 2s

function update_server_ip() {
  local ip=$(hostname -I | awk '{print $1}')
  local yml_file="docker-compose.yml"

  if [[ -f "$yml_file" ]]; then
    sed -i "s/SERVER_IP=.*/SERVER_IP=$ip/" "$yml_file"
    echo "SERVER_IP parameter in $yml_file has been updated to $ip"
  else
    echo "$yml_file not found."
  fi
}

function get_config_count() {
  local yml_file="docker-compose.yml"
  if [[ -f "$yml_file" ]]; then
    read -p "Enter # of wireguard server configurations to generate: " count
    sed -i "s/CONFIG_CT=.*/CONFIG_CT=$count/" "$yml_file"
    echo "SERVER_IP parameter in $yml_file has been updated to $ip"
  else
    echo "$yml_file not found."
  fi
}


#!/bin/bash

function set_password_and_tz {
    local yml_file="docker-compose.yml"

    read -p "Enter timezone (e.g. America/New_York): " timezone
    sed -i "s|TZ:.*|TZ: \"$timezone\"|" "$yml_file"
    #sed -i "s/TZ:.*/TZ: \"$timezone\"/" "$yml_file"

    read -sp "Enter password for Pihole Dashboard: " password
    sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
}


if command -v docker &> /dev/null
then
    echo "Docker is installed"
else
    echo "Docker is not installed"
    sleep 3s
    echo "installing Docker"



# Prereqs and docker
sudo apt-get update &&
  sudo apt-get install -yqq \
      curl \
      git \
      apt-transport-https \
      ca-certificates \
      gnupg-agent \
      software-properties-common

# Install Docker repository and keys
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) \
      stable" &&
  sudo apt-get update &&
  sudo apt-get install docker-ce docker-ce-cli containerd.io -yqq

# docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.26.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose &&
  sudo chmod +x /usr/local/bin/docker-compose &&
  sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

fi

# Portainer -LOCATION -> host-ip:9000
docker volume create portainer_data
docker run -d -p 8000:8000 -p 9000:9000 --name=portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce


cd Wirehole &&

echo "#######################################################################"
echo "SET TIMEZONE AND DASHBOARD PASSWORD"
echo "#######################################################################"
    set_password_and_tz &&
        echo "#######################################################################"
        echo "MAKE WANTED CHANGES SAVE AND EXIT"
        echo "#######################################################################"
        sleep 2s
        nano docker-compose.yml
    docker-compose up --detach &&
    cd .. &&

cd  WG-Dashboard &&

echo "#######################################################################"
echo "SETTING SERVER IP FOR WIREGUARD"
echo "#######################################################################"
    update_server_ip &&
    get_config_count &&
        echo "#######################################################################"
        echo "MAKE NECESSARY CHANGES SAVE AND EXIT"
        echo "#######################################################################"
        sleep 2s
        nano docker-compose.yml
    docker-compose up --detach &&

 sleep 1s