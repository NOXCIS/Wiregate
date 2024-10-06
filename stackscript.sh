#!/bin/bash

BRANCH=${1:-main}
ARG1=${2:-}
ARG2=${3:-}

git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git
cd Wiregate
chmod +x install.sh

# Only pass ARG1 and ARG2 if they are not empty
if [[ -n "$ARG1" && -n "$ARG2" ]]; then
    ./install.sh "$ARG1" "$ARG2"
else
    ./install.sh
fi


curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && chmod +x stackscript.sh  && ./stackscript.sh terra-firma Tor-br-obfs4 E-P-C

