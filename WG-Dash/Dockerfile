FROM alpine:latest

RUN apk update && \
    apk add --no-cache python3 py3-pip python3-dev && \
    apk add --no-cache build-base wireguard-tools iproute2 iptables && \ 
    apk add --no-cache nano net-tools py3-virtualenv procps openresolv && \
    apk add --no-cache inotify-tools linux-headers libc-dev pcre-dev
    
RUN rm -rf /var/cache/apk/*

RUN mkdir /home/app 

COPY ./src /home/app 

COPY ./entrypoint.sh /home/app/entrypoint.sh

RUN chmod u+x /home/app/entrypoint.sh

ENTRYPOINT ["/home/app/entrypoint.sh"]

WORKDIR /home/app 

