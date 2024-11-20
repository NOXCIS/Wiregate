#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License



set_pihole_tz() {
    local timer=$TIMER_VALUE
    local user_activity=false

    while [ $timer -gt 0 ]; do
        clear

        # Print the updated timer value
        set_pihole_tz_title
        echo "Press Enter to set Timezone or wait$blue $timer$reset seconds for autoset:"

        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done

    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
        timezone=$(cat /etc/timezone)
        export PI_HOLE_TZ="$timezone"
    fi

    if [ "$user_activity" = true ]; then
        # Prompt user to enter and confirm their timezone
        while true; do
            read -p $yellow"Enter Timezone$reset (e.g.,$blue America/New_York$reset): " timezone

            if [ -z "$timezone" ]; then
                echo -e "\033[31m Timezone cannot be empty. Please try again.\033[0m"
                continue
            fi

            # Check if the entered timezone is in the "Area/Location" format
            if [[ ! "$timezone" =~ ^[a-zA-Z]+/[a-zA-Z_]+$ ]]; then
                echo -e "\033[31mInvalid timezone format. Please enter in the format 'Area/Location' (e.g., America/New_York).\033[0m"
                continue
            fi

            export PI_HOLE_TZ="$timezone"
            break
        done
    fi
}

set_pihole_password() {
    #local adguard_yaml_file="./adguard/opt-adguard-conf/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false
    #local username="USER"

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_pihole_title
        echo "Press Enter to set Pihole Dashboard Password  $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random password: $(tput sgr0)"
        
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
        plaintext_pihole_pass=$(head /dev/urandom | tr -dc "$characters" | head -c 16)
        export PI_HOLE_PASS="$plaintext_pihole_pass"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Pihole Dashboard:$(tput sgr0)" pihole_pass 
            printf "%s\n" "$short_stars"
            

            if [[ -z "$pihole_pass" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for Pihole Dashboard:$(tput sgr0) " confirm_pihole_pass
            printf "%s\n" "$short_stars"
            

            if [[ "$pihole_pass" != "$confirm_pihole_pass" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                export PI_HOLE_PASS="$pihole_pass"
                break
            fi
        done
    fi

}

set_pihole_config() {
    clear
    set_pihole_tz
    set_pihole_password
}
