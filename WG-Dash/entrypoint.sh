#!/bin/bash

chmod u+x /home/app/wgd.sh

chmod u+x /home/app/Admins/wg0-dwn.sh
chmod u+x /home/app/Admins/wg0-nat.sh

chmod u+x /home/app/Members/wg1-dwn.sh
chmod u+x /home/app/Members/wg1-nat.sh

chmod u+x /home/app/Resdnts/wg2-dwn.sh
chmod u+x /home/app/Resdnts/wg2-nat.sh

chmod u+x /home/app/Guest/wg3-dwn.sh
chmod u+x /home/app/Guest/wg3-nat.sh


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



create_wiresentinel_user() {
    # Check if the user already exists
    if id "wiresentinel" &>/dev/null; then
        echo "User wiresentinel already exists."
        return 1
    fi

    password=$(openssl rand -base64 180 | tr -d '\n')
    adduser -D -g '' wiresentinel
    echo "wiresentinel:$password" | chpasswd
    addgroup gatekeeper
    adduser wiresentinel gatekeeper
    chmod 750 /home
    chown -R wiresentinel:gatekeeper /home
    chown -R wiresentinel:gatekeeper /etc/wireguard
    #su - wiresentinel 
    # Note: The script will not continue beyond this point if 'su' is successful,
    # as the shell will be running as the newly created user.
}





#create_wiresentinel_user

run_wireguard_up 



/home/app/wgd.sh start
