#!/bin/bash

BRANCH=${1:-main}
ARG1=${2:-}
ARG2=${3:-}
ARG3=${4:-}
TIMER_VALUE=0  # Set a default timer value
ip=""


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
        ip=$(curl -s ifconfig.me)
        #export WGD_REMOTE_ENDPOINT="$ip"
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
                #export WGD_REMOTE_ENDPOINT="$ip"
                break
            
        done
    fi
}


git clone --branch $BRANCH https://github.com/NOXCIS/Wiregate.git
cd Wiregate

    if [ "$ARG3" = "dind" ]; then

    env_file=".env"

    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi

    if [ ! -s "$env_file" ]; then 
        update_server_ip
        echo "WGD_PORT_RANGE_STARTPORT=\"443\"" >> "$env_file"
        echo "WGD_PORT_MAPPINGS=\"443-448:443-448/udp\"" >> "$env_file"
        echo "WGD_REMOTE_ENDPOINT=\"$ip\"" >> "$env_file"
    fi

    fi
  

chmod +x install.sh

# Only pass ARG1 and ARG2 if they are not empty
if [[ -n "$ARG1" && -n "$ARG2" && -n "$ARG3" ]]; then
    ./install.sh "$ARG1" "$ARG2" "$ARG3"
else
    ./install.sh
fi



