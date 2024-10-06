#!/bin/bash

WIREGUARD_INTERFACE=ADMINS
WIREGUARD_LAN=10.0.0.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=10.2.0.100
DNS_UDP_PORT=53
PROXY="$(hostname -i | awk '{print $1}')"
PROXY_PORT=59040

# Flush the custom chain rules
iptables -F ADMIN_RULES
iptables -t nat -F ADMIN_RULES

# Delete the custom chain
iptables -X ADMIN_RULES
iptables -t nat -X ADMIN_RULES


# Remove WireGuard LAN traffic masquerading
iptables -t nat -D POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Remove DNS redirection for UDP traffic
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -p udp --dport 53 -j DNAT --to-destination $DNS_SERVER:$DNS_UDP_PORT

# Remove exclusions for private address ranges from proxy
for NET in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16; do
  iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -d $NET -j RETURN
done

# Remove prevention of masqueraded interface traffic redirection
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -d $MASQUERADE_INTERFACE -j RETURN

# Remove redirections of remaining TCP and UDP traffic to the proxy
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -p tcp -j DNAT --to-destination $PROXY:$PROXY_PORT
iptables -t nat -D PREROUTING -i $WIREGUARD_INTERFACE -p udp -j DNAT --to-destination $PROXY:$PROXY_PORT


