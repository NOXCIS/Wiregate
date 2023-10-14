#!/bin/bash

set -e
export DEBIAN_FRONTEND=noninteractive
export TIMER_VALUE=0


#CORE_IMPORTS
    source ./Core-Installer-Functions/OS-Reqs.sh
    source ./Core-Installer-Functions/Menu.sh
    source ./Core-Installer-Functions/Title.sh
    source ./Core-Installer-Functions/Reset-WormHole.sh
    source ./Core-Installer-Functions/Channels/Channels-ENV-setup.sh
    source ./Core-Installer-Functions/Pihole/Pihole-ENV-setup.sh
    source ./Core-Installer-Functions/WG-Dash/WG-Dash-ENV-setup.sh







#SETUP
    run_setup() {
            
        update_root_hints >/dev/null 2>&1 &&

    #PIHOLE
        set_pihole_tz_title &&
        set_pihole_tz &&
            
    #WIREGUARD
        set_server_ip_title &&
        update_server_ip &&
            
    #CHANNELS_MESSENGER
        #CM_APP
            set_channels_key &&
        #CM_DB
            set_uname_channel_title &&
            set_channels_DB_user &&
            set_pass_channel_title &&
            set_channels_DB_pass &&
        #CM_DB_URI    
            set_channels_DB_URI &&

            rm_exst_configs >/dev/null 2>&1 &&
    
    #DOCKER
            run_docker_title &&
            compose_up &&
            clear &&


    #FINAL_OUTPUT
            generate_wireguard_qr &&
            readme_title &&
            env_var_title 
            return
    }


#SETUP OPTIONS
    #EXP_SET
        express_setup() {
            run_os_update &&
            install_prerequisites &&
            TIMER_VALUE=0
            title &&
            set_config_count &&
            set_port_range &&
            set_pihole_password &&
            run_setup 
        }
    #ADV_SET
        advanced_setup() {
            run_os_update &&
            install_prerequisites &&
            title &&
            set_timer_value &&
            set_config_count &&
            set_port_range &&
            set_pihole_password &&
            run_setup
        }
    #QC_SET
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


    #docker compose down --volumes
    #sudo sed -i '/ports:/,/sysctls:/ {//!d}; /ports:/a\ \ \ \ \ \ - 51820:51820\/udp' "$yml_file"
    docker compose down --volumes 

    if [ -f "$masterkey_file" ]; then
            echo "Removing existing '$masterkey_file'..."
            sudo rm "$masterkey_file"
            echo "Existing '$masterkey_file' removed."
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
