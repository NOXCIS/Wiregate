#!/bin/bash

if [ -z "$(ls -A /etc/wireguard/*.conf 2>/dev/null)" ]; then
  echo "No WireGuard configuration files found. Skipping removal."
else
  rm /etc/wireguard/*.conf
  echo "Existing WireGuard configuration files removed."
fi

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

/home/app/wgd.sh debug
