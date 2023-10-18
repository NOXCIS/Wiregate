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
    source ./Core-Installer-Functions/AdGuard/AdGuard-ENV-setup.sh







#SETUP
    #RUN_PIHOLE_SETUP
        run_pihole_setup() {
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
                encrypt_file >/dev/null 2>&1 &&
                env_var_pihole_title &&
                pihole_compose_swap >/dev/null 2>&1
                return
        }
    #RUN_ADGUARD_SETUP
        run_adguard_setup() {
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
                encrypt_file >/dev/null 2>&1 &&
                env_var_adguard_title &&
                adguard_compose_swap >/dev/null 2>&1
                return
        }



#SETUP OPTIONS
    #PIHOLE
        #EXP_SET
            pihole_express_setup() {
                
                compose_down >/dev/null 2>&1 &&
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
                
                compose_down >/dev/null 2>&1 &&
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
                clear &&
                pihole_install_title &&
                pihole_preset_compose_swap &&
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
                encrypt_file >/dev/null 2>&1 &&
                master_key_pass_title &&
                pihole_compose_swap 
                return
        }
    #ADGUARD
        #EXP_SET
            adguard_express_setup() {
                
                compose_down >/dev/null 2>&1 &&
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
                
                compose_down #>/dev/null 2>&1 &&
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
                clear &&
                adguard_install_title &&
                adguard_preset_compose_swap &&
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
                encrypt_file >/dev/null 2>&1 &&
                master_key_pass_title &&
                adguard_compose_swap 
                return
        }

#DOCKER FUNCTIONS
    compose_up() {
        sudo sysctl -w net.core.rmem_max=2097152 > /dev/null 2>&1
        sudo sysctl -w kern.ipc.maxsockbuf=1048576 > /dev/null 2>&1

        docker compose up -d --build 
    }
    compose_down() {
        local yml_file="docker-compose.yml"
        port_mappings="770-777:770-777/udp"
        export PORT_MAPPINGS="$port_mappings"
        docker compose down --volumes --remove-orphans

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



# Usage: encrypt_file /path/to/file.txt my_password







# Main script
    if [ $# -eq 0 ]; then
        menu
    else
    case $1 in
        advanced) advanced_setup ;;
        auto) express_setup ;;
        fresh) fresh_install ;;
        preset) predefined_setup ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



#rm docker-compose.yml
