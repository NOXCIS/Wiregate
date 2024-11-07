
# builder: FRONTEND - Vite Builder 
FROM  --platform=${BUILDPLATFORM} node:iron-alpine3.20 AS builder
WORKDIR /opt/wireguarddashboard/src/static/app
COPY ./src/static /opt/wireguarddashboard/src/static 
RUN npm install && \                
    npm update && \                
    npm run build  && \              
    rm -r ./node_modules && \
    rm -r /opt/wireguarddashboard/src/static/app/src


# pybuild: BACKEND - WG-Dash Builder for Brcypt & Psutil Binary (Python)
FROM  alpine:latest AS pybuild
RUN apk add --no-cache sudo gcc musl-dev rust cargo linux-headers
WORKDIR /opt/wireguarddashboard/src
COPY ./build_scripts/builder.sh ./build_scripts/builder_requirements.txt /opt/wireguarddashboard/src/
RUN chmod u+x ./builder.sh && ./builder.sh 


# Stage 3: Final image
FROM alpine:latest
LABEL maintainer="NOXCIS"
ENV TZ=UTC
WORKDIR /opt/wireguarddashboard/src

COPY ./src /opt/wireguarddashboard/src/

#Copy Built Bcrypt & Psutil Binarys
COPY --from=pybuild /opt/wireguarddashboard/src/venv /opt/wireguarddashboard/src/venv
COPY --from=pybuild /opt/wireguarddashboard/src/log /opt/wireguarddashboard/src/log

#Copy Built Frontend  
COPY --from=builder /opt/wireguarddashboard/src /opt/wireguarddashboard/src

#Tor Client Transport Plugins
COPY --from=noxcis/tor-bins:latest /lyrebird /usr/local/bin/obfs4
COPY --from=noxcis/tor-bins:latest /webtunnel /usr/local/bin/webtunnel
COPY --from=noxcis/tor-bins:latest /snowflake /usr/local/bin/snowflake

#AmneziaWG Substitute install for WireGuard
COPY --from=noxcis/awg-bins:latest /amneziawg-go /usr/bin/amneziawg-go
COPY --from=noxcis/awg-bins:latest /awg /usr/bin/awg
COPY --from=noxcis/awg-bins:latest /awg-quick /usr/bin/awg-quick


#Entrypoint
RUN apk add --no-cache wireguard-tools bash sudo iptables tzdata && \
    apk upgrade && \
    chmod u+x /opt/wireguarddashboard/src/entrypoint.sh 


HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD \
    sh -c 'pgrep gunicorn > /dev/null && pgrep tail > /dev/null' || exit 1

ENTRYPOINT ["/opt/wireguarddashboard/src/entrypoint.sh"]
#CMD ["docker_start"]

STOPSIGNAL SIGTERM
