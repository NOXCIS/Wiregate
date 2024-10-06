#!/bin/bash
# Set default branch to 'main'
BRANCH=${1:-main}
git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git
cd Wiregate
chmod +x install.sh
./install.sh
