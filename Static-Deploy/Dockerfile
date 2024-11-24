# node: FRONTEND - Vite Builder 
FROM --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
WORKDIR /static/app
COPY ./build_scripts/static /static
RUN npm ci && npm run build          


# builder: WGDashboard & Vanguards Python Binary Build stage
FROM python:alpine AS builder
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
    go 

WORKDIR /build

# Copy application code and dependencies
COPY ./build_scripts/torflux.go .
COPY ./build_scripts/go.mod .
COPY ./build_scripts/dashboard.py .
COPY ./build_scripts/requirements.txt .
COPY ./build_scripts/vanguards /build/vanguards/
COPY ./build_scripts/vanguards.py .

# Set up a virtual environment and install dependencies
RUN     python3 -m venv venv \
        && venv/bin/pip install --upgrade pip \
        && venv/bin/pip install -r requirements.txt

# Use PyInstaller to create a standalone binary with UPX compression
RUN     venv/bin/pip install pyinstaller && \
        venv/bin/pyinstaller --onefile --upx-dir=/usr/bin --name dashboard dashboard.py && \
        venv/bin/pyinstaller --onefile --strip --upx-dir=/usr/bin --name vanguards vanguards.py 

RUN     go build -buildmode=pie -ldflags="-s -w" -o torflux

# Stage 3: Final image
FROM noxcis/hellpine:latest
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
#   AmneziaWG Substitute install for WireGuard
#   UPSTREAM DOCKER GO COMPILE BUILD PIPELINE
#   https://github.com/NOXCIS/Docker-AmneziaWG-GO/blob/main/Dockerfile
#   FOR AMNEZIAWG REPOS ~1hrs AHEAD DAILY UTC
COPY --from=noxcis/awg-bins:latest /amneziawg-go /usr/bin/amneziawg-go
COPY --from=noxcis/awg-bins:latest /awg /usr/bin/awg
COPY --from=noxcis/awg-bins:latest /awg-quick /usr/bin/awg-quick

# Copy WG-Dash & Tor Vanguards binaries
COPY --from=builder /build/dist/dashboard /WireGate/dashboard
COPY --from=builder /build/dist/vanguards /WireGate/vanguards
COPY --from=builder /build/torflux /WireGate/torflux


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep dashboard > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM

