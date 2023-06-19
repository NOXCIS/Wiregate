#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
export TIMER_VALUE=0
sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update > /dev/null 2>&1
sudo sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade > /dev/null 2>&1


menu() {

    echo '  
     █     █░ ▒█████   ██▀███   ███▄ ▄███▓ ██░ ██  ▒█████   ██▓    ▓█████ 
    ▓█░ █ ░█░▒██▒  ██▒▓██ ▒ ██▒▓██▒▀█▀ ██▒▓██░ ██▒▒██▒  ██▒▓██▒    ▓█   ▀ 
    ▒█░ █ ░█ ▒██░  ██▒▓██ ░▄█ ▒▓██    ▓██░▒██▀▀██░▒██░  ██▒▒██░    ▒███   
    ░█░ █ ░█ ▒██   ██░▒██▀▀█▄  ▒██    ▒██ ░▓█ ░██ ▒██   ██░▒██░    ▒▓█  ▄ 
    ░░██▒██▓ ░ ████▓▒░░██▓ ▒██▒▒██▒   ░██▒░▓█▒░██▓░ ████▓▒░░██████▒░▒████▒
    ░ ▓░▒ ▒  ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░░ ▒░   ░  ░ ▒ ░░▒░▒░ ▒░▒░▒░ ░ ▒░▓  ░░░ ▒░ ░
      ▒ ░ ░    ░ ▒ ▒░   ░▒ ░ ▒░░  ░      ░ ▒ ░▒░ ░  ░ ▒ ▒░ ░ ░ ▒  ░ ░ ░  ░
      ░   ░  ░ ░ ░ ▒    ░░   ░ ░      ░    ░  ░░ ░░ ░ ░ ▒    ░ ░      ░   
      ░░ ░                                     ░                      

            Setup Script & Dockerization by Shamar Lee A.K.A NOXCIS
        Thanks to @donaldzou for WGDashboard @klutchell for UnBound Config
    '

    echo "Please choose an option:"
    echo "1. Run Setup"
    echo "2. Manual Configuartion"
    echo "3. Auto Configuatrion"
    echo "4. Get Fresh docker-compose.yml"
    echo "4. Exit"

    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) run_setup ;;
        2) manual_setup ;;
        3) auto_setup ;;
        4) get_docker_compose ;;
        4) exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac

}

run_setup() {

    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Installing prerequisites"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sleep 0.1s
            install_prerequisites &&
    sleep 3s

    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "           SETTING UP FirewallD for Container Stack"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sleep 0.1s
            systemctl restart docker &&
            set_fw &&
    sleep 0.1s

    echo -e "\033[33m\n"
    echo "#######################################################################"
    echo ""
    echo "                 SET TIMEZONE AND DASHBOARD PASSWORD"
    echo ""
    echo "              Input Prompt will timeout after 5s & 10s "
    echo ""
    echo "   The Time Zone will be set Automatically and The password left blank"
    echo "                    When a timeout event occours"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sleep 0.1s
            set_tz &&
    sleep 0.1s
    echo ""
    echo "Enter password for Pihole Dashboard $(tput setaf 1)(Press enter to set password or wait 5 seconds for no password): $(tput sgr0)"  
            set_password &&
    sleep 0.1s


    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "           SETTING SERVER IP & SERVER CONFIG FOR WIREGUARD"
    echo ""
    echo "                Input Prompt will timeout after 5s "
    echo ""
    echo "  The Server IP will be set Automatically and The Config Count set to 1"
    echo "                    When a timeout event occours"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sleep 0.1s
            update_server_ip &&
            config_count &&
    sleep 0.1s

    #Uncomment to review the compose file before build.
    #nano docker-compose.yml


    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Run docker Compose UP"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sleep 0.1s          
            docker-compose up -d --build &&
    sleep 0.1s


    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Create a 2 Gb swapfile"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    sleep 0.1s
            create_swap &&
    sleep 0.1s



    
}

auto_setup() {


    echo '  
     █     █░ ▒█████   ██▀███   ███▄ ▄███▓ ██░ ██  ▒█████   ██▓    ▓█████ 
    ▓█░ █ ░█░▒██▒  ██▒▓██ ▒ ██▒▓██▒▀█▀ ██▒▓██░ ██▒▒██▒  ██▒▓██▒    ▓█   ▀ 
    ▒█░ █ ░█ ▒██░  ██▒▓██ ░▄█ ▒▓██    ▓██░▒██▀▀██░▒██░  ██▒▒██░    ▒███   
    ░█░ █ ░█ ▒██   ██░▒██▀▀█▄  ▒██    ▒██ ░▓█ ░██ ▒██   ██░▒██░    ▒▓█  ▄ 
    ░░██▒██▓ ░ ████▓▒░░██▓ ▒██▒▒██▒   ░██▒░▓█▒░██▓░ ████▓▒░░██████▒░▒████▒
    ░ ▓░▒ ▒  ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░░ ▒░   ░  ░ ▒ ░░▒░▒░ ▒░▒░▒░ ░ ▒░▓  ░░░ ▒░ ░
      ▒ ░ ░    ░ ▒ ▒░   ░▒ ░ ▒░░  ░      ░ ▒ ░▒░ ░  ░ ▒ ▒░ ░ ░ ▒  ░ ░ ░  ░
      ░   ░  ░ ░ ░ ▒    ░░   ░ ░      ░    ░  ░░ ░░ ░ ░ ▒    ░ ░      ░   
      ░░ ░                                     ░                      

            Setup Script & Dockerization by Shamar Lee A.K.A NOXCIS
        Thanks to @donaldzou for WGDashboard @klutchell for UnBound Config
    '
    sleep 5s
    TIMER_VALUE=0 
    run_setup 

}

manual_setup() {

    echo "Enter the timer value (in seconds):"
    read TIMER_VALUE
    echo "Timer value set to $TIMER_VALUE seconds."


}

set_fw() {

    #Enable FirewallD
        systemctl enable --now firewalld 
        firewall-cmd --state 
    # Docker Intigration
        # firewall-cmd --zone=trusted --remove-interface=docker0 --permanent
        # firewall-cmd --reload
        firewall-cmd --zone=docker --permanent --change-interface=docker0
        firewall-cmd --permanent --zone=docker --add-interface=docker0
        firewall-cmd --reload

    # Restart Docker
        systemctl restart docker    

    # Masquerading for docker ingress and egress
        firewall-cmd --zone=public --add-masquerade --permanent 

    # Reload firewall to apply permanent rules
        firewall-cmd --reload 

    # Add firewall rules
        firewall-cmd --permanent --zone=public --add-interface=eth0 
        firewall-cmd --reload 
        firewall-cmd --permanent --zone=public --add-port=443/tcp
        firewall-cmd --permanent --zone=public --add-port=80/tcp
        firewall-cmd --permanent --zone=docker --add-port=51820/udp
        firewall-cmd --permanent --zone=docker --add-port=10086/tcp

    # Reload firewall to apply permanent rules
        firewall-cmd --reload 

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

install_prerequisites() {
    # List of prerequisites
    PREREQUISITES=(
        curl
        git
        apt-transport-https
        ca-certificates
        gnupg
        gnupg-agent
        software-properties-common
        openssl
        firewalld
        docker
        docker-compose
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
}

get_docker_compose() {
    local yml_file="docker-compose.yml"

    if [ -f "$(dirname "$0")/$yml_file" ]; then
        echo "Removing existing '$yml_file'..."
        rm "$(dirname "$0")/$yml_file"
        echo "Existing '$yml_file' removed."
    fi

        echo "Pulling '$yml_file' from GitHub..."
        curl -o "$(dirname "$0")/$yml_file" https://raw.githubusercontent.com/NOXCIS/Worm-Hole/nginx-%2B%2B/docker-compose.yml
        echo "File '$yml_file' successfully pulled from GitHub."
}

create_swap() {

    # Check if a swapfile already exists
    if [[ -f /swapfile ]]; then
        echo "Swapfile already exists."
        exit 1
    fi

    # Create a swapfile
        sudo fallocate -l 2G /swapfile

    # Set permissions for the swapfile
        sudo chmod 600 /swapfile

    # Set up the swap space
        sudo mkswap /swapfile

    # Enable the swapfile
        sudo swapon /swapfile

    # Update the fstab file to make the swapfile persistent across reboots
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
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
        fresh) get_docker_compose ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
    fi



#rm docker-compose.yml
