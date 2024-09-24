# Stage 1: WG-Dash Builder
FROM --platform=${BUILDPLATFORM} alpine:latest AS builder
LABEL maintainer="NOXCIS"

WORKDIR /opt/wireguarddashboard/src

RUN apk add --no-cache sudo gcc musl-dev rust cargo linux-headers npm

COPY ./src/builder.sh ./src/builder_requirements.txt /opt/wireguarddashboard/src/

RUN chmod u+x ./builder.sh && ./builder.sh 


# Stage 1.1: WG-Dash Node Builder
FROM --platform=${BUILDPLATFORM} alpine:latest AS node_builder
LABEL maintainer="NOXCIS"

WORKDIR /opt/wireguarddashboard/src/static/app

RUN apk add --no-cache npm

COPY ./src/static  /opt/wireguarddashboard/src/static
RUN npm audit fix
RUN npm install
RUN npm run build







# Stage 2: Tor Pluggables 
FROM --platform=${BUILDPLATFORM} golang:alpine3.20 AS pluggables
ARG LYREBIRD_VERSION=0.2.0

RUN apk add -U --no-cache bash make

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
    rm -rf /go /tmp/*




# Stage 3: Final image
FROM alpine:latest
WORKDIR /opt/wireguarddashboard/src

COPY ./src /opt/wireguarddashboard/src/
COPY ./src/tor/ /etc/tor/
COPY --from=pluggables /usr/local/bin/lyrebird /usr/local/bin/lyrebird
COPY --from=builder /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=builder /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log/
COPY --from=node_builder /opt/wireguarddashboard/src/static/app/dist /opt/wireguarddashboard/src/static/app/dist

RUN apk add --no-cache wireguard-tools sudo iptables tor && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh 

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
CMD ["docker_start"]

STOPSIGNAL SIGTERM

