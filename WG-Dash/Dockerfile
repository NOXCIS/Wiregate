FROM alpine:latest

RUN apk update && \
    apk add --no-cache python3 py3-pip python3-dev openssl nginx && \
    apk add --no-cache build-base wireguard-tools iproute2 iptables ip6tables uwsgi-python3 && \ 
    apk add --no-cache net-tools procps openresolv && \
    apk add --no-cache inotify-tools linux-headers libc-dev pcre-dev && \
    apk add --no-cache libffi-dev zlib-dev jpeg-dev openssl-dev curl  && \
    rm -rf /var/cache/apk/* && \
    mkdir /home/app && \
    mkdir /home/app/master-key 
    
COPY ./src /home/app 

RUN pip install --upgrade pip --break-system-packages     
RUN  python3 -m pip install -r /home/app/requirements.txt --break-system-packages  


COPY ./entrypoint.sh /home/app/entrypoint.sh
RUN chmod u+x /home/app/entrypoint.sh
ENTRYPOINT ["/home/app/entrypoint.sh"]

WORKDIR /home/app 

