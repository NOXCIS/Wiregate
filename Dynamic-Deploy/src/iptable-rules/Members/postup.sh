#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
#DEFINE INTERFACE ENVIORNMENT 
##############################################################################################################
WIREGUARD_INTERFACE=MEMBERS
WIREGUARD_LAN=192.168.10.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}


# Enable NAT on the interface
iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Add a WIREGUARD chain to the FORWARD chain
CHAIN_NAME="WIREGUARD_$WIREGUARD_INTERFACE"
iptables -N $CHAIN_NAME
iptables -A FORWARD -j $CHAIN_NAME


#START OF CORE RULES 
##############################################################################################################
# Accept related or established traffic
iptables -A $CHAIN_NAME -o $WIREGUARD_INTERFACE -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
# Allow traffic to the local loopback interface
iptables -A $CHAIN_NAME -o lo -j ACCEPT
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


# START OF MEMEBRS RULES
##############################################################################################################
# Accept Foward traffic to WireChat @ port 80 @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.4 -p tcp -m multiport --dports 80,443 -j ACCEPT
# Drop Forward traffic to AdGuard Dashboard @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.100 -j DROP
# Drop Forward traffic to Unbound @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.200 -j DROP
# Drop Forward traffic to Channels Database @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.5 -j DROP
# Drop all other Foward traffic to WireChat @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.4 -j DROP
#END OF MEMEBRS RULES
##############################################################################################################

#PORT FOWARDING RULES
##############################################################################################################
# Accept outgoing connections to on the following ports 20,21,22,80,443,3389 to any IP address (public because of rule above)
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 0.0.0.0/0 -p tcp -m multiport --dports 20,21,22,80,443,3389 -j ACCEPT
##############################################################################################################
# END OF PORT FOWARDING RULES


# Accept traffic from any Wireguard IP address connected to the Wireguard server
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -j ACCEPT
# Drop everything else coming through the Wireguard interface
iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP
# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN
