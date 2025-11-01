#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
WIREGUARD_INTERFACE=GUESTS
WIREGUARD_LAN=192.168.20.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}
DNS_UDP_PORT=53
PROXY="$(ip -4 addr show scope global | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)"
PROXY_PORT=59040


# Flush the custom chain rules
iptables -F GUEST_RULES
iptables -t nat -F GUEST_RULES

# Delete the custom chain
iptables -X GUEST_RULES
iptables -t nat -X GUEST_RULES


