> [!NOTE]
> **Obfs4 Plugin**: Has alot of latency and connection drops, use webtunnel or snowflake plugins if possible.
>
> **AmneziaWG** support is fully functional but is still in devlopement under the **amneziawg** branch for those that want to use AmneziaWG with WGDashboard.
<hr>

# WireGate ![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/WireGate?style=social) ![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard/terra-firma.svg?style=flat&label=image&logo=docker) ![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/WireGate&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false) ![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.githubusercontent.com/NOXCIS/a08fe945ac095cea4f3cc21178ee43fb/raw/clone.json&logo=github)

> **Wiregate** Supported architectures: `x86-64` , `arm64`, `armv7`
>  **Test OS**: Ubuntu LTS | Debian 12 
>  **Test Device:** Raspberry Pi 5 | Apple M2 | x86 CPUs
>  **Build:** Daily




  # Analysis of Traffic Correlation and Deobfuscation

## Introduction

This document evaluates the difficulty of traffic correlation and deobfuscation for a privacy-focused network configuration. The setup combines multiple privacy-enhancing technologies to ensure anonymity and protect against potential adversaries attempting to analyze network traffic.

## 1\. Traffic Correlation Analysis

Traffic correlation involves analyzing packet timings, sizes, and patterns to identify relationships between incoming and outgoing traffic at different points on the network. Adversaries, such as ISPs, government agencies, or other actors with access to multiple parts of the network, may attempt to correlate traffic between your device and the Tor exit nodes.

## 1.1 WireGuard with Obfuscation

**Goal**: WireGuard normally uses fixed headers, which could be recognizable by Deep Packet Inspection (DPI) systems. However, by using obfuscation techniques (like randomized junk headers), you ensure the WireGuard traffic appears as generic encrypted UDP traffic.  

**Effectiveness**: The randomized headers make it nearly impossible for DPI systems to distinguish WireGuard traffic from other encrypted UDP protocols like DTLS (used by WebRTC) or QUIC (used by HTTP/3). This technique would require the adversary to perform more complex statistical analysis, rather than relying on signature-based detection.  

**Mathematical Complexity**: Let N be the number of possible random header combinations. The obfuscation adds entropy to the headers, making the detection problem require searching a space of size O(N). The higher N, the more difficult it is to accurately detect WireGuard.

## 1.2 Tor TransPort

**Goal**: Tor provides anonymity by routing traffic through multiple hops with different Tor nodes. Tor's TransPort feature hides the traffic as if it’s normal Tor traffic without needing SOCKS proxies.  

**Effectiveness**: Since Tor circuits are updated every 2-8 minutes and each circuit uses different Tor relays, the probability of successful correlation diminishes significantly. The use of Tor Vanguard further complicates analysis by frequently changing guards and using isolation techniques.  

**Mathematical Complexity**: For traffic correlation, the adversary would need to match patterns between obfuscated WireGuard traffic and the Tor exit nodes. Let T denote the Tor network's size. The correlation problem involves searching a space of size O(T^n), where n is the number of Tor hops (typically 3). Given the randomized circuit rotation, it becomes a stochastic process, making the correlation require significant computational resources.

# 2\. DNS Deobfuscation and Tracking

DNS requests can be a weak link in privacy if not properly obfuscated. However, WireGates, DNS chain is quite robust via Multi-layer DNS Handling.


**DNS Path**: WireGuard > Pi-hole/AdGuard > Unbound > DNSCrypt > Tor SOCKS > Tor network > ODoH (Oblivious DoH).  

**Effectiveness**: Each layer (especially DNSCrypt, Tor, and ODoH) adds encryption and anonymization. ODoH ensures that DNS queries cannot be linked back to your IP address, as Cloudflare only sees requests from the Oblivious proxy. Also the notion that DNS traffic is proxied through tor before it even reaches the ODOH relay for the upstream ODOH DNS resolver.

**Mathematical Complexity**: An adversary would need to track the DNS queries through multiple encrypted layers, with each layer adding its own level of obfuscation. The complexity grows as O(E^n), where E is the entropy from encryption/anonymization at each layer, and n is the number of layers.

# 3\. Multi-Container Docker Network Isolation

**Goal**: By keeping each container isolated and exposing minimal ports, you reduce the attack surface. Even if an adversary compromises one container, they would have a hard time moving laterally to others.  

**Mathematical Complexity**: Assuming an attacker can only observe encrypted traffic and cannot perform man-in-the-middle attacks, the probability of correlating traffic across containers is low. The complexity would be proportional to O(P^C), where P is the number of ports/protocols an attacker can observe, and C is the number of containers.

# Conclusion

The overall difficulty of traffic correlation and deobfuscation can be approximated as the combined complexity of breaking through each layer:  

Difficulty ≈ O(N) × O(T^n) × O(E^n) × O(P^C)  
<br/>Given the setup:  
- N is large due to WireGuard obfuscation.  
- T is large (thousands of Tor nodes) with n = 3 hops.  
- E is high due to multiple layers of DNS encryption and anonymization.  
- C is relatively small, but the adversary sees minimal exposed ports.  
<br/>
In practical terms, the adversary would need access to multiple points in your network and the ability to perform extensive statistical analysis over time. Given the entropy added at each stage and frequent circuit updates, the mathematical effort required scales exponentially, making traffic correlation and deobfuscation extremely difficult for most adversaries, especially those without global surveillance capabilities.
  



## Table of Contents
- [About](#About)
- [Infrastructure Map](#Infrastructure)
- [Installation](#installation)
- [Usage](#usage)
- [Tor](#Tor)
- [Help](#help)
- [Acknowledgements](#Acknowledgements)
- [Contributing](#contributing)
- [License](#license)




## About

**WireGate** is a fully automated **Docker Based VPN Sever Deployment Tool** with and attachable intranet via docker private networks and support for **Tor** as an exit proxy.

It allows users to host web other applications on their existing server and be able to securely connect to said web applications without exposing them to the open internet. This is done by utilizing the **WireGuard protocol** in conjunction with **Docker Networks and Containers**. Hence applications hosted behind the WireGate private network *`need not expose any ports`* and can only be accessed via a *WireGuard* connection already registered to to an existing server interface on the deployed WireGate instance. Secure by Design, the WireGuard Dashboard & other services are only accessible on first deployment via the **master configuration** that is generated at install and `encrypted after being outputted to the console.` Wiregate also acts as a ISP DNS query logging bypass. Wiregate by default is configured to have minimal or no logging.





### Wiregate vs Wirehole vs WG-Easy vs WG Dashboard (standalone)
Wiregate uses a modified version of WG Dashboard that allows the enviorment to be set from the docker compose or docker run command. Below are comparissions to the other GUI dashboard options for Wireguard.

|Project| Easy Setup | Client Firewall Rules | GUI | DNS Filtering | Tor Proxy | 2FA | 3FA
|--|--|--|--|--|--|--|--|
| **WireGate** 	| ✅|✅ |✅ |✅ |✅ |✅ |✅ |
| **WireHole** 	| ✅|❌ |❌ |❌ |❌ |❌ |❌ |
| **WG-Easy**  	| ✅|❌ |✅ |❌ |❌ |❌ |❌ |
| **WireAdmin** | ✅|✅ |✅ |❌|✅ |❌ |❌ |

### Zone Permissions

Wiregate is configured with 4 zones that peers can be added to. The zone a peer belongs to dictates the network access permissions of said peer.  


| Zone | Internet Access | WireGuard Dashboard Access | Docker Network Access | Peer to Peer Access |
|--|--|--|--|--|
| **Admin** |✅| ✅ | ✅ | ✅ |
| **Members**|✅|❌|✅|✅|
| **LAN Users**|❌|❌|❌|✅|
| **Guest**|✅|❌|❌|❌|



## Infrastructure
 Symbolic Network Map


![Symbolic Network Map](https://mermaid.ink/svg/pako:eNqtWAtv4kYQ_isjn9K0KiHGQADfNSpgSCJdL_RI7qSGqlrsBSzMruVHHk3y3zuztjEPE7iodhTs3f3mPbOzftZs6XDN1I6OnkfCFW5kAj4cRzO-4McmHI9ZyI9L2cg3Frhs7PHwOFnmB-6CBU9d6cmAVn-oMb2ltxQgnbvhj1E-P5lMVic7MnB4kE_ruq6mPVfwfLTf7BhGQjTkthTOOkuD7kRGHkTu2iTxG4mReE3-jo7oZSQmnnywZyyI4PPXkYD0asPJyTm89IQdPPkRd-C7G_CLmAUO3ARsMnFtuLUGL9AByEGdA0Fd4puBsucwHk8D5s_AdbgOd5cyjOAPZs9Qfbgq9-DbYAgygEu54DDkwT0P_t4GVuDOkvacB_CFRw8ymMPvUNHLRlkv66dGrQBhwJ2SkkUculJEDPkRZSXWqpxdUNqBlQ_1cKhMGnvSZh54UvpjZs_B58HCJf37KPD3C7BYOBtL5kDbtnkYKgNkNKyUbA-2x_rbQxf5EKzaMHvqJ-te2p4HX6QA68vw9LOSLvXAC1jVdQ1-YPnljy1Phb4kM3LhFEu5RQPyC8kZxcIejrKMBLW--kbCRqAsnR8mNHrVbRrIdUmBCfSnM6XoPh240uPKzR1J0d52Fq5YertvbFtwlVLRtY7qG6n3V8YusrFqGqwFUaGMvmb5VBN4GUaMikeemVcTNEoA1_3-tiy9Vb7VlAKp8GfMA5eHsOdap2BlFAaBfHR5LsLNLJDxdKbkyNzyJqXUmivaXEaRDz-pn3C3autUsqdVK2LVnQ-jJ_SqDmEUyDk3P_T7WJP1UvJ68uA60cys6P5jEaryLpSxgrIah6KqS1S7RfcGqk6oIlztTW7VYmb194DO3gOq6PtR29vIBo3cNgZvju0NGmc7OOeWqdTqVvstVCE-N5LeNaxacx3f3MG18i6UcTiqCN94V8g134VqHYAqTIs8EpqYS029KMILTLNHyl2w1pve3wUzKgdwK-T3dnYYuypM4wdgm1sE3e27kfbJce-RDNL7DTvGx-iEee5UmB6fRMfnXc_lIhqJT6e46nykpV1RZx8u7dSSDTdp1bANuxpsUOo-76RjI18eHJ9vd2bAo5meN3W492Ebgv04PODSKS79B9vpe_oVyQZSHokbnF5ScpJeDLcKN4QZNpm4_8x4wJGmL7EJburlXM5XktO6W5FypG2o-xGweZ-6wgR08MeRdk5mvhrctDufe0P4eov_M3qp_Szj-U0DfjxGGrvUGYmVdjYXVLX0I3G5zzWKLLUsJy5ZeMJsbsI05iG6eRiPkYmJ8W-UK2fNsqGXK4pJ0sdAJGGQCIP6YYsT0OBXJqa4_3c8aqawzzghz6j7tKneGkRMvVcMNZBSVyNnGyHRX5d_29jKvoVKLPhijL3bKotKpsAJXNFC1C7tyUxsDWJOExtN4Pr0r3ArxjIWznK8z7xQTbSd5FyzNdGdMSG4F2I3GDE6MW4uOclj0VrG4saaNaNc7HPqDot4TIRrLsiM0WUCpPCeAM-PgtsRedbn1PimuRQyPGMtKRXab6nMDgO-W1ljv7aZU_KikOaEoeuYXtiWfuWh9LDskAC3IWY4C4HRmQGCdEa173jqdTjiy5tCVPcLYYmwS6fcbSlqRiKEShb7Ce5dBtfW9WUqTAg_09svcD327l0Zh0qua5Ip6VrRG6mU9Nj1ZOxMPIYVimBw62OZ52yhUKEqruGSBQI99hRu6mMdoA81yNgvi1BVwSAWwhVTDAIoqMF58d1dplJdx7HrRUSG6OPkBF9JYlJSxlFat1UqUQhClLbsUX4UQG1QiGimQlP6kStFcpBLZR14MdZf6LiC0VmkBEMhH_oem_MSyPEkrOF54Dsf38SUl1u7GRadA0IuS3dUYuDO6LC3bY5KFn19pSOaQFkgi1YMwQLfbcjTuztwa9hMdkYnTkr3tPwmuU5uuKZMT9N7gjbEbY9wBAOKKvqGRe5gSZUnky4LgfquQZtkAuUFwfB_VtdsfLO4ZuO7a2vG8I1qkyxZt_b-nThTbWur7VUPcFXvkS18bzV1LBbMyYFEIqsXWaT4hk-BGpLRIpUiIZ7dAVMGJ6leLVARRtsthjv36SNkgJlgzxg2fnKxlfZKsOSrGNLwzA8t3nJazsqEkU406o1aA-XQShrSXDDX0UztmToZ3IKJz0gz8RFP2HNlAFzH4kgOn4StmREatqSpdNXMCdX0khb7DnrBctk0YItsic_EXyjnyqtmPmuPmlnHiDWqxpler9WMSuusUdKeNLPSbJbPas1aq1mt1lstvVV_LWn_KgJ6uXlmtFqNRkVv6LWmXq2__gcR_twC)


## Installation

To get started, run the installation script using the following command:

### Via Quick Installer
Running the command below installs prerequsites and runs the terminal based menu.
```bash
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \
sudo chmod +x stackscript.sh && \
sudo ./stackscript.sh
```
The command can also accept passed arguments to skip the menu. **BRANCH** -Selects the target branch of the repo pull from, otherwise set as **main** if ommited. **ARG4** is Optional, see below.

```bash
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \
sudo chmod +x stackscript.sh && \
sudo ./stackscript.sh [-b branch]  [-r arg1]  [-t arg2]  [-n arg3] 
```
Example Usage:
```bash
./stackscript.sh -b main -r E-P-D -t Tor-br-snow -n {CH},{GB} 
```

 The available options are:

- `-b` for specifying a branch.
- `-r` for specifying Resolvers
- `-t` for specifying Tor.
- `-n` for specifying Exit Node.




### Via Docker In Docker 

**Interactive Menu**
```bash
docker run --privileged --name wiregate-dind -d -p 4430-4433:4430-4433/udp docker:dind && \
docker exec -it wiregate-dind /bin/sh -c "

apk add curl git ncurses sudo bash && \
mkdir -p /opt && cd /opt && \
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \
chmod +x stackscript.sh && \
./stackscript.sh -d dind
"
```
**Preset & Automated**
```bash
docker run --privileged --name wiregate-dind -d -p 4430-4433:4430-4433/udp docker:dind && \
docker exec -it wiregate-dind /bin/sh -c "

apk add curl git ncurses sudo bash && \
mkdir -p /opt && cd /opt && \
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \
chmod +x stackscript.sh && \
./stackscript.sh [-b branch]  [-r arg1]  [-t arg2]  [-n arg3]  -d dind
" 
```
Example Usage:
```bash
./stackscript.sh -b main -r E-P-D -t Tor-br-snow -n {CH},{GB} -d dind
```
 The available options are:

- `-b` for specifying a branch.
- `-r` for specifying Resolvers
- `-t` for specifying Tor.
- `-n` for specifying Exit Node.
- `-d` for specifying Docker in Docker.




### ARG1:  Resolver Install Options
|  |  |
|--|--|
| **E-A-D**: | `Express, AdGuard, Darkwire`
| **E-A-C**: |`Express, AdGuard, Channels`
| **E-P-D**: |`Express, Pihole, Darkwire`
| **E-P-C**: |`Express, Pihole, Channels`
| **A-A-D**: |`Advanced, AdGuard, Darkwire`
| **A-A-C**: |`Advanced, AdGuard, Channels`
| **A-P-D**: |`Advanced, Pihole, Darkwire`
| **A-P-C**: |`Advanced, Pihole, Channels`
| **dev**  :| 	 `Development Build`
| **help**:| `Display help menu`
| **reset**:| `Reset WireGate`





### ARG2: TOR Options
|  |  |
|--|--|
| **off**: |`Disable TOR`
| **Tor-br-snow**:| 		`Use Tor with bridges (snowflake)`
| **Tor-br-webtun**:| 	`Use Tor with bridges (webtunnel)`
| **Tor-br-obfs4**:|    	`Use Tor with bridges (obfs4)`
| **Tor-snow**:| 			`Use Tor without bridges (snowflake)`
| **Tor-webtun**:| 		`Use Tor without bridges (webtunnel)`
| **Tor-obfs4**: |			`Use Tor without bridges (obfs4)`

### ARG3:  TOR Exit Node Country Code String
|  |  |
|--|--|
| **Format Example**: | `{US},{GB},{AU} `
|**Default**| `default` |
For more exit node options go to [Tor Country codes list](https://sccmrookie.blogspot.com/2016/03/tor-country-codes-list.html).


### ARG4: OPTIONAL  Docker in Docker Deployment
|  |  |
|--|--|
| **dind**: | `Docker in Docker Enviorment Setup`


### Install via Docker Compose
````yaml

networks:
  private_network:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.enable_icc: "true"
    attachable: true
    internal: false
    ipam:
      config:
        - subnet: 10.2.0.0/24



services:
  dnscrypt:
    image: "klutchell/dnscrypt-proxy"
    restart: unless-stopped
    container_name: dnscrypt
    volumes:
      - ./Global-Configs/DnsCrypt/dnscrypt-proxy.toml:/config/dnscrypt-proxy.toml
    networks:
      private_network:
        ipv4_address: 10.2.0.42

  unbound:
    image: "klutchell/unbound:latest"
    container_name: unbound
    restart: unless-stopped
    hostname: "unbound"
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    volumes:
      - ./Global-Configs/Unbound/custom-unbound.conf:/etc/unbound/custom.conf.d/custom-unbound.conf
    networks:
      private_network:
        ipv4_address: 10.2.0.200


  adguard:
    depends_on: [unbound]
    container_name: adguard
    image: adguard/adguardhome
    restart: unless-stopped
    hostname: adguard
    # Volumes store your data between container upgrades
    volumes:
      - "./Global-Configs/AdGuard/Data:/opt/adguardhome/work"
      - "./Global-Configs/AdGuard/Config:/opt/adguardhome/conf"
    networks:
      private_network:
        ipv4_address: 10.2.0.100

  wiregate:
    image: noxcis/wg-dashboard:terra-firma
    container_name: wiregate
    hostname: wiregate
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    restart: unless-stopped
    volumes:
      - wgd_configs:/etc/wireguard 
      - wgd_db:/opt/wireguarddashboard/src/db 
      - wgd_db:/opt/wireguarddashboard/src/dashboard_config

    environment:
      - TZ=UTC
      - WGD_TOR_PROXY=true
      - WGD_TOR_PLUGIN=webtunnel #OPTIONS webtunnel, obfs4, snowflake
      - WGD_TOR_BRIDGES=true
      - WGD_WELCOME_SESSION=false
      - WGD_USER=james
      - WGD_PASS=admin
      - WGD_REMOTE_ENDPOINT=192.168.1.199
      - WGD_REMOTE_ENDPOINT_PORT=80
      - WGD_DNS="10.2.0.100, 10.2.0.100"
      - WGD_IPTABLES_DNS=10.2.0.100
      - WGD_PEER_ENDPOINT_ALLOWED_IP=0.0.0.0/0
      - WGD_KEEP_ALIVE=21
      - WGD_MTU=1420
      - WGD_PORT_RANGE_STARTPORT=443
    ports:
      - "443-448:443-448/udp"
      - 8000:80/tcp #Comment Out and Compose Up for 3FA via WireGuard
    sysctls:
      - net.ipv4.ip_forward=1
      - net.ipv4.conf.all.src_valid_mark=1
    networks:
      private_network:
        ipv4_address: 10.2.0.3
  
  darkwire:
      image: noxcis/darkwire:terra-firma
      cap_add:
        - NET_ADMIN
      sysctls:
        - net.ipv4.ip_forward=1
        - net.ipv4.conf.all.src_valid_mark=1
      networks:
        private_network:
          ipv4_address: 10.2.0.4

volumes:
    wgd_configs:
    wgd_db:
  ````

## Usage

### Utilities

To reset the deployment, use:

```bash
sudo ./install.sh reset 
```
To run a development build, use:

```bash
sudo ./install.sh dev 
```
### Access 

While connected to WireGate Admins Zone:
- navigate to http://wire.gate/ to use the **WireGuard** dashboard.
- navigate to http://ad.guard/ to use the **AdGuard** Dashboard
- navigate to http://pi.hole/ to use the **PiHole** Dashboard
- navigate to https://dark.wire/ to use the **DarkWire** (if configured)

*The **password** & **username** are randomly generated and **provided in the final output** if not set manually.*
*Clients under the **members** zone **cannot** access the **WireGuard, Pihole, or Adguard** dashboards.*


## Tor

WireGate includes the complied binaries for the following Tor Transort Plugins:
  
- **Lyrebird** (meek_lite,obfs2,obfs3,obfs4,scramblesuit)
- **SnowFlake**
- **WebTunnel**
- 
Plugin choice can be seleted during installation or updated with docker compose. Also at a random intervals between **100** & **1642** seconds, **WireGate will Obtain a new Tor Circuit** if Tor is Enabled.

## Help
All Wiregate supporting configurations can be found in the Global Configs Folder.
If you need assistance, simply run:

```bash
sudo ./install.sh help
```
This will display the usage instructions and available options.




  
## Acknowledgements

The code in this repo is influenced by [IAmStoxe's WireHole](https://github.com/IAmStoxe/Wirehole) project  & the  [WireAdmin](https://github.com/wireadmin/wireadmin) project.
  However, the upstream projects and their authors most certainly also deserve credit for making this all possible.
- [AdGuard](https://github.com/AdguardTeam/AdGuardHome) -AdGuard
- [Pihole](https://github.com/pi-hole). - Pihole
- [NLnetLabs](https://github.com/NLnetLabs). -Unbound
- [Kyle Harding](https://github.com/klutchell). -Distroless Unbound Docker Image
- [Donald Zou](https://github.com/donaldzou). -WG Dashboard (WireGuard UI)

 **Show your support**
Give a ⭐ if this project helped you!



## Contributing

Contributions are welcome! Feel free to fork the repository, make changes, and submit a pull request. For  internet privacy and Freedom.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/NOXCIS/Wiregate/blob/main/LICENSE) file for details.
