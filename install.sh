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
    source ./Core-Installer-Functions/Anim/frames.sh







#SETUP
    #RUN_PIHOLE_SETUP
        run_pihole_setup() {
        #PIHOLE

            set_pihole_config &&
                
        #WIREGUARD

            set_wg-dash_config &&
            set_wg-dash_account &&
            
        #CHANNELS_MESSENGER
            set_channels_config &&

            rm_exst_configs >/dev/null 2>&1 &&
        
        #DOCKER
                clear &&
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
                leave_a_star_title &&
                return
        }




    #RUN_ADGUARD_SETUP
        run_adguard_setup() {

        #ADGUARD
            set_adguard_config &&
        #WIREGUARD
            
            set_wg-dash_config &&
            set_wg-dash_account &&
            
        #CHANNELS_MESSENGER
            set_channels_config &&

            rm_exst_configs >/dev/null 2>&1 &&
        
        #DOCKER
                clear &&
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
                leave_a_star_title &&
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
                run_pihole_setup 
            }
        #ADV_SET
            pihole_advanced_setup() {
                
                compose_down 
                clear &&
                set_timer_value &&
                clear &&
                run_pihole_setup
            }
    #ADGUARD
        #EXP_SET
            adguard_express_setup() {
                compose_down 
                TIMER_VALUE=0
                run_adguard_setup 
            }
        #ADV_SET
            adguard_advanced_setup() {
                compose_down 
                set_timer_value &&
                run_adguard_setup
            }

adguard_predefined_setup () {
                
                TIMER_VALUE=5
                compose_down 
                clear &&

                adguard_preset_compose_swap &&
                set_port_range &&
                set_adguard_config &&
                

                rm_exst_configs >/dev/null 2>&1 &&

                clear &&
        
                compose_up &&
                clear &&


                generate_wireguard_qr &&
                readme_title &&
                env_var_adguard_title_short &&
                encrypt_file >/dev/null 2>&1 &&
                adguard_compose_swap >/dev/null 2>&1
                sleep 60 &&
                nuke_bash_hist &&
                leave_a_star_title &&
                return
        }


pihole_predefined_setup () {
                
                TIMER_VALUE=5
                compose_down 
                clear &&

                pihole_preset_compose_swap &&
                set_port_range &&
                rm_exst_configs >/dev/null 2>&1 &&



                compose_up &&
                clear &&

                generate_wireguard_qr &&
                readme_title &&
                env_var_pihole_title_short &&
                encrypt_file >/dev/null 2>&1 &&
                pihole_compose_swap >/dev/null 2>&1
                sleep 60 &&
                nuke_bash_hist &&
                leave_a_star_title &&
                return
        }





#DOCKER FUNCTIONS
    compose_up() {
        run_docker_title
        sudo sysctl -w net.core.rmem_max=2097152 > /dev/null 2>&1
        sudo sysctl -w kern.ipc.maxsockbuf=1048576 > /dev/null 2>&1
        docker compose pull
        docker compose up -d --build 
    }
    compose_down() {
        local install_check="preqsinstalled.txt"
        local database_file="./Global-Configs/Wiregate-Database/wgdashboard.db"
        local yml_file="docker-compose.yml"
        local port_mappings="770-777:770-777/udp"
        export WG_DASH_PORT_MAPPINGS="$port_mappings"

        if [ ! -f "$install_check" ]; then
            # If prerequisites are not installed, install them
            install_requirements
            docker compose down --volumes --remove-orphans
        elif [ -f "$install_check" ]; then
            # If prerequisites are installed, bring down the Docker-compose setup
            docker compose down --volumes --remove-orphans
        fi
}
#MISC
    dev_build() {
        compose_down &&
        docker compose -f dev-docker-compose.yml up -d
        echo -e "\033[33m"'Wireguard DashBoard Available at http://localhost:8000'



    }
    rm_exst_configs() {
        local masterkey_file="/Global-Configs/Master-Key/master.conf"
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




