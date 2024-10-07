#!/bin/bash


dockerd &

# Wait for Docker to be ready
while (! docker info > /dev/null 2>&1); do
  sleep 1
done

# Your custom commands here

 curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh 
 sudo chmod +x stackscript.sh  
 sudo ./stackscript.sh terra-firma Tor-br-webtun E-P-D




exec "$@"