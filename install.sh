#!/bin/bash

set -e
export DEBIAN_FRONTEND=noninteractive
export TIMER_VALUE=0
source ./Core-Installer-Functions/OS-Reqs.sh
source ./Core-Installer-Functions/Title.sh
source ./Core-Installer-Functions/Reset-WormHole.sh
source ./Core-Installer-Functions/Channels/Channels-ENV-setup.sh
source ./Core-Installer-Functions/Pihole/Pihole-ENV-setup.sh
source ./Core-Installer-Functions/WG-Dash/WG-Dash-ENV-setup.sh


menu() {
    title
    echo "Please choose an option:"
    echo "1. Express Install"
    echo "2. Advanced Install"
    echo "3. Auto configuration with quickset for # of Server Interfaces to Generate & Pihole Password"
    echo "4. Reset Wormhole Deployment"
    echo "5. Exit"
    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) express_setup ;;
        2) advanced_setup ;;
        3) auto_set_wct ;;
        4) fresh_install ;;
        5) exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}




#SETUP

run_setup() {
            
            update_root_hints >/dev/null 2>&1 &&
            set_pihole_tz_title &&
            set_pihole_tz &&
            set_server_ip_title &&
            update_server_ip &&
            
            set_channels_key &&
            set_uname_channel_title &&
            set_channels_DB_user &&
            set_pass_channel_title &&
            set_channels_DB_pass &&

            rm_exst_configs >/dev/null 2>&1 &&
            run_docker_title &&
            compose_up &&
            clear &&

            generate_wireguard_qr &&
            readme_title &&
            env_var_title 
            return
}


#SETUP OPTIONS
express_setup() {
    run_os_update &&
    install_prerequisites &&
    TIMER_VALUE=0
    title &&
    set_config_count &&
    set_port_range &&
    set_pihole_password &&
    TIMER_VALUE=0 
    run_setup 
}
advanced_setup() {
    run_os_update &&
    install_prerequisites &&
    title &&
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "The Timer value dictates how much time you will have in each setup step."
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    read -p "Enter the timer value (in seconds): " TIMER_VALUE
    echo ""
    echo -e "Timer value set to \033[32m$TIMER_VALUE\033[0m seconds."
    echo ""
    set_config_count &&
    set_port_range &&
    set_pihole_password &&
    run_setup
}
auto_set_wct() {
    run_os_update &&
    install_prerequisites &&
    TIMER_VALUE=5
    title &&
    set_config_count &&
    set_port_range &&
    set_pihole_password &&
    TIMER_VALUE=0
    run_setup 

}



#DOCKER FUNCTIONS
compose_up() {
    sudo sysctl -w net.core.rmem_max=2097152 > /dev/null 2>&1
    docker compose up -d --build 
}

#MISC
update_root_hints() {
    # Define the URL for the root server hints file and its MD5 hash
    ROOT_HINTS_URL="https://www.internic.net/domain/named.root"
    MD5_HASH_URL="https://www.internic.net/domain/named.root.md5"

    # Download the MD5 hash file and send its output to /dev/null
    if ! curl -s -o "named.root.md5" "$MD5_HASH_URL" > /dev/null 2>&1; then
        echo "Failed to download MD5 hash file from $MD5_HASH_URL"
        return 1
    fi

    # Extract the MD5 hash value from the downloaded file
    EXPECTED_HASH=$(cat "named.root.md5" | awk '{print $1}')

    # Download the root server hints file and send its output to /dev/null
    wget -O root.hints "$ROOT_HINTS_URL" > /dev/null 2>&1

    # Calculate the MD5 hash of the downloaded root hints file
    ACTUAL_HASH=$(md5sum root.hints | awk '{print $1}')

    # Compare the calculated MD5 hash with the expected MD5 hash
    if [ "$ACTUAL_HASH" = "$EXPECTED_HASH" ]; then
        echo "Root server hints file downloaded and verified successfully."
    else
        echo "Error: Root server hints file download or verification failed."
        rm -f root.hints  # Remove the file in case of failure
    fi

    mv root.hints Global-Configs/Unbound/root.hints

    # Clean up the downloaded MD5 hash file
    rm -f named.root.md5
}
rm_exst_configs() {
    local masterkey_file="./WG-Dash/master-key/master.conf"
    local config_folder="./WG-Dash/config"

    if [ -f "$masterkey_file" ]; then
            echo "Removing existing '$masterkey_file'..."
            sudo rm "$masterkey_file"
            echo "Existing '$masterkey_file' removed."
        fi

        if [ -d "$config_folder" ]; then
            echo "Removing existing '$config_folder'..."
            sudo rm -r "$config_folder"
            echo "Existing '$config_folder' removed."
        fi
}






# Main script
    if [ $# -eq 0 ]; then
        menu
    else
    case $1 in
        manual) manual_setup ;;
        headless) auto_setup ;;
        fresh) fresh_install ;;
        quickcount) auto_set_wct ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



#rm docker-compose.yml
