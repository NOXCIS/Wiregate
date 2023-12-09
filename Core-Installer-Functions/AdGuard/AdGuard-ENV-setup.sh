#!/bin/bash

set_adguard_pass() {
    local adguard_yaml_file="./Global-Configs/AdGuard/Config/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false
    local username="USER"

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_adguard_title
        echo "Press Enter to set Adguard Password  $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random password: $(tput sgr0)"
        
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

        plaintext_adguard_pass=$(head /dev/urandom | tr -dc "$characters" | head -c 16)
        
        output=$(htpasswd -B -n -b "$username" "$plaintext_adguard_pass")

        # Use sed to delete the first 5 characters of $output and assign it to adguard_password
        adguard_password=$(echo "$output" | sed 's/.....//')


        sed -i -E "s|^( *password: ).*|\1$adguard_password|" "$adguard_yaml_file"

        export AD_GUARD_PASS="$plaintext_adguard_pass"


        
        echo -e "\033[32mPassword has been randomly Gernerated.\033[0m"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for AdGuard:$(tput sgr0)" adguard_pass 
            printf "%s\n" "$short_stars"
            

            if [[ -z "$adguard_pass" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for AdGuard:$(tput sgr0) " confirm_adguard_pass
            printf "%s\n" "$short_stars"
            

            if [[ "$adguard_pass" != "$confirm_adguard_pass" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the Database Password
                
                output=$(htpasswd -B -n -b "$username" "$adguard_pass")
                
                # Use sed to delete the first 5 characters of $output and assign it to adguard_password
                manual_adguard_password=$(echo "$output" | sed 's/.....//')
                

                sed -i -E "s|^( *password: ).*|\1$manual_adguard_password|" "$adguard_yaml_file"



                export AD_GUARD_PASS="$adguard_pass"



                break
            fi
        done
    fi

}
set_adguard_user() {
    local adguard_yaml_file="./Global-Configs/AdGuard/Config/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false


    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_uname_adguard_title
        echo "Press Enter to set AdGuard Username $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random username: $(tput sgr0)"
        
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
        adguard_user="${word1}_${word2}_${random_number}"

        sed -i -E "s|^( *- name: ).*|\1$adguard_user|" "$adguard_yaml_file"

        export AD_GUARD_USER="$adguard_user"


        
        echo -e "\033[32mUsername has been randomly Gernerated.\033[0m"
    fi


    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter Username for AdGuard:$(tput sgr0)" adguard_user 
            
            

            if [[ -z "$adguard_user" ]]; then
                echo -e "\033[31mUsername cannot be empty. Please try again.\033[0m"
                continue
            fi

                sed -i -E "s|^( *- name: ).*|\1$adguard_user|" "$adguard_yaml_file"

                export AD_GUARD_USER="$adguard_user"
                break
            
        done
    fi

}
set_adguard_config() {
    clear
    adguard_install_title
    set_adguard_user
    set_adguard_pass
}


