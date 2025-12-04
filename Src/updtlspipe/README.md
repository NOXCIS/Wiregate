[![Go Report Card](https://goreportcard.com/badge/github.com/ameshkov/udptlspipe)](https://goreportcard.com/report/ameshkov/udptlspipe)
[![Latest release](https://img.shields.io/github/release/ameshkov/udptlspipe/all.svg)](https://github.com/ameshkov/udptlspipe/releases)

# udptlspipe

`udptlspipe` is a very simple TLS wrapper for UDP sessions with active probing
protection. The main purpose of it is to wrap WireGuard, OpenVPN or any other
similar UDP sessions. Inspired by [dtlspipe][dtlspipe].

This tool is very simple and created to solve a very specific issue and I intend
to keep it that way.

* [Features](#features)
* [Why would you need it?](#why)
* [How to install udptlspipe](#install)
* [How to use udptlspipe](#howtouse)
* [Custom TLS certificate](#tlscert)
* [Probing protection](#probing)
* [Docker](#docker)
* [All command-line arguments](#allcmdarguments)

[dtlspipe]: https://github.com/SenseUnit/dtlspipe

<a id="features"></a>

## Features

* Cross-platform (Windows/macOS/Linux/Android/*BSD).
* Simple configuration, no complicated configuration files.
* Mimics Android's okhttp library.
* Active probing protection in server mode.
* Suitable to wrap WireGuard, OpenVPN, and other UDP session.
* Uses WebSocket for data transfer so can be behind
  [a CDN that supports WS][cdnwebsocket].

[cdnwebsocket]: https://www.cdnplanet.com/guides/websockets/

<a id="why"></a>

## Why would you need it

There are several use-cases when this tool may be useful, the most popular ones
are:

* You're in a network where UDP-based protocol (like WireGuard) is forbidden.
* You're in a network where UDP works unreliably.

<a id="install"></a>

## How to install udptlspipe

* Using homebrew:
    ```shell
    brew install ameshkov/tap/udptlspipe
    ```
* From source:
    ```shell
    go install github.com/ameshkov/udptlspipe@latest
    ```
* You can get a binary from the [releases page][releases].
* You can also use a [Docker image](#docker) instead.

[releases]: https://github.com/ameshkov/udptlspipe/releases

<a id="howtouse"></a>

## How to use udptlspipe

### Generic case

Let's assume you have the following setup:

* You have a server with a public IP address `1.2.3.4` (**tunnel server**).
* You also have a UDP service running on `2.3.4.5:8123` (**udp server**).
* You want to access the UDP server securely from your **local machine** and
  wrap your UDP datagrams with a TLS layer.

Run the following command on your **tunnel server**.

```shell
udptlspipe --server -l 0.0.0.0:443 -d 2.3.4.5:8123 -p SecurePassword
```

Now run the following command on your **local machine**:

```shell
udptlspipe -l 127.0.0.1:8123 -d 1.2.3.4:443 -p SecurePassword
```

Now instead of using **udp server** address on your local machine use
`127.0.0.1:8123`.

In the end here's the pipe that you have:

**you** → UDP → **local udptlspipe** → TLS → **tunnel server** → UDP → **udp
server**.

### WireGuard

`udptlspipe` setup is completely the same as for the generic case, but you also
need to make some adjustments to the WireGuard client configuration:

* Use the address of the `udptlspipe` client as an endpoint in your WireGuard
  client configuration.
* Add `MTU = 1280` to the `[Peer]` section of both WireGuard client and server
  configuration files.
* Exclude the `udptlspipe` server IP from `AllowedIPs` in the WireGuard client
  configuration. This [calculator][wireguardcalculator] may help you.

[wireguardcalculator]: https://www.procustodibus.com/blog/2021/03/wireguard-allowedips-calculator/

<a id="tlscert"></a>

## Custom TLS certificate

By default, `udptlspipe` generates a self-signed certificate every time you run
a server, and the client does not verify the server certificate. This is an
okay-ish solution for a simple case when the authentication is handled by the
downstream UDP server, but it's not ideal when you want to completely secure
your tunnel. In order to achieve that goal, there is an option to use a custom
TLS certificate on the server-side and to enable certificates verification by
the client.

The first step would be to obtain a valid TLS certificate. You will probably
need to have a domain name to generate a valid TLS certificate. There are
numerous ways to do that, I suggest using a tool like [lego][lego] to automate
this process.

Here is how to run the server with a custom TLS certificate.

```shell
udptlspipe --server \
  -l 0.0.0.0:443 \
  -d 2.3.4.5:8123 \
  -p SecurePassword \
  --tls-servername yourdomain.com \
  --tls-certfile /path/to/cert \
  --tls-keyfile /path/to/key

```

* `--tls-servername` is the server name (should be the same as in your
  certificate).
* `--tls-certfile` is a path to the file with your PEM-encoded certificate.
* `--tls-keyfile` is a path to the file with your PEM-encoded private key.

Now let's run the client so that it could verify the certificate:

```shell
udptlspipe \
  -l 127.0.0.1:8123 \
  -d 1.2.3.4:443 \
  -p SecurePassword \
  --secure \
  --tls-servername yourdomain.com

```

* `--secure` enables TLS certificate verification.
* `--tls-servername` is the server name of the server cert.

[lego]: https://go-acme.github.io/lego/usage/cli/obtain-a-certificate/

## Probing protection

By default `udptlspipe` responds with a generic `403 Forbidden` response to
unauthorized requests. However, it allows to use a more sophisticated
protection. If `--probe-reverseproxyurl` is specified, `udptlspipe` server will
proxy unauthorized requests to the specified target while rewriting `Host` and
keeping the original path. This way you can imitate a real existing website.

```shell
udptlspipe --server \
  -l 0.0.0.0:443 \
  -d 2.3.4.5:8123 \
  -p SecurePassword \
  --probe-reverseproxyurl "http://example.com"

```

<a id="docker"></a>

## Docker

The docker image [is available][dockerregistry]. `udptlspipe` listens to the
port `8443` inside the container, so you don't have to specify the listen
address, other arguments are available.

Tunnel server: run `udptlspipe` as a background service in server mode and
expose on the host's port `443` (tcp):

```shell
docker run -d --name udptlspipe -p 443:8443/tcp \
  ghcr.io/ameshkov/udptlspipe \
  --server \
  -d 2.3.4.5:8123 \
  -p SecurePassword
```

Local machine: run `udptlspipe` as a background service in client mode and
expose on the host's port `1234` (udp):

```shell
docker run -d --name udptlspipe -p 1234:8443/udp \
  ghcr.io/ameshkov/udptlspipe \
  -d 2.3.4.5:8123 \
  -p SecurePassword
```

[dockerregistry]: https://github.com/ameshkov/udptlspipe/pkgs/container/udptlspipe

<a id="allcmdarguments"></a>

## All command-line arguments

```shell
Usage:
  udptlspipe [OPTIONS]

Application Options:
  -s, --server                                              Enables the server mode (optional). By default it runs in client
                                                            mode.
  -l, --listen=<IP:Port>                                    Address the tool will be listening to (required).
  -d, --destination=<IP:Port>                               Address the tool will connect to (required).
  -p, --password=<password>                                 Password is used to detect if the client is allowed (optional).
  -x, --proxy=[protocol://username:password@]host[:port]    URL of a proxy to use when connecting to the destination address
                                                            (optional).
      --secure                                              Enables server TLS certificate verification in client mode
                                                            (optional).
      --tls-servername=<hostname>                           Configures TLS server name that will be sent in the TLS
                                                            ClientHello in client mode, and the stub certificate name in
                                                            server mode. If not set, the the default domain name
                                                            (example.org) will be used (optional).
      --tls-certfile=<path-to-cert-file>                    Path to the TLS certificate file. Allows to use a custom
                                                            certificate in server mode. If not set, the server will generate
                                                            a self-signed stub certificate (optional).
      --tls-keyfile=<path-to-key-file>                      Path to the private key for the cert specified in tls-certfile.
      --probe-reverseproxyurl=<hostname>                    Unauthorized requests and probes will be proxied to the URL.
  -v, --verbose                                             Verbose output (optional).

Help Options:
  -h, --help                                                Show this help message
```

## TODO

* [X] Docker image.
* [X] Certificate configuration.
* [X] Use WebSocket for transport instead of the custom binary proto.
* [ ] Use several upstream connections instead of a single one.
* [ ] Automatic TLS certs generation (let's encrypt, lego).