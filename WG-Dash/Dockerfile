FROM alpine:latest

WORKDIR /home/app 
RUN apk update && \
    apk add --no-cache python3 py3-pip openssl nginx uwsgi-python3 && \
    apk add --no-cache build-base wireguard-tools iproute2 iptables ip6tables && \ 
    apk add --no-cache net-tools procps openresolv && \
    apk add --no-cache inotify-tools linux-headers libc-dev pcre-dev && \
    apk add --no-cache libffi-dev zlib-dev openssl-dev && \
    rm -rf /var/cache/apk/* && \
    mkdir /home/app/master-key 
    
COPY ./src /home/app


RUN pip install --upgrade pip --no-cache-dir --break-system-packages  && \   
    python3 -m pip install -r /home/app/requirements.txt --no-cache-dir --break-system-packages && \
    chmod u+x /home/app/entrypoint.sh 

ENTRYPOINT ["/home/app/entrypoint.sh"]



