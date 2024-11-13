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
    gcc \
    musl-dev \
    zlib-dev \
    libffi-dev \
    openssl-dev \
    linux-headers \
    rust \
    cargo \
    upx 
WORKDIR /build

# Copy application code and dependencies
COPY ./build_scripts/dashboard.py .
COPY ./build_scripts/requirements.txt .
COPY ./build_scripts/vanguards /build/vanguards/
COPY ./build_scripts/vanguards.py .

# Set up a virtual environment and install dependencies
RUN python3 -m venv venv \
    && venv/bin/pip install --upgrade pip \
    && venv/bin/pip install -r requirements.txt

# Use PyInstaller to create a standalone binary with UPX compression
RUN venv/bin/pip install pyinstaller && \
    venv/bin/pyinstaller --onefile --upx-dir=/usr/bin --name dashboard dashboard.py && \
    venv/bin/pyinstaller --onefile --strip --upx-dir=/usr/bin --name vanguards vanguards.py && \
    upx --best --lzma /build/dist/vanguards


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
    rm -rf /tmp/* /var/tmp/*



# Copy only the build output from the build-stage
COPY --from=node /static/app/dist /WireGate/static/app/dist
COPY --from=node /static/app/index.html /WireGate/static/app/index.html
COPY --from=node /static/app/public /WireGate/static/app/public
COPY --from=node /static/locale /WireGate/static/locale

# Copy Tor Client Transport Plugin binaries
COPY --from=noxcis/tor-bins:latest /lyrebird /usr/local/bin/obfs4
COPY --from=noxcis/tor-bins:latest /webtunnel /usr/local/bin/webtunnel
COPY --from=noxcis/tor-bins:latest /snowflake /usr/local/bin/snowflake

# Copy AmneziaWG binaries
COPY --from=noxcis/awg-bins:latest /amneziawg-go /usr/bin/amneziawg-go
COPY --from=noxcis/awg-bins:latest /awg /usr/bin/awg
COPY --from=noxcis/awg-bins:latest /awg-quick /usr/bin/awg-quick

# Copy WG-Dash & Tor Vanguards binaries
COPY --from=builder /build/dist/dashboard /WireGate/dashboard
COPY --from=builder /build/dist/vanguards /WireGate/vanguards

# Set executable permissions
RUN chmod +x /WireGate/wiregate.sh && chmod +x /WireGate/entrypoint.sh

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM

