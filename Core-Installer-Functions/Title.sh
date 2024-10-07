#!/bin/bash

red="$(tput setaf 1)"
green="$(tput setaf 2)"
yellow="$(tput setaf 3)"
blue="$(tput setaf 6)"
reset="$(tput sgr0)"
dashes='----------------------------------------------------------------------------------------------------------------------------------------'
equals='========================================================================================================================================'
short_stars='***************'
stars='**********************************************************************************'
htag='##################################################################################'





help() {
    clear
    echo -e "Usage sudo ./install.sh <ARG1> <ARG2>\n"    
            echo "$yellow Options for Install ARG 1"
            printf "%s\n" "$dashes"
            echo "|$blue TOR OFF:      $yellow| off           |               |                 "
            echo "|$blue TOR BRIDGED:  $yellow| Tor-br-snow   | Tor-br-webtun | Tor-br-obfs4    " 
            echo "|$blue TOR NoBRIDGE: $yellow| Tor-snow      | Tor-webtun    | Tor-obfs4       "
            printf "%s\n" "$dashes"

            echo -e "$yellow Options for Install ARG 2\n"
            printf "%s\n" "$dashes"
            echo "|$blue EXAMPLE:  $yellow|$red E-A-D $yellow for Express-AdGuard-Darkwire        $red|                                     |  "
            echo "|$blue LEDGEND:  $yellow|$green <InstallType>-<DNS>-<IncludeDarkwire>      $red|                                     |$yellow"
            printf "%s\n" "$equals"
            echo "|$blue USAGE:    $yellow| (E) $reset for Express $red or $yellow (A) $reset for Advanced   $red|||$yellow (A) $reset for AdGuard $red or $yellow (P) $reset for Pihole $red|||$yellow (D) $reset to include Darkwire $red or $yellow (C) $reset to omit"
            printf "$yellow%s\n" "$equals"
            echo -e "|$blue UTIL:     $yellow| Use $red dev $yellow or $red reset $yellow with $green off $yellow as $reset ARG1 $yellow to reset the deployment or run Development Build \n"
            printf "%s\n" "$dashes"


}

title() {
    echo -e "\033[32m"  # Set text color to green
    echo -e '
________________________________________________________________________________
|                                                                               
|       ██╗    ██╗██╗██████╗ ███████╗ ██████╗  █████╗ ████████╗███████╗         
|       ██║    ██║██║██╔══██╗██╔════╝██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝         
|       ██║ █╗ ██║██║██████╔╝█████╗  ██║  ███╗███████║   ██║   █████╗           
|       ██║███╗██║██║██╔══██╗██╔══╝  ██║   ██║██╔══██║   ██║   ██╔══╝           
|       ╚███╔███╔╝██║██║  ██║███████╗╚██████╔╝██║  ██║   ██║   ███████╗         
|        ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝         
|                                                                                  
|                        [TOR] Transport Plugin:   \033[33m'"$WGD_TOR_PLUGIN"'\033[32m                    
|                        [TOR] Transport Enabled:  \033[33m'"$DEPLOY_TYPE"'\033[32m                        
|                        [TOR] Use Bridges:        \033[33m'"$WGD_TOR_BRIDGES"'\033[32m                        
|_______________________________________________________________________________'                                                               
    echo -e "\033[0m"  # Reset to default text color
}



env_var_pihole_title() {

    echo -e  '
______________________________________________________________________________________________________________________________________
                                    |                                       
        ENVIRONMENT VARIABLES       |   VALUES                   
____________________________________|_________________________________________________________________________________________________                                                                       
                                    |                                       
    SERVER IP                       |   \033[33m'"$WGD_REMOTE_ENDPOINT"'\033[0m                     
------------------------------------|-------------------------------------------------------------------------------------------------
    PIHOLE PASSWORD                 |   \033[33m'"$PI_HOLE_PASS"'\033[0m                  
------------------------------------|-------------------------------------------------------------------------------------------------
    WIREGUARD DASHBOARD USER        |   \033[33m'"$WGD_USER"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------
    WIREGUARD DASHBOARD PASSWORD    |   \033[33m'"$WGD_PASS"'\033[0m               
------------------------------------|-------------------------------------------------------------------------------------------------
    WIREGUARD PORT MAPPINGS         |   \033[33m'"$WGD_PORT_MAPPINGS"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------
    MASTER KEY DECRYPTION KEY       |   \033[33m'"$MASTER_KEY_PASSWORD"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------'
    echo -e "\033[0m"  # Reset text color to default
    return 0
}

env_var_adguard_title() {

    echo -e  '
______________________________________________________________________________________________________________________________________
                                    |                                       
        ENVIRONMENT VARIABLES       |   VALUES                   
____________________________________|_________________________________________________________________________________________________                                                                       
                                    |                                       
    SERVER IP                       |   \033[33m'"$WGD_REMOTE_ENDPOINT"'\033[0m                     
------------------------------------|-------------------------------------------------------------------------------------------------
    ADGUARD USERNAME                |   \033[33m'"$AD_GUARD_USER"'\033[0m
------------------------------------|-------------------------------------------------------------------------------------------------
    ADGUARD PASSWORD                |   \033[33m'"$AD_GUARD_PASS"'\033[0m                  
------------------------------------|-------------------------------------------------------------------------------------------------
    WIREGUARD DASHBOARD USER        |   \033[33m'"$WGD_USER"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------
    WIREGUARD DASHBOARD PASSWORD    |   \033[33m'"$WGD_PASS"'\033[0m               
------------------------------------|-------------------------------------------------------------------------------------------------
    WIREGUARD PORT MAPPINGS         |   \033[33m'"$WGD_PORT_MAPPINGS"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------
    MASTER KEY DECRYPTION KEY       |   \033[33m'"$MASTER_KEY_PASSWORD"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------'
    echo -e "\033[0m"  # Reset text color to default
    return 0
}

env_var_adguard_title_short() {

    echo -e  '
______________________________________________________________________________________________________________________________________
                                    |                                       
        ENVIRONMENT VARIABLES       |   VALUES                   
____________________________________|_________________________________________________________________________________________________                                                                       
                                    |                                       
    ADGUARD USERNAME                |   \033[33m'"$AD_GUARD_USER"'\033[0m
------------------------------------|-------------------------------------------------------------------------------------------------
    ADGUARD PASSWORD                |   \033[33m'"$AD_GUARD_PASS"'\033[0m                  
------------------------------------|-------------------------------------------------------------------------------------------------                              
    WIREGUARD PORT MAPPINGS         |   \033[33m'"$WGD_PORT_MAPPINGS"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------'
    echo -e "\033[0m"  # Reset text color to default
    return 0
}

env_var_pihole_title_short() {

    echo -e  '
______________________________________________________________________________________________________________________________________
                                    |                                       
        ENVIRONMENT VARIABLES       |   VALUES                   
____________________________________|_________________________________________________________________________________________________                                                                       
                                    |                                       
    WIREGUARD PORT MAPPINGS         |   \033[33m'"$WGD_PORT_MAPPINGS"'\033[0m              
------------------------------------|-------------------------------------------------------------------------------------------------'
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
set_uname_adguard_title() {

    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET USERNAME FOR ADGUARD"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_uname_wgdash_title() {

    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET USERNAME FOR WIREGUARD DASHBOARD"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_pass_wgdash_title() {
    
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET PASSWORD FOR WIREGUARD DASHBOARD"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_pass_adguard_title() {
    
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET PASSWORD FOR ADGUARD"
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
set_dw_rm_hash_title() {
    
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET ROOM HASH SECRET FOR DARKWIRE"
    printf "%s" "$dashes"
    echo -e "\n\033[0m"

}
set_server_ip_title() {
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "                       SET REMOTE ENDPOINT FOR WIREGUARD"
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
set_timer_value() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo ""
    echo "The Timer value dictates how much time you will have in each setup step."
    echo ""
    echo "#######################################################################"
    echo -e "\n\033[0m"
    read -p "Enter the timer value (in seconds): " TIMER_VALUE
    echo ""
    echo -e "Timer value set to \033[32m$TIMER_VALUE\033[0m seconds."
    echo ""
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

    echo -e "$green
    ███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗     ██╗  ██╗███████╗██╗   ██╗
    ████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗    ██║ ██╔╝██╔════╝╚██╗ ██╔╝
    ██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝    █████╔╝ █████╗   ╚████╔╝ 
    ██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗    ██╔═██╗ ██╔══╝    ╚██╔╝  
    ██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║    ██║  ██╗███████╗   ██║   
    ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝   ╚═╝   \n"

}
readme_title() {
    echo -e "\033[33m\n" 
    echo "#######################################################################"
    echo "        THIS MESSAGE SELF DESTRUCTS IN 60 seconds"
    echo "        Copy Master Key to empty WireGuard .conf file"
    echo "        Connect to Wireguard and access the Dashboard" 
    echo ""
    echo -e "     \033[33mWireGuard Dashboard Address:     \033[32mhttp://wire.gate\033[0m" 
    echo -e "     \033[33mPihole Dashboard Address:        \033[32mhttp://pi.hole\033[0m"
    echo -e "     \033[33mPihole Dashboard Address:        \033[32mhttp://ad.guard\033[0m"    
    echo -e "     \033[33mChannels LAN Messenger Address:  \033[32mhttp://wire.chat\033[0m"
    echo -e "     \033[33mDarkwire Address:                \033[32mhttps://dark.wire\033[0m"
    echo ""
    echo -e "     \033[33mLeave A Star on Github:  \033[32mhttps://github.com/NOXCIS/Worm-Hole\033[0m"
    echo ""
    echo -e "             \033[32mWireGuard Connection Required to Access Dashboards\033[0m" 
    echo -e "\033[33m"
    echo "#######################################################################"
    echo -e "\n\033[0m"
}
master_key_pass_title() {
    echo -e "\033[33m\n" 
    printf "%s\n" "$dashes"
    echo "MASTER KEY DECRYPTION PASSWORD: '"$MASTER_KEY_PASSWORD"'   "
    printf "%s" "$dashes"
    echo -e "\n\033[0m"
}

leave_a_star_title() {

title
echo -e "\033[33m\n" 
    echo ""
    echo -e "\033[33mLeave A Star on Github:  \033[32mhttps://github.com/NOXCIS/Wiregate\033[0m"
    echo ""
    echo -e "\033[33m"
    echo "#######################################################################"
    echo -e "\n\033[0m"



}
