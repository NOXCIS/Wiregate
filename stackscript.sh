#!/bin/bash

BRANCH=${1:-main}
ARG1=${2:-}
ARG2=${3:-}
ARG3=${4:-}

git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git
cd Wiregate

if [ "$ARG1" = "dind" ]; then
    ARG3="$ARG1"
    ARG1=""  # Reset ARG1 after assigning it to ARG3

    env_file=".env"

    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi

    if [ ! -s "$env_file" ]; then 
        ip=$(curl -s ifconfig.me)
        echo "WGD_PORT_RANGE_STARTPORT=\"443\"" >> "$env_file"
        echo "WGD_PORT_MAPPINGS=\"443-448:443-448/udp\"" >> "$env_file"
        echo "WGD_REMOTE_ENDPOINT=\"$ip\"" >> "$env_file"
    fi
fi

chmod +x install.sh

# Only pass ARG1 and ARG2 if they are not empty
if [[ -n "$ARG1" && -n "$ARG2" ]]; then
    ./install.sh "$ARG1" "$ARG2"  # Both ARG1 and ARG2 are passed to install.sh
elif [[ -n "$ARG1" ]]; then
    ./install.sh "$ARG1"  # Only ARG1 is passed to install.sh
else
    ./install.sh  # No arguments are passed to install.sh
fi
