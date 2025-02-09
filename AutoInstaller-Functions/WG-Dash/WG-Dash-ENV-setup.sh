#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License


env_file=".env"

# Create environment file if it doesn't exist
if [ ! -f "$env_file" ]; then
        touch "$env_file"

fi

    # Function to check if .env file is empty
is_env_file_empty() {
        [ ! -s "$env_file" ]
}





set_wiregate_env() {
    local awg_vars=("WGD_JC" "WGD_JMIN" "WGD_JMAX" "WGD_S1" "WGD_S2" "WGD_H1" "WGD_H2" "WGD_H3" "WGD_H4")
    local missing_vars=()

    # Ensure the .env file exists
    if [[ ! -f "$env_file" ]]; then
        echo "Error: $env_file not found. Creating it." >&2
        touch "$env_file"
    fi

    # Check if .env file is empty
    if is_env_file_empty; then
        # Update server IP and port range
        if ! update_server_ip; then
            echo "Error: Failed to update server IP." >&2
            return 1
        fi

        if ! set_port_range; then
            echo "Error: Failed to set port range." >&2
            return 1
        fi

        # Write base configuration to .env file
        {
            echo "WGD_PORT_RANGE_STARTPORT=\"$HOST_PORT_START\""
            echo "WGD_PORT_MAPPINGS=\"$port_mappings\""
            echo "WGD_REMOTE_ENDPOINT=\"$ip\""
        } >> "$env_file"
    fi

    # Check if any awg_vars are missing in the .env file
    for var in "${awg_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file"; then
            missing_vars+=("$var")
        fi
    done

    # Update .env with missing awg_vars based on AMNEZIA_WG flag
    if [[ "${#missing_vars[@]}" -gt 0 ]]; then
        echo "Updating missing AWG parameters in $env_file."
        for var in "${missing_vars[@]}"; do
            if [[ "$AMNEZIA_WG" == "true" ]]; then
                echo "$var=\"${!var}\"" >> "$env_file"
            else
                echo "$var=" >> "$env_file"
            fi
        done
    fi

    # Reload environment variables
    export $(grep -v '^#' "$env_file" | xargs)
}


update_server_ip() {
    local timer=$TIMER_VALUE
    local user_activity=false
    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_server_ip_title
        echo "Press Enter to set Wireguard Dashboard Server IP $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for autoset: $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
    # Array of websites to query for the public IP
    websites=("ifconfig.me" "ipinfo.io/ip" "icanhazip.com" "checkip.amazonaws.com")
    
    ip=""
    for site in "${websites[@]}"; do
        ip=$(curl -s "$site")
        if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            break # Exit loop once a valid IP is found
        fi
    done
    
    # If no IP was retrieved, handle the error
    if [ -z "$ip" ]; then
        echo "Failed to retrieve public IP address."
        sleep 3
        exit 1
    fi

    echo "Public IP: $ip"
    # Uncomment the next line to set WGD_REMOTE_ENDPOINT
    export WGD_REMOTE_ENDPOINT="$ip"
    fi



    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter Wireguard Dashboard Server IP:$(tput sgr0)" ip
            
            
        if [[ -z "$ip" ]]; then
            echo -e "\033[31mIPv4 address cannot be empty. Please try again.\033[0m"
            continue
        fi

        # Regular expression for a valid IPv4 address
        ipv4_pattern="^([0-9]{1,3}\.){3}[0-9]{1,3}$"

        # Check if the provided IP address matches the pattern
        if [[ ! "$ip" =~ $ipv4_pattern ]]; then
            echo -e "\033[31mInvalid IPv4 address format. Please enter a valid IPv4 address.\033[0m"
            continue
        fi
                export WGD_REMOTE_ENDPOINT="$ip"
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
            local pcount=4
            local port_found=0
            
            # Function to check if a port is in use
            is_port_in_use() {
                local port=$1
                if [ "$(uname)" == "Darwin" ]; then
                    # macOS: Use lsof to check if the port is in use
                    if lsof -i :$port > /dev/null; then
                        return 0 # Port is in use
                    else
                        return 1 # Port is not in use
                    fi
                else
                    # Linux: Use ss to check if the port is in use
                    if ss -tuln | grep ":$port " > /dev/null; then
                        return 0 # Port is in use
                    else
                        return 1 # Port is not in use
                    fi
                fi
            }

            # Main loop to generate port range
            while [ $port_found -eq 0 ]; do
                # Generate a random starting port
                HOST_PORT_START=$((1042 + RANDOM % (65534 - 1042 + 1)))
                HOST_PORT_END=$((HOST_PORT_START + pcount - 1))

                # Check if any port in the range is in use
                port_in_range=0
                for ((port=HOST_PORT_START; port<=HOST_PORT_END; port++)); do
                    if is_port_in_use $port; then
                        port_in_range=1
                        break
                    fi
                done
                
                # If no ports are in use, accept the range
                if [ $port_in_range -eq 0 ]; then
                    port_found=1
                fi
            done
            
            port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
            echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"
            export WGD_PORT_RANGE_STARTPORT="$HOST_PORT_START"
            export WGD_PORT_MAPPINGS="$port_mappings"
    fi

    if [ "$user_activity" = true ]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter the starting port for WireGuard Server interface's Port Range: $(tput sgr0)" HOST_PORT_START
        
            pcount=4
            HOST_PORT_END=$((HOST_PORT_START + pcount - 1))  
            port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
            echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"
            #export WGD_PORT_RANGE_STARTPORT="$HOST_PORT_START"
            #export WGD_PORT_MAPPINGS="$port_mappings"
            break
        done
    fi


}

generate_wireguard_qr() {
    local config_file="./configs/master-key/master.conf"
    echo -n "Generating Master Key"

    while ! [ -f "$config_file" ]; do
        for s in / - \\ \|; do
            echo -ne "\rGenerating Master Key $s"
            sleep 0.2
        done
    done

    echo -e "\rGenerating Master Key ... Done!"

    # Generate the QR code and display it in the CLI
    master_key_title
    printf "%s\n" "$stars"
    printf "%s\n" "$dashes" $yellow
    cat ./configs/master-key/master.conf 
    printf $green"%s\n" "$equals"
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
    local timer=$TIMER_VALUE
    local user_activity=false
    local username="USER"

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_wgdash_title
        echo "Press Enter to set WireGuard Dashboard Password $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for a random$(tput sgr0)$(tput setaf 4) password$(tput sgr0):"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
        # Generate a random password using pwgen
        plaintext_wgdash_pass=$(pwgen -s 16 1)  # Generate a secure 16-character password
        export WGD_PASS="$plaintext_wgdash_pass"
        echo -e "$(tput setaf 2)Random password for WireGuard Dashboard set to: $plaintext_wgdash_pass$(tput sgr0)"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for WireGuard Dashboard:$(tput sgr0) " wgdash_pass
            printf "\n%s\n" "$short_stars"
            
            if [[ -z "$wgdash_pass" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for WireGuard Dashboard:$(tput sgr0) " confirm_wgdash_pass
            printf "\n%s\n" "$short_stars"
            
            if [[ "$wgdash_pass" != "$confirm_wgdash_pass" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the WireGuard Dashboard Password
                export WGD_PASS="$wgdash_pass"
                echo -e "$(tput setaf 2)Password for WireGuard Dashboard has been successfully set.$(tput sgr0)"
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
        echo "Press Enter to set Wireguard Dashboard Username $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random$blue username$reset: $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done
    
    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then


        quirky_words=("majestic" "noble"  "celestial" "magnificent" "sublime" "enigmatic" "shrouded" "veiled" "cryptic" "mystical" "oracular" "arcane")
        build_names=("kraken" "cetus" "squid" "orca" "marlin" "mantis" "manta" "stingray" "bullshark" "hammerhead")

        # Randomly shuffle the glorifying words and build names arrays
        shuffled_quirky_words=($(shuf -e "${quirky_words[@]}"))
        shuffled_build_names=($(shuf -e "${build_names[@]}"))

        # Randomly select one word from each shuffled array
        word2="${shuffled_build_names[0]}"
        word1="${shuffled_quirky_words[0]}"

        

        # Generate a random number between 100 and 999
        random_number=$(shuf -i 100-999 -n 1)

        # Combine words and number to create a quirky username
        wgdash_user="${word1}_${word2}_${random_number}"

        #sed -i -E "s|^( *- name: ).*|\1$wgdash_user|" "$adguard_yaml_file"

        export WGD_USER="$wgdash_user"


        
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

                export WGD_USER="$wgdash_user"
                break
            
        done
    fi

}

set_wg-dash_config() {
    set_wiregate_env


}
set_wg-dash_account() {
    set_wg-dash_user
    set_wg-dash_pass
}


