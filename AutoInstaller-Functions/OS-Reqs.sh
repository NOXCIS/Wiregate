#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License


run_os_update() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                     Getting OS Updates and Upgrades"
    echo "                        This may take some time ..."
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

    if [ -f /etc/alpine-release ]; then
        sudo apk update && sudo apk upgrade
    else
        sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy update 
        sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy upgrade
    fi

    clear
}
x_alpine_repo() {
  # Path to repositories file
  REPO_FILE="/etc/apk/repositories"
  
  # Check if the community repository is already present (commented or uncommented)
  if grep -q "#.*community" "$REPO_FILE"; then
    echo "Uncommenting Alpine community repository..."
    # Uncomment the line containing 'community'
    sed -i 's/^#.*community/http:\/\/dl-cdn.alpinelinux.org\/alpine\/$(cat /etc/alpine-release | cut -d '.' -f 1)\/community/' "$REPO_FILE"
  elif ! grep -q "community" "$REPO_FILE"; then
    echo "Adding Alpine community repository..."
    # Add the community repository (adjust the URL to your Alpine version)
    echo "http://dl-cdn.alpinelinux.org/alpine/$(cat /etc/alpine-release | cut -d '.' -f 1)/community" >> "$REPO_FILE"
  else
    echo "Alpine community repository is already active."
  fi

  # Update APK index
  apk update
}
install_prerequisites() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Installing prerequisites"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

    # List of prerequisites for Alpine
    PREREQUISITES=(
        curl
        ca-certificates
        gnupg
        openssl
        apache2-utils
        pwgen
        jq
    )

    # Define ANSI color codes
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    RESET=$(tput sgr0)
    
    # Check if Alpine Linux is used
    if [ -f /etc/alpine-release ]; then
        apk add libqrencode libqrencode-tools > /dev/null 2>&1
        for prerequisite in "${PREREQUISITES[@]}"
        do
            if ! apk info -e "$prerequisite" > /dev/null 2>&1; then
                echo "${GREEN}$prerequisite is not installed.${RESET} ${YELLOW}Installing...${RESET}"
                sudo apk add "$prerequisite"
            else
                echo "${GREEN}$prerequisite is already installed.${RESET} ${YELLOW}Skipping...${RESET}"
            fi
        done
    else
        # For non-Alpine systems (Debian/Ubuntu)
               sudo apt-get install qrencode -y > /dev/null 2>&1
        for prerequisite in "${PREREQUISITES[@]}"
        do
            if ! dpkg -s "$prerequisite" > /dev/null 2>&1; then
                echo "${GREEN}$prerequisite is not installed.${RESET} ${YELLOW}Installing...${RESET}"
                sudo DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -qy install "$prerequisite"
            else
                echo "${GREEN}$prerequisite is already installed.${RESET} ${YELLOW}Skipping...${RESET}"
            fi
        done
    fi
}

install_docker() {
    # Color codes for terminal output
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RESET='\033[0m'

    # Check if Docker is installed and running
    if command -v docker > /dev/null 2>&1 && docker ps > /dev/null 2>&1; then
        printf "${GREEN}Docker is already installed and running.${RESET} ${YELLOW}Skipping installation...${RESET}\n"
        return
    fi

    # Detect Alpine Linux
    if [ -f /etc/alpine-release ]; then
        echo "Installing Docker on Alpine Linux..."
        sudo apk update
        sudo apk add docker docker-cli-compose

    else
        # Handle other distros (Debian/Ubuntu)
        if [ -f /etc/apt/keyrings/docker.gpg ]; then
            sudo rm /etc/apt/keyrings/docker.gpg
        fi

        for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
            sudo apt-get remove -y $pkg > /dev/null 2>&1 || true
        done

        sudo install -m 0755 -d /etc/apt/keyrings
        sleep 0.25s

        source /etc/os-release
        distro=$ID
        codename=$VERSION_CODENAME

        case $distro in
        "ubuntu")
            repo_url="https://download.docker.com/linux/ubuntu"
            ;;
        "debian")
            repo_url="https://download.docker.com/linux/debian"
            ;;
        *)
            printf "${RED}Unsupported Linux distribution: $distro${RESET} \n"
            printf "${RED}To Continue Manually install Docker on : $distro${RESET}"
            exit 1
            ;;
        esac

        sudo curl -fsSL "$repo_url/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg

        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $repo_url $codename stable" |
            sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update

        DOCREQS=(
            docker-ce
            docker-ce-cli
            containerd.io
            docker-buildx-plugin
            docker-compose-plugin
        )

        for docreqs in "${DOCREQS[@]}"; do
            if ! dpkg -s "$docreqs" > /dev/null 2>&1; then
                printf "${GREEN}Docker is not installed. Installing...${RESET}\n"
                sudo apt-get install -y "$docreqs"
            else
                printf "${GREEN}$docreqs is already installed.${RESET} ${YELLOW}Skipping...${RESET}\n"
            fi
        done
    fi
}

create_swap() {

        # Check if a swapfile already exists
        if [[ -f /swapfile ]]; then
            echo "Swapfile already exists."
        elif [[ ! -f /swapfile ]]; then
            echo "Swapfile does not exist. Creating..."
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
        fi
}
install_confirm() {
    cat <<EOF >"preqsinstalled.txt"
        !!!!!!
EOF
}

install_requirements() {
    local MAX_ATTEMPTS=3
    local attempts=1
    local install_check="preqsinstalled.txt"

    # Function to check if a command exists
    check_command() {
        if ! command -v "$1" &>/dev/null; then
            echo "Error: $1 is not installed. Please install it to proceed."
            return 1
        fi
        return 0
    }

    while [ $attempts -le $MAX_ATTEMPTS ]; do
        echo "Attempt $attempts of $MAX_ATTEMPTS"

        # Attempt the installation
        if run_os_update && install_prerequisites; then
            if [[ "$DEPLOY_SYSTEM" == "docker" ]]; then
                install_docker || { echo "Docker installation failed."; exit 1; }
            elif [[ "$DEPLOY_SYSTEM" == "podman" ]]; then
                clear
                echo "Checking for required tools for Podman deployment..."

                # Check for Podman
                if ! check_command "podman"; then
                    podman_install_title
                    exit 1
                fi

                # Check for Podman Compose
                if ! (command -v "podman-compose" &>/dev/null || podman compose version &>/dev/null); then
                    echo "Error: podman-compose or 'podman compose' is not installed. Please install it to proceed."
                    exit 1
                fi
            fi

            # Create swap space and confirm installation
            if create_swap && install_confirm; then
                # Verify successful installation
                if [ -f "$install_check" ]; then
                    echo "Installation successful."
                    break
                else
                    echo "Installation verification failed. Retrying..."
                fi
            else
                echo "Installation steps failed. Retrying..."
            fi
        else
            echo "OS update or prerequisites installation failed. Retrying..."
        fi

        ((attempts++))
    done

    if [ $attempts -gt $MAX_ATTEMPTS ]; then
        echo "Max attempts reached. Installation failed."
        exit 1
    fi
}
