#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

fresh_install() {
    local masterkey_file="./configs/master-key/master.conf"
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
    echo "        Your Client, Server, Master Key Configs, & All Database        "
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"

    read -p "Continue Resetting Wireguard? $(tput setaf 1)(y/n)$(tput sgr0) " answer 
    echo ""
    echo ""

    if [[ $answer == [Yy] || -z $answer ]]; then
        port_mappings="770-777:770-777/udp"
        export WGD_PORT_MAPPINGS="$port_mappings"
        $DEPLOY_SYSTEM compose down --volumes --remove-orphans

        if [ -f "$masterkey_file" ]; then
            echo "Removing existing maskerkey ..."
            sudo rm "$masterkey_file"
            sudo rm -r .env
            echo "Existing masterkey removed."
        fi



        echo "Removing existing Compose File"
        sudo rm "$yml_file"
        echo "Existing Compose File removed."

        echo "Pulling from Default Compose File..."
        cat AutoInstaller-Functions/Docker-Compose/AdGuard/adguard.yml > "$yml_file"
        echo "File successfully pulled from Default Compose File."
        
        clear
        menu
    else
        clear
        menu
    fi
}






pihole_channl_cswap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    cat AutoInstaller-Functions/pihole/default-pihole.yml > "$yml_file"
    return
}



pihole_dwire_cswap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    cat AutoInstaller-Functions/Docker-Compose/Pihole/pihole.yml > "$yml_file"
    return
}



adguard_channl_cswap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    echo "Pulling from Preset Compose File..."
    cat AutoInstaller-Functions/Docker-Compose/AdGuard/default-adguard.yml > "$yml_file"
    echo "File successfully pulled from Preset Compose File."
    return
}



adguard_dwire_cswap() {
    local yml_file="docker-compose.yml"
    sudo rm "$yml_file"
    echo "Pulling from Preset Compose File..."
    cat AutoInstaller-Functions/Docker-Compose/AdGuard/adguard.yml > "$yml_file"
    echo "File successfully pulled from Preset Compose File."
    return
}








