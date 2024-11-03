#!/bin/bash
# Copyright(C) 2024 NOXCIS [https://github.com/NOXCIS]
# Under MIT License
WIREGUARD_INTERFACE=MEMBERS
WIREGUARD_LAN=192.168.10.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=${WGD_IPTABLES_DNS}
DNS_UDP_PORT=53
PROXY="$(hostname -i | awk '{print $1}')"
PROXY_PORT=59040

# Create a custom chain for WireGuard rules
iptables -N MEMBERS_RULES
iptables -t nat -N MEMBERS_RULES



# Allow local loopback traffic
iptables -A MEMBERS_RULES -i lo -j ACCEPT
iptables -A MEMBERS_RULES -o lo -j ACCEPT

# Allow new incoming traffic on WireGuard interface [NEEDED]
iptables -A MEMBERS_RULES -i $WIREGUARD_INTERFACE -s $WIREGUARD_LAN -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

# Masquerade WireGuard LAN DNS Redirection 
iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -d 10.2.0.100 -p udp -m multiport --dports 53,853,443 -j MASQUERADE -s $WIREGUARD_LAN
iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -d 10.2.0.100 -p tcp -m multiport --dports 53,853,443 -j MASQUERADE -s $WIREGUARD_LAN
iptables -t nat -A PREROUTING -i $WIREGUARD_INTERFACE -p udp -m multiport --dports 53,853 -j DNAT --to-destination $DNS_SERVER:$DNS_UDP_PORT

# Masquerade WireGuard LAN Internal Services
iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -d 10.2.0.4 -p tcp -m multiport --dports 80,443 -j MASQUERADE -s $WIREGUARD_LAN
iptables -t nat -A PREROUTING -i $WIREGUARD_INTERFACE -d 10.2.0.4 -j RETURN




# Redirect remaining TCP traffic to the proxy
iptables -t nat -A PREROUTING -i $WIREGUARD_INTERFACE -p tcp -j DNAT --to-destination $PROXY:$PROXY_PORT
# Redirect remaining UDP traffic to the proxy
iptables -t nat -A PREROUTING -i $WIREGUARD_INTERFACE -p udp -j DNAT --to-destination $PROXY:$PROXY_PORT
# Allow new outgoing TCP connections
iptables -A MEMBERS_RULES -o $MASQUERADE_INTERFACE -p tcp --tcp-flags FIN,SYN,RST,ACK SYN -m state --state NEW -j ACCEPT


# Redirect specific network ranges to the proxy
iptables -t nat -A MEMBERS_RULES -d 10.192.0.0/10 -p tcp -m tcp -j DNAT --to-destination $PROXY:$PROXY_PORT

# Accept established outgoing traffic
iptables -A MEMBERS_RULES -m state --state ESTABLISHED -j ACCEPT

# Drop invalid packets
iptables -A MEMBERS_RULES -m conntrack --ctstate INVALID -j DROP
iptables -A MEMBERS_RULES -m state --state INVALID -j DROP

# Exclude private network ranges from NAT
for NET in 127.0.0.0/8 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 0.0.0.0/8 100.64.0.0/10 169.254.0.0/16 192.0.0.0/24 \
           192.0.2.0/24 192.88.99.0/24 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 224.0.0.0/4 240.0.0.0/4 \
           255.255.255.255/32; do
  iptables -t nat -A MEMBERS_RULES -d $NET -j RETURN
done

# Allow loopback traffic to bypass NAT
iptables -t nat -A MEMBERS_RULES -o lo -j RETURN

# Drop invalid TCP FIN/ACK and RST/ACK packets not from loopback
iptables -A MEMBERS_RULES ! -o lo ! -d 127.0.0.1 ! -s 127.0.0.1 -p tcp --tcp-flags ACK,FIN ACK,FIN -j DROP
iptables -A MEMBERS_RULES ! -o lo ! -d 127.0.0.1 ! -s 127.0.0.1 -p tcp --tcp-flags ACK,RST ACK,RST -j DROP


# Link the custom chain to INPUT and FORWARD chains
iptables -A INPUT -j MEMBERS_RULES
iptables -A OUTPUT -j MEMBERS_RULES
iptables -A FORWARD -j MEMBERS_RULES

