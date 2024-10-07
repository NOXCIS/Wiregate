docker run --privileged --name hellpine -d -p 443-446:443-446/udp  docker:dind




docker run --privileged --name hellpine --restart unless-stopped -d -p 443-446:443-446/udp docker:dind

enter container and run 

apk add git curl bash sudo ncurses

 curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && sudo chmod +x stackscript.sh  && sudo ./stackscript.sh terra-firma  E-P-C Tor-obfs4 dind