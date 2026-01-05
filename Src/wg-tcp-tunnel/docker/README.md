# wg-tcp-tunnel Docker Setup

This directory contains Docker configurations for running wg-tcp-tunnel as both a server and client.

## Quick Start

Build and run both containers:

```bash
docker-compose up --build
```

This will:
1. Build both server and client containers
2. Start the server listening on TCP port 51820
3. Start the client connecting to the server
4. Run test UDP echo server and client in test mode

## Architecture

```
┌─────────────┐         TCP          ┌─────────────┐
│   Client    │ ───────────────────> │   Server    │
│             │                      │             │
│ UDP:51822   │                      │ TCP:51820   │
│             │                      │             │
│             │                      │ UDP:51820   │
└─────────────┘                      └─────────────┘
```

## Services

### Server

- **TCP Port**: 51820 (listens for incoming TCP connections)
- **UDP Port**: 51820 (forwards to local WireGuard or test server)
- **Container**: `wg-tcp-tunnel-server`

### Client

- **UDP Port**: 51822 (listens for incoming UDP packets)
- **TCP Connection**: Connects to `server:51820`
- **Container**: `wg-tcp-tunnel-client`

## Environment Variables

### Server

- `TCP_PORT`: TCP listen port (default: 51820)
- `UDP_PORT`: UDP forward port (default: 51820)
- `VERBOSE`: Verbosity level 0-3 (default: 0)
- `TEST_MODE`: Enable test UDP echo server (default: false)
- `TCP_KEEP_ALIVE`: TCP keep-alive idle time in seconds (optional)

### Client

- `UDP_PORT`: UDP listen port (default: 51822)
- `SERVER_HOST`: Server hostname (default: server)
- `SERVER_PORT`: Server TCP port (default: 51820)
- `VERBOSE`: Verbosity level 0-3 (default: 0)
- `TEST_MODE`: Enable test UDP client (default: false)
- `TCP_KEEP_ALIVE`: TCP keep-alive idle time in seconds (optional)

## Testing

With `TEST_MODE=true` (default in docker-compose.yml):

1. Server runs a UDP echo server on port 51820
2. Client sends test packets every 2 seconds to 127.0.0.1:51822
3. Packets flow: Client UDP → Client tunnel → Server TCP → Server tunnel → Server UDP echo
4. Echo responses flow back the same path

View logs:

```bash
# All logs
docker-compose logs -f

# Server only
docker-compose logs -f server

# Client only
docker-compose logs -f client
```

## Manual Testing

### Test from host to client

```bash
# Send UDP packet to client
echo "Hello from host" | nc -u localhost 51822
```

### Test from client to server

```bash
# Execute in client container
docker exec wg-tcp-tunnel-client /test-udp-client.sh 127.0.0.1 51822
```

### Check server logs

```bash
docker logs wg-tcp-tunnel-server
```

## Production Use

For production, set `TEST_MODE=false`:

```yaml
environment:
  - TEST_MODE=false
```

Then configure WireGuard to:
- **Client side**: Point to `127.0.0.1:51822`
- **Server side**: Point to `127.0.0.1:51820`

## Building Individual Containers

### Server only

```bash
docker build -f Dockerfile.server -t wg-tcp-tunnel-server .
docker run -p 51820:51820 -p 51820:51820/udp wg-tcp-tunnel-server
```

### Client only

```bash
docker build -f Dockerfile.client -t wg-tcp-tunnel-client .
docker run -p 51822:51822/udp \
  -e SERVER_HOST=your-server-ip \
  wg-tcp-tunnel-client
```

## Troubleshooting

### Check if containers are running

```bash
docker-compose ps
```

### View container logs

```bash
docker-compose logs server
docker-compose logs client
```

### Test connectivity

```bash
# From host, test server TCP port
nc -zv localhost 51820

# From client container, test server connection
docker exec wg-tcp-tunnel-client nc -zv server 51820
```

### Restart services

```bash
docker-compose restart
```

### Clean rebuild

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

