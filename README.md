# WireGate ![GitHub Repo stars](https://img.shields.io/github/stars/NOXCIS/WireGate?style=social) ![Docker Pulls](https://img.shields.io/docker/pulls/noxcis/wg-dashboard.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/noxcis/wg-dashboard/terra-firma.svg?style=flat&label=image&logo=docker) ![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/NOXCIS/WireGate&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false) ![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clone&query=count&url=https://gist.githubusercontent.com/NOXCIS/a08fe945ac095cea4f3cc21178ee43fb/raw/clone.json&logo=github)


## Table of Contents
- [About](#About)
- [Infrastructure Map](#Infrastructure)
- [Installation](#installation)
- [Usage](#usage)
- [Options](#options)
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

| Project | Easy Setup | Production Ready | Client Firewall Rules | GUI | DNS Filtering | Built in Security | Tor Proxy | 2FA | 3FA |
|--|--|--|--|--|--|--|--|--|--|--|
| **Wiregate** 	|✅|✅|✅|✅|✅|✅|✅|✅|✅|
| **Wirehole** 	|✅|:x:|:x:|:x:|✅|:x:|:x:|:x:|:x:|
| **WG-Easy** 	|✅|:x:|:x:|✅|:x:|:x:|:x:|:x:|:x:|
| **WireAdmin** |✅|:x:|:x:|✅|:x:|:x:|:x:|:x:|:x:|

### Zone Permissions

Wiregate is configured with 4 zones that peers can be added to. The zone a peer belongs to dictates the network access permissions of said peer. **Wiregate** supports the `x86-64` and `arm64` CPU architectures . Tested on **Ubuntu LTS & Debian 12**

  

| Zone | Internet Access | WireGuard Dashboard Access | Docker Network Access | Peer to Peer Access |
|--|--|--|--|--|
| **Admin** |✅| ✅ | ✅ | ✅ |
| **Members**|✅|:x:|✅|✅|
| **LAN Users**|:x:|:x:|:x:|✅|
| **Guest**|✅|:x:|:x:|:x:|



## Infrastructure
 Symbolic Network Map


![Symbolic Network Map](https://mermaid.ink/svg/pako:eNqtWAtv4kgS_islj-ayqwNiGwjgmYsWMCSR5ibskMxIF06nxm7Aium2_Mhjk_nvW9W2MQ8TmOhgNLG7-qt3VVfzojnS5Zqlffz4MhGe8GIL8OEkXvAlP7HgZMoiflLJV76z0GNTn0cn6bYg9JYsfO5LX4a0-0OD6R29owAZ7YY_xQV9NputE3sydHlYkHVdV2TfE7xYHbZ7ppkyjbgjhbsp0qRvqiMPY2-DSPImYiJ-pv8-fqSXiZj58tFZsDCGL98mArJPF6rVc3gdCCd8DmLuwg8v5BcJC124Cdls5jlwa49eoQdQgHpHgvokNwflz1EynYcsWIDnch3uLmUUw7-Zs0Dz4ao2gO-jMcgQLuWSw5iHDzz87y7QgDtbOvc8hK88fpThPfwBhl4za3pNPzUbJQgT7pSWLObQlyJmKI84K7XW9eyDsg7sYmmASzWy2JcO88GXMpgy5x4CHi49sn-ICv-4AJtFi6lkLnQdh0eRckDOw87YDmB3bbi7dFEswboP86dhuu-16_vwVQqwv45Pvyjtsgi8gl3ftOAXtl_-2vZM6UtyIxduuZY7PKD4IDuzXNnjUbaZojZ330jYSpRV8KOUx6C-ywOlrjgwgfF055TdpyNP-lyFuScp27vu0hOraA_NXQ-ucyr7bKKGZhb9tbWLfK2eJWtJViinb3g-swRexzGj5lFU5tUMnRLC9XC4q8tgXW4940Am_Jnw0OMRHPhscrBzDqNQPnm8UOFmEcpkvlB6vMkh8-KaFZdxHMA_1J9ov0mbXPKnde9ht70fx88YTR2iOJT33PowHGIv1ivpa_XRc-OFZejBUxnKeBfKXEPZrWNR9RWq26HvFqpJqDJc401p9XJhzfeAzt4DMvTDqN3jY4tH4RuTt6fOFo-zPZILzxiNpt19C1WKL5yk90270d7Et_dINd6FMo9HleFb70q59rtQnSNQpWVRZEIba6mtl2V4iWsOaLkP1nkz-vtgpnGEtFJ5b1eHua_DtH4Btn000Ld7N9E-u94DskF-_8JJ8SmuMt-bC8vns_jkvO97XMQT8fkUd51PtGwa6h3CZRNaetCmIxqOX1ejLU79l718HJTLw5Pz3YkMeLzQi2EOzzwcP3AOh0fcOset_8Mx-oH-ivQ8r03EDZJXnNx0BsOjwotggcMlnjsLHnLkGUgcftt6rdDzJ-lp361pOdG2zP0EOLTPPWEBBvjTRDsnN1-Nbrq9L4MxfLvF_3N-mf9s8-VNB346QR77zJmItTG2UFSN8hNxeSg0ii2NKlWPPDxjDrdgnvAIwzxOpijEwvw3a8ZZu2bqNUMJSecXiCWMUmXQPhxtQlr8xsQcz_2eT0MUzhdVioz6nrbVW4uYqXfDVAsZd7VytpUSw039d52t_FtqxJIvpzizrYswcgOqcEUb0bpsFrNwNEg4EbaGv03yP-FWTGUi3NX6kPmRInTd9D6zQ-gvmBDcj3AKjBndFLe3VItctFe5uLVnwykXh4K6xyM-E9FGCHJn9JkAKfxnwHuj4E5MkQ04DbxZLUUM71YrTqX-Wxmzx4HvNtY8bG0elKIpZDVh6jqWF46j33gkfWw7pMBthBXOImB0V4Awo6ixHW-7Lkd8bVuJ-mElbBH16Xa7q0XDTJVQxeI8w4PH4Nq-vsyUieA3evsdrqf-gyeTSOl1TTqlUytGI9OSHvu-TNyZz7BDEQxuA2zznC0VKlLNNVqJQKDPnqNte-wj7KEBGedlEakuGCZCeGKOSQAlPbhovvvbVGbrNPH8mNgQfyTO8JU0JiNlEmd9W5USpSDE2cgeF1cAtAaViBcqNWUQe1KkF7hM15GfYP-FnicY3UEqMBbyceize14BOZ1FDbwP_ODTm4Tqcuc0w6ZzRMrl5Y5GjLwFXfJ23WHk2TdUNqILlAfybMUULIndlj6DuyOPhu1iZ3TTpHLP2m9a6xSGa6r0rLxn6EM89ghHMKCsot-uKBws7fLk0lUjUL9n0CGZQnlJMvw_u2u-vt1c8_X9vTUX-Ea3SbdsevvwSZybtnPUDupHhGrwxJaBv146NgvvKYDEIu8XeaYEZkCJGpHTYlUiEd7ZAUsGidSvlmgIo-MW050H9ONjiJXgLBgOfnK5U_ZKsfTXMOThWx86vON23DWCmRFazVajhXpoFQ15Lpnnapb2QpMMHsEkZ6JZ-Ig37HvlANzHkliOn4WjWTE6tqKpctWsGfX0ipYELkbB9tg8ZMvVasDEf1DRHIKvmvWiPWlWtdnBeeOs0Wk0z9r1dttsV7RnzWrX6vW6gbR6w2zqzfbPivaXwhu1pqGbLbPVMOpGq9Xo_PwbyivY2A)


## Installation

To get started, run the installation script using the following command:

**Via Quick Installer**
Running the command below installs prerequsites and runs the terminal based menu.
```bash
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh \
&& sudo chmod +x stackscript.sh \
&& sudo ./stackscript.sh 
```
The command can also accept passed arguments to skip the menu. **BRANCH** -Selects the target branch of the repo pull from.  **ARG3** is Optional, see below.

```bash
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh \
&& sudo chmod +x stackscript.sh \
&& sudo ./stackscript.sh <BRANCH> <ARG1> <ARG2> <ARG3>
```


### ARG1: Install Options
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

### ARG3: OPTIONAL 
|  |  |
|--|--|
| **dind**: | `Docker in Docker Enviorment Setup`
To start a docker in docker container depoymen, the following commands can be run to deploy the Wiregate container stack in a single container for devopemental purposes.

**Interactive Menu**
```bash
docker run --privileged --name wiregate-dind -d -p 443-446:443-446/udp docker:dind
docker exec -it wiregate-dind /bin/sh
cd .. && cd opt
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh \ 
&&  sudo  chmod +x stackscript.sh \ 
&&  sudo ./stackscript.sh  dind

```
**Preset & Automated**
```bash
docker run --privileged --name wiregate-dind -d -p 443-446:443-446/udp docker:dind
docker exec -it wiregate-dind /bin/sh
cd .. && cd opt
curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh \ 
&&  sudo  chmod +x stackscript.sh \ 
&&  sudo ./stackscript.sh <BRANCH>  <ARG1>  <ARG2>  dind

```


## Usage

### Example Commands

To install with Express, AdGuard, and Darkwire:

```bash
sudo ./install.sh E-A-D Tor-br-webtun
```

### Explanation

- **Install Type**: 
  - ( **E** ) for **Express** 
  - ( **A** ) for **Advanced**
- **DNS Options**: 
  - ( **A** ) for **AdGuard**
  - ( **P** ) for **Pihole**
- **Include Darkwire/Channels**: 
  - ( **D** ) to include **Darkwire** 
  - ( **C** ) to omit **Darkwire** 

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
