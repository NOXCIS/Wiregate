#!/bin/bash


start_wgd () {
  echo -e "Start Dashboard--------------------------------------------------------------------------------\n"
  echo ""
  echo ""
    uwsgi --ini wiregate.ini 
  echo "--------------------------------------------------------------------------------"
}

newconf_wgd () {
  newconf_wgd0
  newconf_wgd1
  newconf_wgd2
  newconf_wgd3
  return
}


newconf_wgd0() {
    local port_wg0=$WG_DASH_PORT_RANGE_STARTPORT
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)
    cat <<EOF >"/etc/wireguard/ADMINS.conf"
[Interface]
PrivateKey = $private_key
Address = 10.0.0.1/24
ListenPort = $port_wg0
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/Admins/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/Admins/postdown.sh

EOF
    if [ ! -f "/master-key/master.conf" ]; then
        make_master_config  # Only call make_master_config if master.conf doesn't exist
    fi 
}


newconf_wgd1() {
    local port_wg1=$WG_DASH_PORT_RANGE_STARTPORT
    local port_wg1=$((port_wg1 + 1))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/MEMBERS.conf"
[Interface]
PrivateKey = $private_key
Address = 192.168.10.1/24
ListenPort = $port_wg1
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/Members/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/Members/postdown.sh

EOF
}

newconf_wgd2() {
    local port_wg2=$WG_DASH_PORT_RANGE_STARTPORT
    local port_wg2=$((port_wg2 + 2))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/LANP2P.conf"
[Interface]
PrivateKey = $private_key
Address = 172.16.0.1/24
ListenPort = $port_wg2
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/LAN-only-users/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/LAN-only-users/postdown.sh

EOF
}

newconf_wgd3() {
    local port_wg3=$WG_DASH_PORT_RANGE_STARTPORT
    local port_wg3=$((port_wg3 + 3))
    private_key=$(wg genkey)
    public_key=$(echo "$private_key" | wg pubkey)

    cat <<EOF >"/etc/wireguard/GUESTS.conf"
[Interface]
PrivateKey = $private_key
Address = 192.168.20.1/24
ListenPort = $port_wg3
SaveConfig = true
PostUp =  /home/app/Iptables/fowarding-rules/Guest/postup.sh
PreDown = /home/app/Iptables/fowarding-rules/Guest/postdown.sh

EOF
}


make_master_config() {
        local svr_config="/etc/wireguard/ADMINS.conf"
        # Check if the specified config file exists
        if [ ! -f "$svr_config" ]; then
            echo "Error: Config file $svr_config not found."
            exit 1
        fi


        #Function to generate a new peer's public key
        generate_public_key() {
            local private_key="$1"
            echo "$private_key" | wg pubkey
        }

        # Function to generate a new preshared key
        generate_preshared_key() {
            wg genpsk
        }   



    # Generate the new peer's public key, preshared key, and allowed IP
    wg_private_key=$(wg genkey)
    peer_public_key=$(generate_public_key "$wg_private_key")
    preshared_key=$(generate_preshared_key)

    # Add the peer to the WireGuard config file with the preshared key
    echo -e "\n[Peer]" >> "$svr_config"
    echo "PublicKey = $peer_public_key" >> "$svr_config"
    echo "PresharedKey = $preshared_key" >> "$svr_config"
    echo "AllowedIPs = 10.0.0.254/32" >> "$svr_config"


    server_public_key=$(grep -E '^PrivateKey' "$svr_config" | awk '{print $NF}')
    svrpublic_key=$(echo "$server_public_key" | wg pubkey)


    # Generate the client config file
    cat <<EOF >"/home/app/master-key/master.conf"
[Interface]
PrivateKey = $wg_private_key
Address = 10.0.0.254/32
DNS = 10.2.0.100,10.2.0.100
MTU = 1420

[Peer]
PublicKey = $svrpublic_key
AllowedIPs = 0.0.0.0/0
Endpoint = $WG_DASH_SERVER_IP:$WG_DASH_PORT_RANGE_STARTPORT
PersistentKeepalive = 21
PresharedKey = $preshared_key
EOF
}






if [ "$#" != 1 ];
  then
    help
      elif [ "$1" = "start" ]; then
        start_wgd 
      elif [ "$1" = "newconfig" ]; then
        newconf_wgd
      else
        help
    
fi