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



run_config() {
    local config=$1

    # Common steps for all configurations
    compose_down
    TIMER_VALUE=${TIMER_VALUE:-0}

    case $config in
        "Ex-AdG-D" | "Adv-AdG-D" | "Pre_Conf-AdG-D")
            adguard_dwire_cswap
            run_adguard_setup
            ;;
        "Ex-AdG-Chnls" | "Adv-AdG-Chnls" | "Pre_Conf-AdG-Chnls")
            adguard_channl_cswap
            run_adguard_setup
            ;;
        "Ex-Pih-D" | "Adv-Pih-D" | "Pre_Conf-Pih-D")
            pihole_dwire_cswap
            run_pihole_setup
            ;;
        "Ex-Pih-Chnls" | "Adv-Pih-Chnls" | "Pre_Conf-Pih-Chnls")
            pihole_channl_cswap
            run_pihole_setup
            ;;
        "Adv-AdG-D" | "Adv-AdG-Chnls" | "Adv-Pih-D" | "Adv-Pih-Chnls")
            set_timer_value
            ;;
        "Pre_Conf-AdG-D" | "Pre_Conf-AdG-Chnls")
            clear &&
            adguard_preset_${config#*-*} &&
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
            sleep 60 &&
            nuke_bash_hist &&
            leave_a_star_title
            ;;
        "Pre_Conf-Pih-D" | "Pre_Conf-Pih-Chnls")
            clear &&
            pihole_preset_${config#*-*} &&
            set_port_range &&
            rm_exst_configs >/dev/null 2>&1 &&
            compose_up &&
            clear &&
            generate_wireguard_qr &&
            readme_title &&
            env_var_pihole_title_short &&
            encrypt_file >/dev/null 2>&1 &&
            sleep 60 &&
            nuke_bash_hist &&
            leave_a_star_title
            ;;
        *)
            echo "Unknown configuration: $config"
            return 1
            ;;
    esac

    # Return early for Pre_Conf cases to avoid redundant code
    [[ "$config" == Pre_Conf-* ]] && return
}




run_pihole_setup() {
    set_pihole_config &&
    set_wg-dash_config &&
    set_wg-dash_account &&
    set_dwire_config &&
    set_channels_config &&
    rm_exst_configs >/dev/null 2>&1 &&
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
run_adguard_setup() {
    set_adguard_config &&
    set_wg-dash_config &&
    set_wg-dash_account &&
    set_dwire_config &&

    rm_exst_configs >/dev/null 2>&1 &&  
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
        ad-exp-dwire) set_tag; Express-AdGuard-Darkwire ;;
        ad-exp-channl) set_tag; Express-AdGuard-Channels ;;
        pi-exp-dwire) set_tag; Express-Pihole-Darkwire ;;
        pi-exp-channl) set_tag; Express-Pihole-Channels ;;
        ad-adv-dwire) set_tag; Advanced-AdGuard-Darkwire ;;
        ad-adv-channl) set_tag; Advanced-AdGuard-Channels ;;
        pi-adv-dwire) set_tag; Advanced-Pihole-Darkwire ;;
        pi-adv-channl) set_tag; Advanced-Pihole-Channels ;;
        ad-predef-dwire) set_tag; Pre_Configured-AdGuard-Darkwire ;;
        ad-predef-channl) set_tag; Pre_Configured-AdGuard-Channels ;;
        pi-predef-dwire) set_tag; Pre_Configured-Pihole-Darkwire ;;
        pi-predef-channl) set_tag; Pre_Configured-Pihole-Channels ;;    
        requirements) install_requirements ;;
        reset) fresh_install ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi




