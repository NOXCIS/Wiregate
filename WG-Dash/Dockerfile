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
RUN rm -r ./src
WORKDIR /opt/wireguarddashboard/src
COPY ./src/builder.sh ./src/builder_requirements.txt /opt/wireguarddashboard/src/
RUN chmod u+x ./builder.sh && ./builder.sh 


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



# Stage 3: Final image
FROM fedora:rawhide
ENV TZ=UTC
WORKDIR /opt/wireguarddashboard/src
COPY ./src /opt/wireguarddashboard/src/
COPY --from=pluggables /usr/local/bin/lyrebird /webtunnel/main/client/client /snowflake/client/client /usr/local/bin/
COPY --from=builder /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
#COPY --from=builder /opt/wireguarddashboard/src /opt/wireguarddashboard/src
COPY --from=builder /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log/

RUN dnf update -y
#RUN dnf copr enable -y amneziavpn/amneziawg fedora-40-aarch64
# Detect architecture and enable the appropriate Copr repository
RUN ARCH=$(uname -m) && \
    if [[ "$ARCH" == "x86_64" ]]; then \
        dnf copr enable -y amneziavpn/amneziawg fedora-40-x86_64; \
    elif [[ "$ARCH" == "aarch64" ]]; then \
        dnf copr enable -y amneziavpn/amneziawg fedora-40-aarch64; \
    else \
        echo "Unsupported architecture: $ARCH"; \
        exit 1; \
    fi

RUN sudo ln -s /usr/bin/awg /usr/bin/wg
RUN sudo ln -s /usr/bin/awg-quick /usr/bin/wg-quick



RUN dnf install -y tor iptables iproute hostname amneziawg-dkms amneziawg-tools sudo && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh && \
    rm -r /opt/wireguarddashboard/src/static/app/src
    

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
CMD ["docker_start"]

STOPSIGNAL SIGTERM

