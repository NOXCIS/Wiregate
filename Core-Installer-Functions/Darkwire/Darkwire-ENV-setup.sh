#!/bin/bash

set_darkwire_room_hash() {
    local timer=0
    local user_activity=false


    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_dw_rm_hash_title
        echo "Press Enter to set Darkwire Room Hash  $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random password: $(tput sgr0)"
        
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
        plaintext_rm_hash=$(head /dev/urandom | tr -dc "$characters" | head -c 420)
        export DW_ROOM_HASH="$plaintext_rm_hash"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Pihole Dashboard:$(tput sgr0)" rm_hash 
            printf "%s\n" "$short_stars"
            

            if [[ -z "$rm_hash" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for Pihole Dashboard:$(tput sgr0) " confirm_rm_hash
            printf "%s\n" "$short_stars"
            

            if [[ "$rm_hash" != "$confirm_rm_hash" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                export DW_ROOM_HASH="$rm_hash"
                break
            fi
        done
    fi

}

set_dwire_config() {
    set_darkwire_room_hash
}