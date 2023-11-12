FROM alpine:latest

RUN apk update && \
    apk add --no-cache python3 py3-pip python3-dev openssl && \
    apk add --no-cache build-base wireguard-tools iproute2 iptables && \ 
    apk add --no-cache nano net-tools procps openresolv && \
    apk add --no-cache inotify-tools linux-headers libc-dev pcre-dev && \
    apk add --no-cache libffi-dev zlib-dev jpeg-dev openssl-dev curl  && \
    rm -rf /var/cache/apk/* && \
    mkdir /home/app && \
    mkdir /home/app/master-key 
    
COPY ./src /home/app 

RUN pip install --upgrade pip   && \    
    python3 -m pip install -r /home/app/requirements.txt 


COPY ./entrypoint.sh /home/app/entrypoint.sh
RUN chmod u+x /home/app/entrypoint.sh
ENTRYPOINT ["/home/app/entrypoint.sh"]

WORKDIR /home/app 

