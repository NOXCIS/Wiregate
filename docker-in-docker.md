docker run --privileged --name hellpine -d -p 443-448:443-448/udp  docker:dind

enter container and run 

apk add git curl bash sudo ncurses

curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && sudo chmod +x stackscript.sh  && sudo ./stackscript.sh terra-firma Tor-br-obfs4 E-P-C dind