#!/bin/bash

set -e
export HISTFILE=/dev/null
export DEBIAN_FRONTEND=noninteractive
export DOCKER_CONTENT_TRUST=1
export TIMER_VALUE=0


#CORE_IMPORTS
    source ./Core-Installer-Functions/OS-Reqs.sh
    source ./Core-Installer-Functions/Menu.sh
    source ./Core-Installer-Functions/Title.sh
    source ./Core-Installer-Functions/Reset-WormHole.sh
    source ./Core-Installer-Functions/Channels/Channels-ENV-setup.sh
    source ./Core-Installer-Functions/Pihole/Pihole-ENV-setup.sh
    source ./Core-Installer-Functions/WG-Dash/WG-Dash-ENV-setup.sh
    source ./Core-Installer-Functions/AdGuard/AdGuard-ENV-setup.sh







#SETUP
    #RUN_PIHOLE_SETUP
        run_pihole_setup() {
        #PIHOLE
            set_pihole_tz_title &&
            set_pihole_tz &&
                
        #WIREGUARD
            set_wg-dash_key &&
            set_server_ip_title &&
            update_server_ip &&
            set_wg-dash_user &&
            set_wg-dash_pass &&
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
                clear &&
                run_docker_title &&
                compose_up &&
                clear &&


        #FINAL_OUTPUT
                generate_wireguard_qr &&
                readme_title &&
                encrypt_file >/dev/null 2>&1 &&
                env_var_pihole_title &&
                pihole_compose_swap >/dev/null 2>&1
                sleep 60 &&
                nuke_bash_hist &&
                return
        }
    #RUN_ADGUARD_SETUP
        run_adguard_setup() {
        #WIREGUARD
            set_wg-dash_key &&
            set_server_ip_title &&
            update_server_ip &&
            set_wg-dash_user &&
            set_wg-dash_pass &&
                
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
                clear &&
                run_docker_title &&
                compose_up &&
                clear &&


        #FINAL_OUTPUT
                generate_wireguard_qr  &&
                readme_title &&
                encrypt_file >/dev/null 2>&1 &&
                env_var_adguard_title &&
                adguard_compose_swap >/dev/null 2>&1
                sleep 60 &&
                nuke_bash_hist &&
                return
        }



#SETUP OPTIONS
    #PIHOLE
        #EXP_SET
            pihole_express_setup() {
                
                compose_down 
                clear &&
                TIMER_VALUE=0
                clear &&
                pihole_install_title &&
                set_config_count &&
                set_port_range &&
                set_pihole_password &&
                run_pihole_setup 
            }
        #ADV_SET
            pihole_advanced_setup() {
                
                compose_down 
                clear &&
                pihole_install_title &&
                set_timer_value &&
                set_config_count &&
                set_port_range &&
                set_pihole_password &&
                run_pihole_setup
            }
        #PRE_SET
            pihole_predefined_setup () {
                
                TIMER_VALUE=5
                compose_down 
                clear &&
                pihole_install_title &&
                pihole_preset_compose_swap &&
                set_pihole_password &&
                set_wg-dash_user &&
                set_wg-dash_pass &&
                rm_exst_configs >/dev/null 2>&1 &&
                clear &&
                run_docker_title &&
                compose_up &&
                clear &&
                generate_wireguard_qr &&
                readme_title &&
                encrypt_file >/dev/null 2>&1 &&
                env_var_pihole_title &&
                pihole_compose_swap >/dev/null 2>&1
                sleep 60 &&
                nuke_bash_hist &&
                return
        }
    #ADGUARD
        #EXP_SET
            adguard_express_setup() {
                
                compose_down 
                clear &&
                TIMER_VALUE=0
                clear &&
                adguard_install_title &&
                set_config_count &&
                set_port_range &&
                set_adguard_user &&
                set_adguard_pass &&
                run_adguard_setup 
            }
        #ADV_SET
            adguard_advanced_setup() {
                
                compose_down 
                clear &&
                adguard_install_title &&
                set_timer_value &&
                set_config_count &&
                set_port_range &&
                set_adguard_user &&
                set_adguard_pass &&
                run_adguard_setup
            }
        #PRE_SET
            adguard_predefined_setup () {
                
                TIMER_VALUE=5
                compose_down 
                clear &&
                adguard_install_title &&
                adguard_preset_compose_swap &&
                sqwip &&
                set_adguard_user &&
                set_adguard_pass &&
                set_wg-dash_user &&
                set_wg-dash_pass &&
                rm_exst_configs >/dev/null 2>&1 &&
                clear &&
                run_docker_title &&
                compose_up &&
                clear &&
                generate_wireguard_qr &&
                readme_title &&
                encrypt_file >/dev/null 2>&1 &&
                env_var_adguard_title &&
                adguard_compose_swap >/dev/null 2>&1
                sleep 60 &&
                nuke_bash_hist &&
                return
        }

#DOCKER FUNCTIONS
    compose_up() {
        sudo sysctl -w net.core.rmem_max=2097152 > /dev/null 2>&1
        sudo sysctl -w kern.ipc.maxsockbuf=1048576 > /dev/null 2>&1
        docker compose pull
        docker compose up -d --build 
    }
    compose_down() {
        local yml_file="docker-compose.yml"
        local port_mappings="770-777:770-777/udp"
        export PORT_MAPPINGS="$port_mappings"

        # Check if the 'docker' command is available

        REQUIRED_PACKAGES=(
        "curl"
        "qrencode"
        "gpg"
        "openssl"
        "docker"
        
    )

    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! command -v "$package" &>/dev/null; then
            echo "Error: '$package' command not found. Installing requirements..."
            install_requirements
            return 0
        fi
    done






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
    salt=$(openssl rand -base64 8 | tr -d '=')

    # Derive the encryption key from the password and salt using PBKDF2
    encryption_key=$(echo -n "$password$salt" | openssl dgst -sha256 -binary | xxd -p -c 256)

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
    nuke_bash_hist() {
        # Overwrite ~/.bash_history with "noxcis" 42 times
        for i in {1..42}; do
        # Generate a 42-character long random string
        random_string=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 42 ; echo '')
        # Overwrite ~/.bash_history with the random string
        echo "$random_string" > ~/.bash_history
        shred -u ~/.bash_history
        done
        history -c
        clear
}



# Usage: encrypt_file /path/to/file.txt my_password







# Main script
    if [ $# -eq 0 ]; then
        menu
    else
    case $1 in
        pi-exp) pihole_express_setup ;;
        pi-adv) pihole_advanced_setup ;;
        pi-predef) pihole_predefined_setup ;;
        ad-exp) adguard_express_setup ;;
        ad-adv) adguard_advanced_setup ;;
        ad-predef) adguard_predefined_setup ;;
        install_requirements) install_requirements ;;
        fresh) fresh_install ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



#rm docker-compose.yml
