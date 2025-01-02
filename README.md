
> [!NOTE]
>  Everypone use the
>
> **EDGE**: [noxcis/wiregate:jiaotu-beta-v0.3](https://hub.docker.com/layers/noxcis/wiregate/jiaotu-beta-v0.3/images/sha256-93941fc4f2e317b477ed731b15186224017bbd85eec727feb76dc9e3c37e1da9) docker image.
> 
> **STABLE**: [noxcis/wiregate:vidar](https://hub.docker.com/layers/noxcis/wiregate/vidar/images/sha256-427d75bfa850dfd7ebd185b6f1de7f8ffe667ef6a8fe247db8fe59be72a39055?context=explore) docker image. 
>
> Dont Expose your Dashboard.
>
> 
> Use Static State until Further Notice
<hr>

  

# WireGate 
![enter image description here](https://github.com/NOXCIS/Wiregate/blob/main/Docs/logo.png?raw=true)

![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/WireGate?style=social) ![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard/terra-firma.svg?style=flat&label=image&logo=docker) ![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/WireGate&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false) ![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.githubusercontent.com/NOXCIS/a08fe945ac095cea4f3cc21178ee43fb/raw/clone.json&logo=github)

  

>  **Wiregate** Supported architectures: `x86-64` , `arm64`, `armv7`, `armv6`
>  **Test OS**: Ubuntu LTS | Debian 12 
>  **Test Device:** Raspberry Pi 5 | Apple M2 | x86 CPUs
>  **Build:** Daily UTC

**Show your support**
Give a ⭐ if this project helped you!

  [![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-orange.png)](https://paypal.me/noxcisthedev)
  
  

## Table of Contents

- [About](#About)

- [Infrastructure Map](#infrastructure)
- [Screenshots](#screenshots)
- [Installation](#installation)
	- [Quick Install](#via-quick-installer) 
	- [Docker Compose](#install-full-stack-via-docker-compose) 
	- [Docker Compose Standalone](#install-standalone-via-docker-compose) 
- [Additional Resourses](#additional-resourses)
- [Acknowledgements](#acknowledgements)
- [Contributing](#contributing)
- [License](#license)

  

  
  

## About

  

**WireGate** is a fully automated **Docker Based Wireguard  & AmneziaWG VPN Sever Deployment & Management Tool** with and attachable intranet via docker private networks and support for **Tor** as an exit proxy.

  

It allows users to host web other applications on their existing server and be able to securely connect to said web applications without exposing them to the open internet. This is done by utilizing the **WireGuard protocol** in conjunction with **Docker Networks and Containers**. Hence applications hosted behind the WireGate private network *`need not expose any ports`* and can only be accessed via a *WireGuard* connection already registered to to an existing server interface on the deployed WireGate instance. Secure by Design, the WireGuard Dashboard & other services are only accessible on first deployment via the **master configuration** that is generated at install and `encrypted after being outputted to the console.` Wiregate also acts as a ISP DNS query logging bypass. Wiregate by default is configured to have minimal or no logging.

  
  
  

  

### Default Zone Permissions
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

>  [!NOTE]
> The quick installer only supports  Debian based Distros but will run on anything that runs Docker. 
> Its main purpose is to serve as an aid to less teachincal users.  Advanced users are expected to use the docker compose directly after using the installer to deploy.

> [!NOTE]
>Use the installer after running the quick installer to avoid recursive downloads.
>The -e flag isnt required you can just pass your enviornment witout the flag.

Running the command below installs prerequsites and runs the terminal based menu.

```bash

curl  -O  https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \

sudo  chmod  +x  stackscript.sh && \

sudo  ./stackscript.sh

```

Example Usage:
**The last option must always be** `-e`.
```bash

./stackscript.sh  -b  main -t  Tor-br-snow  -n  {CH},{GB} -e  E-P-D 

```

  

The available options are:

 |Flag | Usage| Example | 
|--|--|--|
|`-b` |for specifying a branch. 	| `main` or `<branch-name-here>` |
|`-e` |for specifying Enviorment 	| `E-A-D` |
|`-t` |for specifying Tor.			| `-t Tor-br-webtun`
|`-n` |Tor Proxy Exit Nodes 		| `-n {us},{ch},{gb}`
|`-l` |Tor DNS Exit Nodess 			| `-l {us},{ch},{gb}` 
|`-p` |Wireguard Protocol Type			| `-p awg` for **Amnezia Wireguard** or `-p wg` for **Vannilla WireGuard**|
|`-s` |Deploy State				| `-s static` or `-s dynamic` 
|`-d` |Docker In Docker			| `Dont Use In Prod, Dev Only.` 
  For more exit node options go to [Tor Country codes list](https://sccmrookie.blogspot.com/2016/03/tor-country-codes-list.html).
  
  


---

### `-e` : Enviorment Install Options
|Option String | Details|
|--|--|
| **E-A-D**: | `Express, AdGuard, Darkwire`
| **E-A-C**: |`Express, AdGuard, Channels`
| **E-P-D**: |`Express, Pihole, Darkwire`
| **E-P-C**: |`Express, Pihole, Channels`
| **A-A-D**: |`Advanced, AdGuard, Darkwire`
| **A-A-C**: |`Advanced, AdGuard, Channels`
| **A-P-D**: |`Advanced, Pihole, Darkwire`
| **A-P-C**: |`Advanced, Pihole, Channels`
| **dev** :| `Development Build`
| **help**:| `Display help menu`
| **reset**:| `Reset WireGate`

  
  
  
  
  
---
### `-t`: TOR  Install Options
| Option String | Details|
|--|--|
| **off**: |`Disable TOR`
| **Tor-br-snow**:| `Use Tor with bridges (snowflake)`
| **Tor-br-webtun**:| `Use Tor with bridges (webtunnel)`
| **Tor-br-obfs4**:| `Use Tor with bridges (obfs4)`
| **Tor-snow**:| `Use Tor without bridges (snowflake)`
| **Tor-webtun**:| `Use Tor without bridges (webtunnel)`
| **Tor-obfs4**: | `Use Tor without bridges (obfs4)`


For more exit node options go to [Tor Country codes list](https://sccmrookie.blogspot.com/2016/03/tor-country-codes-list.html).

  
---

### Install Full Stack via Docker Compose

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
    depends_on: [wiregate]
    image: "noxcis/dnscrypt:latest"
    restart: unless-stopped
    container_name: dnscrypt
    volumes:
      - ./configs/dnscrypt:/config
    networks:
      private_network:
        ipv4_address: 10.2.0.42

  unbound:
    depends_on: [dnscrypt]
    image: "noxcis/unbound:latest"
    container_name: unbound
    restart: unless-stopped
    hostname: "unbound"
    cap_add:
      - NET_ADMIN
    healthcheck:
      test: ["CMD", "drill", "@127.0.0.1", "dnssec.works"]
      interval: 30s
      timeout: 30s
      retries: 3
      start_period: 30s 
    #volumes:
    #  - "./configs/unbound:/etc/unbound/custom.conf.d"
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
      - "./configs/adguard/Data:/opt/adguardhome/work"
      - "./configs/adguard:/opt/adguardhome/conf"
    networks:
      private_network:
        ipv4_address: 10.2.0.100   

  wiregate:
      image: noxcis/wiregate:vidar
      container_name: wiregate
      hostname: wiregate
      cap_add:
        - NET_ADMIN
      devices:
        - /dev/net/tun:/dev/net/tun  
      restart: unless-stopped
      volumes:
        - pf_conf:/WireGate/iptable-rules/
        #- conf:/etc/wireguard 
        - db:/WireGate/db
        - ./configs/dnscrypt:/WireGate/dnscrypt
        - ./configs/tor:/etc/tor/
        - ./configs/logs:/WireGate/log/
        - ./configs/master-key:/WireGate/master-key

      environment:
      #Config Path Optional
        #- WGDCONF_PATH=/etc/wireguard
      #Use Ofuscated Wireguard (AmneziaWG)
        - AMNEZIA_WG=true
      #Set Timezone
        - TZ=America/New_York

      #Tor Settings
      ##########################################################
        - WGD_TOR_PROXY=true          #Enable Tor
        - WGD_TOR_EXIT_NODES={ch}     #Ex. {gb},{fr}
        - WGD_TOR_DNS_EXIT_NODES={us}
        - WGD_TOR_BRIDGES=true        #Enable Tor Bridges
        - WGD_TOR_PLUGIN=snowflake    #OPTIONS webtunnel, obfs4, snowflake
      #WGDashboard Global Settings
      ##########################################################
        - WGD_WELCOME_SESSION=false	  ##Promts user accont creation after fist sign in. 
        - WGD_AUTH_REQ=true
        - WGD_USER=admin
        - WGD_PASS=admin
        - WGD_REMOTE_ENDPOINT=0.0.0.0 #your domain or ip
        - WGD_REMOTE_ENDPOINT_PORT=80
        - WGD_PEER_ENDPOINT_ALLOWED_IP=0.0.0.0/0, ::/0
        - WGD_KEEP_ALIVE=21
        - WGD_MTU=1420
        - WGD_PORT_RANGE_STARTPORT=4430
      #DNS Setiings (Set To use Containers Above) You can use your own DNS
      ##########################################################
        - WGD_DNS=10.2.0.100
        - WGD_IPTABLES_DNS=10.2.0.100
      ports:
        - "4430-4433:4430-4433/udp" #UDP Interface Listen Ports For Zones
        - 8000:80/tcp #Comment Out for full network lockdown, I.E only Accessible via VPN conttenction at http://wire.gate using config in generated ./configs/master-key folder
      sysctls:        #Otherwise access the dashboard @ your-sever-ip/domain:6060
        - net.ipv4.ip_forward=1
        - net.ipv4.conf.all.src_valid_mark=1
        - net.ipv6.conf.all.forwarding=1
        - net.ipv6.conf.default.forwarding=1
      networks:
        private_network:
          ipv4_address: 10.2.0.3
    


volumes:
    db:
    conf:
    pf_conf:
````

  
### Install Standalone via Docker Compose
```yaml
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
  wiregate:
      #image: noxcis/wg-dashboard:chimera #Dynamic  Image
      image: noxcis/wiregate:vidar     #Static   Image
      container_name: wiregate
      hostname: wiregate
      cap_add:
        - NET_ADMIN
      devices:
        - /dev/net/tun:/dev/net/tun
      restart: unless-stopped
      volumes:
        - pf_conf:/WireGate/iptable-rules
        - conf:/etc/wireguard 
        - db:/WireGate/db
        - ./configs/tor:/etc/tor/
        - ./configs/logs:/WireGate/log/
        - ./configs/master-key:/WireGate/master-key
      environment:
      #Config Path Optional
        #- WGDCONF_PATH=/etc/wireguard
      #Use Ofuscated Wireguard (AmneziaWG)
        - AMNEZIA_WG=true
      #Set Timezone
        - TZ=America/New_York
      #Tor Settings
      ##########################################################
        - WGD_TOR_PROXY=true          #Enable Tor
        - WGD_TOR_EXIT_NODES={ch}     #Ex. {gb},{fr}
        - WGD_TOR_DNS_EXIT_NODES={us}
        - WGD_TOR_BRIDGES=true        #Enable Tor Bridges
        - WGD_TOR_PLUGIN=snowflake    #OPTIONS webtunnel, obfs4, snowflake
      #WGDashboard Global Settings
      ##########################################################
        - WGD_WELCOME_SESSION=false   #Promts user accont creation after fist sign in. 
        - WGD_AUTH_REQ=true			  
        - WGD_USER=admin
        - WGD_PASS=admin
        - WGD_REMOTE_ENDPOINT=0.0.0.0 #your domain or ip
        - WGD_REMOTE_ENDPOINT_PORT=80
        - WGD_PEER_ENDPOINT_ALLOWED_IP=0.0.0.0/0, ::/0
        - WGD_KEEP_ALIVE=21
        - WGD_MTU=1420
        - WGD_PORT_RANGE_STARTPORT=4430

      #DNS Setiings (Set To use Containers Above) You can use your own DNS
      ##########################################################
        - WGD_DNS=1.1.1.1
        - WGD_IPTABLES_DNS=1.1.1.1

      ports:
        - "4430-4433:4430-4433/udp" #UDP Interface Listen Ports
        - 8000:80/tcp #Comment Out for full network lockdown, I.E only Accessible via VPN conttenction at http://wire.gate using config in generated ./config/master-key folder
      sysctls:        #Otherwise access the dashboard @ your-sever-ip/domain:6060
        - net.ipv4.ip_forward=1
        - net.ipv4.conf.all.src_valid_mark=1
        - net.ipv6.conf.all.forwarding=1
        - net.ipv6.conf.default.forwarding=1
      networks:
        private_network:
          ipv4_address: 10.2.0.3
    

volumes:
    db:
    conf:
    pf_conf:
  
```


### Access

  

While connected to WireGate Admins Zone:

- navigate to http://wire.gate/ to use the **WireGate** dashboard.
- navigate to http://ad.guard/ to use the **AdGuard** Dashboard
- navigate to http://pi.hole/ to use the **PiHole** Dashboard
- navigate to https://dark.wire/ to use the **DarkWire** (if configured)

  

*The **password** & **username** are randomly generated and **provided in the final output** if not set manually.*

*Clients under the **members** zone **cannot** access the **WireGuard, Pihole, or Adguard** dashboards.*

  
  
## Additional Resourses
> [!NOTE]
> All configs can be found in ./configs

### Tor

  

WireGate includes the complied binaries for the following Tor Transort Plugins:

-  **Lyrebird** (meek_lite,obfs2,obfs3,obfs4,scramblesuit)

-  **SnowFlake**

-  **WebTunnel**


Plugin choice can be seleted during installation or updated with docker compose. Also at a random intervals between **100** & **1642** seconds, **WireGate will Obtain a new Tor Circuit** if Tor is Enabled.

[Tor Manual Pages](https://2019.www.torproject.org/docs/tor-manual.html.en)

### DnsCrypt
[DnsCrypt Config](https://github.com/DNSCrypt/dnscrypt-proxy/blob/master/dnscrypt-proxy/example-dnscrypt-proxy.toml)

### Iptable Routing with WireGuard
>NOTE
>Iptable routing is what makes proxying wireguard peers thorugh tor possible.
>
[WireGuard User Network Restrictions](https://gist.github.com/qdm12/4e0e4f9d1a34db9cf63ebb0997827d0d)
[Tor TransPort](https://gitlab.torproject.org/legacy/trac/-/wikis/doc/TransparentProxy)

## Help

All Wiregate supporting configurations can be found in the Global Configs Folder.

If you need assistance, simply run:

  

```bash

sudo  ./install.sh  help

```





This will display the usage instructions and available options.

  

## Acknowledgements

  

The code in this repo is influenced by [IAmStoxe's WireHole](https://github.com/IAmStoxe/Wirehole) project & the [WireAdmin](https://github.com/wireadmin/wireadmin) project.

However, the upstream projects and their authors most certainly also deserve credit for making this all possible.

- [AdGuard](https://github.com/AdguardTeam/AdGuardHome) -AdGuard

- [Pihole](https://github.com/pi-hole). - Pihole

- [NLnetLabs](https://github.com/NLnetLabs). -Unbound

- [Kyle Harding](https://github.com/klutchell). -Distroless Unbound Docker Image

- [Donald Zou](https://github.com/donaldzou). -WG Dashboard (WireGuard UI)

  




  
  
  
## Screenshots
![enter image description here](https://github.com/NOXCIS/Wiregate/blob/main/Docs/screenshots/Screenshot-SignIn.png?raw=true)
![enter image description here](https://github.com/NOXCIS/Wiregate/blob/main/Docs/screenshots/Screenshot-New-Config.png?raw=true)

![enter image description here](https://github.com/NOXCIS/Wiregate/blob/main/Docs/screenshots/Screenshot-Config-List.png?raw=true)
![enter image description here](https://github.com/NOXCIS/Wiregate/blob/main/Docs/screenshots/Screenshot-Config-Settings.png?raw=true)

![enter image description here](https://github.com/NOXCIS/Wiregate/blob/main/Docs/screenshots/Screenshot-Backup-Restore.png?raw=true)


## Contributing

  

Contributions are welcome! Feel free to fork the repository, make changes, and submit a pull request. For internet privacy and Freedom.

  

## License

  

This project is licensed under the MIT License - see the [LICENSE](https://github.com/NOXCIS/Wiregate/blob/main/LICENSE) file for details.
