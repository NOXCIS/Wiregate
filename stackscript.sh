#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Initialize variables for flags
BRANCH="main"
ARG1=""
ARG2=""
ARG3=""
ARG4=""
ARG5=""
# Parse options
while getopts "b:e:t:n:d:c:" opt; do
  case "$opt" in
    b)  BRANCH="$OPTARG" ;;   # -b for branch
    e)  ARG1="$OPTARG" ;;     # -1 for ARG1
    t)  ARG2="$OPTARG" ;;     # -2 for ARG2
    n)  ARG3="$OPTARG" ;;     # -3 for ARG3
    d)  ARG4="$OPTARG" ;;     # -4 for ARG4
    c)  ARG5="$OPTARG" ;;     # -4 for ARG4
    \?) echo "Usage: $0 [-b branch] [-r arg1] [-t arg2] [-n arg3] [-d arg4] [-c arg5]"; exit 1 ;;
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
            echo "WGD_PORT_RANGE_STARTPORT=\"4430\"" >> "$env_file"
            echo "WGD_PORT_MAPPINGS=\"4430-4433:4430-4433/udp\"" >> "$env_file"
            echo "WGD_REMOTE_ENDPOINT=\"$ip\"" >> "$env_file"
        fi
fi

chmod +x install.sh



if [[ -n "$ARG1" && -n "$ARG2" && -n "$ARG3" && -n "$ARG5" ]]; then
    ./install.sh  -c "$ARG5" -t "$ARG2" -n "$ARG3" "$ARG1"

elif [[ -n "$ARG1" && -n "$ARG2" && -n "$ARG3" ]]; then
    ./install.sh -t "$ARG2" -n "$ARG3" "$ARG1"

elif [[ -n "$ARG1" && -n "$ARG2" ]]; then
    ./install.sh -t "$ARG2" "$ARG1"

elif [[ -n "$ARG1" ]]; then
    ./install.sh "$ARG1"  # Only ARG1 is passed to install.sh
else
    ./install.sh  # No arguments are passed to install.sh
fi