FROM alpine:latest

RUN apk update && apk add --no-cache python3 py3-pip python3-dev build-base wireguard-tools iproute2 iptables nano net-tools py3-virtualenv procps openresolv inotify-tools linux-headers libc-dev pcre-dev 
    
RUN rm -rf /var/cache/apk/*

RUN mkdir /home/app 

RUN mkdir /home/app/master-key

COPY ./src /home/app 

RUN python3 -m pip install -U pip 
                
RUN python3 -m pip install -U -r /home/app/requirements.txt 

COPY ./entrypoint.sh /home/app/entrypoint.sh

RUN chmod u+x /home/app/entrypoint.sh

ENTRYPOINT ["/home/app/entrypoint.sh"]

WORKDIR /home/app 

