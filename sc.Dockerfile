# node: FRONTEND - Vite + Vue3 Builder with pnpm (Enhanced Security)
##########################################################
FROM --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
WORKDIR /static/app

# Install pnpm globally for enhanced security
RUN npm install -g pnpm

COPY ./Src/static /static

# Use pnpm for secure package management
ENV CI=true
RUN pnpm install --frozen-lockfile
RUN pnpm run build  



# minimal-base: Minimal base image built from scratch (BusyBox-free)
##########################################################
FROM alpine:latest AS utils_extractor

# Install coreutils to get standalone GNU utilities (not BusyBox)
RUN apk add --no-cache coreutils findutils gawk util-linux grep sed

FROM scratch AS minimal-base

# Copy standalone GNU utilities (non-BusyBox alternatives)
COPY --from=utils_extractor \
    /bin/mkdir \
    /bin/chmod \
    /bin/chown \
    /bin/cp \
    /bin/mv \
    /bin/rm \
    /bin/ln \
    /bin/ls \
    /bin/cat \
    /bin/echo \
    /bin/grep \
    /bin/sed \
    /bin/

COPY --from=utils_extractor \
    /usr/bin/gawk \
    /usr/bin/awk

COPY --from=utils_extractor \
    /usr/bin/cut \
    /usr/bin/head \
    /usr/bin/tail \
    /usr/bin/sort \
    /usr/bin/uniq \
    /usr/bin/wc \
    /usr/bin/find \
    /usr/bin/id \
    /usr/bin/whoami \
    /usr/bin/test \
    /bin/

COPY --from=utils_extractor \
    /bin/mknod \
    /sbin/mknod

# Copy essential Alpine binaries (shell and basic tools)
COPY --from=alpine:latest /bin/sh /bin/sh
COPY --from=alpine:latest /lib/ld-musl-*.so.1 /lib/
COPY --from=alpine:latest /lib/libc.musl-*.so.1 /lib/

COPY --from=alpine:latest \
    /usr/lib/libz.so.1 \
    /usr/lib/libssl.so.3 \
    /usr/lib/libcrypto.so.3 \
    /usr/lib/

# Copy additional required libraries for GNU utilities
COPY --from=utils_extractor \
    /usr/lib/libpcre2-8.so.0 \
    /usr/lib/libacl.so.1 \
    /usr/lib/libattr.so.1 \
    /usr/lib/libutmps.so.0.1 \
    /usr/lib/libskarnet.so.2.14 \
    /usr/lib/

# Create essential system files from scratch
RUN /bin/echo "root:x:0:0:root:/root:/bin/sh" > /etc/passwd && \
    /bin/echo "root:x:0:" > /etc/group && \
    /bin/echo "root:*:0:0:99999:7:::" > /etc/shadow && \
    /bin/echo "tor:x:1000:1000:tor:/var/lib/tor:/bin/false" >> /etc/passwd && \
    /bin/echo "tor:x:1000:" >> /etc/group

# Create essential directories and files
RUN /bin/mkdir -p /tmp /var /var/tmp /var/log /var/lib /etc /dev /proc /sys /run && \
    /bin/chmod 1777 /tmp /var/tmp && \
    /bin/chmod 755 /etc



# base_cve_patch: Security-hardened minimal base (BusyBox-free)
##########################################################
FROM minimal-base AS base_cve_patch

# Create essential device files (only if they don't exist)
RUN [ ! -e /dev/null ] && /sbin/mknod /dev/null c 1 3 || true && \
    [ ! -e /dev/zero ] && /sbin/mknod /dev/zero c 1 5 || true && \
    [ ! -e /dev/random ] && /sbin/mknod /dev/random c 1 8 || true && \
    [ ! -e /dev/urandom ] && /sbin/mknod /dev/urandom c 1 9 || true && \
    /bin/chmod 666 /dev/null /dev/zero /dev/random /dev/urandom

# Set proper permissions
RUN /bin/chmod 755 /bin/sh



# binary-builder-deps: Base Image with Python dependencies (RAPID DEVELOPMENT)
##########################################################
FROM python:alpine AS base_dependencies

WORKDIR /build

COPY ./Src/requirements.txt .

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

RUN python3 -m venv venv \
    && venv/bin/pip install --upgrade pip \
    && venv/bin/pip install -r requirements.txt



# builder: WGDashboard & Vanguards Python Binary Build stage
##########################################################
FROM alpine:latest AS builder
ARG TARGETPLATFORM
ARG GO_VERSION=1.24.6

RUN apk add --no-cache \
    wget \
    gcc \
    musl-dev

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

ENV PATH="/usr/local/go/bin:${PATH}"

WORKDIR /build

RUN mkdir -p /build/torflux-build /build/traffic_weir

COPY ./Src/torflux/torflux.go /build/torflux-build/
COPY ./Src/torflux/go.mod /build/torflux-build/
COPY ./Src/traffic_weir/traffic-weir.go /build/traffic_weir/
COPY ./Src/traffic_weir/go.mod /build/traffic_weir/

RUN cd /build/torflux-build && \
    GOOS=linux GOARCH=$GO_ARCH CGO_ENABLED=0 go build \
    -ldflags="-X main.version=v1.0.0 -s -w" \
    -o /build/torflux

RUN cd /build/traffic_weir && \
    GOOS=linux GOARCH=$GO_ARCH CGO_ENABLED=0 go build \
    -ldflags="-X main.version=v1.0.0 -s -w" \
    -o /build/traffic-weir



# pybuilder: Python binary builder
##########################################################
FROM base_dependencies AS pybuilder
WORKDIR /build

# Copy ALL source files together (like the working Dockerfile)
COPY ./Src/wiregate /build/wiregate/
COPY ./Src/wiregate.py .
COPY ./Src/vanguards /build/vanguards/
COPY ./Src/vanguards.py .

# Use PyInstaller to create standalone binaries with UPX compression
RUN venv/bin/pyinstaller \
        --onefile \
        --clean \
        --distpath=/build/dist \
        --name=wiregate \
        wiregate.py && \
    venv/bin/pyinstaller \
        --onefile \
        --clean \
        --distpath=/build/dist \
        --name=vanguards \
        vanguards.py



# runtime-deps: Prepare runtime dependencies
##########################################################
FROM alpine:latest AS runtime-deps

# Install and extract only the runtime packages we need
RUN apk add --no-cache \
    wireguard-tools \
    iptables \
    ip6tables \
    tzdata \
    sudo \
    tor \
    curl \
    ca-certificates \
    net-tools \
    bash \
    util-linux \
    procps

# Create a directory to copy essential runtime files
RUN mkdir -p /runtime-files/bin /runtime-files/sbin /runtime-files/usr/bin /runtime-files/usr/sbin \
             /runtime-files/lib /runtime-files/usr/lib /runtime-files/etc /runtime-files/usr/share



# Final stage: Minimal WireGate container
##########################################################
FROM base_cve_patch AS final

LABEL maintainer="NOXCIS"

# Set environment variables
ENV TZ=UTC
ENV WGD_CONF_PATH="/etc/wireguard"

# Create necessary directories
RUN mkdir -p /WireGate /etc/wireguard /var/lib/tor /var/log/tor /proc /sys /dev/pts

WORKDIR /WireGate

# Copy essential runtime binaries and libraries from runtime-deps
COPY --from=runtime-deps \
    /usr/bin/wg \
    /usr/bin/wg-quick \
    /usr/bin/sudo \
    /usr/bin/tor \
    /usr/bin/curl \
    /usr/bin/

COPY --from=runtime-deps \
    /usr/sbin/iptables \
    /usr/sbin/ip6tables \
    /usr/sbin/iptables-restore \
    /usr/sbin/ip6tables-restore \
    /sbin/

COPY --from=runtime-deps \
    /bin/netstat \
    /bin/bash \
    /bin/hostname \
    /bin/sleep \
    /bin/date \
    /bin/stat \
    /bin/base64 \
    /bin/sync \
    /bin/

COPY --from=runtime-deps \
    /sbin/modprobe \
    /sbin/lsmod \
    /sbin/

COPY --from=runtime-deps \
    /sbin/ip \
    /bin/ip

COPY --from=runtime-deps \
    /usr/bin/readlink \
    /usr/bin/od \
    /usr/bin/tr \
    /usr/bin/basename \
    /bin/

# Copy essential libraries
COPY --from=runtime-deps /lib/ld-musl-*.so.1 /lib/

COPY --from=runtime-deps \
    /usr/lib/libcurl.so.4 \
    /usr/lib/libnghttp2.so.14 \
    /usr/lib/libevent-2.1.so.7 \
    /usr/lib/libz.so.1 \
    /usr/lib/libssl.so.3 \
    /usr/lib/libcrypto.so.3 \
    /usr/lib/

COPY --from=runtime-deps \
    /usr/lib/libmnl.so.0 \
    /usr/lib/libnftnl.so.11 \
    /usr/lib/libreadline.so.8 \
    /usr/lib/libncursesw.so.6 \
    /usr/lib/liblzma.so.5 \
    /usr/lib/libzstd.so.1 \
    /usr/lib/

COPY --from=runtime-deps \
    /usr/lib/libseccomp.so.2 \
    /usr/lib/libcap.so.2 \
    /usr/lib/libelf.so.1 \
    /usr/lib/libxtables.so.12 \
    /usr/lib/

COPY --from=runtime-deps /usr/lib/xtables /usr/lib/xtables

RUN /bin/mkdir -p /usr/lib/sudo

COPY --from=runtime-deps \
    /usr/lib/sudo/libsudo_util.so.0 \
    /usr/lib/sudo/sudoers.so \
    /usr/lib/sudo/sudo_intercept.so \
    /usr/lib/sudo/sudo_noexec.so \
    /usr/lib/sudo/

# Copy timezone data and CA certificates
COPY --from=runtime-deps /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=runtime-deps /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy essential configuration files
COPY --from=runtime-deps /etc/tor /etc/tor
COPY --from=runtime-deps /usr/share/tor /usr/share/tor
COPY --from=runtime-deps /etc/sudoers /etc/sudoers

# Copy application files
COPY ./Src/iptable-rules /WireGate/iptable-rules
COPY ./Src/wiregate.sh /WireGate/wiregate.sh
COPY ./Src/entrypoint.sh /WireGate/entrypoint.sh    
COPY ./Src/dnscrypt /WireGate/dnscrypt
COPY ./Src/db/wsgi.ini /WireGate/db/wsgi.ini

# Set permissions
RUN chmod +x /WireGate/wiregate.sh /WireGate/entrypoint.sh

# Copy and setup restricted shell for security hardening
# COPY ./Src/restricted_shell.sh /WireGate/restricted_shell.sh
# RUN chmod +x /WireGate/restricted_shell.sh

# No restricted shell needed - using scratch image with only necessary binaries

# Copy built frontend assets
COPY --from=node \
    /static/app/dist \
    /WireGate/static/app/dist

# Copy public assets (favicon, manifest, etc.)
COPY --from=node \
    /static/app/public \
    /WireGate/static/app/public

COPY --from=node /static/locale /WireGate/static/locale

# Copy Tor Client Transport Plugin binaries
COPY --from=noxcis/tor-bins:latest \
    /lyrebird \
    /webtunnel \
    /snowflake \
    /usr/local/bin/

RUN mv /usr/local/bin/lyrebird /usr/local/bin/obfs4

# Copy AmneziaWG binaries  
COPY --from=noxcis/awg-bins:latest \
    /amneziawg-go \
    /awg \
    /awg-quick \
    /usr/bin/

# Copy WG-Dash & Tor Vanguards binaries
COPY --from=pybuilder \
    /build/dist/wiregate \
    /build/dist/vanguards \
    /WireGate/

COPY --from=builder \
    /build/torflux \
    /build/traffic-weir \
    /WireGate/

# Set final permissions
RUN chmod +x /WireGate/wiregate /WireGate/vanguards /WireGate/torflux /WireGate/traffic-weir

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep wiregate > /dev/null && \
    PORT=$(netstat -tulpn 2>/dev/null | grep wiregate | head -n1 | awk "{print \$4}" | cut -d: -f2) && \
    [ -n "$PORT" ] && \
    (curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200\|301\|302\|307\|308") || exit 1'

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM