#!/bin/bash

chmod u+x /home/app/wgd.sh

if [ ! -f "/home/app/wg-dashboard.ini" ]; then
  /home/app/wgd.sh install
fi


/home/app/wgd.sh newconfig

function run_wireguard_up() {
  config_files=$(find /etc/wireguard -type f -name "*.conf")
  
  for file in $config_files; do
    config_name=$(basename "$file" ".conf")
    chmod 600 "$config_name"
    wg-quick up "$config_name"
  done
}

run_wireguard_up

/home/app/wgd.sh debug
