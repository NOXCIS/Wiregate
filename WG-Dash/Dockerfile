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
    echo "DONE LYREBIRD" 

RUN git clone https://git.torproject.org/pluggable-transports/snowflake.git \
    && cd snowflake/client \
    && go build \
    && echo "DONE SNOWFLAKE"

RUN git clone https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/webtunnel.git \
    && cd webtunnel/main/client \
    && go build \
    && echo "DONE WEBTUNNEL" 


# builder: WG-Dash Builder for Brcypt & Psutil Binary
FROM  node:iron-alpine3.20 AS builder
LABEL maintainer="NOXCIS"
RUN apk add --no-cache sudo gcc musl-dev rust cargo linux-headers
WORKDIR /opt/wireguarddashboard/src/static/app
COPY ./src/static /opt/wireguarddashboard/src/static 
RUN npm install                    
RUN npm update                    
RUN npm run build                 
RUN rm -r ./node_modules 
WORKDIR /opt/wireguarddashboard/src
COPY ./src/builder.sh ./src/builder_requirements.txt /opt/wireguarddashboard/src/
RUN chmod u+x ./builder.sh && ./builder.sh 






# Stage 3: Final image
FROM alpine:latest
ENV TZ=UTC
WORKDIR /opt/wireguarddashboard/src
COPY ./src /opt/wireguarddashboard/src/
COPY --from=pluggables /usr/local/bin/lyrebird /webtunnel/main/client/client /snowflake/client/client /usr/local/bin/
COPY --from=builder /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=builder /opt/wireguarddashboard/src /opt/wireguarddashboard/src
COPY --from=amneziavpn/amnezia-wg:latest --chmod=755 /usr/bin/wireguard-go /usr/bin/wireguard-go
COPY --from=amneziavpn/amnezia-wg:latest --chmod=755 /usr/bin/wg-quick /usr/bin/wg-quick
COPY --from=amneziavpn/amnezia-wg:latest --chmod=755 /usr/bin/wg /usr/bin/wg
RUN apk add --no-cache bash sudo iptables tzdata && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh && \
    rm -r /opt/wireguarddashboard/src/static/app/src

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
CMD ["docker_start"]

STOPSIGNAL SIGTERM
