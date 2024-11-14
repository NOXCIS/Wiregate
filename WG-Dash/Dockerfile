
# builder: FRONTEND - Vite Builder 
FROM  --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS node
WORKDIR /static/app
COPY ./src/static /static 
RUN npm ci && npm run build  


# pybuild: BACKEND - WG-Dash Builder for Brcypt & Psutil Binary (Python)
FROM  alpine:latest AS pybuild
RUN apk add --no-cache sudo build-base musl-dev rust cargo linux-headers
WORKDIR /opt/wireguarddashboard/src
COPY ./build_scripts/builder.sh ./build_scripts/builder_requirements.txt ./build_scripts/torflux.c . /opt/wireguarddashboard/src/
RUN gcc -static -o torflux torflux.c && \
    chmod u+x ./builder.sh && ./builder.sh 


# Stage 3: Final image
FROM alpine:latest
LABEL maintainer="NOXCIS"
WORKDIR /opt/wireguarddashboard/src
ENV TZ=UTC
ENV WGD_CONF_PATH="/etc/wireguard"
COPY ./src /opt/wireguarddashboard/src/


COPY --from=pybuild /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=pybuild /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log
COPY --from=pybuild /opt/wireguarddashboard/src/torflux /opt/wireguarddashboard/src/torflux


#Copy Built Frontend  
COPY --from=node /static/app/dist /opt/wireguarddashboard/src/static/app/dist
COPY --from=node /static/app/index.html /opt/wireguarddashboard/src/static/app/index.html
COPY --from=node /static/app/public /opt/wireguarddashboard/src/static/app/public
COPY --from=node /static/locale /opt/wireguarddashboard/src/static/locale

#Tor Client Transport Plugins
#UPSTREAM DOCKER GO COMPILE BUILD PIPELINE 
#FOR TOR REPOS ~2hrs AHEAD DAILY UTC
COPY --from=noxcis/tor-bins:latest /lyrebird /usr/local/bin/obfs4
COPY --from=noxcis/tor-bins:latest /webtunnel /usr/local/bin/webtunnel
COPY --from=noxcis/tor-bins:latest /snowflake /usr/local/bin/snowflake

#AmneziaWG Substitute install for WireGuard
#UPSTREAM DOCKER GO COMPILE BUILD PIPELINE 
#FOR AMNEZIAWG REPOS ~1hrs AHEAD DAILY UTC
COPY --from=noxcis/awg-bins:latest /amneziawg-go /usr/bin/amneziawg-go
COPY --from=noxcis/awg-bins:latest /awg /usr/bin/awg
COPY --from=noxcis/awg-bins:latest /awg-quick /usr/bin/awg-quick


#Entrypoint
RUN apk add --no-cache wireguard-tools sudo iptables ip6tables tzdata && \
    apk upgrade && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh 


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]


STOPSIGNAL SIGTERM
