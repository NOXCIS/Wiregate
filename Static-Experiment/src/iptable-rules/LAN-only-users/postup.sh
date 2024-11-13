#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
#DEFINE INTERFACE ENVIORNMENT 
##############################################################################################################
WIREGUARD_INTERFACE=LANP2P
WIREGUARD_LAN=172.16.0.1/24
MASQUERADE_INTERFACE=eth0

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
#Accept on connections to peers of LAN zone only
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 172.16.0.1/24 -j ACCEPT
#END OF CORE RULES
##############################################################################################################


# Drop everything else coming through the Wireguard interface
iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP
# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN