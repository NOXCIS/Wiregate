  

# WireGate

  
![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/WireGate?style=social) ![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard.svg?style=flat&label=image&logo=docker) ![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/WireGate&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false) ![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.githubusercontent.com/NOXCIS/a08fe945ac095cea4f3cc21178ee43fb/raw/clone.json&logo=github)

  

  
  
  

### What Is WireGate?

WireGate is a fully automated Docker Based **intranet deployment**  that allows users to host web other applications on their existing server and be able to securely connect to said web applications without exposing them to the open internet. This is done by utilizing the **WireGuard protocol** in conjunction with **Docker Networks and Containers**. Hence applications hosted behind the WireGate private network *`need not expose any ports`* and can only be accessed via a *WireGuard* connection already registered to to an existing server interface on the deployed WireGate instance. Secure by Design, the WireGuard Dashboard & other services are only accessible on first deployment via the **master configuration** that is generated at install and `encrypted after being outputted to the console.`  Wiregate also acts as a ISP DNS query logging bypass. Wiregate by default is configured to have minimal logging.

  

### Supported Architectures
The WireGuard Dashboard image supports the `x86-64` and `arm64` CPU architectures . Tested on **Ubuntu LTS**


|Container| Status |Know Image CVE's|Tag| 
|--|--|--|--|
| WG-Dashboard | ✅ | 0 | noxcis/wg-dashboard:orca
|Pihole|✅|30|pihole/pihole:latest|
|AdGuard|✅|0|adguard/adguardhome:latest |
|Channels|✅|0|noxcis/channels:orca |
|Unbound|✅|0| klutchell/unbound:latest |
|Postgres|✅|0|postgres:13-alpine|

### Wiregate Use Cases

|Use Case | Description  |
|--|--|
| Authentication | Access to service can be limited by requiring a WireGuard client config as well as a registered account on said service  |
|Secure Self Hosted VPN|  Self Explanatory|
|Local Network Filter Proxy | By using a raspberry Pi ruining on the same local network your able to pre proxy all network traffic through your desired device using adguard/pihole & unbound. The unbound config will need to be modified to use an upstream DNS server for this to work, unless a cloud based Wiregate Node  is used in conjunction with the Raspeberry Pi. |
|Secure Invite Only Messaging Service | This is done via channels and allows all members of the Wiregate Private Network to communicate under the same secure umbrella.|
|||


### Show your support


Give a ⭐ if this project helped you!

<a  href="https://paypal.me/noxcisthedev?country.x=US&locale.x=en_US"  target="_blank"><img  src="https://i.imgur.com/6JvV0aR.png"  alt="Buy Me A Coffee"  style="height: 60px !important;width: 217px !important;"  ></a>

  

  

  

  

## Installation Instructions
Run these commands to install WormHole.
```bash
#!/bin/bash
git  clone  https://github.com/NOXCIS/WireGate.git
cd  WireGate
chmod  +x  install.sh
sudo  ./install.sh
```

  

## Install Options

  



### Installer Menu

  

- ./install.sh -Starts the setup script menu.
![enter image description here](https://i.postimg.cc/6phrt4m3/Screenshot-2023-10-18-at-10-56-00-AM.png)

  

---

  

### Express Install

**For Pihole Setup**
- ./install.sh **pi-exp** - Starts the setup script and automatically configures the compose file with following environment variables:.

**For AdGuard Setup**
  

- ./install.sh **pi-adv** - Starts the setup script and automatically configures the compose file with following environment variables:.

  

![enter image description here](https://i.imgur.com/PxI8lVh.png)
 
---

  

### Advanced Install

 
  **For Pihole Setup**
- ./install.sh **pi-adv** - Start the setup script allowing the user to manually configure the compose file environment variables.

**For AdGuard Setup**
- ./install.sh **ad-adv** - Start the setup script allowing the user to manually configure the compose file environment variables.

  


### Custom PreConfigured Install

 **For AdGuard Setup**

- ./install.sh **ad-predef**  - Set your Desired Environment Variables in the environment files located in **Global-Configs/ENV-FILES**

**For Pihole Setup**

  - ./install.sh **pi-predef**  - Set your Desired Environment Variables in the environment files located in **Global-Configs/ENV-FILES**



  
### Reset WireGate Deployment

  

- ./install.sh **fresh** - Reset WireGuard Dashboard
![enter image description here](https://i.imgur.com/JYITQiu.png)


  
  
  
  

  

## Connecting to WireGuard & Accessing Dashboard

  

The installer will output a master client config similar to the one below. The master key file is automatically encrypted after the final output. To decrypt the Master Key use the Master Key decryption key.

  

![enter image description here](https://i.imgur.com/yJk4Eeu.png)

  

## Access Channels Messenger

While connected to WireGate, navigate to http://channels.msg/

WireGate has a updated version of Channels messenger by [dzionek](https://github.com/dzionek) built in, to felicitate secure encrypted communication via the WireGate network.

![enter image description here](https://github.com/dzionek/channels/raw/master/readme_screenshots/screenshot-1.png)

  

Flask web-application where you can create own channels, manage them, and chat with your friends/colleagues.

Inspired by the Project 2 of Harvard's [CS50’s Web Programming with Python and JavaScript](https://cs50.harvard.edu/web/2018/).

  

  

## Access WG-DashBoard

  

While connected to WireGate, navigate to http://worm.hole/

*The password & username is **admin**.*

  

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/PWA.gif)

  

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/HomePage.png)

  

  

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/AddPeer.png)

  



 

## Access Adguard (If Selected)
While connected to WireGate, navigate to http://ad.guard/
*The **password** is randomly generated and **provided in the final output** if not set manually.*

![enter image description here](https://i.postimg.cc/4y7SKQ9s/Screenshot-2023-10-18-at-10-37-21-AM.png)
  

## Access PiHole (If Selected)

While connected to WireGate, navigate to http://pi.hole/

*The **password** is randomly generated and **provided in the final output** if not set manually.*

  

![enter image description here](https://camo.githubusercontent.com/dea9baf54793ba7a4c38b5f36f624790116fa5d11f971efa0fd1f8fad98904e9/68747470733a2f2f692e696d6775722e636f6d2f686c484c3656412e706e67)

  



  

## Custom Unbound Configuration

Custom unbound confurations can be done by modifying the file **unbound.conf** loacated in the **Unbound-Custom-Config** folder before stack deployment.

### Modifying the upstream DNS provider for Unbound

If you choose to not use Cloudflare any reason you are able to modify the upstream DNS provider in `unbound.conf`.

Search for `forward-zone` and modify the IP addresses for your chosen DNS provider.

>**NOTE:** The anything after `#` is a comment on the line.

 
What this means is it is just there to tell you which DNS provider you put there. It is for you to be able to reference later. I recommend updating this if you change your DNS provider from the default values.

  

  

```yaml
forward-zone:
name: "."
forward-addr: 1.1.1.1@853#cloudflare-dns.com
forward-addr: 1.0.0.1@853#cloudflare-dns.com
forward-addr: 2606:4700:4700::1111@853#cloudflare-dns.com
forward-addr: 2606:4700:4700::1001@853#cloudflare-dns.com
forward-tls-upstream: yes
```

  



  


  
  
  

## Acknowledgements

  
  

The code in this repo is influenced by [IAmStoxe's WireGate](https://github.com/IAmStoxe/WireGate) project.

WireGate lacked the ability to easily generate new users and has recenlty stopped working due to updates to the parent project of Unbound-Docker, [Unbound-Docker by MatthewVance](https://github.com/MatthewVance/unbound-docker) .
 
Therefore with the help of klutchell's unbound-docker Docker image & donaldzou's WGDashboard Dockerized by Noxcis, WireGate was recreated as WireGate.
However, the upstream projects and their authors most certainly also deserve credit for making this all possible.

  
  
- [AdGuard](https://github.com/AdguardTeam/AdGuardHome) -AdGuard

- [Pihole](https://github.com/pi-hole). - Pihole 

- [NLnetLabs](https://github.com/NLnetLabs). -Unbound 

- [Kyle Harding](https://github.com/klutchell). -Distroless Unbound Docker Image

- [Donald Zou](https://github.com/donaldzou). -WG Dashboard (WireGuard UI)

- [Bartosz Dzionek](https://github.com/dzionek) -Channels Messenger

Nox 2002-2023

 
