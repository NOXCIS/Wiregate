#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License


menu() {
    title
    echo -e "\033[33m"
    printf "%s\n" "$equals"
    echo "|[$blue Toggle         $yellow]|$reset Tor Transport Proxy  $red ($blue A $red) $yellow|$reset Tor Plugin $red($blue B $red) $yellow|$reset Tor Bridges $red($blue C $red) $yellow|$reset Use Podman $red($blue D $red) $yellow"
    printf "%s\n" "$dashes"
    echo "|[$blue Toggle         $yellow]|$reset DEPLOY STATE  $red ($blue S $red) $yellow|$yellow "
    printf "%s\n" "$dashes"
    echo "|[$blue Toggle         $yellow]|$reset PROTOCOL TYPE  $red ($blue W $red) $yellow|$yellow "
    printf "%s\n" "$dashes"
    echo "|[$blue Set Exit Nodes $yellow]|$reset Ex. <{US},{GB},{AU}> $red ($blue N $red) $yellow|"

    echo "-------------------------------------------------------------------------------------------"
    echo "|[$blue I      $yellow]| Start Install"
    echo "|[$blue R      $yellow]| Reset WireGate Deployment"
    echo "|[$blue H      $yellow]| Help"
    echo "|[$blue Dev    $yellow]| Launch Development Build"
    echo "|[$blue E      $yellow]| Exit"
    echo "-----------------------------------------------------"
    read -p "$(tput setaf 1)Enter your choice: $(tput sgr0)" choice
    echo ""

    case $choice in
        I) init_menu ;;
        A) toggle_tor_proxy ;;
        B) toggle_tor_plugin ;;
        C) toggle_tor_bridge ;;
        D) toggle_container_orchestrator ;;
        N) set_tor_exit_nodes ;;
        Dev) dev_build ;;
        R) fresh_install ;;
        H) help ;;
        E) clear; exit ;;
        S) toggle_dstate_type ;;
        W) toggle_proto_type ;;
        *) 
                clear
                echo "Invalid choice. Please try again."
                menu;;
    esac
}

toggle_dstate_type() {
    if [ "$DEPLOY_STATE" == "STATIC" ]; then
        DEPLOY_STATE="DYNAMIC"
        STATE="wg-dashboard"
    else
        DEPLOY_STATE="STATIC"
        STATE="wiregate"
    fi

    export DEPLOY_STATE
    export STATE
    clear
    menu
}

toggle_proto_type() {
    if [ "$PROTOCOL_TYPE" == "WireGuard" ]; then
        PROTOCOL_TYPE="AmneziaWG"
        AMNEZIA_WG="true"
        generate_awgd_values
    else
        PROTOCOL_TYPE="WireGuard"
        AMNEZIA_WG="false"
    fi

    export PROTOCOL_TYPE
    export AMNEZIA_WG
    clear
    menu
}

toggle_container_orchestrator () {
    if [ "$DEPLOY_SYSTEM" == "podman" ]; then
        DEPLOY_SYSTEM="docker"
    elif [ "$DEPLOY_SYSTEM" == "docker" ]; then
        DEPLOY_SYSTEM="podman"
    fi
    export DEPLOY_SYSTEM
    clear
    menu
}


toggle_tor_proxy() {
    if [ "$WGD_TOR_PROXY" == "true" ]; then
        WGD_TOR_PROXY="false"
        DEPLOY_TYPE="false"
    else
        WGD_TOR_PROXY="true"
        DEPLOY_TYPE="true"
    fi

    export WGD_TOR_PROXY
    export DEPLOY_TYPE
    clear
    menu
}

toggle_tor_bridge() {
    if [ "$WGD_TOR_BRIDGES" == "true" ]; then
        WGD_TOR_BRIDGES="false"
    else
        WGD_TOR_BRIDGES="true"
    fi

    export WGD_TOR_BRIDGES
    clear
    menu
}

toggle_tor_plugin() {
    case "$WGD_TOR_PLUGIN" in
        "snowflake")
            WGD_TOR_PLUGIN="webtunnel"
            ;;
        "webtunnel")
            WGD_TOR_PLUGIN="obfs4"
            ;;
        "obfs4")
            WGD_TOR_PLUGIN="snowflake"
            ;;
        *)
            # If WGD_TOR_PLUGIN has an unexpected value, reset to "snowflake"
            WGD_TOR_PLUGIN="snowflake"
            ;;
    esac

    export WGD_TOR_PLUGIN
    clear
    menu
}

set_tor_exit_nodes() {
    while true; do
        # Prompt the user for input, with 'default' as the default value
        read -p $red"Enter the TOR Exit Nodes$reset in the format $blue{US},{GB},{AU},{etc} or press Enter for 'default'$reset: " WGD_TOR_EXIT_NODES

        # If no input is given, set it to 'default'
        WGD_TOR_EXIT_NODES=${WGD_TOR_EXIT_NODES:-default}
        clear
        # Check if the input matches the expected format or is "default"
        if [[ "$WGD_TOR_EXIT_NODES" =~ ^\{[A-Z][A-Z]\}(,\{[A-Z][A-Z]\})*$ || "$WGD_TOR_EXIT_NODES" == "default" ]]; then
            # Valid format or default, export the variable
            export WGD_TOR_EXIT_NODES
            menu
            break
        else
            echo ""
            echo "Invalid input. Please use the correct format: {US},{GB},{AU}, etc., or press Enter for 'default'."
        fi
    done
}



run_menu_update() {
    local menu_type=$1
    local index=$2
    case $menu_type in
        menu)     local menu_array=("${menu[@]}") ;;
        dnsMenu)  local menu_array=("${dnsMenu[@]}") ;;
        commsMenu) local menu_array=("${commsMenu[@]}") ;;
        *) echo "Invalid menu type" && return 1 ;;
    esac
    # Clear all entries and mark the specified index
    for i in "${!menu_array[@]}"; do
        menu_array[$i]=" "
    done
    menu_array[$index]="X"

    # Assign the updated array back to the appropriate menu
    case $menu_type in
        menu)     menu=("${menu_array[@]}") ;;
        dnsMenu)  dnsMenu=("${menu_array[@]}") ;;
        commsMenu) commsMenu=("${menu_array[@]}") ;;
    esac

    # Export variables based on menu selection
    case $menu_type in
        menu) 
            if [[ ${menu[0]} == "X" ]]; then
                export INSTALL_TYPE="Express"
            elif [[ ${menu[1]} == "X" ]]; then
                export INSTALL_TYPE="Advanced"
            fi
            ;;
        dnsMenu)
            if [[ ${dnsMenu[0]} == "X" ]]; then
                export DNS_SETUP="AdGuard"
            elif [[ ${dnsMenu[1]} == "X" ]]; then
                export DNS_SETUP="Pihole"
            fi
            ;;
        commsMenu)
            if [[ ${commsMenu[0]} == "X" ]]; then
                export COMMS_SETUP="Darkwire"
            elif [[ ${commsMenu[1]} == "X" ]]; then
                export COMMS_SETUP="None"
            fi
            ;;
    esac
}

display_menu() {
    clear
    title
    echo "1.$(tput setaf 3) Select Install Type: or ENTER 0 for main menu"
    echo "------------------------------------------------------------------------------------------"
    echo "$(tput setaf 2)1 $(tput sgr0)(${menu[0]}) $(tput setaf 3)Express$(tput sgr0)    $(tput setaf 3)|  $(tput setaf 2)2 $(tput sgr0)(${menu[1]}) $(tput setaf 3)Advanced$(tput sgr0)  $(tput setaf 3)"
    echo "$(tput setaf 2)==========================================================================================$(tput sgr0)"
    echo
    echo "2.$(tput setaf 3) Select DNS Setup: or ENTER 0 for main menu"
    echo "------------------------------------------------------------------------------------------"
    echo "$(tput setaf 2)1 $(tput sgr0)(${dnsMenu[0]}) $(tput setaf 3)AdGuard$(tput sgr0)    $(tput setaf 3)|  $(tput setaf 2)2 $(tput sgr0)(${dnsMenu[1]}) $(tput setaf 3)Pihole$(tput sgr0)"
    echo "$(tput setaf 2)==========================================================================================$(tput sgr0)"
    echo
    echo "3.$(tput setaf 3) Select Comms Platform: or ENTER 0 for main menu"
    echo "------------------------------------------------------------------------------------------"
    echo "$(tput setaf 2)1 $(tput sgr0)(${commsMenu[0]})  $(tput setaf 3)Darkwire$(tput sgr0)  $(tput setaf 3)|  $(tput setaf 2)2 $(tput sgr0)(${commsMenu[1]}) $(tput setaf 3)None$(tput sgr0)"
    echo "$(tput setaf 2)==========================================================================================$(tput sgr0)"
    echo
}


init_menu() {
    # Initialize menus
    menu=(" " " ")     # Install Type
    dnsMenu=(" " " ")  # DNS Setup
    commsMenu=(" " " ") # Comms Setup

    # Define an array of menus
    menus=("menu" "dnsMenu" "commsMenu")


    # Iterate through each menu
    for i in "${!menus[@]}"; do
        display_menu        
        while true; do
            read -p "Enter your choice: " choice
            
            # Validate input
            if [[ ! "$choice" =~ ^[1-9]$ ]]; then
                echo "Invalid choice. Please enter a number corresponding to the options."
                continue
            fi
            
            # Check if choice is within valid range
            if (( choice < 1 || choice > ${#menu[@]} )); then
                echo "Choice out of range. Please select a valid option."
            else
                run_menu_update "${menus[i]}" $((choice - 1))
                break
            fi
        done
        clear
    done

    display_menu

    # Confirm user selection
    read -p "$(tput setaf 1)Are you sure you want to proceed with the selected options? ($(tput setaf 3)yes/no$(tput sgr0)$(tput setaf 1)): $(tput sgr0)" confirm
    if [ "$confirm" == "yes" ]; then
        echo
        echo -e "\033[32m"
        echo "################--------------DEPLOYING--------------##################"
        echo "#######################################################################"
        echo "INSTALL_TYPE: $INSTALL_TYPE"
        echo "DNS_SETUP: $DNS_SETUP"
        echo "COMMS_SETUP: $COMMS_SETUP"
        echo "#######################################################################"
        echo -e "\033[0m"

        # Call functions based on user selections
        case "$INSTALL_TYPE-$DNS_SETUP-$COMMS_SETUP" in
            "Express-AdGuard-Darkwire") setup_environment "Express" "AdGuard" "Darkwire" ;;
            "Express-AdGuard-None") setup_environment "Express" "AdGuard" "Channels" ;;
            "Express-Pihole-Darkwire") setup_environment "Express" "Pihole" "Darkwire" ;;
            "Express-Pihole-None") setup_environment "Express" "Pihole" "Channels" ;;
            "Advanced-AdGuard-Darkwire") setup_environment "Advanced" "AdGuard" "Darkwire" ;;
            "Advanced-AdGuard-None") setup_environment "Advanced" "AdGuard" "Channels" ;;
            "Advanced-Pihole-Darkwire") setup_environment "Advanced" "Pihole" "Darkwire" ;;
            "Advanced-Pihole-None") setup_environment "Advanced" "Pihole" "Channels" ;;
            *) echo "Invalid combination, no specific action taken." ;;
        esac
    elif [ "$confirm" == "no" ]; then
        clear
        menu
    else 
        clear
        init_menu # Call the menu function if the user says 'no'
    fi
}

# Start the script