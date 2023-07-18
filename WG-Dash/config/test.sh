#!/bin/bash

# Function to generate a new peer's public key
generate_public_key() {
    local private_key="$1"
    echo "$private_key" | wg pubkey
}

# Function to generate a new preshared key
generate_preshared_key() {
    wg genpsk
}

# Function to find an available IP range for the new peer
find_available_ip() {
    local config_file="$1"
    local start_ip="10.0.0.2"

    # Extract existing IP addresses from the config file
    existing_ips=$(awk '/^Address/{print $NF}' "$config_file")

    # Loop to find an available IP
    current_ip="$start_ip"
    while echo "$existing_ips" | grep -q "$current_ip"; do
        current_ip=$(printf '%s\n' "$current_ip" | awk -F. 'NF==4{if($4<255){$4++;print;exit} else if($3<255){$3++;$4=0;print;exit} else if($2<255){$2++;$3=$4=0;print;exit} else if($1<255){$1++;$2=$3=$4=0;print;exit}}')
    done

    echo "$current_ip"
}

# Check if the script is run with the correct number of arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <config_file>"
    exit 1
fi

config_file="$1"

# Check if the specified config file exists
if [ ! -f "$config_file" ]; then
    echo "Error: Config file $config_file not found."
    exit 1
fi

# Generate the new peer's public key, preshared key, and allowed IP
wg_private_key=$(wg genkey)
peer_public_key=$(generate_public_key "$wg_private_key")
preshared_key=$(generate_preshared_key)
peer_allowed_ips=$(find_available_ip "$config_file")

# Add the peer to the WireGuard config file with the preshared key
echo -e "\n[Peer]" >> "$config_file"
echo "PublicKey = $peer_public_key" >> "$config_file"
echo "PresharedKey = $preshared_key" >> "$config_file"
echo "AllowedIPs = $peer_allowed_ips" >> "$config_file"

# Generate the client config file
client_config_file="client.conf"
echo "[Interface]" > "$client_config_file"
echo "PrivateKey = $wg_private_key" >> "$client_config_file"
echo "Address = $peer_allowed_ips/32" >> "$client_config_file"
echo "DNS = 10.2.0.100,10.2.0.200" >> "$client_config_file"
echo "MTU = 1420" >> "$client_config_file"

server_public_key=$(grep -E '^PrivateKey' "$config_file" | awk '{print $NF}')


svrpublic_key=$(echo "$server_public_key" | wg pubkey)

echo -e "\n[Peer]" >> "$client_config_file"
echo "PublicKey = $svrpublic_key" >> "$client_config_file"
echo "PresharedKey = $preshared_key" >> "$client_config_file"
echo "AllowedIPs = 0.0.0.0/0" >> "$client_config_file"
echo "Endpoint = your_server_ip:51820" >> "$client_config_file"

# Generate the QR code and display it in the terminal
qrencode -t ansiutf8 < "$client_config_file"

echo "Peer added to the WireGuard config file with a preshared key. Client config file and QR code have been generated successfully."
