#!/bin/bash

red="$(tput setaf 1)"
green="$(tput setaf 2)"
yellow="$(tput setaf 3)"
blue="$(tput setaf 6)"
reset="$(tput sgr0)"


menu() {
    clear
    title
    echo -e "\033[33m"
    echo "-------------------------------------------------------------------------------------------"
    echo "|[$blue I      $yellow]| Start Install"
    echo "|[$blue Toggle $yellow]| Tor Transport Proxy$red[ $blue A $red ] $reset|$yellow Tor Plugin$red[ $blue B $red ] $reset|$yellow Tor Bridges$red[ $blue C $red ] $yellow"
    echo "|[$blue Dev    $yellow]| Launch Development Build"
    echo "|[$blue R      $yellow]| Reset WireGate Deployment"
    echo "|[$blue E      $yellow]| Exit"
    echo "-----------------------------------------------------"
    read -p "$(tput setaf 1)Enter your choice: $(tput sgr0)" choice
    echo ""

    case $choice in
        I) init_menu ;;
        A) toggle_tor_proxy ;;
        B) toggle_tor_plugin ;;
        C) toggle_tor_bridge ;;
        Dev) dev_build ;;
        R) fresh_install ;;
        E) clear; exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
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
    menu
}

toggle_tor_bridge() {
    if [ "$WGD_TOR_BRIDGES" == "true" ]; then
        WGD_TOR_BRIDGES="false"
    else
        WGD_TOR_BRIDGES="true"
    fi

    export WGD_TOR_BRIDGES
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
    menu
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
    dnsMenu=(" " " ")       # DNS Setup
    commsMenu=(" " " " " ") # Comms Setup

    # Define an array of menus and their labels
    menus=("menu" "dnsMenu" "commsMenu")
    labels=("Install Type: (1) Express (2) Advanced (3) Pre_Configured"
            "DNS Setup: (1) AdGuard (2) Pihole"
            "Comms Platform: (1) Darkwire (2) Channels")

    # Iterate through each menu
    for i in "${!menus[@]}"; do
        display_menu
        # Uncomment the line below if you want to show the label for each menu
        # echo "${labels[i]}"
        read -p "Enter your choice: " choice
        run_menu_update "${menus[i]}" $((choice - 1))
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
            "Express-Pihole-Darkwire") setup_environment  "Express" "Pihole" "Darkwire" ;;
            "Express-Pihole-None") setup_environment  "Express" "Pihole" "Channels" ;;
            "Advanced-AdGuard-Darkwire") setup_environment "Advanced" "AdGuard" "Darkwire" ;;
            "Advanced-AdGuard-None") setup_environment "Advanced" "AdGuard" "Channels" ;;
            "Advanced-Pihole-Darkwire") setup_environment  "Advanced" "Pihole" "Darkwire" ;;
            "Advanced-Pihole-None") setup_environment  "Advanced" "Pihole" "Channels" ;;
            *) echo "Invalid combination, no specific action taken." ;;
        esac
    else
        menu # Call the menu function if the user says 'no'
    fi
}

# Start the script