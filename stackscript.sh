#!/bin/bash

sudo apt-get update -q && sudo apt-get upgrade -qy
git clone https://github.com/NOXCIS/Worm-Hole.git
cd Worm-Hole 
chmod +x setup.sh
./setup.sh