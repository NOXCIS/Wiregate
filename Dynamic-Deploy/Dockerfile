
# node: FRONTEND - Vite Builder 
FROM --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
WORKDIR /static/app
COPY ./build_scripts/static /static
RUN npm ci && npm run build     


# pybuild: BACKEND - WG-Dash Builder for Brcypt & Psutil Binary (Python)
FROM  alpine:latest AS pybuild
RUN apk add --no-cache sudo build-base musl-dev rust cargo linux-headers go upx
WORKDIR /WireGate
COPY ./build_scripts/builder.sh ./build_scripts/builder_requirements.txt ./build_scripts/torflux.go ./build_scripts/go.mod . /WireGate/
RUN chmod u+x ./builder.sh && ./builder.sh \
    && CGO_ENABLED=0 go build -buildmode=pie -ldflags="-s -w" -o torflux 


# Stage 3: Final image
FROM noxcis/hellpine:latest
LABEL maintainer="NOXCIS"
WORKDIR /WireGate
ENV TZ=UTC
ENV WGD_CONF_PATH="/etc/wireguard"
COPY ./src /WireGate/


COPY --from=pybuild /WireGate/venv /WireGate/venv
COPY --from=pybuild /WireGate/log /WireGate/log
COPY --from=pybuild /WireGate/torflux /WireGate/torflux


#Copy Built Frontend  
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


# Install necessary tools and libraries in the final image
RUN apk add --no-cache wireguard-tools iptables ip6tables tzdata sudo && \
    apk upgrade && \
    apk cache clean && \
    chmod +x /WireGate/wiregate.sh && chmod +x /WireGate/entrypoint.sh &&\
    rm -rf /tmp/* /var/tmp/* && \
    rm -rf /var/cache/apk/* && \
    rm -rf /build /root/.cache /tmp/* /var/tmp/*


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/WireGate/entrypoint.sh"]
STOPSIGNAL SIGTERM
