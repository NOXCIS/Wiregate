#!/bin/bash

chmod u+x /home/app/wgd.sh

if [ ! -f "/etc/wireguard/wg0.conf" ]; then
    /home/app/wgd.sh newconfig

fi

run_wireguard_up() {
  config_files=$(find /etc/wireguard -type f -name "*.conf")
  
  for file in $config_files; do
    config_name=$(basename "$file" ".conf")
    chmod 600 "/etc/wireguard/$config_name.conf"
    wg-quick up "$config_name" 
  done
}


shadow_socks_up() {




    cat <<EOF >"/home/app/master-key/wg-tun.json"
{
  "server": "<Wireguard server's IP address>",
  "server_port": <server port>,
  "local_address": "0.0.0.0",
  "local_port": 42,
  "password": "<server password>",
  "timeout": 300,
  "method": "chacha20-ietf-poly1305",
  "mode": "tcp_and_udp",
  "tunnel_address": "127.0.0.1:<Wireguard server's port>"
}
EOF

}





























run_wireguard_up 



/home/app/wgd.sh start
