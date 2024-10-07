FROM alpine:latest

WORKDIR /opt

# Set TERM environment variable
ENV TERM=xterm-256color

# Install necessary packages
RUN apk add --no-cache sudo ca-certificates curl git docker bash ncurses

# Install Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Set up Docker daemon
ENV DOCKER_HOST=unix:///var/run/docker.sock

# Download and run the script
RUN curl -O https://raw.githubusercontent.com/NOXCIS/Wiregate/main/stackscript.sh 
RUN chmod +x stackscript.sh 
RUN ./stackscript.sh terra-firma off dev

# Command to run your application
CMD ["docker", "run", "-it", "alpine", "sh"]
# Start Docker daemon
#RUN service docker start

