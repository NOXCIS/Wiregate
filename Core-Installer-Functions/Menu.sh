#!/bin/bash


menu() {
    run_animation
    cat <<EOF >"run-log.txt"
     Anim Tribute has been ran!!!
EOF
   
    title
    echo "Please choose an DNS Provider:"
    echo "1. Pihole Install"
    echo "2. AdGuard Install"
    echo "3. Reset Wormhole Deployment"
    echo "4. Switch to local deploy I.E RaspberryPi"
    echo "5. Switch to Cloud deploy I.E AWS" 
    echo "6. Exit"
    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) pihole_install_menu ;;
        2) adguard_install_menu ;;
        3) fresh_install ;;
        4) unbound_config_swap ;;
        5) unbound_config_swapback ;;
        6) exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}


pihole_install_menu() {
    clear 
    pihole_install_title 
    pihole_compose_swap >/dev/null 2>&1
    echo "Please choose an option:"
    echo "1. Express Install"
    echo "2. Advanced Install"
    echo "3. Custom PreConfigured Install"
    echo "4. Reset Wormhole Deployment"
    echo "5. Exit"
    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) pihole_express_setup ;;
        2) pihole_advanced_setup ;;
        3) pihole_predefined_setup ;;
        4) fresh_install ;;
        5) menu ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}

adguard_install_menu() {
    clear 
    adguard_install_title
    adguard_compose_swap >/dev/null 2>&1
    echo "Please choose an option:"
    echo "1. Express Install"
    echo "2. Advanced Install"
    echo "3. Custom PreConfigured Install"
    echo "4. Reset Wormhole Deployment"
    echo "5. Exit"
    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) adguard_express_setup ;;
        2) adguard_advanced_setup ;;
        3) adguard_predefined_setup ;;
        4) fresh_install ;;
        5) menu ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}