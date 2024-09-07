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



# Use Alpine Linux as the base image
FROM alpine:latest




# Install necessary packages
RUN apk update && \
    apk add --no-cache tor


# Copy custom Tor configuration if needed
COPY torrc /etc/tor/torrc
COPY ./torrc.d  /etc/tor/
COPY --from=pluggables /usr/local/bin/lyrebird /usr/local/bin/lyrebird




#ENTRYPOINT ["/etc/tor/tor_start.sh"]
CMD [ "tor" ]
