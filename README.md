  

# Worm-Hole

![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard/latest.svg?style=flat&label=image&logo=docker) ![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/Worm-Hole?style=social)

  

[Worm-Hole ](https://github.com/NOXCIS/Worm-Hole) is an improvement on Wirehole by IAmStoxe.

  

WireHole is a combination of WireGuard, PiHole, and Unbound in a docker-compose project with the intent of enabling users to quickly and easily create and deploy a personally managed full or split-tunnel WireGuard VPN with ad blocking capabilities (via Pihole), and DNS caching with additional privacy options (via Unbound).

Wormhole also acts as a ISP DNS query logging bypass. Wormhole by default is configured to have minimal logging.

## Installation Instructions
Installing using the install.sh script.
The installation script has a few setup options which are:
- ./install.sh -Starts the setup script menu.

 - ./install.sh **headless** - Starts the setup script and automatically configures the compose file. 
 
	This option allows docker install and container stack deployment with out user interaction. 

	The script will auto set the following environment variables for the **Wireguard Dashboard** running at **your_server_ip:10086** & **Pihole** respectively.
	
	Server IP Address

	Pihole Time Zone

	Pihole Password as **empty**

	Number of WG Server Configs as **1**	
 
 -  ./install.sh **manual** - Starts the setup script allowing the user to manually configure the compose file.
 
 -  ./install.sh **fresh** - gets a fresh docker compose from GitHub

  

### Installing on Debian Based Linux Server

  

Worm-Hole can be installed on Ubuntu Server via the install.sh script

```bash

#!/bin/bash

git  clone  https://github.com/NOXCIS/Worm-Hole.git

cd  Worm-Hole

chmod  +x  install.sh

sudo  ./install.sh <script-option>

```

## Custom Unbound Configuration
Custom unbound confurations can be done by modifying the file **unbound.conf** loacated in the **Unbound-Custom-Config** folder before stack deployment.

  

## Added functionality

  

-  **WGDashboard** -as a front end dashboard to control wireguard server and user configs.

-  **Portainer** - for overall container management on a lightweight VPS.

-  **Install Script** - to modify the docker-compose environment variables before the container stack is created.


  

## Working Containers

  

| Status | Container | Source |

| ✅ | Pihole | pihole/pihole:latest |

| ✅ | Unbound | klutchell/unbound:latest |

| ✅ | WG-Dashboard | noxcis/wg-dashboard:latest |

| ✅ | Portainer | portainer/portainer:latest |





  
  

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

  

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/Worm-Hole&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false)](https://github.com/origamiofficial/docker-pihole-unbound)