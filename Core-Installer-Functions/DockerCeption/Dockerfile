FROM alpine:latest

WORKDIR /opt

# Set TERM environment variable
ENV TERM=xterm-256color

# Install necessary packages
RUN apk add --no-cache sudo ca-certificates curl git docker bash ncurses

# Set up Docker daemon
ENV DOCKER_HOST=unix:///var/run/docker.sock

# Download and run the script
RUN curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh 
RUN chmod +x stackscript.sh 
RUN    ./stackscript.sh terra-firma Tor-br-obfs4 E-P-C

# Command to run your application
CMD ["docker", "run", "-it", "alpine", "sh"]
# Start Docker daemon
#RUN service docker start


