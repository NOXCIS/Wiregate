#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
WIREGUARD_INTERFACE=MEMBERS
WIREGUARD_LAN=192.168.10.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}
DNS_UDP_PORT=53
PROXY="$(ip -4 addr show scope global | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)"
PROXY_PORT=59040


# Flush the custom chain rules
iptables -F MEMBERS_RULES
iptables -t nat -F MEMBERS_RULES

# Delete the custom chain
iptables -X MEMBERS_RULES
iptables -t nat -X MEMBERS_RULES

