#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
WIREGUARD_INTERFACE=GUESTS
WIREGUARD_LAN=192.168.20.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}
DNS_UDP_PORT=53
PROXY="$(hostname -i | awk '{print $1}')"
PROXY_PORT=59040


# Flush the custom chain rules
iptables -F GUEST_RULES
iptables -t nat -F GUEST_RULES

# Delete the custom chain
iptables -X GUEST_RULES
iptables -t nat -X GUEST_RULES


