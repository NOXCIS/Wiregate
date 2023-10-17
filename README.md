  

# Worm-Hole

![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/Worm-Hole?style=social) ![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard.svg?style=flat&label=image&logo=docker) ![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/Worm-Hole&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false) ![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.githubusercontent.com/NOXCIS/a08fe945ac095cea4f3cc21178ee43fb/raw/clone.json&logo=github)

  



### What Is Worm-Hole?
Worm-Hole is an **intranet deployment** application that allows users to host web other applications on their existing server and be able to securely connect to said web applications without exposing them to the open internet. This is done by utilizing the **WireGuard protocol** in conjunction with **Docker Networks and Containers**. Hence applications hosted behind the worm-hole private network *need not expose any ports* and can only be accessed via a *WireGuard* connection.  
Wormhole also acts as a ISP DNS query logging bypass. Wormhole by default is configured to have minimal logging.

### Supported Architectures

  

The WireGuard Dashboard image supports the `x86-64` and `arm64` CPU architectures . The docker manifest is untied for multi-platform awareness.

  
  


  



  



  
  
  

### Show your support

  

Give a ⭐ if this project helped you!

  
  

<a  href="https://paypal.me/noxcisthedev?country.x=US&locale.x=en_US"  target="_blank"><img  src="https://i.imgur.com/6JvV0aR.png"  alt="Buy Me A Coffee"  style="height: 60px !important;width: 217px !important;"  ></a>

  

  
  
  
  

  

## Installation Instructions

  

Run these commands to install WormHole.

```bash

#!/bin/bash

git  clone  https://github.com/NOXCIS/Worm-Hole.git

cd  Worm-Hole

chmod  +x  install.sh

sudo  ./install.sh

```

## Install Options

-
  ### Installer Menu

- ./install.sh -Starts the setup script menu.

![enter image description here](https://i.imgur.com/498nQEx.png)

  
---

### Express Install

 ./install.sh **auto** - Starts the setup script and automatically configures the compose file with following environment variables:.

- Server IP Address

- Pihole Time Zone

- Pihole Password as **random**

- Number of WG Server Configs as **1**
![enter image description here](https://i.imgur.com/PxI8lVh.png)

---

### Advanced Install

  

- ./install.sh **manual** - Start the setup script allowing the user to manually configure the compose file environment variables.

### Custom PreConfigured Install

- ./install.sh **preset** - Set your Desired Environment Variables in the environment files located in **Global-Configs/ENV-FILES**

---

### Reset Worm-Hole Deployment

- ./install.sh **fresh** - Reset WireGuard Dashboard

![enter image description here](https://i.imgur.com/JYITQiu.png)

---




  
  
  

### Connecting to WireGuard & Accessing Dashboard

-The installer will output a master client config similar to the one below. The master key file is automatically encrypted after the final output. 

![enter image description here](https://i.imgur.com/yJk4Eeu.png)

## Access Channels Messenger
While connected to Worm-Hole, navigate to http://channels.msg/

Worm-Hole has a updated version of Channels messenger by [dzionek](https://github.com/dzionek) built in, to felicitate secure encrypted communication via the Worm-Hole network. 

![enter image description here](https://github.com/dzionek/channels/raw/master/readme_screenshots/screenshot-1.png)

Flask web-application where you can create own channels, manage them, and chat with your friends/colleagues.
Created with Python, TypeScript, SCSS, Bootstrap, Socket.io, Handlebars templates, and love. Bundled with Webpack.
Containerized with Docker.

Inspired by the Project 2 of Harvard's [CS50’s Web Programming with Python and JavaScript](https://cs50.harvard.edu/web/2018/).
  

  

## Access WG-DashBoard

While connected to Worm-Hole, navigate to http://worm.hole/
*The password & username is admin.*

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/PWA.gif)

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/HomePage.png)

  

![enter image description here](https://github.com/donaldzou/WGDashboard/raw/main/img/AddPeer.png)

---

  

## Access PiHole

While connected to Worm-Hole, navigate to http://pi.hole/
*The password is randomly generated and provided in the final output.*

![enter image description here](https://camo.githubusercontent.com/dea9baf54793ba7a4c38b5f36f624790116fa5d11f971efa0fd1f8fad98904e9/68747470733a2f2f692e696d6775722e636f6d2f686c484c3656412e706e67)

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