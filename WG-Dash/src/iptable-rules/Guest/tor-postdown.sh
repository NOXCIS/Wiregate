#!/bin/bash
WIREGUARD_INTERFACE=GUESTS
WIREGUARD_LAN=192.168.20.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=10.2.0.100
DNS_UDP_PORT=53
PROXY="$(hostname -i | awk '{print $1}')"
PROXY_PORT=59040


# Flush the custom chain rules
iptables -F GUEST_RULES
iptables -t nat -F GUEST_RULES

# Delete the custom chain
iptables -X GUEST_RULES
iptables -t nat -X GUEST_RULES

iptables -t nat -D POSTROUTING -o $MASQUERADE_INTERFACE -d 10.2.0.100 -p udp -m multiport --dports 53,853 -j MASQUERADE -s $WIREGUARD_LAN
iptables -t nat -D POSTROUTING -o $MASQUERADE_INTERFACE -d 10.2.0.100 -p tcp -m multiport --dports 53,853 -j MASQUERADE -s $WIREGUARD_LAN
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -p udp -m multiport --dports 53,853 -j DNAT --to-destination $DNS_SERVER:$DNS_UDP_PORT
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -d $MASQUERADE_INTERFACE -j RETURN

# Remove redirections of remaining TCP and UDP traffic to the proxy
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -p tcp -j DNAT --to-destination $PROXY:$PROXY_PORT
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -p udp -j DNAT --to-destination $PROXY:$PROXY_PORT


