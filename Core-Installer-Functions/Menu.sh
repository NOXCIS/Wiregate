#!/bin/bash

menu() {
    run_animation
    cat <<EOF >"run-log.txt"
R.I.P JRC Weir Tribute.
EOF
    clear
    set_tag
    title
    echo -e "\033[33m"
    echo "-----------------------------------------------------"
    echo "1. Start Install"
    echo "2. Launch Development Build"
    echo "3. Switch to Local Install Mode I.E RaspberryPi 64 bit"
    echo "4. Switch to Cloud Install Mode I.E AWS" 
    echo "5. Reset WireGate Deployment"
    echo "6. Exit"
    echo "-----------------------------------------------------"
    read -p "$(tput setaf 1)Enter your choice: $(tput sgr0)" choice
    echo ""

    case $choice in
        1) init_menu ;;
        2) dev_build ;;
        3) unbound_local ;;
        4) unbound_cloud ;;
        5) fresh_install ;;
        6) clear; exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}

run_menu_update() {
    local menu_type=$1
    local index=$2

    # Choose the appropriate menu array based on menu_type
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
            elif [[ ${menu[2]} == "X" ]]; then
                export INSTALL_TYPE="Pre_Configured"
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
                export COMMS_SETUP="Channels"
            fi
            ;;
    esac
}

display_menu() {
    clear
    title
    echo "1.$(tput setaf 3) Select Install Type: or ENTER 0 for main menu"
    echo "------------------------------------------------------------------------------------------"
    echo "$(tput setaf 2)1 $(tput sgr0)(${menu[0]}) $(tput setaf 3)Express$(tput sgr0)    $(tput setaf 3)|  $(tput setaf 2)2 $(tput sgr0)(${menu[1]}) $(tput setaf 3)Advanced$(tput sgr0)  $(tput setaf 3)|  $(tput setaf 2)3 $(tput sgr0)(${menu[2]}) $(tput setaf 3)Pre_Configured$(tput sgr0)"
    echo "$(tput setaf 2)==========================================================================================$(tput sgr0)"
    echo
    echo "2.$(tput setaf 3) Select DNS Setup: or ENTER 0 for main menu"
    echo "------------------------------------------------------------------------------------------"
    echo "$(tput setaf 2)1 $(tput sgr0)(${dnsMenu[0]}) $(tput setaf 3)AdGuard$(tput sgr0)    $(tput setaf 3)|  $(tput setaf 2)2 $(tput sgr0)(${dnsMenu[1]}) $(tput setaf 3)Pihole$(tput sgr0)"
    echo "$(tput setaf 2)==========================================================================================$(tput sgr0)"
    echo
    echo "3.$(tput setaf 3) Select Comms Platform: or ENTER 0 for main menu"
    echo "------------------------------------------------------------------------------------------"
    echo "$(tput setaf 2)1 $(tput sgr0)(${commsMenu[0]})  $(tput setaf 3)Darkwire$(tput sgr0)  $(tput setaf 3)|  $(tput setaf 2)2 $(tput sgr0)(${commsMenu[1]}) $(tput setaf 3)Channels$(tput sgr0)"
    echo "$(tput setaf 2)==========================================================================================$(tput sgr0)"
    echo
}

init_menu() {
    # Initialize menus
    menu=(" " " " " ")     # Install Type
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

        export $INSTALL_TYPE
        export $DNS_SETUP
        export $COMMS_SETUP

        # Call functions based on user selections
        case "$INSTALL_TYPE-$DNS_SETUP-$COMMS_SETUP" in
            "Express-AdGuard-Darkwire") setup_environment "Express" "AdGuard" "Darkwire" ;;
            "Express-AdGuard-Channels") setup_environment Ex-AdG-Chnls ;;
            "Express-Pihole-Darkwire") setup_environment Ex-Pih-D ;;
            "Express-Pihole-Channels") setup_environment Ex-Pih-Chnls ;;
            "Advanced-AdGuard-Darkwire") setup_environment Adv-AdG-D ;;
            "Advanced-AdGuard-Channels") setup_environment Adv-AdG-Chnls ;;
            "Advanced-Pihole-Darkwire") setup_environment Adv-Pih-D ;;
            "Advanced-Pihole-Channels") setup_environment Adv-Pih-Chnls ;;
            "Pre_Configured-AdGuard-Darkwire") setup_environment Pre_Conf-AdG-D ;;
            "Pre_Configured-AdGuard-Channels") setup_environment Pre_Conf-AdG-Chnls ;;
            "Pre_Configured-Pihole-Darkwire") setup_environment Pre_Conf-Pih-D ;;
            "Pre_Configured-Pihole-Channels") setup_environment Pre_Conf-Pih-Chnls ;;
            *) echo "Invalid combination, no specific action taken." ;;
        esac
    else
        menu # Call the menu function if the user says 'no'
    fi
}

# Start the script
