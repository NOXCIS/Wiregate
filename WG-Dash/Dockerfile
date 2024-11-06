# builder: WG-Dash Builder for Brcypt & Psutil Binary
FROM  alpine:latest AS builder
LABEL maintainer="NOXCIS"
WORKDIR /opt/wireguarddashboard/src
RUN apk add --no-cache sudo gcc musl-dev rust cargo linux-headers
COPY ./src/builder.sh ./src/builder_requirements.txt /opt/wireguarddashboard/src/
RUN chmod u+x ./builder.sh && ./builder.sh 



# Stage 3: Final image
FROM alpine:latest
ENV TZ=UTC
WORKDIR /opt/wireguarddashboard/src
COPY ./src /opt/wireguarddashboard/src/
COPY --from=noxcis/tor-bins:latest /lyrebird /usr/local/bin/lyrebird
COPY --from=noxcis/tor-bins:latest /webtunnel /usr/local/bin/webtunnel
COPY --from=noxcis/tor-bins:latest /snowflake /usr/local/bin/snowflake
COPY --from=builder /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=builder /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log/

RUN apk add --no-cache wireguard-tools sudo iptables tzdata && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh 

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
CMD ["docker_start"]

STOPSIGNAL SIGTERM

