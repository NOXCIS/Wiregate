#!/bin/bash

# if [ -z "$(ls -A /etc/wireguard)" ]; then
#   mv /wg0.conf /etc/wireguard
#   echo "Moved conf file to /etc/wireguard"
# else
#   rm wg0.conf
#   echo "Removed unneeded conf file"
# fi

# wg-quick up wg0
chmod u+x /home/app/wgd.sh
if [ ! -f "/home/app/wg-dashboard.ini" ]; then
  /home/app/wgd.sh install
fi
/home/app/wgd.sh start
