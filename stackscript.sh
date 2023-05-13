#!/bin/bash
sudo apt-get update -yqqq && sudo apt-get upgrade -yqqq
git clone https://github.com/NOXCIS/Worm-Hole.git
cd Worm-Hole 
chmod +x setup.sh
./setup.sh
