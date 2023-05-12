#!/bin/bash
sudo apt-get update -y && sudo apt-get upgrade -yqq
git clone https://github.com/NOXCIS/Worm-Hole.git
cd Worm-Hole 
chmod +x setup.sh
./setup.sh
