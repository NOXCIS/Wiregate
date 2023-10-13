#!/bin/bash



title() {
    echo -e "\033[32m"
    echo '  

    ██╗    ██╗ ██████╗ ██████╗ ███╗   ███╗██╗  ██╗ ██████╗ ██╗     ███████╗
    ██║    ██║██╔═══██╗██╔══██╗████╗ ████║██║  ██║██╔═══██╗██║     ██╔════╝
    ██║ █╗ ██║██║   ██║██████╔╝██╔████╔██║███████║██║   ██║██║     █████╗  
    ██║███╗██║██║   ██║██╔══██╗██║╚██╔╝██║██╔══██║██║   ██║██║     ██╔══╝  
    ╚███╔███╔╝╚██████╔╝██║  ██║██║ ╚═╝ ██║██║  ██║╚██████╔╝███████╗███████╗
     ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝

                            Your Private Internet
**********************************************************************************
##################################################################################'
    echo -e "\033[0m"
}

dashes='----------------------------------------------------------------------------------'
equals='=================================================================================='
short_stars='***************'
stars='**********************************************************************************'
htag='##################################################################################'

env_var_title() {

    echo -e  '
__________________________________________________________________________
                                    |                                       
        ENVIRONMENT VARIABLES       |   VALUES                   
____________________________________|_______________________________________                                                                       
                                    |                                       
        SERVER IP                   |   \033[33m'"$SERVER_IP"'\033[0m                     
------------------------------------|---------------------------------------
        PIHOLE PASSWORD             |   \033[33m'"$PI_HOLE_PASS"'\033[0m                  
------------------------------------|---------------------------------------
        WIREGUARD PORT MAPPINGS     |   \033[33m'"$PORT_MAPPINGS"'\033[0m              
------------------------------------|---------------------------------------
        WIREGUARD INTERFACE COUNT   |   \033[33m'"$INTERFACE_COUNT"'\033[0m               
____________________________________|_______________________________________'
    
    echo -e "\033[0m"  # Reset text color to default
    return 0
}


set_uname_channel_title() {

    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET USERNAME FOR CHANNELS DATABASE"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}

set_pass_channel_title() {
    
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET PASSWORD FOR CHANNELS DATABASE"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_pass_pihole_title() {
    
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET PASSWORD FOR PIHOLE DASHBOARD"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_config_count_title() {
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET SERVER INTEFACE COUNT FOR WIREGUARD"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_server_ip_title() {
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET SERVER IP FOR WIREGUARD"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_config_port_range_title() {
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET WIREGUARD PORT RANGE"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_pihole_tz_title() {
    echo -e "\033[33m\n"
    printf "%s\n" "$dashes"
    echo "                       SET TIMEZONE "
    printf "%s" "$dashes"
    echo -e "\n\033[0m"
}
run_docker_title() {
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       Run Docker Compose "
    printf "%s\n" "$dashes"
    echo -e "\n\033[0m"
}
master_key_title() {
    echo -e "\033[32m"
    echo '
    ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗     ██╗  ██╗███████╗██╗   ██╗
    ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗    ██║ ██╔╝██╔════╝╚██╗ ██╔╝
    ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝    █████╔╝ █████╗   ╚████╔╝ 
    ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗    ██╔═██╗ ██╔══╝    ╚██╔╝  
    ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║    ██║  ██╗███████╗   ██║   
    ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝   ╚═╝   '
    echo -e "\033[0m"
}
readme_title() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "             Copy Master Key to empty WireGuard .conf file"
    echo "             Connect to Wireguard and access the Dashboard" 
    echo ""
    echo -e "     \033[33mWireGuard Dashboard Address:     \033[32mhttp://worm.hole\033[0m" 
    echo -e "     \033[33mPihole Dashboard Address:        \033[32mhttp://pi.hole\033[0m"
    echo -e "     \033[33mChannels LAN Messenger Address:  \033[32mhttp://channels.msg\033[0m"
    echo ""
    echo -e     "\033[33mLeave A Star on Github:  \033[32mhttps://github.com/NOXCIS/Worm-Hole\033[0m"
    echo -e "             \033[32mVPN Connection Required to Access Dashboards\033[0m" 
    echo -e "\033[33m"
    echo "#######################################################################"
    echo -e "\n\033[0m"
}