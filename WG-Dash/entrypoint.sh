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
    wg-quick up "$config_name" #> /dev/null 2>&1
  done
}

cout_master_key() {
    cat ./master-key/master.conf 
}
generate_wireguard_qr() {
    local config_file="./master-key/master.conf"

    if ! [ -f "$config_file" ]; then
        echo "Error: Config file not found."
        return 1
    fi

    # Generate the QR code and display it in the CLI
    qrencode -t ANSIUTF8 < "$config_file"

    if [ $? -eq 0 ]; then
        echo "QR code generated." #> /dev/null 2>&1
    else
        echo "Error: QR code generation failed."
        return 1
    fi
}

run_wireguard_up #> /dev/null 2>&1
# Change permission for all generated config files
echo -e "\033[32m"
echo '

███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗     ██╗  ██╗███████╗██╗   ██╗
████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗    ██║ ██╔╝██╔════╝╚██╗ ██╔╝
██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝    █████╔╝ █████╗   ╚████╔╝ 
██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗    ██╔═██╗ ██╔══╝    ╚██╔╝  
██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║    ██║  ██╗███████╗   ██║   
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝   ╚═╝   

'
echo -e "\033[0m"

cout_master_key
echo '
'

generate_wireguard_qr


/home/app/wgd.sh debug
