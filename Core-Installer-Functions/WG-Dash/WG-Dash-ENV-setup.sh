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
        HOST_PORT_START=$((1 + RANDOM % 65535))
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
set_wg-dash_pass() {
    #local adguard_yaml_file="./adguard/opt-adguard-conf/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false
    local username="USER"

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_wgdash_title
        echo "Press Enter to set Wireguard Dashboard Password  $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for no password: $(tput sgr0)"
        
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
        
        output=$(htpasswd -B -n -b "$username" "$plaintext_wgdash_pass")

        # Use sed to delete the first 5 characters of $output and assign it to wgdash_password
        wgdash_password=$(echo "$output" | sed 's/.....//')


        #sed -i -E "s|^( *password: ).*|\1$wgdash_password|" "$adguard_yaml_file"

        export WG_DASH_PASS="$plaintext_wgdash_pass"
        export WG_DASH_PASS_ENCRYPTED="$wgdash_password"


        
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
                
                output=$(htpasswd -B -n -b "$username" "$wgdash_pass")
                
                # Use sed to delete the first 5 characters of $output and assign it to wgdash_password
                manual_adguard_password=$(echo "$output" | sed 's/.....//')
                

                #sed -i -E "s|^( *password: ).*|\1$manual_adguard_password|" "$adguard_yaml_file"



                export WG_DASH_PASS="$wgdash_pass"
                export WG_DASH_PASS_ENCRYPTED="$manual_adguard_password"


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
        echo "Press Enter to set Wireguard Dashboard Username $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for no password: $(tput sgr0)"
        
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
            
            read -p "$(tput setaf 3)Confirm Username for Wireguard Dashboard:$(tput sgr0) " confirm_user
            
            

            if [[ "$wgdash_user" != "$confirm_user" ]]; then
                echo -e "\033[31mUsernames do not match. Please try again.\033[0m"
            else
                # Passwords match, set the Database Password


                #sed -i -E "s|^( *- name: ).*|\1$wgdash_user|" "$adguard_yaml_file"



                export WG_DASH_USER="$wgdash_user"
                break
            fi
        done
    fi

}





