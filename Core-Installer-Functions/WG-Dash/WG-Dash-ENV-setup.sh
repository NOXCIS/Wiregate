#!/bin/bash

update_server_ip() {

        ip=$(hostname -I | awk '{print $1}')
        export WG_DASH_SERVER_IP="$ip"

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
        HOST_PORT_START=$((1 + RANDOM % 65535))
        pcount=6
        HOST_PORT_END=$((HOST_PORT_START + pcount-1))  
        port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
        echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"
        export WG_DASH_PORT_RANGE_STARTPORT="$HOST_PORT_START"
        export WG_DASH_PORT_MAPPINGS="$port_mappings"
    fi


    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter the starting port for WireGuard Server interface's Port Range: $(tput sgr0)" HOST_PORT_START
        
        pcount=6
        HOST_PORT_END=$((HOST_PORT_START + pcount-1))  
        port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
        echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"
        export WG_DASH_PORT_RANGE_STARTPORT="$HOST_PORT_START"
        export WG_DASH_PORT_MAPPINGS="$port_mappings"
        break
        done
    fi

}
generate_wireguard_qr() {
    local config_file="./Global-Configs/Master-Key/master.conf"
    sleep 2s
    if ! [ -f "$config_file" ]; then
        echo "Error: Config file not found thi."
        #return 1
    fi

    # Generate the QR code and display it in the CLI
    master_key_title
    printf "%s\n" "$stars"
    printf "%s\n" "$dashes"
    cat ./Global-Configs/Master-Key/master.conf | sed 's/.*/\x1b[33m&\x1b[0m/'
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
set_wg-dash_pass() {
    #local adguard_yaml_file="./adguard/opt-adguard-conf/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false
    local username="USER"

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_wgdash_title
        echo "Press Enter to set Wireguard Dashboard Password  $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random password: $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
    
        characters="A-Za-z0-9!@#$%^&*()"

        plaintext_wgdash_pass=$(head /dev/urandom | tr -dc "$characters" | head -c 16)
        
    
        export WG_DASH_PASS="$plaintext_wgdash_pass"



        
        echo -e "\033[32mPassword has been randomly Gernerated.\033[0m"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Wireguard Dashboard:$(tput sgr0)" wgdash_pass 
            printf "%s\n" "$short_stars"
            

            if [[ -z "$wgdash_pass" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for Wireguard Dashboard:$(tput sgr0) " confirm_wgdash_pass
            printf "%s\n" "$short_stars"
            

            if [[ "$wgdash_pass" != "$confirm_wgdash_pass" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the Database Password
                




                export WG_DASH_PASS="$wgdash_pass"
                


                break
            fi
        done
    fi

}
set_wg-dash_user() {
    #local adguard_yaml_file="./adguard/opt-adguard-conf/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false


    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_uname_wgdash_title
        echo "Press Enter to set Wireguard Dashboard Username $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random username: $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then


        quirky_words=("funky" "zany" "bizarre" "whimsical" "kooky" "offbeat" "wacky" "eccentric" "oddball" "quirky")

        # Randomly select two quirky words
        word1="${quirky_words[$(shuf -i 0-9 -n 1)]}"
        word2="${quirky_words[$(shuf -i 0-9 -n 1)]}"

        # Generate a random number between 100 and 999
        random_number=$(shuf -i 100-999 -n 1)

        # Combine words and number to create a quirky username
        wgdash_user="${word1}_${word2}_${random_number}"

        #sed -i -E "s|^( *- name: ).*|\1$wgdash_user|" "$adguard_yaml_file"

        export WG_DASH_USER="$wgdash_user"


        
        echo -e "\033[32mUsername has been randomly Gernerated.\033[0m"
    fi


    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter Username for Wireguard Dashboard:$(tput sgr0)" wgdash_user 
            
            

            if [[ -z "$wgdash_user" ]]; then
                echo -e "\033[31mUsername cannot be empty. Please try again.\033[0m"
                continue
            fi

                export WG_DASH_USER="$wgdash_user"
                break
            
        done
    fi

}
set_wg-dash_key() {
    # Generate a 512-bit random key using OpenSSL and convert it to hexadecimal
    secret_key_hex=$(openssl rand -hex 64)
    # Export the key to the MSG_SECRET_KEY variable
    export WG_DASH_SECRET_KEY="$secret_key_hex"
}
set_wg-dash_config() {
    set_wg-dash_key
    update_server_ip
    set_port_range

}
set_wg-dash_account() {
    set_wg-dash_user
    set_wg-dash_pass
}


