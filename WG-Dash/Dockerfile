# pybuild: WG-Dash Builder for Brcypt | Psutil | TorFlux
FROM  alpine:latest AS pybuild
LABEL maintainer="NOXCIS"
RUN apk add --no-cache sudo build-base musl-dev rust cargo linux-headers go upx
WORKDIR /opt/wireguarddashboard/src
COPY ./src/builder.sh ./src/builder_requirements.txt ./src/torflux.go ./src/go.mod . /opt/wireguarddashboard/src/
RUN chmod u+x ./builder.sh && ./builder.sh \
    && go build -buildmode=pie -ldflags="-s -w" -o torflux


# wgcf-builder: Build wgcf for Cloudflare Warp support
FROM alpine:latest AS wgcf-builder
LABEL maintainer="NOXCIS"
RUN apk add --no-cache git go upx
WORKDIR /build
RUN git clone https://github.com/ViRb3/wgcf.git . && \
    go build -buildmode=pie -ldflags="-s -w" -o wgcf && \
    upx --best --lzma wgcf


# Stage 3: Final image
FROM alpine:latest
ENV TZ=UTC
WORKDIR /opt/wireguarddashboard/src
COPY ./src /opt/wireguarddashboard/src/
COPY --from=noxcis/tor-bins:latest /lyrebird /usr/local/bin/lyrebird
COPY --from=noxcis/tor-bins:latest /webtunnel /usr/local/bin/webtunnel
COPY --from=noxcis/tor-bins:latest /snowflake /usr/local/bin/snowflake
COPY --from=wgcf-builder /build/wgcf /usr/local/bin/wgcf
COPY --from=pybuild /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=pybuild /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log/
COPY --from=pybuild /opt/wireguarddashboard/src/torflux /opt/wireguarddashboard/src/torflux

RUN apk add --no-cache wireguard-tools sudo iptables tzdata && \
    apk upgrade && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh 

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
CMD ["docker_start"]

STOPSIGNAL SIGTERM

