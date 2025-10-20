# node: FRONTEND - Vite + Vue3 Builder with pnpm (Enhanced Security)
##########################################################
FROM --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
ARG DASHBOARD_MODE=development
WORKDIR /static/app

# Install pnpm, copy source, and build in single layer
RUN npm install -g pnpm
COPY ./Src/static /static
ENV CI=true
ENV DASHBOARD_MODE=${DASHBOARD_MODE}
RUN pnpm install --frozen-lockfile && pnpm run build

# minimal-base: Minimal base image built from scratch (BusyBox-free)
##########################################################
FROM alpine:latest AS utils_extractor

# Copy and run mirror selection script
COPY select-mirror.sh /tmp/select-mirror.sh
RUN chmod +x /tmp/select-mirror.sh && /tmp/select-mirror.sh

RUN apk add --no-cache coreutils findutils gawk util-linux grep sed

FROM scratch AS minimal-base

# Copy utilities to /bin/
COPY --from=utils_extractor \
    /bin/mkdir /bin/chmod /bin/chown /bin/cp /bin/mv /bin/rm /bin/ln /bin/ls /bin/cat /bin/echo /bin/grep /bin/sed \
    /usr/bin/gawk /usr/bin/awk /usr/bin/cut /usr/bin/head /usr/bin/tail /usr/bin/sort /usr/bin/uniq /usr/bin/wc /usr/bin/find /usr/bin/id /usr/bin/whoami /usr/bin/test \
    /bin/

# Copy mknod to /sbin/
COPY --from=utils_extractor /bin/mknod /sbin/mknod

# Copy shell first (required before any RUN commands)
COPY --from=alpine:latest /bin/sh /bin/sh

# Copy libraries
COPY --from=alpine:latest /lib/ld-musl-*.so.1 /lib/
COPY --from=alpine:latest /lib/libc.musl-*.so.1 /lib/
COPY --from=alpine:latest /usr/lib/libz.so.1 /usr/lib/libssl.so.3 /usr/lib/libcrypto.so.3 /usr/lib/

COPY --from=utils_extractor \
    /usr/lib/libpcre2-8.so.0 /usr/lib/libacl.so.1 /usr/lib/libattr.so.1 /usr/lib/libutmps.so.0.1 /usr/lib/libskarnet.so.2.14 \
    /usr/lib/

# Create system files and directories in single operations
RUN /bin/echo "root:x:0:0:root:/root:/bin/sh" > /etc/passwd && \
    /bin/echo "root:x:0:" > /etc/group && \
    /bin/echo "root:*:0:0:99999:7:::" > /etc/shadow && \
    /bin/echo "tor:x:1000:1000:tor:/var/lib/tor:/bin/false" >> /etc/passwd && \
    /bin/echo "tor:x:1000:" >> /etc/group && \
    /bin/mkdir -p /tmp /var /var/tmp /var/log /var/lib /etc /dev /proc /sys /run && \
    /bin/chmod 1777 /tmp /var/tmp && \
    /bin/chmod 755 /etc

# base_cve_patch: Security-hardened minimal base (BusyBox-free)
##########################################################
FROM minimal-base AS base_cve_patch

# Create device files and set permissions in single layer
RUN [ ! -e /dev/null ] && /sbin/mknod /dev/null c 1 3 || true && \
    [ ! -e /dev/zero ] && /sbin/mknod /dev/zero c 1 5 || true && \
    [ ! -e /dev/random ] && /sbin/mknod /dev/random c 1 8 || true && \
    [ ! -e /dev/urandom ] && /sbin/mknod /dev/urandom c 1 9 || true && \
    /bin/chmod 666 /dev/null /dev/zero /dev/random /dev/urandom && \
    /bin/chmod 755 /bin/sh

# binary-builder-deps: Base Image with Python dependencies (RAPID DEVELOPMENT)
##########################################################
FROM python:3.13-alpine AS base_dependencies
WORKDIR /build

COPY ./Src/requirements.txt .

# Copy and run mirror selection script, then install packages
COPY select-mirror.sh /tmp/select-mirror.sh
RUN chmod +x /tmp/select-mirror.sh && /tmp/select-mirror.sh && \
    apk add --no-cache \
        py3-virtualenv py3-pip musl-dev build-base zlib-dev libffi-dev openssl-dev \
        linux-headers rust cargo upx wget openldap-dev ccache && \
    python3 -m venv venv && \
    venv/bin/pip install --upgrade pip && \
    venv/bin/pip install -r requirements.txt

# builder: WGDashboard & Vanguards Python Binary Build stage
##########################################################
FROM alpine:latest AS builder
ARG TARGETPLATFORM
ARG GO_VERSION=1.24.6

# Copy and run mirror selection script, then install packages and download Go
COPY select-mirror.sh /tmp/select-mirror.sh
RUN chmod +x /tmp/select-mirror.sh && /tmp/select-mirror.sh && \
    apk add --no-cache wget gcc musl-dev && \
    set -eux; \
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

# Copy source files and build binaries in single layer
COPY ./Src/torflux/torflux.go ./Src/torflux/go.mod /build/torflux-build/
COPY ./Src/traffic_weir/ /build/traffic_weir/

RUN mkdir -p /build/torflux-build /build/traffic_weir && \
    cd /build/torflux-build && \
    GOOS=linux GOARCH=$GO_ARCH CGO_ENABLED=0 go build \
    -ldflags="-X main.version=v1.0.0 -s -w" \
    -o /build/torflux && \
    cd /build/traffic_weir && \
    GOOS=linux GOARCH=$GO_ARCH CGO_ENABLED=0 go build \
    -ldflags="-X main.version=v1.0.0 -s -w" \
    -o /build/traffic-weir

# pybuilder: Python binary builder
##########################################################
FROM base_dependencies AS pybuilder
WORKDIR /build

# Copy all source files in single operation
COPY ./Src/wiregate /build/wiregate/
COPY ./Src/wiregate.py ./
COPY ./Src/vanguards /build/vanguards/
COPY ./Src/vanguards.py ./

# Build both Python binaries in single layer
RUN venv/bin/pyinstaller \
        --onefile --clean --distpath=/build/dist --name=wiregate \
        wiregate.py && \
    venv/bin/pyinstaller \
        --onefile --clean --distpath=/build/dist --name=vanguards \
        vanguards.py

# runtime-deps: Prepare runtime dependencies
##########################################################
FROM alpine:latest AS runtime-deps

# Copy and run mirror selection script, then install packages and create directories
COPY select-mirror.sh /tmp/select-mirror.sh
RUN chmod +x /tmp/select-mirror.sh && /tmp/select-mirror.sh && \
    apk add --no-cache \
        wireguard-tools iptables ip6tables iproute2 tzdata sudo tor ca-certificates \
        net-tools bash && \
    mkdir -p /runtime-files/bin /runtime-files/sbin /runtime-files/usr/bin /runtime-files/usr/sbin \
             /runtime-files/lib /runtime-files/usr/lib /runtime-files/etc /runtime-files/usr/share && \
    # Verify Tor installation includes GEOIP files
    ls -la /usr/share/tor/ && \
    echo "Tor GEOIP files check:" && \
    if [ -f /usr/share/tor/geoip ] && [ -f /usr/share/tor/geoip6 ]; then \
        echo "GEOIP files found in Alpine Tor package"; \
    else \
        echo "GEOIP files missing, checking if they exist elsewhere..."; \
        find /usr -name "geoip*" 2>/dev/null || echo "No GEOIP files found in /usr"; \
    fi

# Final stage: Minimal WireGate container
##########################################################
FROM base_cve_patch AS final

LABEL maintainer="NOXCIS"

# Set environment variables and create directories in single layer
ENV TZ=UTC
ENV WGD_CONF_PATH="/etc/wireguard"
RUN mkdir -p /WireGate /etc/wireguard /var/lib/tor /var/log/tor /proc /sys /dev/pts

WORKDIR /WireGate

# Copy runtime binaries in grouped operations
COPY --from=runtime-deps \
    /usr/bin/wg /usr/bin/wg-quick /usr/bin/sudo /usr/bin/tor /usr/bin/wget \
    /usr/bin/

COPY --from=runtime-deps \
    /usr/sbin/iptables /usr/sbin/ip6tables /usr/sbin/iptables-restore /usr/sbin/ip6tables-restore \
    /sbin/

COPY --from=runtime-deps \
    /bin/netstat /bin/bash /bin/hostname /bin/sleep /bin/date /bin/stat /bin/base64 /bin/sync \
    /bin/


COPY --from=runtime-deps \
    /sbin/modprobe /sbin/lsmod /sbin/ip /sbin/tc \
    /sbin/

COPY --from=runtime-deps \
    /usr/bin/readlink /usr/bin/od /usr/bin/tr /usr/bin/basename \
    /bin/

# Copy libraries in grouped operations
COPY --from=runtime-deps /lib/ld-musl-*.so.1 /lib/

COPY --from=runtime-deps \
    /usr/lib/libevent-2.1.so.7 /usr/lib/libz.so.1 \
    /usr/lib/libssl.so.3 /usr/lib/libcrypto.so.3 \
    /usr/lib/

COPY --from=runtime-deps \
    /usr/lib/libmnl.so.0 /usr/lib/libnftnl.so.11 /usr/lib/libreadline.so.8 /usr/lib/libncursesw.so.6 \
    /usr/lib/liblzma.so.5 /usr/lib/libzstd.so.1 \
    /usr/lib/

COPY --from=runtime-deps \
    /usr/lib/libseccomp.so.2 /usr/lib/libcap.so.2 /usr/lib/libelf.so.1 /usr/lib/libxtables.so.12 \
    /usr/lib/

COPY --from=runtime-deps /usr/lib/xtables /usr/lib/xtables

# Setup sudo and copy configuration files
RUN /bin/mkdir -p /usr/lib/sudo

COPY --from=runtime-deps \
    /usr/lib/sudo/libsudo_util.so.0 /usr/lib/sudo/sudoers.so /usr/lib/sudo/sudo_intercept.so /usr/lib/sudo/sudo_noexec.so \
    /usr/lib/sudo/

COPY --from=runtime-deps /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=runtime-deps /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=runtime-deps /etc/tor /etc/tor
COPY --from=runtime-deps /usr/share/tor /usr/share/tor
COPY --from=runtime-deps /etc/sudoers /etc/sudoers

# Verify GEOIP files are properly copied from runtime-deps
RUN echo "Verifying GEOIP files in final image:" && \
    ls -la /usr/share/tor/ && \
    if [ -f /usr/share/tor/geoip ] && [ -f /usr/share/tor/geoip6 ]; then \
        echo "GEOIP files successfully copied to final image"; \
        echo "geoip file size: $(wc -l < /usr/share/tor/geoip) lines"; \
        echo "geoip6 file size: $(wc -l < /usr/share/tor/geoip6) lines"; \
    else \
        echo "ERROR: GEOIP files missing in final image!"; \
        exit 1; \
    fi

# Copy application files and set permissions in single layer
COPY ./Src/iptable-rules /WireGate/iptable-rules
COPY ./Src/wiregate.sh ./Src/entrypoint.sh /WireGate/
COPY ./Src/dnscrypt /WireGate/dnscrypt
COPY ./Src/db/wsgi.ini /WireGate/db/wsgi.ini
COPY ./Src/restricted_shell.sh /WireGate/restricted_shell.sh

RUN chmod +x /WireGate/wiregate.sh /WireGate/entrypoint.sh /WireGate/restricted_shell.sh

# Copy frontend assets
COPY --from=node /static/app/dist /WireGate/static/app/dist
COPY --from=node /static/app/public /WireGate/static/app/public
COPY --from=node /static/locale /WireGate/static/locale

# Copy external binaries
COPY --from=noxcis/tor-bins:latest /lyrebird /webtunnel /snowflake /usr/local/bin/
RUN mv /usr/local/bin/lyrebird /usr/local/bin/obfs4

COPY --from=noxcis/awg-bins:latest /amneziawg-go /awg /awg-quick /usr/bin/

# Copy built binaries and set permissions
COPY --from=pybuilder /build/dist/wiregate /build/dist/vanguards /WireGate/
COPY --from=builder /build/torflux /build/traffic-weir /WireGate/

# Copy Python shared library for PyInstaller executables
#COPY --from=base_dependencies /usr/local/lib/libpython3.13.so.1.0 /usr/local/lib/
#RUN ln -sf /usr/local/lib/libpython3.13.so.1.0 /lib/libpython3.13.so.1.0

RUN chmod +x /WireGate/wiregate /WireGate/vanguards /WireGate/torflux /WireGate/traffic-weir

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'PORT=$(netstat -tulpn 2>/dev/null | grep ":80 " | head -n1 | awk "{print \$4}" | cut -d: -f2) && \
    [ -n "$PORT" ] && \
    wget -q --spider http://127.0.0.1:$PORT/api/health'

# Set shorter stop timeout for faster container shutdown
ENV DOCKER_STOP_TIMEOUT=10

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM
