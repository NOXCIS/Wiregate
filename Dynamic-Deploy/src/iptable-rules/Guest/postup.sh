#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
#DEFINE INTERFACE ENVIORNMENT 
##############################################################################################################
WIREGUARD_INTERFACE=GUESTS
WIREGUARD_LAN=192.168.20.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}

# Enable NAT on the interface
iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Add a WIREGUARD chain to the FORWARD chain
CHAIN_NAME="WIREGUARD_$WIREGUARD_INTERFACE"
iptables -N $CHAIN_NAME
iptables -A FORWARD -j $CHAIN_NAME
##############################################################################################################


#START OF CORE RULES 
##############################################################################################################
# Accept related or established traffic
iptables -A $CHAIN_NAME -o $WIREGUARD_INTERFACE -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
# Drop traffic to wg-dashboard
iptables -A INPUT -i $WIREGUARD_INTERFACE -j DROP
#END OF CORE RULES
##############################################################################################################


#START OF GLOBAL DNS FORWARDING RULES 
##############################################################################################################
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p tcp --dport 53 -j ACCEPT
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p udp --dport 53 -j ACCEPT
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p tcp --dport 853 -j ACCEPT
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p udp --dport 853 -j ACCEPT
#END OF GLOBAL DNS FORWARDING RULES 
##############################################################################################################


# START OF GUEST RULES
##############################################################################################################
# Drop traffic to private IP address ranges
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16 -j DROP
# Accept outgoing connections to HTTP(S) ports to any IP address (public because of rule above)
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 0.0.0.0/0 -p tcp -m multiport --dports 80,443 -j ACCEPT
#END OF GUEST RULES
##############################################################################################################



# Accept traffic from any Wireguard IP address connected to the Wireguard server
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -j ACCEPT
# Drop everything else coming through the Wireguard interface
iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP
# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN
#END OF GUEST RULES
##############################################################################################################