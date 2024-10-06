#!/bin/bash

BRANCH=${1:-main}
ARG1=${2:-}
ARG2=${3:-}

git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git
cd Wiregate
chmod +x install.sh
./install.sh "$ARG1" "$ARG2"
