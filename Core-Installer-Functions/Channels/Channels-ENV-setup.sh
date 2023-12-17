#!/bin/bash
set_channels_key() {
    # Generate a 512-bit random key using OpenSSL and convert it to hexadecimal
    secret_key_hex=$(openssl rand -hex 64)
    # Export the key to the MSG_SECRET_KEY variable
    export MSG_SECRET_KEY="$secret_key_hex"
}
set_channels_DB_pass() {
    local db_password=""
    local confirm_db_pass=""
    local timer=$TIMER_VALUE
    local user_activity=false

    while [ $timer -gt 0 ]; do
        clear  # Clear the screen

        # Print the updated timer value
        set_pass_channel_title
        echo "Press Enter to set Channels Database Password  $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for a random password: $(tput sgr0)"
        
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
        db_password=$(head /dev/urandom | tr -dc "$characters" | head -c 32)
        export MSG_DB_PASS="$db_password"
    fi

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Channels Database:$(tput sgr0)" db_password 
            printf "%s\n" "$short_stars"
            

            if [[ -z "$db_password" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -sp "$(tput setaf 3)Confirm password for Channels Database:$(tput sgr0) " confirm_db_pass
            printf "%s\n" "$short_stars"
            

            if [[ "$db_password" != "$confirm_db_pass" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the Database Password
                export MSG_DB_PASS="$db_password"



                break
            fi
        done
    fi

}
set_channels_DB_user() {
    local db_user=""
    local confirm_user=""
    local timer=$TIMER_VALUE
    local user_activity=false


    while [ $timer -gt 0 ]; do
        clear  # Clear the screen
        # Print the updated timer value
        set_uname_channel_title
        echo "Press Enter to set Channels Database Username $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$timer$(tput sgr0)$(tput setaf 1) seconds for a random username: $(tput sgr0)"
        
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
        db_user=$(head /dev/urandom | tr -dc "$characters" | head -c 32)
        export MSG_DB_USER="$db_user"
    
        echo -e "\033[32mUsername has been randomly Gernerated.\033[0m"
    fi


    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -p "$(tput setaf 3)Enter Username for Channels Database:$(tput sgr0)" db_user 
            
            

            if [[ -z "$db_user" ]]; then
                echo -e "\033[31mUsername cannot be empty. Please try again.\033[0m"
                continue
            fi
            
            read -p "$(tput setaf 3)Confirm Username for Channels Database:$(tput sgr0) " confirm_user
            
            

            if [[ "$db_user" != "$confirm_user" ]]; then
                echo -e "\033[31mUsernames do not match. Please try again.\033[0m"
            else
                # Passwords match, set the Database Password
                export MSG_DB_USER="$db_user"
                break
            fi
        done
    fi

}
set_channels_DB_URI() {
    
    db_uri="postgresql://$MSG_DB_USER:$MSG_DB_PASS@db:5432/db"
    export DB_URI="$db_uri"

}

set_channels_config() {
    set_channels_key
    set_channels_DB_user
    set_channels_DB_pass
    set_channels_DB_URI
}


