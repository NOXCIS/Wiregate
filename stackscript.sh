#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Initialize variables for flags
BRANCH="main"
ENV=""
TOR=""
TNODE=""
T_DNS_NODE=""
DIND=""
DSYS=""
DSTATE=""
DPROTO=""

# Parse options
while getopts "b:e:t:n:d:c:s:p:l:" opt; do
  case "$opt" in
    b)  BRANCH="$OPTARG" ;;     # -b for branch
    e)  ENV="$OPTARG" ;;        # -e for ENV
    t)  TOR="$OPTARG" ;;        # -t for TOR
    n)  TNODE="$OPTARG" ;;      # -n for TNODE
    l)  T_DNS_NODE="$OPTARG" ;; # -l for T_DNS_NODE
    d)  DIND="$OPTARG" ;;       # -d for DIND
    c)  DSYS="$OPTARG" ;;       # -c for DSYS
    s)  DSTATE="$OPTARG" ;;     # -s for DSTATE
    p)  DPROTO="$OPTARG" ;;     # -p for DPROTO
    \?) echo "Usage: $0 [-b branch] [-e ENV] [-t arg2] [-n arg3] [-d DIND] [-c DSYS]"; exit 1 ;;
  esac
done
shift "$((OPTIND - 1))"  # Shift past processed options

# Clone repository and navigate into it
git clone --branch "$BRANCH" https://github.com/NOXCIS/Wiregate.git
cd Wiregate || exit 1

# Handle DIND-related logic
if [ "$DIND" = "dind" ]; then
    env_file=".env"
    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi
    if [ ! -s "$env_file" ]; then 
        ip=$(curl -s ifconfig.me)
        cat <<EOF >"$env_file"
WGD_PORT_RANGE_STARTPORT="4430"
WGD_PORT_MAPPINGS="4430-4433:4430-4433/udp"
WGD_REMOTE_ENDPOINT="$ip"
EOF
    fi
fi

chmod +x install.sh

# Dynamically build the arguments for install.sh
INSTALL_ARGS=()
[ -n "$DSYS" ] && INSTALL_ARGS+=("-c" "$DSYS")
[ -n "$DSTATE" ] && INSTALL_ARGS+=("-s" "$DSTATE")
[ -n "$DPROTO" ] && INSTALL_ARGS+=("-p" "$DPROTO")
[ -n "$TOR" ] && INSTALL_ARGS+=("-t" "$TOR")
[ -n "$TNODE" ] && INSTALL_ARGS+=("-n" "$TNODE")
[ -n "$T_DNS_NODE" ] && INSTALL_ARGS+=("-l" "$T_DNS_NODE")
[ -n "$ENV" ] && INSTALL_ARGS+=("$ENV")

# Execute the install script with the constructed arguments
./install.sh "${INSTALL_ARGS[@]}"

