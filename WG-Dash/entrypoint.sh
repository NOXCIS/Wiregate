#!/bin/bash

chmod u+x /home/app/wgd.sh

chmod u+x /home/app/FIREWALLS/Admins/wg0-dwn.sh
chmod u+x /home/app/FIREWALLS/Admins/wg0-nat.sh

chmod u+x /home/app/FIREWALLS/Members/wg1-dwn.sh
chmod u+x /home/app/FIREWALLS/Members/wg1-nat.sh

chmod u+x /home/app/FIREWALLS/LAN-only-users/wg2-dwn.sh
chmod u+x /home/app/FIREWALLS/LAN-only-users/wg2-nat.sh

chmod u+x /home/app/FIREWALLS/Guest/wg3-dwn.sh
chmod u+x /home/app/FIREWALLS/Guest/wg3-nat.sh

chmod u+x /home/app/FIREWALLS/IPV6/wg0-dwn.sh
chmod u+x /home/app/FIREWALLS/IPV6/wg0-nat.sh

chmod u+x /home/app/FIREWALLS/IPV6/wg1-dwn.sh
chmod u+x /home/app/FIREWALLS/IPV6/wg1-nat.sh



if [ ! -f "/etc/wireguard/wg0.conf" ]; then
    /home/app/wgd.sh newconfig

fi
run_wireguard_up() {
  config_files=$(find /etc/wireguard -type f -name "*.conf")

  for file in $config_files; do
    config_name=$(basename "$file" ".conf")
    chmod 600 "/etc/wireguard/$config_name.conf"
    #wg-quick up "$config_name"  
  done
  
}

config_nginx () {
    rm /etc/nginx/http.d/default.conf
    cat <<EOF > "/etc/nginx/http.d/default.conf"
server {
    listen 80;

    location / {
        include uwsgi_params;
        uwsgi_pass 127.0.0.1:10086;
    }
}
EOF
}


logs_title() {
  echo -e "\033[32m"
  echo '
________________________________________________________________________________
|                                                                               |
|       ██╗    ██╗██╗██████╗ ███████╗ ██████╗  █████╗ ████████╗███████╗         |
|       ██║    ██║██║██╔══██╗██╔════╝██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝         |
|       ██║ █╗ ██║██║██████╔╝█████╗  ██║  ███╗███████║   ██║   █████╗           |
|       ██║███╗██║██║██╔══██╗██╔══╝  ██║   ██║██╔══██║   ██║   ██╔══╝           |
|       ╚███╔███╔╝██║██║  ██║███████╗╚██████╔╝██║  ██║   ██║   ███████╗         |
|        ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝         |
|                                    LOGS                                       |
|_______________________________________________________________________________|'                                                               
  echo -e "\033[33m"
  echo ""
}

network_logs_out() {
  echo ""
  echo ""
  echo -e "NETWORK INTERFACES--------------------------------------------------------------------------------\n"
    ifconfig
  echo ""
  echo -e "IPTABLES LIST--------------------------------------------------------------------------------\n"
    iptables -L -n
  echo ""
  echo -e "IPTABLES NAT LIST--------------------------------------------------------------------------------\n" 
    iptables -t nat -L -n
  echo ""
}

logs_title &&

run_wireguard_up #>/dev/null 2>&1 && 
wg-quick up ADMINS
network_logs_out &&
config_nginx &&
nginx &&
/home/app/wgd.sh start

