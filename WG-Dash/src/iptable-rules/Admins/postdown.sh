#!/bin/bash
WIREGUARD_INTERFACE=ADMINS
WIREGUARD_LAN=10.0.0.1/24
MASQUERADE_INTERFACE=eth0
DNS_SERVER=10.2.0.100
DNS_UDP_PORT=53
PROXY=10.2.0.3
PROXY_PORT=59040

# Remove established incoming connection acceptance
iptables -D INPUT -m state --state ESTABLISHED -j ACCEPT

# Remove local loopback traffic acceptance
iptables -D INPUT -i lo -j ACCEPT
iptables -D OUTPUT -o lo -j ACCEPT

# Remove new incoming traffic acceptance on WireGuard interface
iptables -D INPUT -i $WIREGUARD_INTERFACE -s $WIREGUARD_LAN -m conntrack --ctstate NEW,RELATED,ESTABLISHED -j ACCEPT

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

# Remove new outgoing TCP connections acceptance
iptables -D OUTPUT -o $MASQUERADE_INTERFACE -p tcp --tcp-flags FIN,SYN,RST,ACK SYN -m state --state NEW -j ACCEPT

# Remove redirections of specific network ranges to the proxy
iptables -t nat -D OUTPUT -d 10.192.0.0/10 -p tcp -m tcp -j DNAT --to-destination $PROXY:$PROXY_PORT

# Remove established outgoing traffic acceptance
iptables -D OUTPUT -m state --state ESTABLISHED -j ACCEPT

# Remove invalid packet drops
iptables -D OUTPUT -m conntrack --ctstate INVALID -j DROP
iptables -D OUTPUT -m state --state INVALID -j DROP

# Remove exclusions for private network ranges from NAT
for NET in 127.0.0.0/8 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 0.0.0.0/8 100.64.0.0/10 169.254.0.0/16 192.0.0.0/24 \
           192.0.2.0/24 192.88.99.0/24 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 224.0.0.0/4 240.0.0.0/4 \
           255.255.255.255/32; do
  iptables -t nat -D OUTPUT -d $NET -j RETURN
done

# Remove loopback traffic NAT bypass
iptables -t nat -D OUTPUT -o lo -j RETURN

# Remove invalid TCP FIN/ACK and RST/ACK packet drops not from loopback
iptables -D OUTPUT ! -o lo ! -d 127.0.0.1 ! -s 127.0.0.1 -p tcp --tcp-flags ACK,FIN ACK,FIN -j DROP
iptables -D OUTPUT ! -o lo ! -d 127.0.0.1 ! -s 127.0.0.1 -p tcp --tcp-flags ACK,RST ACK,RST -j DROP
