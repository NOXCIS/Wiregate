#!/bin/bash






menu() {
    run_animation
    cat <<EOF >"run-log.txt"
    R.I.P JRC Weir Tribute.
EOF
    clear
    title
    echo -e "\033[33m"
    echo "-----------------------------------------------------"
    echo "1. Start Install"
    echo "2. Launch Developement Build"
    echo "3. Switch to Local Install Mode I.E RaspberryPi 64 bit"
    echo "4. Switch to Cloud Install Mode I.E AWS" 
    echo "5. Reset WireGate Deployment"
    echo "6. Exit"
    echo "-----------------------------------------------------"
    read -p "$(tput setaf 1)Enter your choice: $(tput sgr0)" choice
    echo ""

    case $choice in
        1) run_selection ;;
        2) dev_build  ;;
        3) unbound_local ;;
        4) unbound_cloud ;;
        5) fresh_install ;;
        6) clear;exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}




















run_selection() {
# Function to display the menu and get user input
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

# Function to update menu options based on user input
update_menu() {
    local index=$1
    for i in "${!menu[@]}"; do
        menu[$i]=" "
    done
    menu[$index]="X"
}

update_dns_menu() {
    local index=$1
    for i in "${!dnsMenu[@]}"; do
        dnsMenu[$i]=" "
    done
    dnsMenu[$index]="X"
}

update_comms_menu() {
    local index=$1
    for i in "${!commsMenu[@]}"; do
        commsMenu[$i]=" "
    done
    commsMenu[$index]="X"
}

# Initialize menus
menu=(" " " " " ")     # Install Type
dnsMenu=(" " " ")       # DNS Setup
commsMenu=(" " " " " ") # Comms Setup



run_menu_update() {
display_menu
read -p "$(tput setaf 1)Enter Install Type Selection: $(tput sgr0)" installType
if [[ $installType -eq 0 ]]; then
    menu  # Call the 'menu' function
else
    update_menu $((installType - 1))

    export INSTALL_TYPE=""
    if [[ ${menu[0]} == "X" ]]; then
        INSTALL_TYPE="Express"
    elif [[ ${menu[1]} == "X" ]]; then
        INSTALL_TYPE="Advanced"
    elif [[ ${menu[2]} == "X" ]]; then
        INSTALL_TYPE="Pre_Configured"
    fi
fi
}

run_dns_menu_update() {
display_menu
read -p "$(tput setaf 1)Enter DNS Setup Selection: $(tput sgr0)" dnsSetup
if [[ $dnsSetup -eq 0 ]]; then
    menu  # Call the 'menu' function
else
    update_dns_menu $((dnsSetup - 1))
# Get user input for DNS Setup
    export DNS_SETUP=""
    if [[ ${dnsMenu[0]} == "X" ]]; then
        DNS_SETUP="AdGuard"
    elif [[ ${dnsMenu[1]} == "X" ]]; then
        DNS_SETUP="Pihole"
    fi
fi
return
}


run_comms_menu_update() {
display_menu
read -p "$(tput setaf 1)Enter Comms Setup Selection: $(tput sgr0)" commsSetup
if [[ $commsSetup -eq 0 ]]; then
        menu  # Call the 'menu' function
    else
    update_comms_menu $((commsSetup - 1))
    export COMMS_SETUP=""
    if [[ ${commsMenu[0]} == "X" ]]; then
        COMMS_SETUP="Darkwire"
    elif [[ ${commsMenu[1]} == "X" ]]; then
        COMMS_SETUP="Channels"
    fi
fi

}



run_menu_update
run_dns_menu_update
run_comms_menu_update




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
        "Express-AdGuard-Darkwire") Express-AdGuard-Darkwire ;;
        "Express-AdGuard-Channels") Express-AdGuard-Channels ;;
        "Express-Pihole-Darkwire") Express-Pihole-Darkwire ;;
        "Express-Pihole-Channels") Express-Pihole-Channels ;;
        "Advanced-AdGuard-Darkwire") Advanced-AdGuard-Darkwire ;;
        "Advanced-AdGuard-Channels") Advanced-AdGuard-Channels ;;
        "Advanced-Pihole-Darkwire") Advanced-Pihole-Darkwire ;;
        "Advanced-Pihole-Channels") Advanced-Pihole-Channels ;;
        "Pre_Configured-AdGuard-Darkwire") Pre_Configured-AdGuard-Darkwire ;;
        "Pre_Configured-AdGuard-Channels") Pre_Configured-AdGuard-Channels ;;
        "Pre_Configured-Pihole-Darkwire") Pre_Configured-Pihole-Darkwire ;;
        "Pre_Configured-Pihole-Channels") Pre_Configured-Pihole-Channels ;;
        *) echo "Invalid combination, no specific action taken." ;;
    esac
else
    menu # Call the menu function if the user says 'no'
fi
}