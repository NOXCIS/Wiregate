#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Initialize variables for flags
BRANCH="main"
ENV=""
TOR=""
TNODE=""
DIND=""
DSYS=""
DSTATE=""
DPROTO=""


# Parse options
while getopts "b:e:t:n:d:c:s:p:" opt; do
  case "$opt" in
    b)  BRANCH="$OPTARG" ;;     # -b for branch
    e)  ENV="$OPTARG" ;;        # -e for ENV
    t)  TOR="$OPTARG" ;;        # -t for TOR
    n)  TNODE="$OPTARG" ;;      # -n for TNODE
    d)  DIND="$OPTARG" ;;       # -d for DIND
    c)  DSYS="$OPTARG" ;;       # -c for DSYS
    s)  DSTATE="$OPTARG" ;;     # -s for DSTATE
    p)  DPROTO="$OPTARG" ;;     # -p for DPROTO
    \?) echo "Usage: $0 [-b branch] [-e ENV] [-t arg2] [-n arg3] [-d DIND] [-c DSYS]"; exit 1 ;;
  esac
done
shift "$((OPTIND - 1))"  # Shift past processed options





git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git   
cd Wiregate


if [ "$DIND" = "dind" ]; then
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



if [[ -n "$ENV" && -n "$TOR" && -n "$TNODE" && -n "$DSYS" && -n "$DSTATE" && -n "$DPROTO" ]]; then
    ./install.sh  -c "$DSYS" -s "$DSTATE" -p "$DPROTO" -t "$TOR" -n "$TNODE" "$ENV"


elif [[ -n "$ENV" && -n "$TOR" && -n "$TNODE" && -n "$DSYS" && -n "$DSTATE" ]]; then
    ./install.sh  -c "$DSYS" -s "$DSTATE" -t "$TOR" -n "$TNODE" "$ENV"

elif [[ -n "$ENV" && -n "$TOR" && -n "$TNODE" && -n "$DSYS" ]]; then
    ./install.sh  -c "$DSYS" -t "$TOR" -n "$TNODE" "$ENV"

elif [[ -n "$ENV" && -n "$TOR" && -n "$TNODE" ]]; then
    ./install.sh -t "$TOR" -n "$TNODE" "$ENV"

elif [[ -n "$ENV" && -n "$TOR" ]]; then
    ./install.sh -t "$TOR" "$ENV"

elif [[ -n "$ENV" ]]; then
    ./install.sh "$ENV"  # Only ENV is passed to install.sh
else
    ./install.sh  # No arguments are passed to install.sh
fi

echo "$TNODE"