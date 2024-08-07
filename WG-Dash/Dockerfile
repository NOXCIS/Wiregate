FROM alpine:latest

WORKDIR /home/app 
RUN    apk update && \
    apk add --no-cache py3-bcrypt py3-psutil && \
    apk add --no-cache wireguard-tools && \
    apk add --no-cache net-tools iproute2 iptables ip6tables  && \
    apk add --no-cache inotify-tools procps openresolv  && \
    mkdir /home/app/master-key 
    
COPY ./src /home/app
RUN    chmod u+x /home/app/entrypoint.sh 

ENTRYPOINT ["/home/app/entrypoint.sh"]






