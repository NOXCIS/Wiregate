  

# Worm-Hole
![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/Worm-Hole?style=social)   ![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard/latest.svg?style=flat&label=image&logo=docker)    	![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/Worm-Hole&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false) ![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.githubusercontent.com/NOXCIS/a08fe945ac095cea4f3cc21178ee43fb/raw/clone.json&logo=github)

  ### Supported Architectures

The WireGuard Dashboard image supports multiple architectures such as `x86-64`, `arm64` and `armhf`.  The docker manifest is untied for multi-platform awareness. 


Simply pulling `noxcis/wg-dashboard:squid-multi-arch` should retrieve the correct image for your arch.

> *This is the default configuration in this project*

**The architectures supported by this image are:**

| Architecture | Tag |
| :----: | --- |
| x86-64 | amd64-latest |
| arm64 | arm64v8-latest |
| armhf | arm32v7-latest |


  ### What is WormHole?
[Worm-Hole ](https://github.com/NOXCIS/Worm-Hole) is an improvement on Wirehole by IAmStoxe.

WireHole is a combination of WireGuard, PiHole, and Unbound in a docker-compose project with the intent of enabling users to quickly and easily create and deploy a personally managed full or split-tunnel WireGuard VPN with ad blocking capabilities (via Pihole), and DNS caching with additional privacy options (via Unbound).

Wormhole also acts as a ISP DNS query logging bypass. Wormhole by default is configured to have minimal logging.

  ### Show your support

Give a ⭐ if this project helped you!


<a href="https://paypal.me/noxcisthedev?country.x=US&locale.x=en_US" target="_blank"><img src="https://i.imgur.com/6JvV0aR.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

  




  

## Installation Instructions

Run these commands to install WormHole.
```bash
#!/bin/bash
git  clone  https://github.com/NOXCIS/Worm-Hole.git
cd  Worm-Hole
chmod  +x  install.sh
sudo  ./install.sh 
```
The installation script has a few setup options which are:

- ./install.sh -Starts the setup script menu.
![enter image description here](https://i.imgur.com/gu4IxUj.png)
  

- ./install.sh **headless** - Starts the setup script and automatically configures the compose file with following environment variables:.
		 	    	  
	- Server IP Address
	- Pihole Time Zone
	 - Pihole Password as **empty**
	- Number of WG Server Configs as **1**

- ./install.sh **manual** - Start the setup script allowing the user to manually configure the compose file environment variables.
- ./install.sh **fresh** - Reset WireGuard Dashboard
	![enter image description here](https://i.imgur.com/HzdAg2I.png)
- ./install.sh **quickcount** - Auto configuration with quickset for # of  Server Interfaces  to Generate & Pihole Password



 ### Connecting to WireGuard & Accessing Dashboard
  -The install script will output a client config similar to the one below:
```bash

#######################################################################

             Copy Master Key to empty WireGuard .conf file
             Connect to Wireguard and access the Dashboard

             WireGuard Dashboard Address: http://worm.hole
             Pihole Dashboard Address:    http://pi.hole

             VPN Connection Required to Access Dashboards

#######################################################################





███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗     ██╗  ██╗███████╗██╗   ██╗
████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗    ██║ ██╔╝██╔════╝╚██╗ ██╔╝
██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝    █████╔╝ █████╗   ╚████╔╝
██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗    ██╔═██╗ ██╔══╝    ╚██╔╝
██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║    ██║  ██╗███████╗   ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝   ╚═╝



[Interface]
PrivateKey = XXXXXXXXXXXXXXXXXXXXXXXXXXrJGXyu0P8U4=
Address = 10.0.0.254/32
DNS = 10.2.0.100,10.2.0.100
MTU = 1420

[Peer]
PublicKey = XXXXXXXXXXXXXXXXXXXXXXXXXXx8bQpVAHYS/KFU=
AllowedIPs = 0.0.0.0/0
Endpoint = <HOSTIP>:51820
PersistentKeepalive = 21
PresharedKey = XXXXXXXXXXXXXXXXXXXXXXXXXXiDqBQucHM8+I=


█████████████████████████████████████████████████████████████████████████
█████████████████████████████████████████████████████████████████████████
████ ▄▄▄▄▄ █▀▄█▄ ███▀▀███▀▀▄▄█▄ ▄▄▄▀ ▀█▀▀█▄▀█ ▀ ▄▀ ▄ ██▄▄ █▄▀█ ▄▄▄▄▄ ████
████ █   █ █▄▄▄▀ ▀███▀▄▄▄ ▄ ▀ █ ▀ ▄ █▀▀▄█▄▄▄█▄ ▀█▄  ██▄██▄ ▀▄█ █   █ ████
████ █▄▄▄█ █ ▀▄█▄▀ █▄▄▄▀  █▄ █ ▄▀█ ▄▄▄  ▀▀ █ ▀    ▀█▄ ▄▄█▄▀█▄█ █▄▄▄█ ████
████▄▄▄▄▄▄▄█ █▄▀▄█ █▄▀▄█ █▄▀▄▀▄▀ █ █▄█ ▀ ▀▄▀▄▀▄▀ ▀ █ █▄█▄█▄█▄█▄▄▄▄▄▄▄████
████▄▄▀ ▀▀▄▄▀█▄ ▄█▀▄▄  ▄█▄ ███▀█▄▀▄▄▄▄▄▀ ▄█ ▄▀▄▀█▀▄ ▄▀██▄█▄█▀▀  ▄▀▄ █████
████▄█  ▀█▄▄▀▀ █▀▄▀███▀▀ █▄ ▄▄▀▀▄█ ▄ ▄▀▀▄▄▀▀█▄▀▄ █▀▀ ▄▀█▀▀  ▄▀▄▄▀▄▀▀▀████
████▀▄▀▀▀ ▄▀██▀▄▄ ▄▄▀▀ ▀ ▄ █ ▄▄█▄▄▀  █ ▄▄█▄  ██▄▄▀▀ ▄▀▄▄  ▄▄█▄  ▄▀   ████
████   █▄ ▄▄ ██▀▄█▀ ▄▀▄█  █▄▀  █▀▄▀▀▀▀█ ▀▀   ▄▄ █▄▀ ▄██ ▄▄ ▄ ▀█   █▄ ████
████ █▄▄▄▄▄▀▀▀▄▀▄▄▀███▄▄▄▀ █ ▀▄▀ █ ▄ █ ▄▄▀▄▄█  ▄▄▄█ ▄▄█ █▀▀  ▀█▀▄ ▄▀ ████
████▄▀█▄█▄▄███▄ ▀▀▀██ ▀▀▀ ██▀▄▀█▄█▄██▀█▀█▀▄▀█▀▀ ▀▀▄▄▀██▀█▀▀▀▄ ▄ ▀ ▄ ▄████
████  ▀▀▄▄▄▄█  █  ██ ▀█▄▄ █▄▄ ▄██▄▀ ▀ █▄ █▄▄▄█▄█▀██ ▄▀█▄ █▄▄▄▄█▀ ▀  ▀████
█████  ▀█▀▄ ▄▀  ▄ ▄█ █▀███▀█ █▀▄▀▄▄▀ ▀▄█ █ █▄▀▄▀█▀▀▀ ██▄▀▄█  █▀▄ ▄▀ █████
█████▄ █▄▄▄▄▀█▄  █▄▀ ▀▄▀▄▀▄███▄ ▀██▄▀▄ ▄▄ ▄▄▄▀▄▀▄█▀█▄██▀ ▀ ▀▄ ▀▄▄█ ▀ ████
████▀  ▄ ▄▄█▄██▄█  ▀▀█▀▄█▀█ █▀  ▄   ▄▀ ▀  ▄▀▀██▄▄▀▄▄▄   ▀▀▀█▄▀█▄███▀▄████
████▄ ▄ ▀▄▄▄█▄▀ █▀▄ █▄ ▀ ▄▀▄▄▀  ██▄ ▀▄█▄    ▀ ▄█ ▀█ ▄█ ▄▀▀█▄▀▄▄▄ ▄▄██████
████▀▄▄▀ ▄▄▄ █▀▄▀ ▀  ▄ ▄▄ ▀ ▄ █  █ ▄▄▄ ▀▄ ▀  ███▄██▀   ▀██ ▀ ▄▄▄ █▄▄▄████
████▀▄▀█ █▄█ ▀▀▄▄ ▀█▄ ▀▀▄▀▀▄ ▀▀▀▄  █▄█ █▄██▀▀█▄▀  ▄███▀ ▀▀▄  █▄█ █  ▀████
█████▀██  ▄  ▀▀██▄▄ █▀▄█▄██  ▄ ▀ ▀     ▄█  ▀ ▀▀▀█▀ █▀▄██ ▀▄    ▄▄▄▀▀▄████
████▄█ ▀ ▄▄ ▄ █▄▄█▄▄ █▄▀▄█ ▄█▀▄█▀▀▄ █ ▀▄▄ █▄▄ ██▄▀▀█▄▄▄▄▄██▄▄▄▄ █ █▄▀████
████▄▄▀ ▀ ▄▀█▀█  ▄▄█▀█▄▀ ▀▄▀▀▀ ▀▀▀█▄█▄▄█ ▀▄▄█▀██▀▄▀█▀▀▄ ▀▄█▀ ██ ▄██▄ ████
████▄█▀▀▀▄▄▀█▄ ▄▀ █▀▀▄▄▀▄█▀ █▀ █▄█▄▀▀▄▀▄▄▄▀ ▀██  ▄██  ▀███▄▄  █▀█   █████
████▀ ▄ ▀▀▄▄██  ▄  ▄█▄█  ▀ █▄██▄█ ▀██▀██   ▀█▄▀▀ ▄▄ ▀██▀▀▀▄▄▄█▄▀█▀█▀ ████
████ ▄ ▀██▄██▄▄ █▄▄█ ▀ █▀▄▄▄  ██  ▄▀█▄██  █  ▄█▄█▀██ ██▄▄█▄▀▀ ▄  █▀ ▄████
████▀▄█  ▀▄▀█ ▄▀  ▄█ ▄▄▄█  ▀▀▀██ ▀▄   █▄█▄█ ▄▀▀ ▄▄▄█ █▀ ▀▀▀ █▀█▀ ▄▀ █████
████ ▄▄█  ▄ ▄█ ▀▀ ▀▀▀▀▄█ ▀ ▀▀▄ █ ▄█▀▀█▄███▀▄ ██▀ ██▀ ▀█▀█▀██▄▄ ▄▄▀▄▀ ████
████▄▀█▀▀▀▄▀  ██▀▀ ██▀▀▄▀ ▀▄    ▄▄█▄  ▄▄█▀  ▀ ▄▄ ██▄▀▀█▀▀ █▀ ▄▄ ▄██  ████
████▀█ ▀ ▄▄▄ █▀▄ █▀█▄▄█▄▀ ▄▀▄▀▀▄▄▄▄▄▀▄▄▀█   █▀▄ ▄▄██▄▄  █ ▄ ▀▄███▄█▄ ████
████▀█▄ █▄▄   ▄▄█▄▀  █▄█▄▄▀█▀▀▄█▀  ▄▀▀▀█▄ ▀▀  ▄▄▀█ ▀  ▀▄█▄██▄   █▀█▀ ████
█████▄▄█▄█▄█ █▀▄▀▄▀███  █▀ ▄█ ▀█▄  ▄▄▄ ▀  █▀  ▄███▄ ▄▀▄ ▄ ▄█ ▄▄▄  █▄▄████
████ ▄▄▄▄▄ █▄▀▀▀▄█ █▀▀   ▀▀▀▄▀▀██▄ █▄█ █▀  ▀ ▀▄▀▄ ██▄▀▀▀▀▀ ▄ █▄█ ▄▀▀▄████
████ █   █ █▀ █▄ ▄█  ▄▄▄▄▄  ▄▄     ▄   ▄ █▄▄▄█▄ ▄▀ ▄▄▄█  █▄▄ ▄ ▄   ▀▀████
████ █▄▄▄█ █▀▄█▀ █▀ ▄▀  █ █▀▄   ▄ ▀▄█▄▄▀▄█▄▀ █▀ ▀▀▀▀ ▀   ▄▀█ █▄█▄▀▀▀▄████
████▄▄▄▄▄▄▄█▄▄███████▄▄▄████▄▄███▄█▄▄██▄█▄█▄██▄▄▄▄▄▄▄▄▄██▄██▄▄█▄▄▄█▄█████
█████████████████████████████████████████████████████████████████████████
█████████████████████████████████████████████████████████████████████████

```
---

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
  ---

## Access WG-DashBoard

While connected to WireGuard, navigate to http://worm.hole/

*The password & username is admin.*

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/PWA.gif)
  
  ![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/HomePage.png)

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/AddPeer.png)  
---

## Access PiHole

While connected to WireGuard, navigate to http://pi.hole/

*The password (unless you set it in `docker-compose.yml`) is blank.*
![enter image description here](https://camo.githubusercontent.com/dea9baf54793ba7a4c38b5f36f624790116fa5d11f971efa0fd1f8fad98904e9/68747470733a2f2f692e696d6775722e636f6d2f686c484c3656412e706e67)
 
  ---
  


  

## WGDashboard Github Repository

  

https://github.com/donaldzou/WGDashboard

  

  

## Pihole Github Repository

  

https://github.com/pi-hole/docker-pi-hole

  

  

## Unbound-Docker Github Repository

  

https://github.com/klutchell/unbound-docker

  

  

## Acknowledgements

  

The code in this repo is influenced by [IAmStoxe's Wirehole](https://github.com/IAmStoxe/wirehole) project.

  

  

Wirehole lacked the ability to easily generate new users and has recenlty stopped working due to updates to the parent project of Unbound-Docker, [Unbound-Docker by MatthewVance](https://github.com/MatthewVance/unbound-docker) .

  

  

Therefore with the help of klutchell's unbound-docker Docker image & donaldzou's WGDashboard Dockerized by Noxcis, Wirehole was recreated as Worm-Hole.

  

  

However, the upstream projects and their authors most certainly also deserve credit for making this all possible.

  

- [pi-hole](https://github.com/pi-hole).

  

- [NLnetLabs](https://github.com/NLnetLabs).

  

- [Kyle Harding](https://github.com/klutchell).

  

- [Donald Zou](https://github.com/donaldzou).

  

- [MatthewVance](https://github.com/MatthewVance).

  

  

## Warning

  

  

I'm not responsible if your internet goes down using this Docker container Stack. Use at your own risk.

  

  

