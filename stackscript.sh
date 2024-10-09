#!/bin/bash

# Initialize variables for flags
BRANCH="main"
ARG1=""
ARG2=""
ARG3=""
ARG4=""

# Parse options
while getopts "b:r:t:n:d:" opt; do
  case "$opt" in
    b)  BRANCH="$OPTARG" ;;   # -b for branch
    r)  ARG1="$OPTARG" ;;     # -1 for ARG1
    t)  ARG2="$OPTARG" ;;     # -2 for ARG2
    n)  ARG3="$OPTARG" ;;     # -3 for ARG3
    d)  ARG4="$OPTARG" ;;     # -4 for ARG4
    \?) echo "Usage: $0 [-b branch] [-r arg1] [-t arg2] [-n arg3] [-d arg4]"; exit 1 ;;
  esac
done
shift "$((OPTIND - 1))"  # Shift past processed options





git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git   
cd Wiregate


if [ "$ARG4" = "dind" ]; then
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



if [[ -n "$ARG1" && -n "$ARG2" && -n "$ARG3" ]]; then
    ./install.sh "$ARG1" "$ARG2" "$ARG3"

elif [[ -n "$ARG1" && -n "$ARG2" ]]; then
    ./install.sh "$ARG1" "$ARG2"

elif [[ -n "$ARG1" ]]; then
    ./install.sh "$ARG1"  # Only ARG1 is passed to install.sh
else
    ./install.sh  # No arguments are passed to install.sh
fi