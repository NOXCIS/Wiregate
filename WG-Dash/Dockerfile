# pluggables: Tor Transport Plugin Binary Builder
FROM  golang:alpine3.20 AS pluggables
ARG LYREBIRD_VERSION=0.2.0
WORKDIR /

RUN apk add -U --no-cache bash make git

SHELL ["/bin/bash", "-c"]
RUN set -ex && cd /tmp && \
    wget "https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/lyrebird/-/archive/lyrebird-${LYREBIRD_VERSION}/lyrebird-lyrebird-${LYREBIRD_VERSION}.tar.gz" && \
    tar -xvf lyrebird-lyrebird-${LYREBIRD_VERSION}.tar.gz && \
    pushd lyrebird-lyrebird-${LYREBIRD_VERSION} && \
    go get -u ./... && \
    go mod tidy && \
    make build -e VERSION=${LYREBIRD_VERSION} && \
    cp ./lyrebird /usr/local/bin && \
    popd && \
    rm -rf /go /tmp/* && \
    echo "DONE LYREBIRD AKA OBFS4" 
RUN git clone https://git.torproject.org/pluggable-transports/snowflake.git \
    && cd snowflake/client \
    && CGO_ENABLED=0 go build -a -installsuffix cgo \
    && echo "DONE SNOWFLAKE"
RUN git clone https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/webtunnel.git \
    && cd webtunnel/main/client \
    && CGO_ENABLED=0 go build -a -installsuffix cgo \
    && echo "DONE WEBTUNNEL" 


# builder: Vite Frontend Builder 
FROM  --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS builder
WORKDIR /opt/wireguarddashboard/src/static/app
COPY ./src/static /opt/wireguarddashboard/src/static 
RUN npm install                    
RUN npm update                    
RUN npm run build                 
RUN rm -r ./node_modules 


# pybuild: WG-Dash Builder for Brcypt & Psutil Binary (Python)
FROM  alpine:latest AS pybuild
RUN apk add --no-cache sudo gcc musl-dev rust cargo linux-headers
WORKDIR /opt/wireguarddashboard/src
COPY ./src/builder.sh ./src/builder_requirements.txt /opt/wireguarddashboard/src/
RUN chmod u+x ./builder.sh && ./builder.sh 


# awg: BUILD AmneziaWG (Obfuscated Wireguard) 
FROM  golang:alpine3.20 AS awg
WORKDIR /go
RUN apk update && apk add --no-cache git make bash build-base linux-headers
RUN git clone --depth=1 https://github.com/amnezia-vpn/amneziawg-tools.git && \
    git clone --depth=1 https://github.com/amnezia-vpn/amneziawg-go.git
RUN cd /go/amneziawg-tools/src && make
RUN cd /go/amneziawg-go && \
    go get -u ./... && \
    go mod tidy && \
    make


# Stage 3: Final image
FROM alpine:latest
LABEL maintainer="NOXCIS"
ENV TZ=UTC
WORKDIR /opt/wireguarddashboard/src

COPY ./src /opt/wireguarddashboard/src/

#Tor Client Transport Plugins
COPY --from=pluggables /usr/local/bin/lyrebird /webtunnel/main/client/client /snowflake/client/client /usr/local/bin/

#Copy Built Bcrypt & Psutil Binarys
COPY --from=pybuild /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=pybuild /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log

#Copy Built Frontend  
COPY --from=builder /opt/wireguarddashboard/src /opt/wireguarddashboard/src


#AmneziaWG Substitute install for WireGuard
COPY --from=awg /go/amneziawg-go/amneziawg-go /usr/bin/amneziawg-go
COPY --from=awg /go/amneziawg-tools/src/wg /usr/bin/awg
COPY --from=awg /go/amneziawg-tools/src/wg-quick/linux.bash /usr/bin/awg-quick

#AmneziaWG Symbolic Links to (wg & wg-quick) Commands
#RUN ln -s /usr/bin/awg /usr/bin/wg
#RUN ln -s /usr/bin/awg-quick /usr/bin/wg-quick


#Entrypoint
RUN apk add --no-cache wireguard-tools bash sudo iptables tzdata && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh && \
    rm -r /opt/wireguarddashboard/src/static/app/src


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
#CMD ["docker_start"]

STOPSIGNAL SIGTERM
