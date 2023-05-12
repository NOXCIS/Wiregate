FROM ubuntu:20.04


RUN apt-get update && \
apt-get install -y --no-install-recommends  iproute2 wireguard-tools wireguard iptables nano net-tools python3 python3-pip python3-venv procps openresolv inotify-tools && \
apt-get clean


RUN mkdir /home/app 
COPY ./src /home/app 

RUN pip3 install -r /home/app/requirements.txt   --no-cache-dir
COPY ./entrypoint.sh /home/app/entrypoint.sh
RUN chmod u+x /home/app/entrypoint.sh

ENTRYPOINT ["/home/app/entrypoint.sh"]
WORKDIR /home/app 

EXPOSE 10086
EXPOSE 51820/udp
