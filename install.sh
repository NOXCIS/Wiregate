#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
export STATE="wiregate"
export HISTFILE=/dev/null
export DEBIAN_FRONTEND=noninteractive
export DOCKER_CONTENT_TRUST=1
export TIMER_VALUE=0
export DEPLOY_SYSTEM="docker"
export DEPLOY_TYPE="false"
export WGD_TOR_PROXY="false"
export WGD_TOR_PLUGIN="obfs4"
export WGD_TOR_BRIDGES="false"
export WGD_TOR_EXIT_NODES="default"
export WGD_TOR_DNS_EXIT_NODES="default"
export AMNEZIA_WG="false"
export PROTOCOL_TYPE="WireGuard"
export DEPLOY_STATE="STATIC"

#CORE_IMPORTS
source ./AutoInstaller-Functions/OS-Reqs.sh
source ./AutoInstaller-Functions/Menu.sh
source ./AutoInstaller-Functions/Title.sh
source ./AutoInstaller-Functions/Reset-WormHole.sh
source ./AutoInstaller-Functions/Pihole/Pihole-ENV-setup.sh
source ./AutoInstaller-Functions/WG-Dash/WG-Dash-ENV-setup.sh
source ./AutoInstaller-Functions/AdGuard/AdGuard-ENV-setup.sh
source ./AutoInstaller-Functions/Anim/frames.sh


setup_environment() {
    local mode=$1
    local system=$2
    local config_type=$3
    export config_type
    export system
    clear
    run_animation_seq
    case "$mode" in
        "Express")
            title  
            sleep 2
            compose_down
            clear
            
            if [ "$system" = "AdGuard" ]; then
                case "$config_type" in  
                    "Darkwire")
                        adguard_dwire_cswap
                        run_AdGuard_setup
                        ;;
                    "Channels")
                        adguard_channl_cswap
                        run_AdGuard_setup
                        ;;
                    *)
                        echo "Unknown config type for AdGuard: $config_type"
                        return 1
                        ;;
                esac
               
            elif [ "$system" = "Pihole" ]; then  # Add spaces around brackets
               case "$config_type" in  
                    "Darkwire")
                        pihole_dwire_cswap
                        run_Pihole_setup
                        ;;
                    "Channels")
                        pihole_channl_cswap
                        run_Pihole_setup
                        ;;
                    *)
                        echo "Unknown config type for AdGuard: $config_type"
                        return 1
                        ;;
                esac
            else
                echo "Unknown system: $system"
                return 1
            fi
            ;;
        
        "Advanced")
            title  
            sleep 2
            compose_down
            clear
            
            if [ "$system" = "AdGuard" ]; then
                case "$config_type" in  
                    "Darkwire")
                        adguard_dwire_cswap
                        set_timer_value
                        run_AdGuard_setup
                        ;;
                    "Channels")
                        adguard_channl_cswap
                        set_timer_value
                        run_AdGuard_setup
                        ;;
                    *)
                        echo "Unknown config type for AdGuard: $config_type"
                        return 1
                        ;;
                esac
               
            elif [ "$system" = "Pihole" ]; then  # Add spaces around brackets
               case "$config_type" in  
                    "Darkwire")
                        pihole_dwire_cswap
                        set_timer_value
                        run_Pihole_setup
                        ;;
                    "Channels")
                        pihole_channl_cswap
                        set_timer_value
                        run_Pihole_setup
                        ;;
                    *)
                        echo "Unknown config type for AdGuard: $config_type"
                        return 1
                        ;;
                esac
            else
                echo "Unknown system: $system"
                return 1
            fi
            ;;
        
        *)
            echo "Unknown mode: $mode"
            return 1
            ;;
    esac
}
run_Pihole_setup() {
        if [ "$mode" = "Express" ]; then
            TIMER_VALUE=0
        elif [ "$mode" = "Advanced" ]; then
            echo "OK" 
        fi
    set_pihole_config &&
    set_wg-dash_config &&
    set_wg-dash_account &&
    #rm_exst_configs >/dev/null 2>&1 &&
    clear &&
    compose_up &&
    clear &&
    mkey_output
}
run_AdGuard_setup() {
        if [ "$mode" = "Express" ]; then
            TIMER_VALUE=0
        elif [ "$mode" = "Advanced" ]; then
            echo "OK" 
        fi
        set_pihole_tz &&
        set_adguard_config &&
        set_wg-dash_config && 
        set_wg-dash_account &&
        #rm_exst_configs >/dev/null 2>&1 &&  
        clear &&
        compose_up &&
        clear &&
        mkey_output
}

mkey_output() {
    #FINAL_OUTPUT
            title
            generate_wireguard_qr  &&
            readme_title &&
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
is_alpine() {
    # Check for the presence of "alpine" in the /etc/os-release file
    if grep -q "Alpine Linux" /etc/os-release; then
        return 0 # true
    else
        return 1 # false
    fi
}

compose_up() {
    set_tag --stable
    run_docker_title
    if is_alpine; then
        $DEPLOY_SYSTEM-compose pull
        $DEPLOY_SYSTEM-compose up -d --build
    else
        $DEPLOY_SYSTEM compose pull
        $DEPLOY_SYSTEM compose up -d --build
    fi
}

compose_down() {
    local install_check="preqsinstalled.txt"
    local yml_file="docker-compose.yml"
    local port_mappings="770-777:770-777/udp"
    export WGD_PORT_MAPPINGS="$port_mappings"

    if [ ! -f "$install_check" ]; then
        # If prerequisites are not installed, install them
        install_requirements
        if is_alpine; then
            $DEPLOY_SYSTEM-compose down --remove-orphans
        else
            $DEPLOY_SYSTEM compose down --remove-orphans
        fi
        $DEPLOY_SYSTEM volume ls -q | grep 'wg_data' | xargs -r docker volume rm
    elif [ -f "$install_check" ]; then
        # If prerequisites are installed, bring down the Docker-compose setup
        if is_alpine; then
            $DEPLOY_SYSTEM-compose down --remove-orphans
        else
            $DEPLOY_SYSTEM compose down --remove-orphans
        fi
        # Uncomment the line below if you want to remove volumes
        # docker volume ls -q | grep 'wg_data' | xargs -r docker volume rm
    fi
}
#MISC
    set_tag() {
        # Docker Hub repository

        REPO="noxcis/${STATE}"

        # Fetch the tags from Docker Hub API
        response=$(curl -s -f "https://hub.docker.com/v2/repositories/${REPO}/tags/?page_size=100")

        # Initialize the search pattern
        pattern=""

        # Check input arguments
        while [[ $# -gt 0 ]]; do
            case $1 in
                --allow-dev)
                    pattern="dev"
                    shift
                    ;;
                --allow-beta)
                    pattern="beta"
                    shift
                    ;;
                --stable)
                    pattern="exclude" # Indicate exclusion for beta and dev
                    shift
                    ;;
                *)
                    echo "Invalid option: $1"
                    exit 1
                    ;;
            esac
        done

        # Construct jq filter based on the pattern
        if [[ $pattern == "exclude" ]]; then
            # Default behavior to exclude tags with 'beta' or 'dev'
            filter="select(.name | test(\"beta|dev\"; \"i\") | not)"
        elif [[ -n "$pattern" ]]; then
            # Only include tags that contain the specified pattern
            filter="select(.name | test(\"$pattern\"; \"i\"))"
        else
            # No pattern provided, which could be an error state.
            echo "No valid pattern provided."
            exit 1
        fi

        # Extract the latest updated tag based on the filter using jq
        latest_tag=$(echo "$response" | jq -r "[.results[] | $filter] | sort_by(.last_updated) | last(.[]).name")

        # Check if the tag is extracted
        if [ -z "$latest_tag" ]; then
            echo "Failed to fetch a suitable latest updated tag."
            exit 1
        else
            echo "Latest suitable updated tag: $latest_tag"
        fi

        export TAG="$latest_tag"
    }
    dev_build() {
        local adguard_yaml_file="./configs/adguard/AdGuardHome.yaml"
        local adguard_password='$2a$12$t6CGhUcXtY6lGF2/A9Jd..Wn315A0RIiuhLlHbNHG2EmDbsN7miwO'
        local adguard_user="admin"

        compose_down &&
        run_animation_seq &&
        sed -i '' -E "s|^( *password: ).*|\1$adguard_password|" "$adguard_yaml_file" && \
        sed -i '' -E "s|^( *- name: ).*|\1$adguard_user|" "$adguard_yaml_file"
        title &&
        docker compose -f dev-docker-compose.yml up -d
        echo -e "\033[33m"'Wireguard DashBoard Available at http://localhost:8000'



    }
    rm_exst_configs() {
        local masterkey_file="./configs/master-key/master.conf"
        if [ -f "$masterkey_file" ]; then
            echo "Removing existing '$masterkey_file'..."
            sudo rm "$masterkey_file"
            echo "Existing '$masterkey_file' removed."
        fi
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
    switch_tor() {
        # Accept the input argument as a string
        input_string="$1"
        
        # Split the input string by '-' into components
        IFS='-' read -r transport_type bridge_type plugin_type <<< "$input_string"
        
        # Default bridge_type to an empty string if omitted
        if [[ -z "$bridge_type" ]]; then
            bridge_type=""
        fi

        # Check if the first component is 'Tor'
        if [[ "$transport_type" == "Tor" ]]; then
            export WGD_TOR_PROXY="true"
            export DEPLOY_TYPE="true "
        else
            export WGD_TOR_PROXY="false"
            export DEPLOY_TYPE="false"
        fi

        # Set bridge options
        if [[ "$bridge_type" == "br" ]]; then
            export WGD_TOR_BRIDGES="true"
        elif [[ "$bridge_type" == "nobrg" ]]; then
            export WGD_TOR_BRIDGES="false"
        else
            echo "Invalid bridge."
            sleep 5
        fi

        # Set plugin type
        if [[ "$plugin_type" == "snow" ]]; then
            export WGD_TOR_PLUGIN="snowflake"
        elif [[ "$plugin_type" == "obfs4" ]]; then
            export WGD_TOR_PLUGIN="obfs4"
        elif [[ "$plugin_type" == "webtun" ]]; then
            export WGD_TOR_PLUGIN="webtunnel"
        else 
            echo "Invalid plugin choice. Please choose 'snow', 'obfs4', or 'webtun'."
            return 1  # Exit with error
        fi
    }
    



# Parse options with getopts
while getopts ":c:n:t:p:s:l:" opt; do
  case $opt in
    l)  
     if [[ "${OPTARG}" =~ \{[A-Za-z][A-Za-z]\}(,\{[A-Za-z][A-Za-z]\})* ]]; then
        WGD_TOR_DNS_EXIT_NODES="${OPTARG}"
        export WGD_TOR_DNS_EXIT_NODES
      else
        
        echo "Invalid input for -e. Expected format: {US},{GB},{AU}, etc."
        exit 1
      fi
      ;;
    c)  # Deployment system (Docker or Podman)
      case "${OPTARG}" in
        Docker)
          export DEPLOY_SYSTEM="docker"
          ;;
        Podman)
          export DEPLOY_SYSTEM="podman"
          ;;
        *)
          echo "Invalid input for -s. Expected 'Docker' or 'Podman'."
          exit 1
          ;;
      esac
      ;;
    p)  # Deployment system (Docker or Podman)
      case "${OPTARG}" in
        awg)
          export AMNEZIA_WG="true"
          export PROTOCOL_TYPE="AmneziaWG"
          ;;
        wg)
          export AMNEZIA_WG="false"
          export PROTOCOL_TYPE="WireGuard"
          ;;
        *)
          echo "Invalid input for -p [PROTOCOL]. Expected 'wg' or 'awg'."
          exit 1
          ;;
      esac
      ;;
    s)  # Deployment system (Docker or Podman)
      case "${OPTARG}" in
        static)
          export STATE="wiregate"
          export DEPLOY_STATE="STATIC"
          ;;
        dynamic)
          export STATE="wg-dashboard"
          export DEPLOY_STATE="DYNAMIC"
          ;;
        *)
          echo "Invalid input for -s [STATE]. Expected 'dynamic' or 'static'."
          exit 1
          ;;
      esac
      ;;
    n)  
     if [[ "${OPTARG}" =~ \{[A-Za-z][A-Za-z]\}(,\{[A-Za-z][A-Za-z]\})* ]]; then
        WGD_TOR_EXIT_NODES="${OPTARG}"
        export WGD_TOR_EXIT_NODES
      else
        
        echo "Invalid input for -e. Expected format: {US},{GB},{AU}, etc."
        exit 1
      fi
      ;;
    t)  
      case "${OPTARG}" in
        off)
          export DEPLOY_TYPE="false"
          export WGD_TOR_PLUGIN="None"
          export WGD_TOR_PROXY="false"
          export WGD_TOR_BRIDGES="false"
          ;;
        Tor-br-snow) 
          switch_tor Tor-br-snow
          ;;
        Tor-br-webtun) 
          switch_tor Tor-br-webtun
          ;;
        Tor-br-obfs4) 
          switch_tor Tor-br-obfs4
          ;;
        Tor-snow) 
          switch_tor Tor-nobrg-snow
          ;;
        Tor-webtun) 
          switch_tor Tor-nobrg-webtun
          ;;
        Tor-obfs4) 
          switch_tor Tor-nobrg-obfs4
          ;;
        *)
          echo "$red Error:$reset Invalid option for -t...wait"
          sleep 1.5
          help
          exit 1
          ;;
      esac
      ;;
    \?)
      echo "Invalid option: -$OPTARG"
      help
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument."
      help
      exit 1
      ;;
  esac
done

shift $((OPTIND - 1))

# If no arguments provided, run default functions
if [ $# -eq 0 ]; then
  run_animation_seq
  menu
else
  case "$1" in
    E-A-D)  setup_environment "Express" "AdGuard" "Darkwire" ;;
    E-A-C)  setup_environment "Express" "AdGuard" "Channels" ;;
    E-P-D)  setup_environment "Express" "Pihole" "Darkwire" ;;
    E-P-C)  setup_environment "Express" "Pihole" "Channels" ;;
    A-A-D)  setup_environment "Advanced" "AdGuard" "Darkwire" ;;
    A-A-C)  setup_environment "Advanced" "AdGuard" "Channels" ;;
    A-P-D)  setup_environment "Advanced" "Pihole" "Darkwire" ;;
    A-P-C)  setup_environment "Advanced" "Pihole" "Channels" ;;
    dev)
      dev_build
      ;;
    help)
      help
      ;;
    reset)
      fresh_install
      ;;
    *)
      echo "$red Error:$reset Invalid option for positional argument...wait"
      sleep 1.5
      help
      exit 1
      ;;
  esac
fi
