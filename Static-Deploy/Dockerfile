# node: FRONTEND - Vite Builder 
FROM --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
WORKDIR /static/app
COPY ./build_scripts/static /static
RUN npm update 
RUN npm ci && npm run build          


# builder: WGDashboard & Vanguards Python Binary Build stage
FROM python:alpine AS builder
# Receive the target platform. Buildx passes this automatically.
ARG TARGETPLATFORM
# Specify the desired Go version.
ARG GO_VERSION=1.23.6

# Install required packages.
# Note: Removed "go" from the list so we can install a newer version manually.
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
    wget

# Set GO_ARCH based on TARGETPLATFORM so we download the correct binary.
RUN set -eux; \
    case "${TARGETPLATFORM}" in \
        "linux/amd64") GO_ARCH="amd64" ;; \
        "linux/arm64") GO_ARCH="arm64" ;; \
        "linux/arm/v6" | "linux/arm/v7") GO_ARCH="armv6l" ;; \
        *) echo "unsupported platform: ${TARGETPLATFORM}" && exit 1 ;; \
    esac; \
    echo "Downloading Go ${GO_VERSION} for ${GO_ARCH}"; \
    wget https://golang.org/dl/go${GO_VERSION}.linux-${GO_ARCH}.tar.gz; \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-${GO_ARCH}.tar.gz; \
    rm go${GO_VERSION}.linux-${GO_ARCH}.tar.gz

# Prepend the new Go binary to PATH.
ENV PATH="/usr/local/go/bin:${PATH}"

WORKDIR /build

# Create directories for each Go program
RUN mkdir -p /build/torflux-build /build/traffic_weir

# Copy files into their respective directories
COPY ./build_scripts/torflux/torflux.go /build/torflux-build/
COPY ./build_scripts/torflux/go.mod /build/torflux-build/
COPY ./build_scripts/traffic_weir/traffic-weir.go /build/traffic_weir/
COPY ./build_scripts/traffic_weir/go.mod /build/traffic_weir/
COPY ./build_scripts/wiregate /build/wiregate/
COPY ./build_scripts/wiregate.py .
COPY ./build_scripts/requirements.txt .
COPY ./build_scripts/vanguards /build/vanguards/
COPY ./build_scripts/vanguards.py .

# Set up a virtual environment and install dependencies
RUN     python3 -m venv venv \
        && venv/bin/pip install --upgrade pip \
        && venv/bin/pip install -r requirements.txt

# Use PyInstaller to create a standalone binary with UPX compression
RUN     venv/bin/pip install pyinstaller && \
        venv/bin/pyinstaller --clean --onefile --upx-dir=/usr/bin --name wiregate wiregate.py && \
        venv/bin/pyinstaller --clean --onefile --strip --upx-dir=/usr/bin --name vanguards vanguards.py 

# Build each program from its directory
RUN cd /build/torflux-build && \
    go build -buildmode=pie -ldflags="-X main.version=v1.0.0 -s -w" -o /build/torflux

RUN cd /build/traffic_weir && \
    go build -buildmode=pie -ldflags="-X main.version=v1.0.0 -s -w" -o /build/traffic-weir


# Stage 3: Final image
FROM alpine:latest
LABEL maintainer="NOXCIS"
WORKDIR /WireGate
ENV TZ=UTC
ENV WGD_CONF_PATH="/etc/wireguard"
COPY ./src /WireGate/

# Install necessary tools and libraries in the final image
RUN apk add --no-cache wireguard-tools iptables ip6tables tzdata sudo && \
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
COPY --from=builder /build/dist/wiregate /WireGate/wiregate
COPY --from=builder /build/dist/vanguards /WireGate/vanguards
COPY --from=builder /build/torflux /WireGate/torflux
COPY --from=builder /build/traffic-weir /WireGate/traffic-weir

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep dashboard > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM

