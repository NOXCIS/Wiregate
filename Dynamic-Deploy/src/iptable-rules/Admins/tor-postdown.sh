#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License

WIREGUARD_INTERFACE=ADMINS
WIREGUARD_LAN=10.0.0.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}
DNS_UDP_PORT=53
PROXY="$(hostname -i | awk '{print $1}')"
PROXY_PORT=59040

# Flush the custom chain rules
iptables -F ADMIN_RULES
iptables -t nat -F ADMIN_RULES

# Delete the custom chain
iptables -X ADMIN_RULES
iptables -t nat -X ADMIN_RULES


