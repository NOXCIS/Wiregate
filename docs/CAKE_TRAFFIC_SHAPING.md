# CAKE Traffic Shaping for Wiregate

## Overview

This document describes the CAKE (Common Applications Kept Enhanced) traffic shaping integration for Wiregate. CAKE is a modern Linux kernel qdisc (queuing discipline) that provides superior bufferbloat control, fair queuing, and automatic bandwidth management compared to traditional traffic shapers.

## Table of Contents

- [What is CAKE?](#what-is-cake)
- [Why Use CAKE?](#why-use-cake)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Usage](#usage)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [References](#references)

---

## What is CAKE?

**CAKE** (Common Applications Kept Enhanced) is a comprehensive queue management system designed to replace older traffic shaping solutions like HTB + fq_codel. It was developed to address bufferbloat issues and improve network performance with minimal configuration.

### Key Features

1. **Automatic Burst Handling**: Unlike token-bucket shapers, CAKE uses a deficit-mode shaper that automatically bursts precisely as needed to maintain configured throughput without initial burst issues.

2. **Triple-Isolate Fair Queuing**: CAKE's novel "triple-isolate" mode (enabled by default) balances per-host and per-flow fair queuing even through NAT, ensuring fair bandwidth distribution among multiple clients.

3. **Built-in ACK Filtering**: Automatically filters redundant TCP ACKs to improve performance, especially on asymmetric connections.

4. **GSO Packet Splitting**: Properly handles Generic Segmentation Offload (GSO) packets for accurate traffic shaping.

5. **NAT Awareness**: Correctly identifies flows through NAT, ensuring fair queuing for each client behind the NAT.

6. **Minimal Configuration**: Sensible defaults are provided for every parameter. In many cases, only the bandwidth limit needs to be set.

---

## Why Use CAKE?

### Benefits for Wiregate Users

- **Reduced Latency**: CAKE significantly reduces bufferbloat, keeping latency low even under heavy load
- **Fair Bandwidth Distribution**: Ensures all VPN clients get fair access to available bandwidth
- **Automatic Rate Adaptation**: Can automatically adjust to actual link speeds
- **Protection Against Abuse**: Prevents individual clients from monopolizing bandwidth
- **Improved VoIP/Gaming Performance**: Low latency and jitter for real-time applications
- **Better Video Streaming**: Smooth streaming without buffering issues

### Comparison with Other Traffic Shapers

| Feature | CAKE | HTB + fq_codel | No Shaping |
|---------|------|----------------|------------|
| Bufferbloat Control | Excellent | Good | None |
| Configuration Complexity | Minimal | Moderate | N/A |
| NAT Awareness | Yes | No | N/A |
| Per-Flow Fairness | Yes | Yes | No |
| ACK Filtering | Built-in | Manual | No |
| CPU Overhead | Low | Low-Medium | Minimal |

---

## Architecture

### Integration Points

CAKE is integrated into Wiregate at the WireGuard interface level. When a WireGuard configuration (zone) is started, CAKE qdisc can be automatically applied to shape traffic for that zone.

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Host (Kernel)                     │
├─────────────────────────────────────────────────────────────┤
│  eth0 (Host NIC)                                            │
│         ↓                                                    │
│    docker0 bridge (10.2.0.0/24)                            │
│         ↓                                                    │
├─────────────────────────────────────────────────────────────┤
│                 WireGate Container                          │
│  ├─ MEMBERS (192.168.10.0/24)                             │
│  │  └─ PostUp: iptables + CAKE (100mbit)                  │
│  │                                                          │
│  ├─ ADMINS (10.0.0.0/24)                                  │
│  │  └─ PostUp: iptables + CAKE (1gbit)                    │
│  │                                                          │
│  ├─ GUESTS (192.168.20.0/24)                              │
│  │  └─ PostUp: iptables + CAKE (50mbit)                   │
│  │                                                          │
│  └─ LANP2P (172.16.0.0/24)                                │
│     └─ PostUp: iptables + CAKE (100mbit)                  │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
WG-Dash/
├── Dockerfile                    # Added iproute2 package
├── src/
│   ├── traffic_control.py       # Python wrapper for tc commands
│   └── iptable-rules/
│       ├── Admins/
│       │   ├── postup.sh        # Calls cake-setup.sh
│       │   ├── postdown.sh      # Calls cake-teardown.sh
│       │   ├── cake-setup.sh    # CAKE configuration
│       │   └── cake-teardown.sh # CAKE cleanup
│       ├── Members/
│       │   └── ... (same structure)
│       ├── Guest/
│       │   └── ... (same structure)
│       └── LAN-only-users/
│           └── ... (same structure)
```

---

## Configuration

### Default Bandwidth Limits

CAKE comes with sensible defaults for each WireGuard zone:

| Zone | Default Bandwidth | Use Case |
|------|------------------|----------|
| **ADMINS** | 1 Gbit/s | Full-speed access for administrators |
| **MEMBERS** | 100 Mbit/s | Standard user access |
| **GUESTS** | 50 Mbit/s | Limited access for guest users |
| **LANP2P** | 100 Mbit/s | LAN-only peer-to-peer connections |

### Environment Variables

CAKE is controlled via environment variables that can be set in your `.env` file or Docker Compose configuration:

#### Global CAKE Toggle

```bash
# Enable or disable CAKE traffic shaping
CAKE_ENABLED=true          # Set to "true" to enable, "false" to disable (default: false)
```

#### Per-Zone Bandwidth Configuration

```bash
# Bandwidth limits per zone (examples)
CAKE_BANDWIDTH_ADMINS=1gbit
CAKE_BANDWIDTH_MEMBERS=100mbit
CAKE_BANDWIDTH_GUESTS=50mbit
CAKE_BANDWIDTH_LANP2P=100mbit
```

#### CAKE Parameters

```bash
# Overhead compensation (bytes added to each packet)
CAKE_OVERHEAD=0            # Default: 0, Range: -64 to 256

# Minimum packet unit (rounds packet size up)
CAKE_MPU=0                 # Default: 0, Range: 0 to 256

# Memory limit for queues
CAKE_MEMLIMIT=32m          # Default: 32m (32 megabytes)

# CAKE options (space-separated list)
CAKE_OPTIONS="besteffort triple-isolate nat nowash split-gso"
```

### CAKE Options Explained

| Option | Description | Recommended |
|--------|-------------|-------------|
| `besteffort` | Single queue mode (no priority handling) | Yes for VPN |
| `triple-isolate` | Per-host and per-flow fairness through NAT | Yes |
| `nat` | Enable NAT awareness | Yes for VPN |
| `nowash` | Don't clear DSCP markings | Yes |
| `wash` | Clear DSCP markings | No for VPN |
| `split-gso` | Split GSO packets for accurate shaping | Yes |
| `ack-filter` | Filter redundant TCP ACKs | Optional |
| `ack-filter-aggressive` | More aggressive ACK filtering | Optional |
| `autorate-ingress` | Automatic rate adaptation for ingress | Optional |

---

## Usage

### Enabling CAKE

1. **Set Environment Variables**

   Edit your `.env` file or `docker-compose.yml`:

   ```bash
   CAKE_ENABLED=true
   CAKE_BANDWIDTH_MEMBERS=100mbit
   ```

2. **Rebuild and Restart Container**

   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. **Start WireGuard Configuration**

   When you start a WireGuard configuration through the dashboard, CAKE will be automatically applied if `CAKE_ENABLED=true`.

### Verifying CAKE is Active

#### Check via tc command

```bash
# Enter the container
docker exec -it wiregate bash

# Check CAKE status for a specific interface
tc qdisc show dev MEMBERS

# Expected output (CAKE is active):
# qdisc cake 1: root refcnt 2 bandwidth 100Mbit besteffort triple-isolate nat nowash split-gso ...
```

#### Check via Python API

```python
from traffic_control import CAKEQdisc

# Check if CAKE is available
print(f"CAKE available: {CAKEQdisc.is_available()}")

# Get CAKE status for an interface
status = CAKEQdisc.get_status('MEMBERS')
print(f"MEMBERS interface status: {status}")

# Get detailed statistics
stats = CAKEQdisc.get_stats('MEMBERS')
print(f"CAKE statistics: {stats}")
```

### Disabling CAKE

To disable CAKE without removing the integration:

```bash
CAKE_ENABLED=false
```

Restart the WireGuard configuration or container for changes to take effect.

---

## Advanced Configuration

### Custom Bandwidth Per Zone

You can set different bandwidth limits for different zones based on your requirements:

```bash
# High-bandwidth for admins
CAKE_BANDWIDTH_ADMINS=10gbit

# Moderate for regular users
CAKE_BANDWIDTH_MEMBERS=200mbit

# Low for guests
CAKE_BANDWIDTH_GUESTS=25mbit

# LAN-only users don't need limiting (or set high value)
CAKE_BANDWIDTH_LANP2P=1gbit
```

### Overhead Compensation

If you're using PPPoE, ATM, or other encapsulation, you may need overhead compensation:

```bash
# PPPoE overhead (PPPoE header + Ethernet)
CAKE_OVERHEAD=18

# ATM overhead (for ADSL)
CAKE_OVERHEAD=44
CAKE_OPTIONS="besteffort triple-isolate nat nowash split-gso atm"
```

### Aggressive ACK Filtering

For asymmetric connections (e.g., cable modem with 200/10 Mbps):

```bash
CAKE_OPTIONS="besteffort triple-isolate nat nowash split-gso ack-filter-aggressive"
```

### Autorate for Variable Bandwidth

If your link bandwidth varies (e.g., cellular, satellite):

```bash
CAKE_OPTIONS="besteffort triple-isolate nat nowash split-gso autorate-ingress"
```

### Manual Configuration

You can also manually apply CAKE using the Python API:

```python
from traffic_control import TrafficControl, CAKEQdisc

# Apply CAKE to a specific interface
CAKEQdisc.apply(
    interface='MEMBERS',
    bandwidth='100mbit',
    overhead=0,
    mpu=0,
    options=['besteffort', 'triple-isolate', 'nat', 'nowash', 'split-gso'],
    memlimit='32m'
)

# Remove CAKE from an interface
CAKEQdisc.remove('MEMBERS')

# Get statistics
stats = CAKEQdisc.get_stats('MEMBERS')
print(f"Bytes sent: {stats['parsed']['bytes_sent']}")
print(f"Packets dropped: {stats['parsed']['dropped']}")
```

---

## Troubleshooting

### CAKE Not Working

**Problem**: CAKE doesn't seem to be applied to the interface.

**Solutions**:

1. **Check if CAKE is enabled**:
   ```bash
   echo $CAKE_ENABLED
   # Should output: true
   ```

2. **Check if iproute2 is installed**:
   ```bash
   docker exec -it wiregate tc -help | grep cake
   # Should show CAKE in the output
   ```

3. **Check kernel support**:
   ```bash
   # On the host system
   modprobe sch_cake
   lsmod | grep cake
   ```

4. **Check container logs**:
   ```bash
   docker logs wiregate | grep CAKE
   # Look for "[CAKE-*] CAKE traffic shaper applied successfully"
   ```

### Interface Not Found

**Problem**: CAKE setup script reports "Interface not found".

**Solutions**:

1. The WireGuard interface may not be up yet. The script waits up to 10 seconds for the interface to appear.

2. Check if WireGuard configuration is active:
   ```bash
   wg show
   ip link show MEMBERS
   ```

### High Latency Despite CAKE

**Problem**: Latency is still high even with CAKE enabled.

**Solutions**:

1. **Bandwidth too high**: Set CAKE bandwidth to 90-95% of your actual link speed:
   ```bash
   # If your link is 100 Mbit/s, try:
   CAKE_BANDWIDTH_MEMBERS=95mbit
   ```

2. **Check for bottlenecks elsewhere**: CAKE only shapes at the WireGuard interface. Check for bottlenecks at:
   - Host network interface
   - ISP connection
   - Remote VPN peer

3. **Enable autorate**:
   ```bash
   CAKE_OPTIONS="besteffort triple-isolate nat nowash split-gso autorate-ingress"
   ```

### Permission Errors

**Problem**: "Operation not permitted" when applying CAKE.

**Solutions**:

1. Ensure container has `NET_ADMIN` capability (should be default in Wiregate):
   ```yaml
   cap_add:
     - NET_ADMIN
   ```

2. Check if running with correct privileges:
   ```bash
   docker inspect wiregate | grep -i cap_add
   ```

---

## Performance Tuning

### Memory Limit

The `CAKE_MEMLIMIT` parameter controls how much memory CAKE uses for queues. More memory allows larger queues (more buffering) but can increase latency.

- **Low latency applications (gaming, VoIP)**: Use smaller values like `16m` or `8m`
- **High throughput applications (large downloads)**: Use larger values like `64m` or `128m`
- **Balanced (default)**: `32m` works well for most scenarios

```bash
# Low latency profile
CAKE_MEMLIMIT=16m

# High throughput profile
CAKE_MEMLIMIT=64m
```

### Bandwidth Allocation

Guidelines for setting bandwidth limits:

1. **Start with 90-95% of link speed**: CAKE works best when set slightly below actual capacity
   ```bash
   # For a 1 Gbps link:
   CAKE_BANDWIDTH_ADMINS=950mbit
   ```

2. **Consider total available bandwidth**: If multiple zones are active, ensure total doesn't exceed link capacity

3. **Monitor and adjust**: Use `tc -s qdisc show dev MEMBERS` to check for drops and overlimits

### Priority Queuing (Optional)

CAKE supports priority tins based on DSCP markings. To enable:

```bash
# Use diffserv4 instead of besteffort
CAKE_OPTIONS="diffserv4 triple-isolate nat nowash split-gso"
```

This creates 4 priority levels:
- **Bulk**: Background traffic
- **Best Effort**: Normal traffic
- **Video**: Streaming media
- **Voice**: Real-time traffic (VoIP, gaming)

---

## Monitoring CAKE Performance

### Real-time Statistics

```bash
# Show detailed statistics
watch -n 1 'tc -s qdisc show dev MEMBERS'

# Key metrics to watch:
# - Sent: Total bytes and packets sent
# - dropped: Packets dropped due to queue limits
# - overlimits: Packets that exceeded bandwidth limit
# - backlog: Current queue size
```

### Python Monitoring Script

```python
#!/usr/bin/env python3
from traffic_control import CAKEQdisc
import time

while True:
    for zone in ['ADMINS', 'MEMBERS', 'GUESTS', 'LANP2P']:
        stats = CAKEQdisc.get_stats(zone)
        if stats:
            parsed = stats['parsed']
            print(f"{zone}:")
            print(f"  Sent: {parsed.get('bytes_sent', 0)} bytes")
            print(f"  Dropped: {parsed.get('dropped', 0)} packets")
            print(f"  Bandwidth: {parsed.get('bandwidth', 'N/A')}")
            print()
    time.sleep(5)
```

---

## Performance Impact

### CPU Overhead

CAKE is designed to be efficient, but there is some CPU overhead:

- **Low traffic (< 100 Mbps)**: Negligible CPU usage (< 1%)
- **Medium traffic (100-500 Mbps)**: Low CPU usage (1-5%)
- **High traffic (500+ Mbps)**: Moderate CPU usage (5-15%)

On modern multi-core systems, CAKE scales well and should not be a bottleneck for most deployments.

### Latency Impact

CAKE is designed to *reduce* latency by preventing bufferbloat:

- **Without CAKE**: Latency can spike to 500ms+ under load
- **With CAKE**: Latency typically stays under 20ms even under heavy load

---

## References

### Official Documentation

- [Linux tc-cake man page](https://man7.org/linux/man-pages/man8/tc-cake.8.html)
- [Bufferbloat.net CAKE Technical Documentation](https://www.bufferbloat.net/projects/codel/wiki/CakeTechnical/)
- [CAKE GitHub Repository](https://github.com/dtaht/tc-adv)

### Articles and Guides

- [GrapheneOS Server Traffic Shaping](https://grapheneos.org/articles/server-traffic-shaping)
- [LWN.net: Add Common Applications Kept Enhanced (cake) qdisc](https://lwn.net/Articles/752777/)

### Research Papers

- [Flow Queue CoDel (FQ-CoDel) RFC 8290](https://tools.ietf.org/html/rfc8290)
- [Bufferbloat: Dark Buffers in the Internet](https://queue.acm.org/detail.cfm?id=2209336)

---

## FAQ

### Q: Does CAKE work with IPv6?

**A**: Yes, CAKE fully supports IPv6 traffic and correctly handles both IPv4 and IPv6 flows.

### Q: Can I use CAKE with Tor proxy enabled?

**A**: Yes, CAKE works independently of Tor proxy settings. It shapes traffic at the WireGuard interface level, regardless of whether traffic is routed through Tor.

### Q: Does CAKE affect encryption?

**A**: No, CAKE operates on already-encrypted packets. It sees WireGuard packets as encrypted UDP and shapes them accordingly.

### Q: Can I have different CAKE settings for different peers in the same zone?

**A**: Not directly at the CAKE level, but CAKE's triple-isolate mode automatically provides fair queuing per peer. For more granular control, you would need to create separate WireGuard zones.

### Q: What happens if I set bandwidth higher than my link speed?

**A**: CAKE will not provide effective bufferbloat control. Always set CAKE bandwidth to 90-95% of actual link speed for best results.

### Q: Can I disable CAKE for specific zones?

**A**: Yes, you can manually edit the `postup.sh` script for that zone and remove or comment out the CAKE setup call, or set `CAKE_ENABLED=false` and manually enable it only for specific zones.

### Q: Does CAKE work with hardware offload features?

**A**: CAKE requires Generic Segmentation Offload (GSO) packets to be split for accurate shaping. The `split-gso` option (enabled by default) handles this automatically.

---

## Support

For issues, questions, or feature requests related to CAKE integration:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review container logs: `docker logs wiregate | grep CAKE`
3. Open an issue on the [Wiregate GitHub repository](https://github.com/NOXCIS/Wiregate)

---

## License

CAKE traffic shaper is part of the Linux kernel and is licensed under GPL v2.

This integration documentation is provided as part of Wiregate and follows the project's licensing terms.
