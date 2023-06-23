#!/bin/bash

#rm /etc/wireguard/*.conf

chmod u+x /home/app/wgd.sh
wg-quick up wg0
if [ ! -f "/home/app/wg-dashboard.ini" ]; 
then
  /home/app/wgd.sh install
fi      
wg-quick up wg0

if [ ! -f "/etc/wireguard/wg0.conf" ]; then
for ((i=1; i<=$CONFIG_CT; i++))
do
  
    /home/app/wgd.sh newconfig
  
done
fi
/home/app/wgd.sh debug