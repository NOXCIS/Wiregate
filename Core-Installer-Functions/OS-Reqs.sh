#!/bin/bash


#OS


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
install_prerequisites() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "                        Installing prerequisites"
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    # List of prerequisites
    PREREQUISITES=(
        curl
        qrencode
        git
        openssl
        apache2-utils
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

install_requirements() {
    run_os_update &&
    install_prerequisites &&
    install_docker &&
    menu
}