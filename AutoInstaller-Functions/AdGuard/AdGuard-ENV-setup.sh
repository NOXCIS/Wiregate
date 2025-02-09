#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

set_adguard_pass() {
    local adguard_yaml_file="./configs/adguard/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false
    local username="USER"

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_adguard_title
        echo "Press Enter to set AdGuard Password $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for a random$(tput sgr0)$(tput setaf 4) password$(tput sgr0):"
        
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
        plaintext_adguard_pass=$(pwgen -s 16 1)  # Generate a secure 16-character password
        output=$(htpasswd -B -n -b "$username" "$plaintext_adguard_pass")

        # Extract the password hash from the htpasswd output
        adguard_password=$(echo "$output" | sed 's/.....//')

        # Update the AdGuardHome YAML file with the hashed password
        sed -i -E "s|^( *password: ).*|\1$adguard_password|" "$adguard_yaml_file"

        export AD_GUARD_PASS="$plaintext_adguard_pass"
        echo -e "$(tput setaf 2)Random password for AdGuard set to: $plaintext_adguard_pass$(tput sgr0)"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for AdGuard:$(tput sgr0) " adguard_pass
            printf "\n%s\n" "$short_stars"
            
            if [[ -z "$adguard_pass" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for AdGuard:$(tput sgr0) " confirm_adguard_pass
            printf "\n%s\n" "$short_stars"
            
            if [[ "$adguard_pass" != "$confirm_adguard_pass" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the AdGuard password
                output=$(htpasswd -B -n -b "$username" "$adguard_pass")
                
                # Extract the password hash from the htpasswd output
                manual_adguard_password=$(echo "$output" | sed 's/.....//')
                
                # Update the AdGuardHome YAML file with the hashed password
                sed -i -E "s|^( *password: ).*|\1$manual_adguard_password|" "$adguard_yaml_file"

                export AD_GUARD_PASS="$adguard_pass"
                echo -e "$(tput setaf 2)Password for AdGuard has been successfully set.$(tput sgr0)"
                break
            fi
        done
    fi
}

set_adguard_user() {
    local adguard_yaml_file="./configs/adguard/AdGuardHome.yaml"
    local timer=$TIMER_VALUE
    local user_activity=false


    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_uname_adguard_title
        echo "Press Enter to set AdGuard Username $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for random$blue username$reset: $(tput sgr0)"
        
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
        adguard_user="${word1}_${word2}_${random_number}"

        sed -i -E "s|^( *- name: ).*|\1$adguard_user|" "$adguard_yaml_file"

        export AD_GUARD_USER="$adguard_user"

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
    set_adguard_user
    set_adguard_pass
}


