#!/bin/bash


WIREGUARD_INTERFACE=wg0
WIREGUARD_LAN=10.0.0.1/24
MASQUERADE_INTERFACE=eth0

iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Add a WIREGUARD_wg0 chain to the FORWARD chain
CHAIN_NAME="WIREGUARD_$WIREGUARD_INTERFACE"
iptables -N $CHAIN_NAME
iptables -A FORWARD -j $CHAIN_NAME

# Accept related or established traffic
iptables -A $CHAIN_NAME -o $WIREGUARD_INTERFACE -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Accept traffic from any Wireguard IP address connected to the Wireguard server
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -j ACCEPT

# Drop everything else coming through the Wireguard interface
#iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP

# DNS
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -d 10.2.0.3 -p udp --dport 53 -j ACCEPT
# Drop traffic to your any private IP address
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -d 10.0.0.0/8,172.16.0.0/12,192.168.0.0/16 -j DROP
# Accept outgoing connections to HTTP(S) ports to any IP address (public because of rule above)
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -d 0.0.0.0/0 -p tcp -m multiport --dports 80,443 -j ACCEPT

# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN