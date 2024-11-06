#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

# Trap the SIGTERM signal and call the stop_service function
trap 'stop_service' SIGTERM

TORRC_PATH="/etc/tor/torrc"
DNS_TORRC_PATH="/etc/tor/dnstorrc"
INET_ADDR="$(hostname -i | awk '{print $1}')"
dashes='------------------------------------------------------------'
equals='============================================================'



clear
printf "%s\n" "$dashes"
echo "Starting WireGate"
printf "%s\n" "$equals"
stop_service() {
  echo "[WIREGATE] Stopping WireGuard Dashboard and Tor."
  ./wgd.sh stop
  kill $TOR_PID
  exit 0
}

clean_up() {
  echo "Looking for remains of previous instances..."
  if [ -f "/opt/wireguarddashboard/app/src/gunicorn.pid" ]; then
    echo "Found old .pid file, removing."
    rm /opt/wireguarddashboard/app/src/gunicorn.pid
  else
    echo "No remains found, continuing."
  fi
}
# Function to get obfs4 bridges from BridgeDB
get_obfs4_bridges() {
    BRIDGEDB_URL="https://bridges.torproject.org/bridges?transport=obfs4"
    
    printf "[TOR] Fetching obfs4 bridges from Tor's BridgeDB...\n"
    
    response=$(curl -s "$BRIDGEDB_URL")
    bridges=$(echo "$response" | sed -n 's/.*\(obfs4 [^<]*\)<br\/>.*/\1/p')
    
    if [[ $response == *"obfs4"* ]]; then
        printf "[TOR] Bridges fetched successfully!\n"
    else
        echo "No obfs4 bridges found or request failed."
    fi
}
# Function to get WebTunnel bridges from BridgeDB 
get_webtunnel_bridges() {
    BRIDGEDB_URL="https://bridges.torproject.org/bridges?transport=webtunnel"
    
    printf "[TOR] Fetching WebTunnel bridges from Tor's BridgeDB...\n"

    response=$(curl -s "$BRIDGEDB_URL")
    bridges=$(echo "$response" | sed -n 's/.*\(webtunnel [^<]*\)<br\/>.*/\1/p')
    
    if [[ $response == *"webtunnel"* ]]; then
        printf "[TOR] Bridges fetched successfully!\n"
    else
        echo "No WebTunnel bridges found or request failed."
    fi
}
make_torrc() {
    printf "%s\n" "$dashes"
    printf "[TOR] Generating torrc to $TORRC_PATH...\n"
    if [ -f "$TORRC_PATH" ]; then
    rm "$TORRC_PATH" 
    fi

    if [[ "$WGD_TOR_PLUGIN" == "webtunnel" ]]; then
    get_webtunnel_bridges
    elif [[ "$WGD_TOR_PLUGIN" == "obfs4" ]]; then
    get_obfs4_bridges
    fi
    
    if [[ "$WGD_TOR_BRIDGES" == "true" ]]; then
    echo -e "UseBridges 1\n" >> "$TORRC_PATH"
    printf "[TOR] Adding bridges to $TORRC_PATH...\n"
    printf "[TOR] Bridges added to $TORRC_PATH successfully!\n"
    fi

    echo -e "AutomapHostsOnResolve 1 \n" >> "$TORRC_PATH"
    echo -e "VirtualAddrNetwork 10.192.0.0/10 \n" >> "$TORRC_PATH"
    echo -e "User tor \n" >> "$TORRC_PATH"
    echo -e "DataDirectory /var/lib/tor \n" >> "$TORRC_PATH"
    echo -e "TransPort ${INET_ADDR}:59040 IsolateClientAddr IsolateClientProtocol IsolateDestAddr IsolateDestPort \n" >> "$TORRC_PATH"
    echo -e "ExtORPort auto \n" >> "$TORRC_PATH"

    if [[ "$WGD_TOR_PLUGIN" == "obfs4" ]]; then
    echo -e "ClientTransportPlugin obfs4 exec /usr/local/bin/lyrebird \n" >> "$TORRC_PATH"
    elif [[ "$WGD_TOR_PLUGIN" == "snowflake" ]]; then
    echo -e "ClientTransportPlugin snowflake exec /usr/local/bin/snowflake -url https://snowflake-broker.azureedge.net/ -front ajax.aspnetcdn.com -ice stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn \n" >> "$TORRC_PATH"
    else
    echo -e "ClientTransportPlugin ${WGD_TOR_PLUGIN} exec /usr/local/bin/${WGD_TOR_PLUGIN} \n" >> "$TORRC_PATH"
    fi
    if [[ "$WGD_TOR_EXIT_NODES" == "default" ]]; then
    echo "Using Default"
    elif [[ -n "$WGD_TOR_EXIT_NODES" ]]; then
    echo -e "ExitNodes $WGD_TOR_EXIT_NODES \n" >> "$TORRC_PATH"
    else
    echo "Invalid input. Please use the correct format: {US},{GB},{AU}, etc."
    fi

    if [[ "$WGD_TOR_PLUGIN" == "snowflake" ]]; then
    echo -e "Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 \n" >> "$TORRC_PATH"
    echo -e "Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA \n" >> "$TORRC_PATH"
    else
    echo "$bridges" | while read -r bridge; do
        echo "Bridge $bridge" >> "$TORRC_PATH"
    done
    fi
    apk del curl > /dev/null 2>&1
    printf "%s\n" "$dashes"
}
make_dns_torrc() {
    printf "%s\n" "$dashes"
    sudo apk add tor curl > /dev/null 2>&1
    printf "[TOR-DNS] Generating DNS-torrc to $DNS_TORRC_PATH...\n"
    if [ -f "$DNS_TORRC_PATH" ]; then
    rm "$DNS_TORRC_PATH" 
    fi
    echo -e "UseBridges 1\n" >> "$DNS_TORRC_PATH"
    echo -e "AutomapHostsOnResolve 1 \n" >> "$DNS_TORRC_PATH"
    echo -e "VirtualAddrNetwork 10.193.0.0/10 \n" >> "$TORRC_PATH"
    echo -e "User tor \n" >> "$DNS_TORRC_PATH"
    echo -e "DataDirectory /var/lib/tor/dns \n" >> "$DNS_TORRC_PATH"
    echo -e "ClientTransportPlugin snowflake exec /usr/local/bin/snowflake -url https://snowflake-broker.azureedge.net/ -front ajax.aspnetcdn.com -ice stun:stun.l.google.com:19302,stun:stun.antisip.com:3478,stun:stun.bluesip.net:3478,stun:stun.dus.net:3478,stun:stun.epygi.com:3478,stun:stun.sonetel.com:3478,stun:stun.uls.co.za:3478,stun:stun.voipgate.com:3478,stun:stun.voys.nl:3478 utls-imitate=hellorandomizedalpn \n" >> "$DNS_TORRC_PATH"
    if [[ "$WGD_TOR_DNS_EXIT_NODES" == "default" ]]; then
    echo "Using Default"
    elif [[ -n "$WGD_TOR_DNS_EXIT_NODES" ]]; then
    echo -e "ExitNodes $WGD_TOR_DNS_EXIT_NODES \n" >> "$DNS_TORRC_PATH"
    else
    echo "Invalid input. Please use the correct format: {US},{GB},{AU}, etc."
    fi

    echo -e "SocksPort ${INET_ADDR}:9053 \n" >> "$DNS_TORRC_PATH"
    echo -e "Bridge snowflake 192.0.2.3:80 2B280B23E1107BB62ABFC40DDCC8824814F80A72 \n" >> "$DNS_TORRC_PATH"
    echo -e "Bridge snowflake 192.0.2.4:80 8838024498816A039FCBBAB14E6F40A0843051FA \n" >> "$DNS_TORRC_PATH"
    
    printf "%s\n" "$dashes"
}
run_tor_flux() {
    printf "%s\n" "$equals"
    printf "[TOR] Starting Tor ...\n"
    { date; tor -f /etc/tor/torrc; printf "\n\n"; } >> ./log/tor_startup_log.txt &
    { date; tor -f /etc/tor/dnstorrc; printf "\n\n"; } >> ./log/tor_startup_log.txt &

    TOR_PID=$!

    while true; do
        sleep_time=$(( RANDOM % (1642 - 300 + 1) + 300 ))
        sleep_kill=$(awk -v seed="$RANDOM" 'BEGIN { srand(seed); printf "%.2f\n", 0.04 + (rand() * (0.50 - 0.04)) }')
        #sleep_time=$(( RANDOM % (15 - 10 + 1) + 10 ))
        printf "[TOR] New Circuit in $sleep_time seconds...\n"  
        printf "%s\n" "$equals" 
        sleep $sleep_time
        printf "%s\n" "$equals" 
        printf "[TOR] Restarting Tor...\n"  
        pkill tor 
        sleep $sleep_kill
        { date; tor -f /etc/tor/torrc; printf "\n\n"; } >> ./log/tor_startup_log.txt &
        { date; tor -f /etc/tor/dnstorrc; printf "\n\n"; } >> ./log/tor_startup_log.txt &
        TOR_PID=$!
    done
       
}
ensure_blocking() {
  sleep 1s
  echo "Ensuring container continuation."
  err_log=$(find /opt/wireguarddashboard/src/log -name "error_*.log" | head -n 1)
  acc_log=$(find /opt/wireguarddashboard/src/log -name "access_*.log" | head -n 1)
  if [ -n "$err_log" ] || [ -n "$acc_log" ]; then
    tail -f $err_log $acc_log &
  fi
  wait
}

# create /dev/net/tun if it does not exist
if [[ ! -c /dev/net/tun ]]; then
    mkdir -p /dev/net && mknod /dev/net/tun c 10 200
fi


# Cleanup old processes
chmod u+x /opt/wireguarddashboard/src/wgd.sh
{ date; clean_up; printf "\n\n"; } >> ./log/install.txt

make_dns_torrc
if [[ "$WGD_TOR_PROXY" == "true" ]]; then
  make_torrc
  
fi


/opt/wireguarddashboard/src/wgd.sh install
/opt/wireguarddashboard/src/wgd.sh docker_start &


WGD_PID=$!

if [[ "$WGD_TOR_PROXY" == "true" ]]; then
  run_tor_flux &
  TOR_PID=$!
fi

# Wait for background processes to finish (if they don't, the script will stay running)
wait $WGD_PID
rm -r .env
echo "" >> .env 
ensure_blocking




