#!/bin/bash

set_pihole_tz() {
    local yml_file="docker-compose.yml"
    read -t $TIMER_VALUE -p "Do you want to automatically get the host timezone? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    if [[ $answer == [Yy] || -z $answer ]]; then
        timezone=$(cat /etc/timezone)
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
    else
        read -p "Enter timezone $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)America/New_York$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " timezone
        if [[ -z $timezone ]]; then
            timezone="America/New_York"
        fi
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
    fi
    export TIMEZONE="$timezone"
}
set_pihole_password() {
    local password=""
    local confirm_password=""
    local timer=$TIMER_VALUE
    local user_activity=false

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_pihole_title
        echo "Press any key to set Pihole Dashboard Password $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for a random password: $(tput sgr0)"
        
        # Decrement the timer value by 1
        timer=$((timer - 1))

        # Check for user activity
        if read -t 1 -n 1; then
            user_activity=true
            break
        fi
    done

    if [ $timer -le 0 ] && [ "$user_activity" = false ]; then
        characters="A-Za-z0-9"
        password=$(head /dev/urandom | tr -dc "$characters" | head -c 16)
        export PI_HOLE_PASS="$password"
        echo ""
        echo -e "\033[32mPassword has been randomly Gernerated.\033[0m"
    fi

    if [ "$user_activity" = true ]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Pihole Dashboard:$(tput sgr0)" password 
            echo ""

            if [ -z "$password" ]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi

            echo ""
            read -sp "$(tput setaf 3)Confirm password for Pihole Dashboard:$(tput sgr0) " confirm_password

            if [ "$password" != "$confirm_password" ]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the WEBPASSWORD environment variable
                export PI_HOLE_PASS="$password"

                break
            fi
        done
    fi
}


