#!/bin/bash
WIREGUARD_INTERFACE=members
WIREGUARD_LAN=192.168.10.1/24
MASQUERADE_INTERFACE=eth0

iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Add a WIREGUARD_wg0 chain to the FORWARD chain
CHAIN_NAME="WIREGUARD_$WIREGUARD_INTERFACE"
iptables -N $CHAIN_NAME
iptables -A FORWARD -j $CHAIN_NAME

# Accept related or established traffic
iptables -A $CHAIN_NAME -o $WIREGUARD_INTERFACE -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Drop incoming traffic from wg1 to wg-dashboard
iptables -A INPUT -i $WIREGUARD_INTERFACE -j DROP
# Accept DNS from Adguard
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.100 -p udp --dport 53 -j ACCEPT
# Accept Channels FEC
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.4 -p tcp --dport 80 -j ACCEPT
# Drop Forward traffic to AdGuard Dashboard
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.100 -j DROP
# Drop Forward traffic to Unbound (members should be restricted form accesing the means of modifying the network)
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.200 -j DROP
# Drop Forward traffic to Channels Database
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.5 -j DROP
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.4 -j DROP

# Drop everything else coming through the Wireguard interface
iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP

# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN
