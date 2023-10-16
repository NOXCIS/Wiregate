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
            encrypt_file &&
            env_var_title &&
            compose_reset 
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
    #PRE_SET
        predefined_setup () {
            run_os_update &&
            install_prerequisites &&
            TIMER_VALUE=5
            title &&
            preset_compose_swap &&
            set_server_ip_title &&
            update_server_ip &&
            set_config_count &&
            set_port_range &&
            rm_exst_configs >/dev/null 2>&1 &&
            run_docker_title &&
            compose_up &&
            clear &&
            generate_wireguard_qr &&
            readme_title &&
            encrypt_file &&
            master_key_pass_title &&
            compose_reset 
            return

        }
#DOCKER FUNCTIONS
    compose_up() {
        sudo sysctl -w net.core.rmem_max=2097152 > /dev/null 2>&1
        sudo sysctl -w kern.ipc.maxsockbuf=1048576 > /dev/null 2>&1

        docker compose restart -d --build 
    }
    compose_down() {
        docker compose down --volumes
    }
#MISC
    rm_exst_configs() {
        local masterkey_file="./WG-Dash/master-key/master.conf"
        local config_folder="./WG-Dash/config"
           

        if [ -f "$masterkey_file" ]; then
            echo "Removing existing '$masterkey_file'..."
            sudo rm "$masterkey_file"
            echo "Existing '$masterkey_file' removed."
        fi

        
    }
    encrypt_file() {
    local characters="A-Za-z0-9!@#$%^&*()"
    local file_path="./WG-Dash/master-key/master.conf"
    local password=$(head /dev/urandom | tr -dc "$characters" | head -c 16)

    # Generate a salt
    salt=$(openssl rand -base64 8)

    # Derive the encryption key from the password and salt using PBKDF2
    encryption_key=$(openssl enc -aes-256-cbc -pass "pass:$password" -P "salt=$salt" | awk -F= '/key/{print $2}' | base64 -d)

    # Encrypt the file using aes-256-cbc algorithm with the derived key
    openssl enc -aes-256-cbc -in "$file_path" -out "${file_path}.enc" -K "$encryption_key" -iv 0

    if [ $? -eq 0 ]; then
        echo "Worm-Hole Master Key encrypted successfully."
        # You can optionally remove the original unencrypted file
        rm "$file_path"
    else
        echo "Worm-Hole Master Key encryption failed."
    fi
    export MASTER_KEY_PASSWORD="$password"
}


# Usage: encrypt_file /path/to/file.txt my_password







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
