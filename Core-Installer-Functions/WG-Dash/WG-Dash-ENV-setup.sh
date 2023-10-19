#!/bin/bash

update_server_ip() {
    local yml_file="docker-compose.yml"
    local ip

        read -t $TIMER_VALUE -p "Do you want to automatically set the server IP address? $(tput setaf 1)(y/n)$(tput sgr0) " auto_ip
        
    if [[ $auto_ip =~ ^[Nn]$ ]]; then
        read -p "Please enter the server IP address $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)127.0.0.1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " ip
        ip=${ip:-127.0.0.1}
        
    else
        ip=$(hostname -I | awk '{print $1}')
    fi

    if [[ -f "$yml_file" ]]; then

        export SERVER_IP="$ip"
        echo -e "Server IP address has been set to \033[32m$ip\033[0m"
        
    else
        echo "$yml_file not found."
    fi
}
set_config_count() {
    local count=""
    local timer=$TIMER_VALUE
    local user_activity=false

    set_config_count_title

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_config_count_title
        echo "Press Enter to set the amount of WireGuard Server Interfaces to generate $(tput setaf 1)timeout in ($(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1)) seconds : $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
        count=1
        export INTERFACE_COUNT="$count"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter # of WireGuard Interfaces to generate: $(tput sgr0)" count 
            
            

            if [[ -z "$$count" ]]; then
                echo -e "\033[31mValue cannot be empty. Please try again.\033[0m"
                continue
            fi
            
                # Passwords match, set the Database Password
                export INTERFACE_COUNT="$count"
                break
            
        done
    fi



}
set_port_range() {

    local timer=$TIMER_VALUE
    local user_activity=false

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_config_port_range_title
        echo "Press Enter to set starting port for WireGuard Server interface's Port Range $(tput setaf 1)timeout in ($(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1)) seconds : $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
        while [[ $HOST_PORT_START -eq 53 || $HOST_PORT_START -eq 67 || $HOST_PORT_START -eq 68 || $HOST_PORT_START -eq 69 || $HOST_PORT_START -eq 161 || $HOST_PORT_START -eq 162 || $HOST_PORT_START -eq 123 || $HOST_PORT_START -eq 514 || $HOST_PORT_START -eq 1812 || $HOST_PORT_START -eq 1813 || $HOST_PORT_START -eq 137 || $HOST_PORT_START -eq 138 || $HOST_PORT_START -eq 139 || $HOST_PORT_START -eq 162 || $HOST_PORT_START -eq 1900 || ($HOST_PORT_START >= 33434 && $HOST_PORT_START <= 33534) ]]; do
            HOST_PORT_START=$((1 + RANDOM % 65535))
        done
        pcount=$INTERFACE_COUNT
        HOST_PORT_END=$((HOST_PORT_START + pcount))  
        port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
        echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"
        export PORT_RANGE_START="$HOST_PORT_START"
        export PORT_MAPPINGS="$port_mappings"
    fi


    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter the starting port for WireGuard Server interface's Port Range: $(tput sgr0)" HOST_PORT_START
        
        pcount=$INTERFACE_COUNT
        HOST_PORT_END=$((HOST_PORT_START + pcount))  
        port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
        echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"
        export PORT_RANGE_START="$HOST_PORT_START"
        export PORT_MAPPINGS="$port_mappings"
        break
        done
    fi

}
generate_wireguard_qr() {
    local config_file="./WG-Dash/master-key/master.conf"

    if ! [ -f "$config_file" ]; then
        echo "Error: Config file not found."
        return 1
    fi

    # Generate the QR code and display it in the CLI
    master_key_title
    printf "%s\n" "$stars"
    printf "%s\n" "$dashes"
    cat ./WG-Dash/master-key/master.conf | sed 's/.*/\x1b[33m&\x1b[0m/'
    printf "%s\n" "$equals"
    printf "%s\n"
    qrencode -t ANSIUTF8 < "$config_file"

    if [ $? -eq 0 ]; then
        echo "QR code generated." > /dev/null 2>&1
    else
        echo "Error: QR code generation failed."
        return 1
    fi
}