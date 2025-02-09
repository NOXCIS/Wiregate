import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js";

export function generateTorIPTables(configParams) {
  const {
    ConfigurationName = "wg0",
    Address = "10.0.0.1/24", // Default subnet if not provided
    MasqueradeInterface = "eth0", // Allow override
    ProxyPort = 59040
  } = configParams;

  // Access the DNS server from the DashboardConfigurationStore
  const dashboardStore = DashboardConfigurationStore();
  const DNS_Server = dashboardStore?.Configuration?.Peers?.peer_global_dns || "8.8.8.8"; // Fallback to 8.8.8.8 if undefined
  const DNS_UDP_Port = 53;
  const ProxyIP = "$(hostname -i | awk '{print $1}')"; // Dynamically resolve the proxy IP

  return `WIREGUARD_INTERFACE=${ConfigurationName}
WIREGUARD_LAN=${Address}
MASQUERADE_INTERFACE=$(ip route | awk '/default/ {print $5}')
DNS_SERVER=${DNS_Server}
DNS_UDP_PORT=53
PROXY="$(hostname -i | awk '{print $1}')"
PROXY_PORT=59040

# Create a custom chain for WireGuard rules
iptables -N ${ConfigurationName}_RULES
iptables -t nat -N ${ConfigurationName}_RULES



# Allow local loopback traffic
iptables -A ${ConfigurationName}_RULES -i lo -j ACCEPT
iptables -A ${ConfigurationName}_RULES -o lo -j ACCEPT

# Allow new incoming traffic on WireGuard interface [NEEDED]
iptables -A ${ConfigurationName}_RULES -i $WIREGUARD_INTERFACE -s $WIREGUARD_LAN -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT

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
iptables -A ${ConfigurationName}_RULES -o $MASQUERADE_INTERFACE -p tcp --tcp-flags FIN,SYN,RST,ACK SYN -m state --state NEW -j ACCEPT


# Redirect specific network ranges to the proxy
iptables -t nat -A ${ConfigurationName}_RULES -d 10.192.0.0/10 -p tcp -m tcp -j DNAT --to-destination $PROXY:$PROXY_PORT

# Accept established outgoing traffic
iptables -A ${ConfigurationName}_RULES -m state --state ESTABLISHED -j ACCEPT

# Drop invalid packets
iptables -A ${ConfigurationName}_RULES -m conntrack --ctstate INVALID -j DROP
iptables -A ${ConfigurationName}_RULES -m state --state INVALID -j DROP

# Exclude private network ranges from NAT
for NET in 127.0.0.0/8 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 0.0.0.0/8 100.64.0.0/10 169.254.0.0/16 192.0.0.0/24 \
           192.0.2.0/24 192.88.99.0/24 198.18.0.0/15 198.51.100.0/24 203.0.113.0/24 224.0.0.0/4 240.0.0.0/4 \
           255.255.255.255/32; do
  iptables -t nat -A ${ConfigurationName}_RULES -d $NET -j RETURN
done

# Allow loopback traffic to bypass NAT
iptables -t nat -A ${ConfigurationName}_RULES -o lo -j RETURN

# Drop invalid TCP FIN/ACK and RST/ACK packets not from loopback
iptables -A ${ConfigurationName}_RULES ! -o lo ! -d 127.0.0.1 ! -s 127.0.0.1 -p tcp --tcp-flags ACK,FIN ACK,FIN -j DROP
iptables -A ${ConfigurationName}_RULES ! -o lo ! -d 127.0.0.1 ! -s 127.0.0.1 -p tcp --tcp-flags ACK,RST ACK,RST -j DROP


# Link the custom chain to INPUT and FORWARD chains
iptables -A INPUT -j ${ConfigurationName}_RULES
iptables -A OUTPUT -j ${ConfigurationName}_RULES
iptables -A FORWARD -j ${ConfigurationName}_RULES

`;
}

export function generatePlainIPTables(configParams) {
  const {
    ConfigurationName = "wg0",
    Address = "10.0.0.1/24", // Default subnet if not provided
    MasqueradeInterface = "eth0" // Allow override
  } = configParams;

  // Access the DNS server from the DashboardConfigurationStore
  const dashboardStore = DashboardConfigurationStore();
  const DNS_Server = dashboardStore?.Configuration?.Peers?.peer_global_dns || "8.8.8.8"; // Fallback to 8.8.8.8 if undefined
  const DNS_UDP_Port = 53;

  return `WIREGUARD_INTERFACE=${ConfigurationName}
WIREGUARD_LAN=${Address}
MASQUERADE_INTERFACE=$(ip route | awk '/default/ {print $5}')
DNS_SERVER=${DNS_Server}


# Enable NAT on the interface
iptables -t nat -I POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Add a WIREGUARD chain to the FORWARD chain
CHAIN_NAME="WIREGUARD_$WIREGUARD_INTERFACE"
iptables -N $CHAIN_NAME
iptables -A FORWARD -j $CHAIN_NAME


#START OF CORE RULES 
##############################################################################################################
# Accept related or established traffic
iptables -A $CHAIN_NAME -o $WIREGUARD_INTERFACE -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
# Allow traffic to the local loopback interface
iptables -A $CHAIN_NAME -o lo -j ACCEPT
# Drop traffic to wg-dashboard
iptables -A INPUT -i $WIREGUARD_INTERFACE -j DROP
#END OF CORE RULES
##############################################################################################################


#START OF GLOBAL DNS FORWARDING RULES 
##############################################################################################################
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p tcp --dport 53 -j ACCEPT
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p udp --dport 53 -j ACCEPT
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p tcp --dport 853 -j ACCEPT
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d $DNS_SERVER -p udp --dport 853 -j ACCEPT
#END OF GLOBAL DNS FORWARDING RULES 
##############################################################################################################


# START OF MEMEBRS RULES
##############################################################################################################
# Accept Foward traffic to WireChat @ port 80 @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.4 -p tcp -m multiport --dports 80,443 -j ACCEPT
# Drop Forward traffic to AdGuard Dashboard @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.100 -j DROP
# Drop Forward traffic to Unbound @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.200 -j DROP
# Drop Forward traffic to Channels Database @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.5 -j DROP
# Drop all other Foward traffic to WireChat @ container address on wiregate_private_network
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 10.2.0.4 -j DROP
#END OF MEMEBRS RULES
##############################################################################################################

#PORT FOWARDING RULES
##############################################################################################################
# Accept outgoing connections to on the following ports 20,21,22,80,443,3389 to any IP address (public because of rule above)
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -d 0.0.0.0/0 -p tcp -m multiport --dports 20,21,22,80,443,3389 -j ACCEPT
##############################################################################################################
# END OF PORT FOWARDING RULES


# Accept traffic from any Wireguard IP address connected to the Wireguard server
iptables -A $CHAIN_NAME -s $WIREGUARD_LAN -i $WIREGUARD_INTERFACE -j ACCEPT
# Drop everything else coming through the Wireguard interface
iptables -A $CHAIN_NAME -i $WIREGUARD_INTERFACE -j DROP
# Return to FORWARD chain
iptables -A $CHAIN_NAME -j RETURN`;
}

export function generateTorIPTablesTeardown(configParams) {
  const { ConfigurationName = "wg0" } = configParams;

  return `WIREGUARD_INTERFACE=${ConfigurationName}

# Flush the custom chain rules
iptables -F ${ConfigurationName}_RULES
iptables -t nat -F ${ConfigurationName}_RULES

# Delete the custom chain
iptables -X ${ConfigurationName}_RULES
iptables -t nat -X ${ConfigurationName}_RULES

`;
}

export function generatePlainIPTablesTeardown(configParams) {
  const {
    ConfigurationName = "wg0",
    Address = "10.0.0.1/24",
    MasqueradeInterface = "eth0" // Allow override
  } = configParams;
  return `WIREGUARD_INTERFACE=${ConfigurationName}
WIREGUARD_LAN=${Address}
MASQUERADE_INTERFACE=$(ip route | awk '/default/ {print $5}')

CHAIN_NAME="WIREGUARD_$WIREGUARD_INTERFACE"

iptables -t nat -D POSTROUTING -o $MASQUERADE_INTERFACE -j MASQUERADE -s $WIREGUARD_LAN

# Remove and delete the WIREGUARD_${ConfigurationName} chain
iptables -D FORWARD -j $CHAIN_NAME
iptables -F $CHAIN_NAME
iptables -X $CHAIN_NAME
`;
}

export function generateBlankIPTables(configParams) {
  const {
    ConfigurationName = "wg0",
    Address = "10.0.0.1/24",
    MasqueradeInterface = "eth0" // Allow override
  } = configParams;
  return `#Hello World`;
}