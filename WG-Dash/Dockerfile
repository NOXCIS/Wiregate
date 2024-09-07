# Pull from small Debian stable image.
FROM alpine:latest AS builder

LABEL maintainer="dselen@nerthus.nl"

WORKDIR /opt/wireguarddashboard/src

RUN    apk update && \
    apk add --no-cache sudo gcc musl-dev rust cargo linux-headers 

COPY ./src/builder.sh /opt/wireguarddashboard/src/
COPY ./src/builder_requirements.txt /opt/wireguarddashboard/src/
RUN   chmod u+x /opt/wireguarddashboard/src/builder.sh
RUN  /opt/wireguarddashboard/src/builder.sh

FROM --platform=${BUILDPLATFORM} golang:alpine AS pluggables
ARG LYREBIRD_VERSION=0.2.0
RUN apk update \
  && apk upgrade \
  && apk add -U --no-cache \
    bash \
    make \
  && rm -rf /var/cache/apk/*
SHELL ["/bin/bash", "-c"]
RUN <<EOT
  set -ex
  cd /tmp

  # Lyrebird - https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/lyrebird
  wget "https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/lyrebird/-/archive/lyrebird-$LYREBIRD_VERSION/lyrebird-lyrebird-$LYREBIRD_VERSION.tar.gz"
  tar -xvf lyrebird-lyrebird-$LYREBIRD_VERSION.tar.gz
  pushd lyrebird-lyrebird-$LYREBIRD_VERSION || exit 1
  make build -e VERSION=$LYREBIRD_VERSION
  cp ./lyrebird /usr/local/bin
  popd || exit 1

  cp -rv /go/bin /usr/local/bin
  rm -rf /go
  rm -rf /tmp/*
EOT

FROM alpine:latest
WORKDIR /opt/wireguarddashboard/src

COPY ./src /opt/wireguarddashboard/src/
COPY ./src/torrc /etc/tor/
COPY ./src/resolv-tor.conf /etc/tor/
COPY ./src/torrc.d/ /etc/tor/torrc.d/

COPY --from=pluggables /usr/local/bin/lyrebird /usr/local/bin/lyrebird
COPY --from=builder /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=builder /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log/

RUN    apk update && \
    apk add --no-cache wireguard-tools sudo && \
    apk add --no-cache iptables tor dnsmasq && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh 

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]

CMD ["docker_start"]    

STOPSIGNAL SIGTERM
