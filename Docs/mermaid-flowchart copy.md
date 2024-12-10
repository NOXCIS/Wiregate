%%{
init: {
'theme': 'base',
'themeVariables': {
'primaryColor': '#4a0909',
'primaryTextColor': '#fff',
'primaryBorderColor': '#000',
'lineColor': '#F8B229',
'secondaryColor': '#424242',
'tertiaryColor': '#fff'

}
}
}%%


flowchart LR
        A --> |Encrypted WireGuard Traffic UDP| B  
        B --> |Encrypted WireGuard Traffic UDP| C

        

    subgraph ide0 [Host Machine I.E VPS or Home Server]
    subgraph ide1 [Docker Network @ 10.2.0.0/24]
    subgraph ide2 [WireGate Container]


 

        C  -->  D
        E  -.-> |local loopback permited For WG Dashboad Access| C
        D  -->  E 
        D  -->  F
        D  -->  G
         
        
        F  --> |All Non DNS/Local Traffic| D3
        E  --> |All Non DNS/Local Traffic| D3
        H  --> |All Non DNS/Local Traffic| D3
        D  --> H

end
        F  --> |All DNS/Local Traffic           | D2
        E  --> |All DNS/Local Traffic           | D2
        D2 --> |Local Traffic To Docker Network Containers    | E3
        D2 --> |DNS Traffic and Adguard/Piole DashBoard Admin Access| F2
        H  --> |DNS Traffic                     | F2
        F2 -->  G2
        G2 -->  G3


        
        
end
end
        D2 -->  |Standard Traffic If Tor OFF                | E2
        G3 -->  |DNS Queries                                | E2
        D3 -->  |Proxied Traffic Through Tor                | E2
        H  -->  |Standard Http & Https Traffic If Tor OFF       | E2
        
      

        linkStyle 0 stroke:#FF0000,stroke-width:10px
        linkStyle 1 stroke:#FF0000,stroke-width:10px
        linkStyle 2 stroke:#FFD700,stroke-width:10px
        linkStyle 3 stroke:#A9A9A9,stroke-width:15px

        linkStyle 4 stroke:#FFD700,stroke-width:3px
        linkStyle 5 stroke:#FFD700,stroke-width:3px
        linkStyle 6 stroke:#FFD700,stroke-width:3px
        linkStyle 10 stroke:#FFD700,stroke-width:3px

        

        linkStyle 13 stroke:#2e8bc0,stroke-width:6px
        linkStyle 14 stroke:#145DA0,stroke-width:6px
        
        linkStyle 15 stroke:#0C2D48,stroke-width:8px
        linkStyle 11 stroke:#0C2D48,stroke-width:8px
        linkStyle 12 stroke:#0C2D48,stroke-width:8px
        
        linkStyle 7 stroke:#FFD700,stroke-width:10px
        linkStyle 8 stroke:#FFD700,stroke-width:10px
        linkStyle 9 stroke:#FFD700,stroke-width:10px

        linkStyle 20 stroke:#800080,stroke-width:15px
        linkStyle 18 stroke:#FFD700,stroke-width:15px
        linkStyle 19 stroke:#145DA0,stroke-width:15px
        linkStyle 21 stroke:#FFD700,stroke-width:15px

        linkStyle 16 stroke:#FFD700,stroke-width:20px
        linkStyle 17 stroke:#FFD700,stroke-width:20px
        


        


A["<div style='text-align:left'>Client
</div>"]


B["<div style='text-align:left'>VPS or Local Server @ IP
</div>"]

C{"<div style='text-align:center'>WireGate Container eth0 @ 10.2.0.3
on the wiregate_private_network.
The WireGate dashboard is hosted here @ port 80.
</div>"}

D[<div style="text-align:left; margin: 5px;">
  IPTABLES RULES
</div>]


D2{"<div style='text-align:left;'>
wiregate_private_network
10.2.0.0/24
</div>"
}

H["<div style='text-align:left'>wireguard-interface: guest
Subnet: 192.168.20.1/24
Access to Private IP Adress Ranges Blocked
- 10.0.0.0/8
- 172.16.0.0/12
- 192.168.0.0/16
</div>"]

F["<div style="text-align:left;">
wireguard-interface: members
- 192.168.10.1/24
- Internet Access: True
- Docker Network Access: True
+ Unbound Access: False
+ AdGuard Access: False
+ Channels Database Access: False
- WireGate Dashboard Access: False
</div>"]

G["<div style='text-align:left'>
wireguard-interface: lans
- 172.16.0.1/24
- Can only connect to peers on the same interface
- Internet Access: False
- Docker Network Access: False
- WireGate Dashboard Access: False
</div>"]

G2["<div style='text-align:left'>
Unbound Container 10.2.0.200
DNS Resolver
- Used as a DNS resolver and hardener.
</div>"]

G3["<div style='text-align:left'>
DnsCrypt Container 10.2.0.42
DNS Privacy via ODOH
- Uses (ODOH) Oblvious DNS Over Https to resolve to Cloudflare ODOH Upstream DNS servers via ODOH relays.
</div>"]

D3["<div style='text-align:left'>
Tor Transport running in WireGate Container 10.2.0.3
wiregate_private_network
- Uses built in Tor netfilters to route wireguard peer traffic through Tor.
 With the optional Transport Plugin Binaries, SnowFlake, obfs4 & WebTunnel
</div>"]



F2["<div style='text-align:left'>
AdGuard or Pihole  Container 10.2.0.100
DNS Filter
-Uses Unbound as Upstream DNS server
</div>"]

E["<div style='text-align:left;'>
wireguard-interface: admins
-10.0.0.1/24

- Only peers of this inteface are able to access ports on the localhost of the WireGate Container
- Internet Access: True
- Docker Network Access: True
+ Unbound Access: True
+ AdGuard Access: True
+ Channels Database Access: True
- WireGate Dashboard Access: True
</div>"]

E2{"<div style='text-align:left;'>Internet
</div>"
}

E3["<div style='text-align:left;'>
Example Container Darkwire

10.2.0.4
-Uses p2p Websockets to send files and messages in ephemeral chatrooms.
</div>"]

style ide1 fill:#9e9d9d
style ide2 fill:#757474
