FROM ubuntu:latest
WORKDIR /build

COPY ./Src/ /build/Src/


RUN apt-get update && apt-get install -y \
    make build-essential wget curl git make tor wireguard iptables sudo


RUN chmod +x ./Src/wiregate.sh

WORKDIR /build/Src

RUN ./wiregate.sh metal_install

WORKDIR /build/WireGate_Built
CMD ["./wiregate.sh", "start"]
#CMD ["tail", "-f", "/dev/null"]


