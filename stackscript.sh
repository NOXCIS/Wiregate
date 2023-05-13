#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade
#sudo apt-get update -q && sudo apt-get upgrade -qy
git clone https://github.com/NOXCIS/Worm-Hole.git
cd Worm-Hole 
chmod +x setup.sh
./setup.sh