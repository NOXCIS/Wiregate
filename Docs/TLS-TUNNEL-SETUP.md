# TLS Tunnel Setup Guide

## Overview

The TLS tunnel feature allows WireGuard traffic to be wrapped in TLS encryption, helping bypass UDP blockings and Deep Packet Inspection (DPI) in restrictive network environments. This is particularly useful in regions where UDP traffic is blocked or heavily throttled.

## How It Works

```
Client Device                    Server
┌─────────────┐                 ┌──────────────┐
│ WireGuard   │                 │  udptlspipe  │
│   Client    │                 │   (TCP 443)  │
│             │   TLS/TCP       │              │
│      ↓      ├────────────────→│      ↓       │
│ udptlspipe  │   Encrypted     │  WireGuard   │
│   Client    │                 │   Server     │
│  (UDP→TLS)  │                 │  (TLS→UDP)   │
└─────────────┘                 └──────────────┘
```

**Flow:**
1. WireGuard client sends UDP packets to local udptlspipe client
2. udptlspipe client wraps UDP in TLS and sends via TCP
3. Server's udptlspipe receives TLS, extracts UDP
4. UDP packets forwarded to WireGuard server
5. Response follows reverse path

## Server Setup

### During Installation

When installing Wiregate using the Advanced mode, you'll be prompted to enable the TLS tunnel:

```bash
./install.sh
# Select "Advanced" mode
# When prompted for TLS tunnel, press Enter and choose 'y'
# Configure TLS port (default: 443)
# Set or generate TLS password
```

### Command Line Installation

You can also configure TLS settings via environment variables:

```bash
export WGD_TLS_ENABLED="true"
export WGD_TLS_PORT="443"
export WGD_TLS_PASSWORD="YourSecurePassword"
./install.sh
```

### Manual Enablement

If you already have Wiregate installed, edit your `.env` file:

```bash
WGD_TLS_ENABLED="true"
WGD_TLS_PORT="443"
WGD_TLS_PASSWORD="YourSecurePassword"
```

Then restart with the TLS profile:

```bash
docker compose --profile tls up -d
```

### Firewall Configuration

Ensure your firewall allows the TLS port:

```bash
# For UFW
sudo ufw allow 443/tcp

# For firewalld
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload

# For iptables
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## Client Setup

### Requirements

- Docker (recommended) or standalone udptlspipe binary
- WireGuard client
- Your WireGuard configuration file
- Server IP and TLS password

### Option 1: Docker (Recommended)

#### Step 1: Run udptlspipe Client Container

Create a directory for your setup:

```bash
mkdir -p ~/wiregate-tls
cd ~/wiregate-tls
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  udptlspipe-client:
    image: ghcr.io/ameshkov/udptlspipe:latest
    container_name: wireguard-tls-tunnel
    restart: unless-stopped
    command: >
      -l 0.0.0.0:51820
      -d YOUR_SERVER_IP:443
      -p YOUR_TLS_PASSWORD
    ports:
      - "51820:51820/udp"
    network_mode: host
```

Replace:
- `YOUR_SERVER_IP` with your Wiregate server IP
- `YOUR_TLS_PASSWORD` with the password set during server setup
- `51820` with your preferred local port (if needed)

Start the container:

```bash
docker compose up -d
```

#### Step 2: Modify WireGuard Configuration

Edit your WireGuard configuration file (e.g., `wg0.conf`):

```ini
[Interface]
PrivateKey = YOUR_PRIVATE_KEY
Address = 10.0.0.2/24
DNS = 10.2.0.100
MTU = 1280

[Peer]
PublicKey = SERVER_PUBLIC_KEY
# Change endpoint to point to local udptlspipe
Endpoint = 127.0.0.1:51820
AllowedIPs = 0.0.0.0/0, ::/0
# Exclude server IP from tunnel (important!)
# Add this to your routing or use wg-quick PostUp rules
PersistentKeepalive = 21
```

#### Step 3: Exclude Server IP from Tunnel

Add PostUp/PostDown rules to prevent routing loops:

```ini
[Interface]
PrivateKey = YOUR_PRIVATE_KEY
Address = 10.0.0.2/24
DNS = 10.2.0.100
MTU = 1280

# Exclude server IP from VPN tunnel
PostUp = ip route add YOUR_SERVER_IP via $(ip route | grep default | awk '{print $3}')
PostDown = ip route del YOUR_SERVER_IP

[Peer]
PublicKey = SERVER_PUBLIC_KEY
Endpoint = 127.0.0.1:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 21
```

Replace `YOUR_SERVER_IP` with your Wiregate server's public IP.

#### Step 4: Start WireGuard

```bash
sudo wg-quick up wg0
```

### Option 2: Standalone Binary

#### Step 1: Install udptlspipe

**Linux/macOS:**
```bash
# Using Homebrew
brew install ameshkov/tap/udptlspipe

# Or download binary
curl -LO https://github.com/ameshkov/udptlspipe/releases/latest/download/udptlspipe-linux-amd64
chmod +x udptlspipe-linux-amd64
sudo mv udptlspipe-linux-amd64 /usr/local/bin/udptlspipe
```

**Windows:**
Download from [releases page](https://github.com/ameshkov/udptlspipe/releases)

#### Step 2: Run udptlspipe Client

**Linux/macOS:**
```bash
udptlspipe -l 127.0.0.1:51820 -d YOUR_SERVER_IP:443 -p YOUR_TLS_PASSWORD
```

**Windows (PowerShell):**
```powershell
.\udptlspipe.exe -l 127.0.0.1:51820 -d YOUR_SERVER_IP:443 -p YOUR_TLS_PASSWORD
```

Keep this running in the background.

#### Step 3: Configure WireGuard

Follow the same configuration steps as in Option 1, Step 2 and 3.

### Option 3: Android

#### Using Termux

1. Install Termux from F-Droid
2. Install required packages:
   ```bash
   pkg update && pkg upgrade
   pkg install golang git
   ```

3. Build udptlspipe:
   ```bash
   go install github.com/ameshkov/udptlspipe@latest
   ```

4. Run in background:
   ```bash
   ~/go/bin/udptlspipe -l 127.0.0.1:51820 -d YOUR_SERVER_IP:443 -p YOUR_TLS_PASSWORD &
   ```

5. Import modified WireGuard config to WireGuard Android app

**Note:** Termux must stay running in the background.

### Option 4: iOS (Jailbroken)

iOS requires jailbreak to run background processes. For non-jailbroken devices, consider using a local proxy server or VPS as an intermediary.

## Verification

### Check udptlspipe Client

```bash
# Docker
docker logs wireguard-tls-tunnel

# Standalone (with verbose logging)
udptlspipe -l 127.0.0.1:51820 -d YOUR_SERVER_IP:443 -p YOUR_TLS_PASSWORD -v
```

Look for successful connection messages.

### Check WireGuard Connection

```bash
sudo wg show
```

You should see:
- Latest handshake (recent timestamp)
- Transfer data increasing

### Test Connectivity

```bash
# Ping WireGuard server
ping 10.0.0.1

# Check if traffic is routed through VPN
curl ifconfig.me
```

## Troubleshooting

### Connection Fails

1. **Check server TLS port is open:**
   ```bash
   telnet YOUR_SERVER_IP 443
   # or
   nc -zv YOUR_SERVER_IP 443
   ```

2. **Verify TLS password matches** between server and client

3. **Check udptlspipe logs:**
   ```bash
   docker logs wireguard-tls-tunnel -f
   ```

### MTU Issues

If experiencing slow speeds or connection drops:

1. **Reduce MTU in WireGuard config:**
   ```ini
   [Interface]
   MTU = 1280
   ```

2. **Or try even lower:**
   ```ini
   [Interface]
   MTU = 1200
   ```

### Routing Loops

If you can't connect after starting WireGuard:

1. **Ensure server IP is excluded from tunnel**
2. **Check routing table:**
   ```bash
   ip route
   # Should show specific route for server IP
   ```

3. **Manually add route:**
   ```bash
   sudo ip route add YOUR_SERVER_IP via $(ip route | grep default | awk '{print $3}')
   ```

### High Latency

1. **Use a closer server** if possible
2. **Try different TLS port** (443, 8443, 853)
3. **Check if ISP throttles specific ports**

## Advanced Configuration

### Multiple Zones

If you want TLS tunnel for multiple WireGuard zones:

Edit `docker-compose.yml` on server:

```yaml
services:
  udptlspipe-admin:
    image: ghcr.io/ameshkov/udptlspipe:latest
    container_name: udptlspipe-admin
    restart: unless-stopped
    command: >
      --server
      -d wiregate:4430
      -p ${WGD_TLS_PASSWORD}
    ports:
      - "443:8443/tcp"
    networks:
      private_network:
        ipv4_address: 10.2.0.5

  udptlspipe-members:
    image: ghcr.io/ameshkov/udptlspipe:latest
    container_name: udptlspipe-members
    restart: unless-stopped
    command: >
      --server
      -d wiregate:4431
      -p ${WGD_TLS_PASSWORD}
    ports:
      - "8443:8443/tcp"
    networks:
      private_network:
        ipv4_address: 10.2.0.6
```

### Custom TLS Certificates

For custom certificates (optional):

1. **Generate certificates:**
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

2. **Mount to container:**
   ```yaml
   volumes:
     - ./cert.pem:/certs/cert.pem:ro
     - ./key.pem:/certs/key.pem:ro
   command: >
     --server
     -d wiregate:${WGD_PORT_RANGE_STARTPORT}
     -p ${WGD_TLS_PASSWORD}
     --tls-certfile /certs/cert.pem
     --tls-keyfile /certs/key.pem
   ```

3. **Use `--secure` on client** with `--tls-servername YOUR_DOMAIN`

### Probing Protection

To make the server respond like a legitimate website to unauthorized probes:

```yaml
command: >
  --server
  -d wiregate:${WGD_PORT_RANGE_STARTPORT}
  -p ${WGD_TLS_PASSWORD}
  --probe-reverseproxyurl https://example.com
```

This proxies unauthorized requests to the specified URL, making detection harder.

## Performance Considerations

- **Overhead:** TLS tunnel adds ~5-15% latency overhead
- **CPU Usage:** Minimal on modern hardware
- **Throughput:** Should achieve 80-95% of direct UDP speeds
- **MTU:** Lower MTU (1280) is required, reducing effective payload

## Security Notes

1. **Password Security:** Use strong, unique passwords (24+ characters)
2. **Port Selection:** Using port 443 helps with censorship circumvention
3. **Certificate Verification:** For maximum security, use custom certificates with `--secure` mode
4. **Server IP Leakage:** Always exclude server IP from VPN tunnel
5. **Logging:** udptlspipe doesn't log traffic by default, but enable minimal logging for debugging

## References

- [udptlspipe GitHub](https://github.com/ameshkov/udptlspipe)
- [WireGuard Documentation](https://www.wireguard.com/)
- [Wiregate Project](https://github.com/NOXCIS/Wiregate)

## Support

For issues specific to:
- **Wiregate:** Open an issue at [Wiregate Issues](https://github.com/NOXCIS/Wiregate/issues)
- **udptlspipe:** Visit [udptlspipe Issues](https://github.com/ameshkov/udptlspipe/issues)
- **WireGuard:** Check [WireGuard Documentation](https://www.wireguard.com/support/)
