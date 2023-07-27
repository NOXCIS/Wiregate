#!/bin/bash

set -e
export DEBIAN_FRONTEND=noninteractive
export TIMER_VALUE=0

title() {
    echo -e "\033[32m"
    echo '  

    ██╗    ██╗ ██████╗ ██████╗ ███╗   ███╗██╗  ██╗ ██████╗ ██╗     ███████╗
    ██║    ██║██╔═══██╗██╔══██╗████╗ ████║██║  ██║██╔═══██╗██║     ██╔════╝
    ██║ █╗ ██║██║   ██║██████╔╝██╔████╔██║███████║██║   ██║██║     █████╗  
    ██║███╗██║██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║██║   ██║██║     ██╔══╝  
    ╚███╔███╔╝╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║╚██████╔╝███████╗███████╗
     ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝

                    Setup Script & Dockerization by NOXCIS
        Thanks to @donaldzou for WGDashboard @klutchell for UnBound Config


**********************************************************************************
##################################################################################        
    '
    echo -e "\033[0m"
}
menu() {
    title
    echo "Please choose an option:"
    echo "1. Manual configuration"
    echo "2. Auto configuration"
    echo "3. Auto configuration with quickset for # of Server Interfaces to Generate & Pihole Password"
    echo "4. Reset WireGuard Dashboard"
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
run_os_update() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                     Getting OS Updates and Upgrades"
    echo "                        This may take some time ..."
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    
    sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update 
    sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade 
    clear
}
run_setup() {
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
    echo "                              SET TIMEZONE "
    echo ""
    echo "                The Time Zone will be set Automatically "
    echo "                    When a timeout event occours"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

            set_tz &&

    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                       SET SERVER IP FOR WIREGUARD"
    echo ""
    echo "                 The Server IP will be set Automatically"
    echo "                      When a timeout event occours"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    
            update_server_ip &&
    
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                           Run Docker Compose "
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
            compose_up &&
    

    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "             Copy Master Key to empty WireGuard .conf file"
    echo "             Connect to Wireguard and access the Dashboard" 
    echo ""
    echo -e "             WireGuard Dashboard Address: \033[32mhttp://worm.hole\033[0m" 
    echo -e "             \033[33mPihole Dashboard Address:    \033[32mhttp://pi.hole\033[0m"
    echo ""
    echo -e "             \033[32mVPN Connection Required to Access Dashboards\033[0m" 
    echo -e "\033[33m"
    echo "#######################################################################"
    echo -e "\n\033[0m"

            docker logs -f wg_dashboard &&
            echo ""
           
            create_swap 
}  
auto_setup() {
    TIMER_VALUE=0
    run_os_update &&
    title &&
    config_count &&
    set_password &&
    TIMER_VALUE=0 
    run_setup 
}
auto_set_wct() {
    TIMER_VALUE=5
    run_os_update &&
    title &&
    config_count &&
    set_password &&
    TIMER_VALUE=0
    run_setup 

}
manual_setup() {
    run_os_update &&
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
    config_count &&
    set_password &&
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
    export TIMEZONE="$timezone"
    #sed -i "s|TZ:.*|TZ: \"$timezone\"|" "$yml_file"
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

        export SERVER_IP="$ip"
        #sed -i "s/SERVER_IP=.*/SERVER_IP=$ip/" "$yml_file"
        echo -e "Server IP address has been set to \033[32m$ip\033[0m"
        echo ""
    else
        echo "$yml_file not found."
    fi
}
set_password() {
    local password=""
    local confirm_password=""
    local timer=$TIMER_VALUE
    local user_activity=false

    echo "Press any key to set Pihole Dashboard Password $(tput setaf 1)or wait $(tput sgr0)$(tput setaf 3)$TIMER_VALUE$(tput sgr0)$(tput setaf 1) seconds for no password: $(tput sgr0)"  
    # Wait for 5 seconds or until user activity is detected
    sleep $timer & PID=$!
    while true; do
        read -t 1 -n 1 && user_activity=true && break || true
        if ! ps -p $PID > /dev/null; then
            # Timer has expired and no user activity detected
            password=""
           
            export WEBPASSWORD="$password"
            echo ""
            echo -e "\033[32mPassword has been set to null.\033[0m"
            
            break
        fi
    done

    if [[ "$user_activity" == true ]]; then
        # Prompt user to enter and confirm their password
        while true; do
            read -sp "$(tput setaf 3)Enter password for Pihole Dashboard:$(tput sgr0)" password 
            echo ""
            

            if [[ -z "$password" ]]; then
                echo -e "\033[31mPassword cannot be empty. Please try again.\033[0m"
                continue
            fi
            echo ""
            read -sp "$(tput setaf 3)Confirm password for Pihole Dashboard:$(tput sgr0) " confirm_password
            
            

            if [[ "$password" != "$confirm_password" ]]; then
                echo -e "\033[31mPasswords do not match. Please try again.\033[0m"
            else
                # Passwords match, set the WEBPASSWORD environment variable
                export WEBPASSWORD="$password"

                echo -e "\033[32m"
                echo '


      ██████╗  █████╗ ███████╗███████╗██╗    ██╗ ██████╗ ██████╗ ██████╗     ███████╗███████╗████████╗
      ██╔══██╗██╔══██╗██╔════╝██╔════╝██║    ██║██╔═══██╗██╔══██╗██╔══██╗    ██╔════╝██╔════╝╚══██╔══╝
      ██████╔╝███████║███████╗███████╗██║ █╗ ██║██║   ██║██████╔╝██║  ██║    ███████╗█████╗     ██║   
      ██╔═══╝ ██╔══██║╚════██║╚════██║██║███╗██║██║   ██║██╔══██╗██║  ██║    ╚════██║██╔══╝     ██║   
      ██║     ██║  ██║███████║███████║╚███╔███╔╝╚██████╔╝██║  ██║██████╔╝    ███████║███████╗   ██║   
      ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝ ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═════╝     ╚══════╝╚══════╝   ╚═╝                         
        '
                
                echo -e "\033[0m"

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
    YELLOW=$(tput setaf 3)
    RESET=$(tput sgr0)
   
    # Check if each prerequisite is already installed
    for prerequisite in "${PREREQUISITES[@]}"
    do
        if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
            echo "${GREEN}$prerequisite is not installed.${RESET} ${YELLOW}Installing...${RESET}"
            sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install "$prerequisite" > /dev/null 2>&1
        else
            echo "${GREEN}$prerequisite is already installed.${RESET} ${YELLOW}Skipping...${RESET}"
        fi
    done

        install_docker
    
}
install_docker() {
    if [ -f /etc/apt/keyrings/docker.gpg ]; then
       sudo rm /etc/apt/keyrings/docker.gpg 
    fi
    for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove -y $pkg; done  > /dev/null 2>&1
    sudo install -m 0755 -d /etc/apt/keyrings
    sleep 0.25s
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 
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

    DOCREQS=(
        docker-ce 
        docker-ce-cli 
        containerd.io 
        docker-buildx-plugin 
        docker-compose-plugin
    )

    YELLOW=$(tput setaf 3)
    GREEN=$(tput setaf 2)
    RESET=$(tput sgr0)

    for docreqs in "${DOCREQS[@]}" 
    do
        if ! dpkg -s "$docreqs" > /dev/null 2>&1; then
        echo "${GREEN}Docker is not installed. Installing...${RESET}"
        sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install "$docreqs" 
    else
            echo "${GREEN}$docreqs is already installed.${RESET} ${YELLOW}Skipping...${RESET}"
    fi
    done
}
config_count() {
    local yml_file="docker-compose.yml"
    local HOST_PORT_START=51820
    local count=1
    echo -e "\033[33m\n"    
    echo '
              
 ██████╗ ██████╗ ███╗   ██╗███████╗██╗ ██████╗ 
██╔════╝██╔═══██╗████╗  ██║██╔════╝██║██╔════╝ 
██║     ██║   ██║██╔██╗ ██║█████╗  ██║██║  ███╗
██║     ██║   ██║██║╚██╗██║██╔══╝  ██║██║   ██║
╚██████╗╚██████╔╝██║ ╚████║██║     ██║╚██████╔╝
 ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚═╝ ╚═════╝ 
                                               
                                             
    '
    echo "#######################################################################"
    echo ""
    echo "                       Set Configuration Options"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
        read -t $TIMER_VALUE -p "Enter # of WireGuard Interfaces to generate $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)1$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " count
        echo '
        '
            if [[ -z "$count" ]]; then
                count=1
            fi

            while true; do

                read -t "$TIMER_VALUE" -p "Enter the starting port for WireGuard Server interface's Port Range $(tput setaf 1)(Press enter for default: $(tput sgr0)$(tput setaf 3)51820$(tput sgr0)$(tput setaf 1)): $(tput sgr0) " HOST_PORT_START
                echo '
                '
        # If the user didn't enter anything, set the default value
        if [[ -z "$HOST_PORT_START" ]]; then
        HOST_PORT_START=51820
        break
        fi

    # Check if the input is a valid integer
    if [[ "$HOST_PORT_START" =~ ^[0-9]+$ ]]; then
        # Convert the input to an integer value
        HOST_PORT_START=$((HOST_PORT_START))

        # Check if the input is within the valid range
        if (( HOST_PORT_START >= 1 && HOST_PORT_START <= 65535 )); then
            break
        fi
    fi
    echo ""
    echo "Invalid input. Please enter a value between 1 and 65535."
done




        if [[ -z "$HOST_PORT_START" ]]; then
        HOST_PORT_START=51820
        fi

        pcount=$((count - 1))
        HOST_PORT_END=$((HOST_PORT_START + pcount))  
        port_mappings="${HOST_PORT_START}-${HOST_PORT_END}:${HOST_PORT_START}-${HOST_PORT_END}/udp"
        echo -e "Wireguard Port Range Set To: \033[32m$port_mappings\033[0m"

        export INTERFACE_COUNT="$count"
        export PORT_RANGE_START="$HOST_PORT_START"
        export PORT_MAPPINGS="$port_mappings"
        echo ""
        echo -e "WireGuard Server Configurations to be Generated has been set to: \033[32m$count\033[0m"
        echo ""
}
fresh_install() {
    local masterkey_file="/WG-Dash/master-key/master.conf"
    local config_folder="/WG-Dash/config"
    local yml_file="docker-compose.yml"
    clear
    echo -e "\033[33m\n"    
    echo '
        ██╗    ██╗ █████╗ ██████╗ ███╗   ██╗██╗███╗   ██╗ ██████╗ 
        ██║    ██║██╔══██╗██╔══██╗████╗  ██║██║████╗  ██║██╔════╝ 
        ██║ █╗ ██║███████║██████╔╝██╔██╗ ██║██║██╔██╗ ██║██║  ███╗
        ██║███╗██║██╔══██║██╔══██╗██║╚██╗██║██║██║╚██╗██║██║   ██║
        ╚███╔███╔╝██║  ██║██║  ██║██║ ╚████║██║██║ ╚████║╚██████╔╝
         ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝                                                   
    '
    echo "#######################################################################"
      echo ""
    echo "                  Resetting WireGuard will Delete            "
    echo "              Your Client, Server , & Master Key Configs         "
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

    read -p "Continue Resetting Wireguard? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    echo ""
    echo ""
    if [[ $answer == [Yy] || -z $answer ]]; then


        sudo sed -i '/ports:/,/sysctls:/ {//!d}; /ports:/a\ \ \ \ \ \ - 51820:51820\/udp' docker-compose.yml
        docker compose down 
    

    if [ -f "$(dirname "$0")$masterkey_file" ]; then
        echo "Removing existing '$masterkey_file'..."
        sudo rm "$(dirname "$0")$masterkey_file"
        echo "Existing '$masterkey_file' removed."
    fi

    if [ -d "$(dirname "$0")$config_folder" ]; then
        echo "Removing existing '$config_folder'..."
        sudo rm -r "$(dirname "$0")$config_folder"
        echo "Existing '$config_folder' removed."
    fi

        echo "Removing existing Compose File"
        sudo rm docker-compose.yml
        echo "Existing Compose File removed."

        echo "Pulling from Clean Compose File..."
        cat Custom-Compose/clean-docker-compose.yml > docker-compose.yml
        echo "File successfully pulled from Clean Compose File."
    
        clear
        menu
        
    else
        clear
        menu  
        
    fi
    

























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
    
    clear
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
        manual) manual_setup ;;
        headless) auto_setup ;;
        fresh) fresh_install ;;
        quickcount) auto_set_wct ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



#rm docker-compose.yml
