#!/bin/bash

set -e
export HISTFILE=/dev/null
export DEBIAN_FRONTEND=noninteractive
export DOCKER_CONTENT_TRUST=1
export TIMER_VALUE=0
export DEPLOY_TYPE="CLOUD DEPLOYMENT MODE"

#CORE_IMPORTS
    source ./Core-Installer-Functions/OS-Reqs.sh
    source ./Core-Installer-Functions/Menu.sh
    source ./Core-Installer-Functions/Title.sh
    source ./Core-Installer-Functions/Reset-WormHole.sh
    source ./Core-Installer-Functions/Darkwire/Darkwire-ENV-setup.sh
    source ./Core-Installer-Functions/Channels/Channels-ENV-setup.sh
    source ./Core-Installer-Functions/Pihole/Pihole-ENV-setup.sh
    source ./Core-Installer-Functions/WG-Dash/WG-Dash-ENV-setup.sh
    source ./Core-Installer-Functions/AdGuard/AdGuard-ENV-setup.sh
    source ./Core-Installer-Functions/Anim/frames.sh


setup_environment() {
    local mode=$1
    local system=$2
    local config_type=$3
    local setup_func
    export $config_type
    export $system



    case "$mode" in
        "Express")
            title  
            sleep 2
            compose_down
            clear
            setup_func="run_${system}_setup"
            ;;
        "Advanced")
            title  
            sleep 2
            compose_down
            clear
            setup_func="run_${system}_setup"
            ;;
        "Pre_Configured")
            title  
            sleep 2
            compose_down
            clear
            set_timer_value
            ;;
        *)
            echo "Unknown mode: $mode"
            return 1
            ;;
    esac

    case "$system" in
        "AdGuard")
            if [ "$mode" = "Pre_Configured" ]; then
                case "$config_type" in
                    "Darkwire")
                        adguard_preset_dwire_cswap
                        ;;
                    "Channels")
                        adguard_preset_channl_cswap
                        ;;
                esac
                set_wg-dash_config 
                set_wg-dash_account
                set_port_range
                set_adguard_config
            else
                case "$config_type" in
                    "Darkwire")
                        adguard_dwire_cswap
                        ;;
                    "Channels")
                        adguard_channl_cswap
                        ;;
                esac
            fi
            ;;
        "Pihole")
            if [ "$mode" = "Pre_Configured" ]; then
                case "$config_type" in
                    "Darkwire")
                        pihole_preset_dwire_cswap
                        ;;
                    "Channels")
                        pihole_preset_channl_cswap
                        ;;
                esac
                set_port_range
            else
                case "$config_type" in
                    "Darkwire")
                        pihole_dwire_cswap
                        ;;
                    "Channels")
                        pihole_channl_cswap

                        ;;
                esac
            fi
            ;;
        *)
            echo "Unknown system: $system"
            return 1
            ;;
    esac

    case "$mode" in
        "Pre_Configured")
            rm_exst_configs >/dev/null 2>&1
            compose_up
            clear
            mkey_output
            ;;
        *)
            if [ "$mode" = "Advanced" ]; then
                set_timer_value
            fi
            $setup_func
            ;;
    esac
}

run_pihole_setup() {
    set_pihole_config &&
    set_wg-dash_config &&
    set_wg-dash_account &&
        if [ "$config_type" = "Channels" ]; then
            set_channels_config 
        elif [ "$config_type" = "Darkwire" ]; then
            set_dwire_config 
        fi
    rm_exst_configs >/dev/null 2>&1 &&
    clear &&
    compose_up &&
    clear &&
    mkey_output
}
run_AdGuard_setup() {
        set_adguard_config &&
        set_wg-dash_config &&
        set_wg-dash_account &&
            if [ "$config_type" = "Channels" ]; then
                set_channels_config 
            elif [ "$config_type" = "Darkwire" ]; then 
                set_dwire_config 
            fi
        rm_exst_configs >/dev/null 2>&1 &&  
        clear &&
        compose_up &&
        clear &&
        mkey_output
}
mkey_output() {
    #FINAL_OUTPUT
            generate_wireguard_qr  &&
            readme_title &&
            encrypt_file >/dev/null 2>&1 &&
            if [ "$system" = "AdGuard" ]; then
                env_var_adguard_title
                adguard_compose_swap >/dev/null 2>&1

            elif [ "$system" = "Pihole" ]; then 
                env_var_pihole_title 
                pihole_compose_swap >/dev/null 2>&1
            fi
            
            adguard_compose_swap >/dev/null 2>&1
            sleep 60 &&
            nuke_bash_hist &&
            leave_a_star_title &&
                        return
}

#DOCKER FUNCTIONS
    compose_up() {
        set_tag
        run_docker_title
        docker compose pull
        docker compose up -d --build 
    }
    compose_down() {
        local install_check="preqsinstalled.txt"
        local yml_file="docker-compose.yml"
        local port_mappings="770-777:770-777/udp"
        export WG_DASH_PORT_MAPPINGS="$port_mappings"

        if [ ! -f "$install_check" ]; then
            # If prerequisites are not installed, install them
            install_requirements
            docker compose down --remove-orphans && 
            docker volume ls -q | grep 'wg_data' | xargs -r docker volume rm
        elif [ -f "$install_check" ]; then
            # If prerequisites are installed, bring down the Docker-compose setup
            docker compose down --remove-orphans #&& 
            #docker volume ls -q | grep 'wg_data' | xargs -r docker volume rm
        fi
}
#MISC
        set_tag() {
        # Docker Hub repository
        REPO="noxcis/wg-dashboard"

        # Fetch the tags from Docker Hub API
        response=$(curl -s "https://hub.docker.com/v2/repositories/${REPO}/tags/?page_size=100")

        # Extract the latest updated tag that doesn't contain 'beta' or 'dev' using jq
        latest_tag=$(echo $response | jq -r '[.results[] | select(.name | test("beta|dev"; "i") | not)] | sort_by(.last_updated) | last(.[]).name')

        # Check if the tag is extracted
        if [ -z "$latest_tag" ]; then
            echo "Failed to fetch a non-beta/non-dev latest updated tag."
            exit 1
        else
            echo "Latest non-beta/non-dev updated tag: $latest_tag"
        fi
        export TAG="$latest_tag"

    }

    dev_build() {
        local adguard_yaml_file="./Global-Configs/AdGuard/Config/AdGuardHome.yaml"
        local adguard_password='$2a$12$t6CGhUcXtY6lGF2/A9Jd..Wn315A0RIiuhLlHbNHG2EmDbsN7miwO'
        local adguard_user="admin"
        compose_down &&
        sed -i -E "s|^( *password: ).*|\1$adguard_password|" "$adguard_yaml_file"
        sed -i -E "s|^( *- name: ).*|\1$adguard_user|" "$adguard_yaml_file"
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
        E-A-D) setup_environment "Express" "AdGuard" "Darkwire" ;;
        E-A-C) setup_environment "Express" "AdGuard" "Channels" ;;
        E-P-D) setup_environment  "Express" "Pihole" "Darkwire" ;;
        E-P-C) setup_environment  "Express" "Pihole" "Channels" ;;
        A-A-D) setup_environment "Advanced" "AdGuard" "Darkwire" ;;
        A-A-C) setup_environment "Advanced" "AdGuard" "Channels" ;;
        A-P-D) setup_environment  "Advanced" "Pihole" "Darkwire" ;;
        A-P-C) setup_environment  "Advanced" "Pihole" "Channels" ;;
        P_Conf-A-D) setup_environment "Pre_Configured" "AdGuard" "Darkwire" ;;
        P_Conf-A-C) setup_environment "Pre_Configured" "AdGuard" "Channels" ;;
        P_Conf-P-D) setup_environment "Pre_Configured" "Pihole" "Darkwire" ;;
        P_Conf-P-C) setup_environment "Pre_Configured" "Pihole" "Channels" ;;
        requirements) install_requirements ;;
        reset) fresh_install ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



