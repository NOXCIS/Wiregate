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
iptables -A $CHAIN_NAME -s 10.0.0.1/24 -o $WIREGUARD_INTERFACE -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -o wg1 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Accept traffic from any Wireguard IP address connected to the Wireguard server
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -j ACCEPT

# Drop everything else coming through the Wireguard interface
#iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP

#iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -j ACCEPT

# DNS
# Accept DNS traffic from your Wireguard client
iptables -A $CHAIN_NAME -s 10.2.0.100 -i wg1 -d 10.0.1.1/24 -j ACCEPT
# Accept DNS traffic from your Wireguard server
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -d 10.2.0.100  -j ACCEPT

iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -d 10.2.0.3 -p udp --dport 771 -j ACCEPT
iptables -A $CHAIN_NAME -s 10.2.0.3 -i wg1 -d 10.0.1.1/24 -p udp --dport 771 -j ACCEPT


# Drop traffic to your any private IP address
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1 -d 10.2.0.3 -p tcp -m multiport --dports 22,8080 -j DROP
# Accept outgoing connections to HTTP(S) ports to any IP address (public because of rule above)
iptables -A $CHAIN_NAME -s 10.0.1.1/24 -i wg1  -p tcp -m multiport --dports 80,443 -j ACCEPT
iptables -A $CHAIN_NAME -i wg1 -d 10.0.1.1/24 -p tcp -m multiport --dports 80,443 -j ACCEPT
# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN