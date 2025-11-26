FROM ubuntu:latest
WORKDIR /build/

COPY ./Src/ /build/Src/
COPY ./example.env.txt /build/Src/.env
COPY ./configs /build/configs

RUN apt-get update && apt-get install -y \
    make build-essential wget curl git tor wireguard-tools iptables sudo \
    python3 python3-venv python3-pip

RUN chmod +x ./Src/wiregate.sh

WORKDIR /build/Src

# Run make install (this will build everything first via 'all' target)
# Use set -x to show commands being executed
# The retry logic in Makefile will handle transient network errors
# If tor-plugins still fail, you can set SKIP_TOR_PLUGINS=1 to skip them entirely
# Example: RUN set -x && SKIP_TOR_PLUGINS=1 make install
RUN set -x && make install

# Verify installation was successful
RUN echo "=== Checking installation directory ===" && \
    ls -la ../WireGate_Built/ && \
    echo "=== Installation contents ===" && \
    find ../WireGate_Built -type f | head -20 || echo "Install directory is empty"

WORKDIR /build/WireGate_Built
#CMD ["./wiregate.sh", "start"]
CMD ["tail", "-f", "/dev/null"]


