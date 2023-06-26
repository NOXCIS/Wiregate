#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update
sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade
cd ..
cd home
git clone https://github.com/NOXCIS/Worm-Hole.git
cd Worm-Hole 
chmod +x install.sh 
./install.sh headless