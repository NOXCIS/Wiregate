# Cloudflare Warp Integration for Wiregate

## Overview

This document describes the Cloudflare Warp integration for Wiregate. Cloudflare Warp allows you to route your Wiregate VPN traffic through Cloudflare's global network, providing enhanced privacy, performance, and security.

## Table of Contents

- [What is Cloudflare Warp?](#what-is-cloudflare-warp)
- [Why Use Warp with Wiregate?](#why-use-warp-with-wiregate)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage](#usage)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)
- [Performance Considerations](#performance-considerations)
- [Security Notes](#security-notes)
- [References](#references)

---

## What is Cloudflare Warp?

**Cloudflare Warp** is Cloudflare's VPN service that:
- Uses WireGuard protocol for efficient, secure tunneling
- Routes traffic through Cloudflare's global network (over 310 data centers worldwide)
- Provides built-in DDoS protection and content filtering
- Offers both free and paid (Warp+) tiers
- Supports modern protocols including HTTP/3 and QUIC

### Key Features

- **Zero Trust Security**: Traffic protected by Cloudflare's security infrastructure
- **Global Network**: Traffic routed through nearest Cloudflare edge location
- **Privacy**: Hides your server's real IP address from destination websites
- **Performance**: Optimized routes and protocol acceleration
- **Reliability**: 99.99% uptime SLA with automatic failover

---

## Why Use Warp with Wiregate?

### Benefits

1. **Enhanced Privacy** 🔒
   - Your Wiregate server's IP is hidden from destination websites
   - Traffic exits through Cloudflare's network
   - Additional layer of anonymity

2. **Improved Performance** ⚡
   - Cloudflare's optimized global network
   - Automatic route optimization
   - HTTP/3 and protocol acceleration
   - Low latency to any destination

3. **Built-in Security** 🛡️
   - DDoS protection included
   - Malware and phishing protection (with Warp+)
   - DNS filtering capabilities
   - Encrypted traffic to Cloudflare edge

4. **Bypass Restrictions** 🌐
   - Access content through Cloudflare's network
   - Bypass regional restrictions
   - Overcome ISP throttling

5. **Redundancy** ♻️
   - Fallback to direct routing if Warp fails
   - Automatic failover capabilities
   - No single point of failure

### Use Cases

- **Privacy-Conscious Users**: Additional anonymity layer
- **Content Creators**: Hide origin server location
- **Businesses**: Leverage Cloudflare's enterprise network
- **Travelers**: Consistent network performance globally
- **Researchers**: Access geo-restricted resources

---

## Architecture

### Network Flow

```
[VPN Client]
    ↓ (WireGuard)
[Wiregate Zone Interface]
    ↓ (iptables MARK + Policy Routing)
[Cloudflare Warp Interface (warp)]
    ↓ (WireGuard to Cloudflare)
[Cloudflare Edge Network]
    ↓ (Optimized Routing)
[Internet / Destination]
```

### Components

1. **wgcf**: Tool to generate Cloudflare Warp credentials
2. **warp Interface**: WireGuard interface connected to Cloudflare
3. **warp-manager.sh**: Script to manage Warp setup and lifecycle
4. **warp-postup.sh**: Per-zone routing configuration (applied when zone starts)
5. **warp-postdown.sh**: Per-zone cleanup (applied when zone stops)

### Routing Mechanism

The integration uses **policy-based routing**:

1. **Packet Marking**: Packets from specified zones are marked with unique fwmark
2. **Routing Table**: Custom "warp" routing table with default route via warp interface
3. **IP Rules**: Policy rules route marked packets through warp table
4. **NAT**: Source NAT applied for traffic exiting via Warp

**Advantages**:
- Selective per-zone routing
- Preserves SSH and management access
- No interference with other services
- Clean separation of routing policies

---

## Configuration

### Environment Variables

Cloudflare Warp is configured via environment variables in your `.env` file or `docker-compose.yml`:

#### Global Settings

```bash
# Enable/disable Cloudflare Warp globally
WGD_WARP_ENABLED=true              # true or false (default: false)

# Specify which zones should use Warp (comma-separated)
WGD_WARP_ZONES=ADMINS,MEMBERS      # Default: ADMINS,MEMBERS

# Warp+ license key (optional, for premium features)
WGD_WARP_LICENSE_KEY=              # Your Warp+ key (optional)
```

#### Advanced Settings

```bash
# Warp endpoint (rarely needs changing)
WGD_WARP_ENDPOINT=engage.cloudflareclient.com:2408

# MTU size for Warp interface
WGD_WARP_MTU=1280                  # Default: 1280, Range: 1280-1420
```

### Zone Configuration

By default, Warp is enabled for **ADMINS** and **MEMBERS** zones. You can customize this:

```bash
# Route only ADMINS through Warp
WGD_WARP_ZONES=ADMINS

# Route all zones through Warp
WGD_WARP_ZONES=ADMINS,MEMBERS,GUESTS,LANP2P

# Disable for all zones (but keep Warp interface running)
WGD_WARP_ZONES=
```

### Warp+ (Premium Tier)

To use Warp+ features:

1. Sign up for Warp+ on mobile app or web
2. Get your license key from account settings
3. Add to configuration:

```bash
WGD_WARP_LICENSE_KEY=XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX
```

**Warp+ Benefits**:
- Faster connection speeds (priority routing)
- Access to Warp+ exclusive features
- Lower latency
- Enhanced security features

---

## Usage

### Basic Setup

1. **Enable Warp in `.env` file**:

```bash
WGD_WARP_ENABLED=true
WGD_WARP_ZONES=ADMINS,MEMBERS
```

2. **Rebuild and restart Wiregate**:

```bash
docker-compose down
docker-compose up -d --build
```

3. **Verify Warp is running**:

```bash
# Check container logs
docker logs wiregate | grep WARP

# Expected output:
# [WARP] Cloudflare Warp is enabled. Initializing...
# [WARP-MANAGER] INFO: wgcf is available
# [WARP-MANAGER] INFO: Registering new Cloudflare Warp account...
# [WARP-MANAGER] INFO: ✓ Warp account registered successfully
# [WARP-MANAGER] INFO: ✓ WireGuard profile generated
# [WARP-MANAGER] INFO: ✓ Configuration customized
# [WARP-MANAGER] INFO: ✓ Warp interface started successfully
# [WARP] ✓ Cloudflare Warp initialized successfully
```

4. **Check Warp interface status**:

```bash
# Enter the container
docker exec -it wiregate bash

# Check Warp interface
wg show warp

# Expected output shows Warp peer with Cloudflare endpoint
```

### Verifying Warp is Working

#### Method 1: Check Your IP

From a VPN client connected to ADMINS or MEMBERS zone:

```bash
# Should show Cloudflare IP, not your server IP
curl https://api.ipify.org
curl https://ifconfig.me
```

#### Method 2: Cloudflare Trace

```bash
# Inside container
docker exec -it wiregate wgcf trace

# Expected output:
# warp=on
# ...other Cloudflare info...
```

#### Method 3: Check Routing

```bash
# Inside container
docker exec -it wiregate bash

# Check if Warp routing is active
ip rule show | grep warp
iptables -t mangle -L PREROUTING -n | grep MARK

# Should show policy rules and packet marking
```

### Starting/Stopping Warp

```bash
# Inside container
docker exec -it wiregate bash

# Start Warp
/opt/wireguarddashboard/src/warp-manager.sh start

# Stop Warp
/opt/wireguarddashboard/src/warp-manager.sh stop

# Restart Warp
/opt/wireguarddashboard/src/warp-manager.sh restart

# Check status
/opt/wireguarddashboard/src/warp-manager.sh status

# Check connectivity
/opt/wireguarddashboard/src/warp-manager.sh check
```

### Disabling Warp

To disable Warp without removing configuration:

```bash
WGD_WARP_ENABLED=false
```

Restart container:

```bash
docker-compose restart
```

Warp will not initialize, and traffic will use default routing.

---

## Advanced Configuration

### Custom MTU

If you experience connection issues, try adjusting MTU:

```bash
# Lower MTU (more compatible but slower)
WGD_WARP_MTU=1280

# Higher MTU (faster but may have issues)
WGD_WARP_MTU=1420

# Optimal for most networks
WGD_WARP_MTU=1380
```

**MTU Guidelines**:
- Start with 1280 (most compatible)
- Increase gradually if no issues
- Test with: `ping -M do -s 1400 cloudflare.com`
- Reduce MTU if you get "Packet too big" errors

### Selective Zone Routing

Route only specific traffic patterns through Warp:

**Example 1: Only ADMINS through Warp**

```bash
WGD_WARP_ENABLED=true
WGD_WARP_ZONES=ADMINS
```

**Example 2: All zones except LANP2P**

```bash
WGD_WARP_ENABLED=true
WGD_WARP_ZONES=ADMINS,MEMBERS,GUESTS
```

**Example 3: Only GUESTS for public access**

```bash
WGD_WARP_ENABLED=true
WGD_WARP_ZONES=GUESTS
```

### Split Tunneling (Advanced)

You can exclude specific destinations from Warp routing by modifying the `warp-postup.sh` script:

```bash
# Edit the appropriate zone's warp-postup.sh
# Add before the MARK rule:

# Exclude specific IPs from Warp routing
iptables -t mangle -A PREROUTING -i "$WIREGUARD_INTERFACE" -d 8.8.8.8 -j RETURN
iptables -t mangle -A PREROUTING -i "$WIREGUARD_INTERFACE" -d 1.1.1.1 -j RETURN
```

### Custom Warp Endpoint

If you want to use a specific Cloudflare endpoint:

```bash
# Use specific region (if available)
WGD_WARP_ENDPOINT=engage.cloudflareclient.com:2408

# Note: Cloudflare automatically routes to nearest edge
# Custom endpoints rarely needed
```

### Manual Credential Generation

To manually generate Warp credentials:

```bash
docker exec -it wiregate bash

# Register new account
/opt/wireguarddashboard/src/warp-manager.sh register

# Generate profile
/opt/wireguarddashboard/src/warp-manager.sh generate

# Setup interface
/opt/wireguarddashboard/src/warp-manager.sh setup
```

---

## Troubleshooting

### Warp Not Starting

**Problem**: Warp interface fails to start during container initialization.

**Solutions**:

1. **Check if wgcf is available**:
   ```bash
   docker exec -it wiregate wgcf --version
   ```

2. **Check logs**:
   ```bash
   docker logs wiregate | grep WARP
   ```

3. **Manually setup Warp**:
   ```bash
   docker exec -it wiregate /opt/wireguarddashboard/src/warp-manager.sh setup
   ```

4. **Check kernel module**:
   ```bash
   # On host
   lsmod | grep wireguard

   # If missing:
   modprobe wireguard
   ```

### No Internet When Warp Enabled

**Problem**: VPN clients lose internet connectivity when Warp is enabled.

**Solutions**:

1. **Check Warp connectivity**:
   ```bash
   docker exec -it wiregate wgcf trace
   # Should show "warp=on"
   ```

2. **Verify routing rules**:
   ```bash
   docker exec -it wiregate ip rule show | grep warp
   docker exec -it wiregate ip route show table warp
   ```

3. **Check NAT rules**:
   ```bash
   docker exec -it wiregate iptables -t nat -L POSTROUTING -n | grep warp
   ```

4. **Test Warp interface directly**:
   ```bash
   docker exec -it wiregate ping -I warp 1.1.1.1
   ```

5. **Try restarting Warp**:
   ```bash
   docker exec -it wiregate /opt/wireguarddashboard/src/warp-manager.sh restart
   ```

### Warp Credentials Not Persisting

**Problem**: Warp re-registers on every container restart.

**Solution**: Mount a persistent volume for Warp data:

```yaml
# In docker-compose.yml
volumes:
  - ./warp-data:/opt/wireguarddashboard/warp
```

### High Latency Through Warp

**Problem**: Increased latency when routing through Warp.

**Solutions**:

1. **Check MTU settings**:
   ```bash
   # Lower MTU can cause fragmentation
   WGD_WARP_MTU=1380
   ```

2. **Verify Warp+ status**:
   ```bash
   docker exec -it wiregate wgcf trace
   # Look for "warp=plus" for premium routing
   ```

3. **Check endpoint location**:
   ```bash
   docker exec -it wiregate wgcf trace | grep loc
   # Verify you're connected to nearest edge
   ```

4. **Compare with direct routing**:
   ```bash
   # Temporarily disable for zone and test
   WGD_WARP_ZONES=  # Empty to disable
   ```

### Warp Account Issues

**Problem**: "Failed to register Warp account" error.

**Solutions**:

1. **Check internet connectivity**:
   ```bash
   docker exec -it wiregate ping -c 3 1.1.1.1
   docker exec -it wiregate curl https://api.cloudflareclient.com
   ```

2. **Rate limiting**: Wait 5-10 minutes and retry

3. **Manual registration**:
   ```bash
   docker exec -it wiregate bash
   cd /opt/wireguarddashboard/warp
   wgcf register --accept-tos
   ```

4. **Use existing credentials**: If you have Warp credentials from another device, you can manually copy them to `/opt/wireguarddashboard/warp/`

### Permission Denied Errors

**Problem**: Permission errors when running warp-manager.sh

**Solution**:

1. **Check script permissions**:
   ```bash
   docker exec -it wiregate ls -l /opt/wireguarddashboard/src/warp-manager.sh
   ```

2. **Make executable if needed**:
   ```bash
   docker exec -it wiregate chmod +x /opt/wireguarddashboard/src/warp-manager.sh
   ```

3. **Check NET_ADMIN capability**:
   ```yaml
   # In docker-compose.yml
   cap_add:
     - NET_ADMIN
   ```

---

## Performance Considerations

### Latency

- **Expected Overhead**: 5-20ms additional latency through Warp
- **Warp+**: Typically lower latency than free tier
- **Geographic Impact**: Minimal overhead when connected to nearby Cloudflare edge

### Throughput

- **Free Tier**: No explicit bandwidth limits, subject to fair use
- **Warp+**: Priority bandwidth allocation
- **Typical Speeds**: 100-500 Mbps depending on network and location

### CPU Usage

- **WireGuard Overhead**: Minimal (< 5% CPU for most use cases)
- **Encryption**: Double encryption (Wiregate → Warp → Internet)
- **Optimization**: Modern CPUs handle WireGuard efficiently

### Memory

- **Warp Interface**: ~10-20 MB additional memory
- **wgcf Tool**: ~5 MB
- **Total Overhead**: Minimal impact on container memory

### Recommendations

1. **For Low Latency**: Use Warp+ and ensure low MTU
2. **For High Throughput**: Ensure adequate bandwidth on host
3. **For Reliability**: Enable health monitoring and failover
4. **For Cost Optimization**: Free tier sufficient for most users

---

## Security Notes

### Privacy Considerations

**What Cloudflare Can See**:
- Your Wiregate server's IP address
- Destination websites/IPs you access
- Timing and volume of traffic (metadata)
- DNS queries (if using Cloudflare DNS)

**What Cloudflare Cannot See**:
- Content of your traffic (encrypted by WireGuard)
- Your VPN clients' real IP addresses
- Traffic content within Wiregate tunnel

### Trust Model

Using Warp means trusting Cloudflare with:
- Network routing decisions
- Traffic metadata
- Potential traffic inspection (though encrypted)

**Consider This If**:
- You require zero-knowledge VPN provider
- You need complete traffic anonymity
- You're concerned about US-based infrastructure

### Best Practices

1. **Use Warp+ for Enhanced Privacy**: Premium tier has additional privacy features
2. **Enable DNS Over HTTPS**: Encrypt DNS queries to Cloudflare
3. **Combine with Tor**: For additional anonymity (not officially supported)
4. **Monitor Logs**: Regularly check Warp logs for anomalies
5. **Rotate Credentials**: Periodically re-register Warp account

### Compliance

- **GDPR**: Cloudflare is GDPR compliant
- **HIPAA**: Warp is not HIPAA compliant without BAA
- **Data Retention**: Cloudflare retains minimal logs (24-48 hours)
- **Jurisdiction**: Cloudflare is US-based but operates globally

---

## Performance Monitoring

### Key Metrics to Monitor

```bash
# Warp interface statistics
docker exec -it wiregate wg show warp

# Routing statistics
docker exec -it wiregate ip -s link show warp

# Packet counters
docker exec -it wiregate iptables -t mangle -L PREROUTING -n -v | grep MARK

# Latency test
docker exec -it wiregate ping -c 10 -I warp 1.1.1.1
```

### Health Checks

Add to your monitoring system:

```bash
# Check if Warp is up
docker exec -it wiregate ip link show warp | grep UP

# Check Warp connectivity
docker exec -it wiregate wgcf trace | grep "warp=on"

# Check active sessions
docker exec -it wiregate wg show warp | grep "latest handshake"
```

---

## Comparison with Other Solutions

### Warp vs. TOR

| Feature | Cloudflare Warp | Tor |
|---------|----------------|-----|
| Speed | Fast (100+ Mbps) | Slow (1-10 Mbps) |
| Latency | Low (10-30ms) | High (100-500ms) |
| Anonymity | Moderate | High |
| Cost | Free / Warp+ $5/mo | Free |
| Reliability | High (99.99%) | Variable |
| Use Case | Performance + Privacy | Maximum Anonymity |

**Recommendation**: Use Warp for general use, Tor for high-threat scenarios.

### Warp vs. Direct Routing

| Feature | With Warp | Without Warp |
|---------|-----------|--------------|
| Privacy | Better (hidden origin) | Lower (exposed origin) |
| Performance | Variable (usually good) | Direct (baseline) |
| Security | Cloudflare protection | Depends on ISP |
| Complexity | Higher | Lower |
| Cost | Free/Warp+ | Free |

**Recommendation**: Enable Warp for enhanced privacy and security.

### Warp vs. Commercial VPN

| Feature | Cloudflare Warp | Commercial VPN |
|---------|----------------|----------------|
| Trust | Cloudflare reputation | Varies by provider |
| Speed | Excellent | Variable |
| Privacy Policy | Transparent | Varies |
| Network Size | 310+ locations | 50-100 typically |
| Cost | Free / $5 | $5-15/mo |

**Recommendation**: Warp is competitive with commercial VPNs and free.

---

## FAQ

### Q: Is Cloudflare Warp free?

**A**: Yes, Cloudflare Warp has a free tier with unlimited data. Warp+ ($4.99/month) offers enhanced performance and priority routing.

### Q: Can I use Warp with Tor simultaneously?

**A**: Yes, but it's not officially supported. Traffic would route: Client → Wiregate → Warp → Tor → Internet. This adds significant latency.

### Q: Does Warp work with IPv6?

**A**: Yes, Cloudflare Warp fully supports IPv6. Wiregate's implementation includes IPv6 routing.

### Q: Can I use my own Cloudflare account?

**A**: The current implementation auto-generates credentials. You can manually import credentials by copying `wgcf-account.toml` to `/opt/wireguarddashboard/warp/`.

### Q: What happens if Warp goes down?

**A**: By default, traffic will fail until Warp recovers. You can implement fallback routing by modifying the `warp-postup.sh` scripts (advanced).

### Q: Can I see my Warp usage statistics?

**A**: Cloudflare doesn't provide detailed usage stats. You can monitor traffic using `wg show warp` for basic metrics.

### Q: Is Warp compatible with all applications?

**A**: Yes, Warp works at the network layer and is application-agnostic. All protocols (HTTP, HTTPS, SSH, etc.) work normally.

### Q: Can I have different zones use different Warp accounts?

**A**: Currently, all zones share one Warp account. Multi-account support could be added as a future enhancement.

### Q: Does Warp log my traffic?

**A**: Cloudflare states they don't log user traffic. They collect minimal metadata for network operation (deleted after 24-48 hours). See [Cloudflare's Privacy Policy](https://www.cloudflare.com/privacypolicy/) for details.

### Q: Can I use Warp for streaming services?

**A**: Yes, but some streaming services may detect and block Cloudflare IPs. Results vary by service and region.

---

## References

### Official Documentation

- [Cloudflare Warp Client](https://developers.cloudflare.com/cloudflare-one/connections/connect-devices/warp/)
- [wgcf GitHub Repository](https://github.com/ViRb3/wgcf)
- [WireGuard Protocol](https://www.wireguard.com/)
- [Cloudflare Network Map](https://www.cloudflare.com/network/)

### Community Resources

- [Warp Setup Guides](https://www.guyrutenberg.com/2023/07/10/creating-a-wireguard-profile-for-cloudflare-warp/)
- [Performance Benchmarks](https://blog.cloudflare.com/benchmarking-edge-network-performance/)
- [Security Analysis](https://blog.cloudflare.com/warp-technical-challenges/)

### Related Wiregate Documentation

- [CAKE Traffic Shaping](./CAKE_TRAFFIC_SHAPING.md)
- [TLS Tunnel Setup](../Docs/TLS-TUNNEL-SETUP.md)
- [Wiregate Main README](../README.md)

---

## Support

For issues, questions, or feature requests related to Cloudflare Warp integration:

1. Check this documentation thoroughly
2. Review container logs: `docker logs wiregate | grep WARP`
3. Test manually: `docker exec -it wiregate /opt/wireguarddashboard/src/warp-manager.sh check`
4. Open an issue on the [Wiregate GitHub repository](https://github.com/NOXCIS/Wiregate)

---

## License

Cloudflare Warp integration for Wiregate is provided as part of the Wiregate project and follows the project's licensing terms.

**Third-Party Components**:
- **wgcf**: MIT License (ViRb3/wgcf)
- **WireGuard**: GPL v2
- **Cloudflare Warp**: Cloudflare Terms of Service

Always ensure compliance with Cloudflare's Terms of Service when using Warp.
