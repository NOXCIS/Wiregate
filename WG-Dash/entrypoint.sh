#!/bin/bash


chmod u+x /home/app/wgd.sh

if [ ! -f "/etc/wireguard/wg0.conf" ]; then
    /home/app/wgd.sh newconfig

fi

function run_wireguard_up() {
  config_files=$(find /etc/wireguard -type f -name "*.conf")
  
  for file in $config_files; do
    config_name=$(basename "$file" ".conf")
    wg-quick up "$config_name"
  done
}

run_wireguard_up

/home/app/wgd.sh debug
