### Via Docker In Docker

  

**Interactive Menu**

```bash

docker  run  --privileged  --name  wiregate-dind  -d  -p  4430-4433:4430-4433/udp  docker:dind && \

docker  exec  -it  wiregate-dind  /bin/sh  -c  "

  

apk add curl git ncurses sudo bash && \

mkdir -p /opt && cd /opt && \

curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \

chmod +x stackscript.sh && \

./stackscript.sh -d dind

"

```

**Preset & Automated**

```bash

docker  run  --privileged  --name  wiregate-dind  -d  -p  4430-4433:4430-4433/udp  docker:dind && \

docker  exec  -it  wiregate-dind  /bin/sh  -c  "

  

apk add curl git ncurses sudo bash && \

mkdir -p /opt && cd /opt && \

curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh && \

chmod +x stackscript.sh && \

./stackscript.sh [-b branch] [-r arg1] [-t arg2] [-n arg3] -d dind

"

```

Example Usage:

```bash

./stackscript.sh  -b  main  -r  E-P-D  -t  Tor-br-snow  -n  {CH},{GB}  -d  dind

```

The available options are:

  

-  `-b` for specifying a branch.

-  `-r` for specifying Resolvers

-  `-t` for specifying Tor.

-  `-n` for specifying Exit Node.

-  `-d` for specifying Docker in Docker.

  
  
  
  