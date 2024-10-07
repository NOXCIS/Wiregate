FROM docker:dind

WORKDIR /opt
#ENV DOCKER_HOST=unix:///var/run/docker.sock

ENV TERM=xterm-256color


RUN apk update

RUN apk upgrade

RUN apk add --no-cache curl git sudo ncurses bash libqrencode





COPY boot.sh /opt/boot.sh
RUN chmod +x /opt/boot.sh




ENTRYPOINT ["/opt/boot.sh"]