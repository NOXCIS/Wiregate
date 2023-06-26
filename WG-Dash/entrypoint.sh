#!/bin/bash

chmod u+x /home/app/wgd.sh

if [ ! -f "/home/app/wg-dashboard.ini" ]; then
  /home/app/wgd.sh install
fi

if [ ! -f "/etc/wireguard/wg0.conf" ]; then
  for ((i=1; i<=$CONFIG_CT; i++))
  do
    /home/app/wgd.sh newconfig
  done
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
