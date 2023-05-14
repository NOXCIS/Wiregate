# Worm-Hole 
![Docker Pulls](https://img.shields.io/docker/pulls/rlabinc/pihole-unbound.svg?style=flat&label=pulls&logo=docker) ![Docker Image Size (tag)](https://img.shields.io/docker/image-size/rlabinc/pihole-unbound/latest.svg?style=flat&label=image&logo=docker) [![Latest Build & Push](https://github.com/origamiofficial/docker-pihole-unbound/actions/workflows/build-and-push-latest.yaml/badge.svg)](https://github.com/origamiofficial/docker-pihole-unbound/actions/workflows/build-and-push-latest.yaml) ![GitHub Repo stars](https://img.shields.io/github/stars/origamiofficial/docker-pihole-unbound?style=social)

[pihole-unbound](https://github.com/origamiofficial/docker-pihole-unbound) is a Docker container to run [Pi-Hole](https://github.com/pi-hole/pi-hole) & [Unbound](https://github.com/NLnetLabs/unbound) on the same container.

## Supported Architectures

We utilise the docker buildx for multi-platform awareness. More information is available from docker [here](https://docs.docker.com/buildx/working-with-buildx/).

Simply pulling `rlabinc/pihole-unbound:latest` should retrieve the correct image for your arch, but you can also pull specific arch images via `--platform`.

The architectures supported by this image are:

| Architecture | Available | Platform |
| :----: | :----: | :----: |
| x86-64 | ✅ | linux/amd64 |
| arm64 | ✅ | linux/arm64 |
| armhf | ✅ | linux/arm/v7 |
| armv6 | ✅ | linux/arm/v6 |
| i386 | ❎ | [Compile Failed](https://github.com/origamiofficial/docker-pihole-unbound/issues/1) \<help wanted\> |

## Usage
Here are the commands you'll need:
```bash
docker run -d --name pihole-unbound \
  --name=pihole-unbound \
  -e TZ=Europe/London `#optional` \
  -p 53:53/tcp -p 53:53/udp \
  -p 80:80/tcp `#Pi-hole web interface port` \
  -e WEBPASSWORD='qwerty123' `#better to use single quotes` \
  --restart=always \
  rlabinc/pihole-unbound:latest
```

### Docker Tags
The Docker tags supported by this image are:

| Tag | Meaning | Type |
| :----: | :----: | ---- |
| `latest` | This image is build every three days | Stable |
| `date` | Same as `latest` | Stable |
| `dev` | This image is build daily | Beta |

Note: Date tag images aren't the same as the official ones, they're based on the build date.

### Installing on Ubuntu
Modern releases of Ubuntu (17.10+) include [`systemd-resolved`](http://manpages.ubuntu.com/manpages/bionic/man8/systemd-resolved.service.8.html) which is configured by default to implement a caching DNS stub resolver. This will prevent pi-hole from listening on port 53.
The stub resolver should be disabled with: `sudo sed -r -i.orig 's/#?DNSStubListener=yes/DNSStubListener=no/g' /etc/systemd/resolved.conf`

This will not change the nameserver settings, which point to the stub resolver thus preventing DNS resolution. Change the `/etc/resolv.conf` symlink to point to `/run/systemd/resolve/resolv.conf`, which is automatically updated to follow the system's [`netplan`](https://netplan.io/):
`sudo sh -c 'rm /etc/resolv.conf && ln -s /run/systemd/resolve/resolv.conf /etc/resolv.conf'`
After making these changes, you should restart systemd-resolved using `systemctl restart systemd-resolved`

Once pi-hole is installed, you'll want to configure your clients to use it ([see here](https://discourse.pi-hole.net/t/how-do-i-configure-my-devices-to-use-pi-hole-as-their-dns-server/245)). If you used the symlink above, your docker host will either use whatever is served by DHCP, or whatever static setting you've configured. If you want to explicitly set your docker host's nameservers you can edit the netplan(s) found at `/etc/netplan`, then run `sudo netplan apply`.
Example netplan:
```yaml
network:
    ethernets:
        ens160:
            dhcp4: true
            dhcp4-overrides:
                use-dns: false
            nameservers:
                addresses: [127.0.0.1]
    version: 2
```

Note that it is also possible to disable `systemd-resolved` entirely. However, this can cause problems with name resolution in vpns ([see bug report](https://bugs.launchpad.net/network-manager/+bug/1624317)). It also disables the functionality of netplan since systemd-resolved is used as the default renderer ([see `man netplan`](http://manpages.ubuntu.com/manpages/bionic/man5/netplan.5.html#description)). If you choose to disable the service, you will need to manually set the nameservers, for example by creating a new `/etc/resolv.conf`.

Users of older Ubuntu releases (circa 17.04) will need to disable dnsmasq.

## Parameters

Container images are configured using parameters passed at runtime (such as those above).

| Parameter | Function |
| :----: | --- |
| `-e TZ=Europe/London` | Specify a timezone to use EG Europe/London. |
| `-p 53:53/tcp -p 53:53/udp` | Default DNS port to use. |
| `-p 80:80/tcp` | Specify Pi-hole web interface port. |
| `-e WEBPASSWORD='qwerty123'` | Specify Pi-hole web interface password. It is better to use single quotes. |
| `--restart=always` | To make sure "It's Always DNS" not happend. |
| `-v /opt/unbound/etc/unbound` | Your customized Unbound configuration `unbound.conf` location. |

This Docker container supports all Pi-hole official Docker container environment variables available [here](https://github.com/pi-hole/docker-pi-hole/#environment-variables).

## Pihole Github Repository
https://github.com/pi-hole/docker-pi-hole

## Unbound Github Repository
https://github.com/NLnetLabs/unbound

## Pi-hole Unbound Github Repository
https://github.com/origamiofficial/docker-pihole-unbound

## Acknowledgements
The code in this image is heavily influenced by MatthewVance's unbound-docker with the help of chriscrowe's docker-pihole-unbound server Docker image configs,
However, the upstream projects most certainly also deserve credit for making this all possible.
- [pi-hole](https://github.com/pi-hole).
- [NLnetLabs](https://github.com/NLnetLabs).
- [MatthewVance](https://github.com/MatthewVance).
- [chriscrowe](https://github.com/chriscrowe).

## Warning

I'm not responsible if your internet goes down using this Docker container. Use at your own risk.

[![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://github.com/origamiofficial/docker-pihole-unbound&icon=github.svg&icon_color=%23FFFFFF&title=hits&edge_flat=false)](https://github.com/origamiofficial/docker-pihole-unbound)