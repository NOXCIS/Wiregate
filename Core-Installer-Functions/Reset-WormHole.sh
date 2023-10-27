fresh_install() {
    local masterkey_file="./WG-Dash/master-key/master.conf"
    local config_folder="./WG-Dash/config"
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
    echo "              Your Client, Server, & Master Key Configs         "
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

    read -p "Continue Resetting Wireguard? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    echo ""
    echo ""

    if [[ $answer == [Yy] || -z $answer ]]; then
        port_mappings="770-777:770-777/udp"
        export PORT_MAPPINGS="$port_mappings"
        docker compose down --volumes --remove-orphans

        if [ -f "$masterkey_file" ]; then
            echo "Removing existing '$masterkey_file'..."
            sudo rm "$masterkey_file"
            echo "Existing '$masterkey_file' removed."
        fi

        if [ -d "$config_folder" ]; then
            echo "Removing existing '$config_folder'..."
            sudo rm -r "$config_folder"
            echo "Existing '$config_folder' removed."
        fi

        echo "Removing existing Compose File"
        sudo rm "$yml_file"
        echo "Existing Compose File removed."

        echo "Pulling from Default Compose File..."
        cat Global-Configs/Docker-Compose/pihole-docker-compose.yml > "$yml_file"
        echo "File successfully pulled from Default Compose File."
        
        clear
        menu
    else
        clear
        menu
    fi
}
pihole_preset_compose_swap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    echo "Pulling from Preset Compose File..."
    cat Global-Configs/Docker-Compose/pihole-custom-docker-compose.yml > "$yml_file"
    echo "File successfully pulled from Preset Compose File."

}
adguard_preset_compose_swap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    echo "Pulling from Preset Compose File..."
    cat Global-Configs/Docker-Compose/adguard-custom-docker-compose.yml > "$yml_file"
    echo "File successfully pulled from Preset Compose File."

}
adguard_compose_swap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    echo "Pulling from Preset Compose File..."
    cat Global-Configs/Docker-Compose/adguard-docker-compose.yml > "$yml_file"
    echo "File successfully pulled from Preset Compose File."
}
pihole_compose_swap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    cat Global-Configs/Docker-Compose/pihole-docker-compose.yml > "$yml_file"
    
}
sqwip() {
    TIMER_VALUE=0
    set_pihole_password &&
    TIMER_VALUE=5
}