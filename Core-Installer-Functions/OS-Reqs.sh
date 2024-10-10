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
install_podman() {
  DISTRO=$(uname -a | grep -i 'debian') && DISTRO='debian' || DISTRO='ubuntu'
  ARCH=$(uname -m)

  echo "Detected distribution: $DISTRO, architecture: $ARCH"

  # Install Podman based on distribution and architecture
  if [[ "$DISTRO" == "debian" ]]; then
    echo "Installing Podman on Debian..."
    sudo apt update && sudo apt install -y podman
  elif [[ "$DISTRO" == "ubuntu" ]]; then
    echo "Installing Podman on Ubuntu..."
    sudo apt update && sudo apt install -y podman
  else
    echo "Unsupported distribution."
    return 1
  fi

  # Start and enable Podman service
  echo "Starting Podman service..."
  sudo systemctl --user start podman.socket
  sudo systemctl --user enable podman.socket
  echo "Podman installed and started successfully."

  # Install QEMU based on architecture
  if [[ "$ARCH" == "armv7l" || "$ARCH" == "armv6l" ]]; then
    echo "32-bit ARM architecture detected. Installing ARM-specific QEMU packages..."
    if [[ "$DISTRO" == "debian" || "$DISTRO" == "ubuntu" ]]; then
     sudo apt update && sudo apt install -y qemu-user-static qemu-system-arm
    fi
  elif [[ "$ARCH" == "aarch64" ]]; then
    echo "64-bit ARM architecture detected. Installing ARM64-specific QEMU packages..."
    if [[ "$DISTRO" == "debian" || "$DISTRO" == "ubuntu" ]]; then
      sudo apt update && sudo apt install -y qemu-user-static qemu-system-aarch64
    fi
  elif [[ "$ARCH" == "x86_64" ]]; then
    echo "x86_64 architecture detected. Installing QEMU for ARM emulation..."
    if [[ "$DISTRO" == "debian" || "$DISTRO" == "ubuntu" ]]; then
      sudo apt update && sudo apt install -y qemu-user-static
    fi
    # Enable QEMU for cross-architecture emulation (for ARM containers)
    echo "Setting up QEMU for cross-platform emulation..."
    sudo update-binfmts --enable qemu-arm
    sudo update-binfmts --enable qemu-aarch64
  fi

  echo "QEMU installed and set up successfully for architecture: $ARCH."
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

    while [ $attempts -le $MAX_ATTEMPTS ]; do
        echo "Attempt $attempts of $MAX_ATTEMPTS"

        # Attempt the installation
        run_os_update &&
        install_prerequisites 

        if [[ "$DEPLOY_SYSTEM" == "docker" ]]; then
            install_docker
        fi

        if [[ "$DEPLOY_SYSTEM" == "podman" ]]; then
            install_podman
        fi

        create_swap &&
        install_confirm &&

        # Check if the installation was successful
        if [ -f "$install_check" ]; then
            echo "Installation successful."
            break  # Exit the loop if successful
        else
            echo "Installation failed. Retrying..."
            ((attempts++))
        fi
    done

    if [ $attempts -gt $MAX_ATTEMPTS ]; then
        echo "Max attempts reached. Installation failed."
    fi
}
