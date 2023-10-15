#!/bin/bash


menu() {
    title
    echo "Please choose an option:"
    echo "1. Express Install"
    echo "2. Advanced Install"
    echo "3. Auto configuration with quickset for # of Server Interfaces to Generate & Pihole Password"
    echo "4. Reset Wormhole Deployment"
    echo "5. Exit"
    read -p "Enter your choice: " choice
    echo ""

    case $choice in
        1) express_setup ;;
        2) advanced_setup ;;
        3) auto_set_wct ;;
        4) fresh_install ;;
        5) exit ;;
        *) echo "Invalid choice. Please try again." ;;
    esac
}