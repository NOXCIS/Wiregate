# node: FRONTEND - Vite Builder 
FROM --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
WORKDIR /static/app
COPY ./Src/static /static
RUN npm update 
RUN npm ci && npm run build          


# builder: WGDashboard & Vanguards Python Binary Build stage
FROM alpine:latest AS builder

ARG TARGETPLATFORM
ARG GO_VERSION=1.24.0
RUN apk add --no-cache \
    wget \
    gcc \
    musl-dev

# Set GO_ARCH based on TARGETPLATFORM so we download the correct binary.
RUN set -eux; \
    case "${TARGETPLATFORM}" in \
        "linux/amd64") GO_ARCH="amd64" ;; \
        "linux/arm64") GO_ARCH="arm64" ;; \
        "linux/arm/v6" | "linux/arm/v7") GO_ARCH="armv6l" ;; \
        *) echo "unsupported platform: ${TARGETPLATFORM}" && exit 1 ;; \
    esac; \
    echo "Downloading Go ${GO_VERSION} for ${GO_ARCH}"; \
    wget -q https://golang.org/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz; \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-${GO_ARCH}.tar.gz; \
    rm go${GO_VERSION}.linux-${GO_ARCH}.tar.gz

# Prepend the new Go binary to PATH.
ENV PATH="/usr/local/go/bin:${PATH}"

WORKDIR /build

# Create directories for each Go program
RUN mkdir -p /build/torflux-build /build/traffic_weir

# Copy files into their respective directories
COPY ./Src/torflux/torflux.go /build/torflux-build/
COPY ./Src/torflux/go.mod /build/torflux-build/
COPY ./Src/traffic_weir/traffic-weir.go /build/traffic_weir/
COPY ./Src/traffic_weir/pf_helper.go /build/traffic_weir/
COPY ./Src/traffic_weir/go.mod /build/traffic_weir/


# Build each program from its directory
RUN cd /build/torflux-build && \
    GOOS=linux GOARCH=$GO_ARCH CGO_ENABLED=0 go build \
    -ldflags="-X main.version=v1.0.0 -s -w" \
    -o /build/torflux

RUN cd /build/traffic_weir && \
    GOOS=linux GOARCH=$GO_ARCH CGO_ENABLED=0 go build \
    -ldflags="-X main.version=v1.0.0 -s -w" \
    -o /build/traffic-weir



FROM python:alpine AS pybuilder
WORKDIR /build

COPY ./Src/wiregate /build/wiregate/
COPY ./Src/wiregate.py .
COPY ./Src/requirements.txt .
COPY ./Src/vanguards /build/vanguards/
COPY ./Src/vanguards.py .

RUN apk add --no-cache \
    py3-virtualenv \
    py3-pip \
    musl-dev \
    build-base \
    zlib-dev \
    libffi-dev \
    openssl-dev \
    linux-headers \
    rust \
    cargo \
    upx \
    wget \
    openldap-dev \
    ccache

# Set up a virtual environment and install dependencies
RUN     python3 -m venv venv \
        && venv/bin/pip install --upgrade pip \
        && venv/bin/pip install -r requirements.txt

# Use PyInstaller to create standalone binaries with UPX compression
RUN    venv/bin/pyinstaller \
            --onefile \
            --clean \
            --hidden-import=gunicorn.glogging \
            --hidden-import=gunicorn.workers.sync \
            --hidden-import=gunicorn.workers.gthread \
            --distpath=/build/dist \
            --name=wiregate \
            wiregate.py && \
        venv/bin/pyinstaller \
            --onefile \
            --clean \
            --distpath=/build/dist \
            --name=vanguards \
            vanguards.py



# Stage 3: Final image
FROM alpine:latest
LABEL maintainer="NOXCIS"
WORKDIR /WireGate
ENV TZ=UTC
ENV WGD_CONF_PATH="/etc/wireguard"
COPY ./Src/iptable-rules /WireGate/iptable-rules
COPY ./Src/wiregate.sh /WireGate/wiregate.sh
COPY ./Src/db/wsgi.ini /WireGate/db/wsgi.ini
COPY ./Src/entrypoint.sh /WireGate/entrypoint.sh    
COPY ./Src/dnscrypt /WireGate/dnscrypt


# Install necessary tools and libraries in the final image
RUN apk add --no-cache wireguard-tools iptables ip6tables tzdata sudo tor curl && \
    apk upgrade && \
    apk cache clean && \
    chmod +x /WireGate/wiregate.sh && chmod +x /WireGate/entrypoint.sh &&\
    rm -rf /tmp/* /var/tmp/* && \
    rm -rf /var/cache/apk/* && \
    rm -rf /build /root/.cache /tmp/* /var/tmp/*



# Copy only the build output from the build-stage
COPY --from=node /static/app/dist /WireGate/static/app/dist
COPY --from=node /static/app/index.html /WireGate/static/app/index.html
COPY --from=node /static/app/public /WireGate/static/app/public
COPY --from=node /static/locale /WireGate/static/locale



# Copy Tor Client Transport Plugin binaries
#   Tor Client Transport Plugins
#   UPSTREAM DOCKER GO COMPILE BUILD PIPELINE 
#   https://github.com/NOXCIS/Docker-Tor-Transports/blob/main/Dockerfile 
#   FOR TOR REPOS ~2hrs AHEAD DAILY UTC
COPY --from=noxcis/tor-bins:latest /lyrebird /usr/local/bin/obfs4
COPY --from=noxcis/tor-bins:latest /webtunnel /usr/local/bin/webtunnel
COPY --from=noxcis/tor-bins:latest /snowflake /usr/local/bin/snowflake

# Copy AmneziaWG binaries
#   AmneziaWG install 
#   UPSTREAM DOCKER GO COMPILE BUILD PIPELINE
#   https://github.com/NOXCIS/Docker-AmneziaWG-GO/blob/main/Dockerfile
#   FOR AMNEZIAWG REPOS ~1hrs AHEAD DAILY UTC
COPY --from=noxcis/awg-bins:latest /amneziawg-go /usr/bin/amneziawg-go
COPY --from=noxcis/awg-bins:latest /awg /usr/bin/awg
COPY --from=noxcis/awg-bins:latest /awg-quick /usr/bin/awg-quick

# Copy WG-Dash & Tor Vanguards binaries
COPY --from=pybuilder /build/dist/wiregate /WireGate/wiregate
COPY --from=pybuilder /build/dist/vanguards /WireGate/vanguards
COPY --from=builder /build/torflux /WireGate/torflux
COPY --from=builder /build/traffic-weir /WireGate/traffic-weir

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep wiregate > /dev/null && \
    PORT=$(netstat -tulpn 2>/dev/null | grep wiregate | head -n1 | awk "{print \$4}" | cut -d: -f2) && \
    [ -n "$PORT" ] && \
    (curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200\|301\|302\|307\|308") || exit 1'

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM

