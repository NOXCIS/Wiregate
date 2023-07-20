#!/bin/bash

set -e
export DEBIAN_FRONTEND=noninteractive
export TIMER_VALUE=0

title() {
    echo '  

    ██╗    ██╗ ██████╗ ██████╗ ███╗   ███╗██╗  ██╗ ██████╗ ██╗     ███████╗
    ██║    ██║██╔═══██╗██╔══██╗████╗ ████║██║  ██║██╔═══██╗██║     ██╔════╝
    ██║ █╗ ██║██║   ██║██████╔╝██╔████╔██║███████║██║   ██║██║     █████╗  
    ██║███╗██║██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║██║   ██║██║     ██╔══╝  
    ╚███╔███╔╝╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║╚██████╔╝███████╗███████╗
    ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝

            Setup Script & Dockerization by Shamar Lee A.K.A NOXCIS
        Thanks to @donaldzou for WGDashboard @klutchell for UnBound Config
    '
}
menu() {
    title
    echo "Please choose an option:"
    echo "1. Manual configuration"
    echo "2. Auto configuration"
    echo "3. Auto configuration with quickset for # of Configs to Generate"
    echo "4. Reset Dashboard"
    echo "5. Exit"

    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) manual_setup ;;
        2) auto_setup ;;
        3) auto_set_wct ;;
        4) fresh_install ;;
        5) exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}
run_setup() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                     Getting OS Updates and Upgrades"
    echo "                        This may take some time ..."
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update > /dev/null 2>&1
    sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade > /dev/null 2>&1
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Installing prerequisites"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
            install_prerequisites &&
    echo -e "\033[33m\n"
    echo "#######################################################################"
    echo ""
    echo "                 SET TIMEZONE AND DASHBOARD PASSWORDS"
    echo ""
    echo ""
    echo ""
    echo "   The Time Zone will be set Automatically and The password left blank"
    echo "                    When a timeout event occours"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
            set_tz &&
    echo ""
    echo "Enter password for Pihole Dashboard $(tput setaf 1)(Press enter to set password or wait 5 seconds for no password): $(tput sgr0)"  
            set_password &&
    

    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                       SET SERVER IP FOR WIREGUARD"
    echo "                   SET # of SERVER INTERFACES TO CREATE"
    echo ""
    echo ""
    echo "                 The Server IP will be set Automatically"
    echo "                      When a timeout event occours"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    
            update_server_ip &&
            add_port_mappings &&
    
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Run docker Compose UP"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
            compose_up &&
    

    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "        Copy Master Client Config to empty WireGuard .conf file "
    echo "           Connect to Wireguard and access the Dashboard" 
    echo ""
    echo "                Dashboard Address http://10.2.0.3:10086" 
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

            docker logs -f wg_dashboard &&
            echo ""
           
            create_swap 
}  
auto_setup() {
    title
    sleep 5s
    TIMER_VALUE=0 
    run_setup 
}
auto_set_wct() {
    TIMER_VALUE=5
    config_count &&
    TIMER_VALUE=0
    run_setup 

}
manual_setup() {
    title
    echo "The Timer value dictates how much time you will have in each setup set."
    echo "Enter the timer value (in seconds):"
    read TIMER_VALUE
    echo -e "Timer value set to \033[32m$TIMER_VALUE\033[0m seconds."
    sleep 2s
    run_setup
}
set_tz() {
    local yml_file="docker-compose.yml"
    read -t $TIMER_VALUE -p "Do you want to automatically get the host timezone? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    echo ""
    echo ""
    if [[ $answer == [Yy] || -z $answer ]]; then
        timezone=$(cat /etc/timezone)
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        
    else
        read -p "Enter timezone $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)America/New_York$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " timezone
        echo ""
        if [[ -z $timezone ]]; then
            timezone="America/New_York"
        fi
        echo -e "Timezone has been set to \033[32m$timezone\033[0m"
        
    fi
    sed -i "s|TZ:.*|TZ: \"$timezone\"|" "$yml_file"
    echo ""
}
update_server_ip() {
    local yml_file="docker-compose.yml"
    local ip

        read -t $TIMER_VALUE -p "Do you want to automatically set the server IP address? $(tput setaf 1)(y/n)$(tput sgr0) " auto_ip
        echo ""
        echo ""
    if [[ $auto_ip =~ ^[Nn]$ ]]; then
        read -p "Please enter the server IP address $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)127.0.0.1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " ip
        ip=${ip:-127.0.0.1}
        echo ""
    else
        ip=$(hostname -I | awk '{print $1}')
    fi

    if [[ -f "$yml_file" ]]; then
        sed -i "s/SERVER_IP=.*/SERVER_IP=$ip/" "$yml_file"
        echo -e "Server IP address has been set to \033[32m$ip\033[0m"
        echo ""
    else
        echo "$yml_file not found."
    fi
}
set_password() {
    local yml_file="docker-compose.yml"
    local password=""
    local confirm_password=""
    local timer=$TIMER_VALUE
    local user_activity=false

    # Wait for 5 seconds or until user activity is detected
    sleep $timer & PID=$!
    while true; do
        read -t 1 -n 1 && user_activity=true && break || true
        if ! ps -p $PID > /dev/null; then
            # Timer has expired and no user activity detected
            password=""
            echo ""
            sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
            echo -e "\033[31mRunning Headless. Password has been set to null.\033[0m"
            echo ""
            break
        fi
    done

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Pihole Dashboard:$(tput sgr0)" password 
            echo ""
            echo ""

            if [[ -z "$password" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi

            read -sp "$(tput setaf 3)Confirm password for Pihole Dashboard:$(tput sgr0) " confirm_password
            echo ""
            echo ""

            if [[ "$password" != "$confirm_password" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, update the yml_file and exit the loop
                sed -i "s/WEBPASSWORD:.*/WEBPASSWORD: \"$password\"/" "$yml_file"
                echo -e "\033[32mPASSWORD HAS BEEN SET\033[0m"
                echo ""
                break
            fi
        done
    fi
}
compose_up() {
    sudo sysctl -w net.core.rmem_max=2097152
    docker compose up -d --build 
}
install_prerequisites() {
    
    # List of prerequisites
    PREREQUISITES=(
        curl
        qrencode
        git
        apt-transport-https
        ca-certificates
        gnupg
        gnupg-agent
        software-properties-common
        openssl
    )
    # Define ANSI color codes
    GREEN=$(tput setaf 2)
    RESET=$(tput sgr0)
    # Check if each prerequisite is already installed
    for prerequisite in "${PREREQUISITES[@]}"
    do
        if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
            echo "${GREEN}$prerequisite is not installed. Installing...${RESET}"
            sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install "$prerequisite" > /dev/null 2>&1
        else
            echo "${GREEN}$prerequisite is already installed. Skipping...${RESET}"
        fi
    done

    if ! command -v docker > /dev/null 2>&1 || ! command -v docker-compose > /dev/null 2>&1; then
        echo "${GREEN}Installing Docker...${RESET}"
        install_docker
    fi
}
install_docker() {

    for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove -y $pkg; done
    sudo install -m 0755 -d /etc/apt/keyrings
    sleep 0.25s
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg -f
    sleep 0.25s
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    sleep 0.25s   
    echo \
    "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sleep 0.25s
    sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update > /dev/null 2>&1
    sleep 0.25s
    sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 

}
config_count() {
    local yml_file="docker-compose.yml"
    local count=""
        read -t $TIMER_VALUE -p "Enter # of WireGuard server configurations to generate $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " count
        echo ""
        echo ""
    if [[ -z "$count" ]]; then
        count=1
    fi
        sed -i "s/CONFIG_CT=.*/CONFIG_CT=$count/" "$yml_file"
        echo -e "WireGuard Server Configurations to be Generated has been set to \033[32m$count\033[0m"
        echo ""
}
add_port_mappings() {
    local config_ct=$(grep -oP '(?<=CONFIG_CT=)\d+' docker-compose.yml)
    local start_port=51820
    local port_mappings=""
        for ((i = 1; i <= config_ct; i++)); do
            local port=$((start_port + i - 1))
            port_mappings+="\n      - $port:$port/udp"
        done

    sed -i '/- 51820:51820\/udp/,/sysctls:/ {//!d}' docker-compose.yml
    sed -i "/- 51820:51820\/udp/a${port_mappings//$'\n'/\\n}" docker-compose.yml
    sed -i '/ports:/,/sysctls:/ { /- 51820:51820\/udp/{n; d; } }' docker-compose.yml

}
fresh_install() {
    
    local masterkey_file="/WG-Dash/master-key/master.conf"
    local config_folder="/WG-Dash/config"
    
    docker compose down 
    

    if [ -f "$(dirname "$0")$masterkey_file" ]; then
        echo "Removing existing '$masterkey_file'..."
        rm "$(dirname "$0")$masterkey_file"
        echo "Existing '$masterkey_file' removed."
    fi

    if [ -d "$(dirname "$0")$config_folder" ]; then
        echo "Removing existing '$config_folder'..."
        rm -r "$(dirname "$0")$config_folder"
        echo "Existing '$config_folder' removed."
    fi

        echo "Removing existing Compose File"
        rm docker-compose.yml
        echo "Existing Compose File removed."

        echo "Pulling from Clean Compose File..."
        cat Custom-Compose/clean-docker-compose.yml > docker-compose.yml
        echo "File successfully pulled from Clean Compose File."
    

    menu
}

create_swap() {

    # Check if a swapfile already exists
    if [[ -f /swapfile ]]; then
        echo "Swapfile already exists."
        exit 1
    fi
    # Create a swapfile
        sudo fallocate -l 2G /swapfile > /dev/null 2>&1
    # Set permissions for the swapfile
        sudo chmod 600 /swapfile > /dev/null 2>&1
    # Set up the swap space
        sudo mkswap /swapfile > /dev/null 2>&1
    # Enable the swapfile
        sudo swapon /swapfile > /dev/null 2>&1
    # Update the fstab file to make the swapfile persistent across reboots
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null 2>&1
        echo "Swapfile created and enabled." 


}




# Main script
    if [ $# -eq 0 ]; then
        menu
    else
    case $1 in
        run) run_setup ;;
        manual) manual_setup ;;
        headless) auto_setup ;;
        fresh) fresh_install ;;
        quickcount) auto_set_wct ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



#rm docker-compose.yml
