# Traffic Shaping API Examples

This document provides practical examples for using Wiregate's traffic shaping API with different schedulers.

## Table of Contents

- [Basic Examples](#basic-examples)
- [Scheduler-Specific Examples](#scheduler-specific-examples)
- [Real-World Scenarios](#real-world-scenarios)
- [Batch Operations](#batch-operations)
- [Error Handling](#error-handling)

---

## Basic Examples

### Set Rate Limits with CAKE

```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/=",
    "upload_rate": 5000,
    "download_rate": 10000,
    "scheduler_type": "cake"
  }'
```

**Response:**
```json
{
  "status": true,
  "message": "Successfully configured rate limiting for peer abc123 on interface ADMINS"
}
```

### Get Current Rate Limits

```bash
curl -X GET "http://localhost:8000/api/get_peer_rate_limit?interface=ADMINS&peer_key=AbCdEfGhIjKlMnOpQrStUvWxYz0123456789%2B%2F%3D" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status": true,
  "message": "Rate limits retrieved successfully",
  "data": {
    "upload_rate": 5000.0,
    "download_rate": 10000.0,
    "scheduler_type": "cake"
  }
}
```

### Remove Rate Limits

```bash
curl -X POST http://localhost:8000/api/remove_peer_rate_limit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/="
  }'
```

**Response:**
```json
{
  "status": true,
  "message": "Rate limits removed successfully for peer abc123 on interface ADMINS"
}
```

---

## Scheduler-Specific Examples

### CAKE - Recommended for Most Use Cases

**Home/Office VPN:**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "MEMBERS",
    "peer_key": "member_key_here",
    "upload_rate": 50000,
    "download_rate": 100000,
    "scheduler_type": "cake"
  }'
```

**Gaming VPN (Low Latency Priority):**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "gamer_key_here",
    "upload_rate": 10000,
    "download_rate": 50000,
    "scheduler_type": "cake"
  }'
```

**Benefits:** Automatic bufferbloat control, per-flow fairness, optimal for gaming/VoIP

### HTB - Simple Rate Limiting

**Basic Bandwidth Cap:**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "GUESTS",
    "peer_key": "guest_key_here",
    "upload_rate": 1000,
    "download_rate": 5000,
    "scheduler_type": "htb"
  }'
```

**Benefits:** Low CPU overhead, simple configuration, works on all kernels

### HFSC - Guaranteed Bandwidth

**VoIP/Video Conferencing (Guaranteed Minimum):**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "voip_user_key",
    "upload_rate": 2000,
    "download_rate": 2000,
    "scheduler_type": "hfsc"
  }'
```

**Benefits:** Guaranteed minimum bandwidth, low-latency service curves

---

## Real-World Scenarios

### Scenario 1: Multi-Tier VPN Service

**Admin Tier (Unlimited):**
```bash
# No rate limits applied - full bandwidth
```

**Premium Tier (100 Mbps):**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "MEMBERS",
    "peer_key": "premium_user_key",
    "upload_rate": 10000,
    "download_rate": 100000,
    "scheduler_type": "cake"
  }'
```

**Standard Tier (50 Mbps):**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "MEMBERS",
    "peer_key": "standard_user_key",
    "upload_rate": 5000,
    "download_rate": 50000,
    "scheduler_type": "cake"
  }'
```

**Free Tier (10 Mbps):**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "GUESTS",
    "peer_key": "free_user_key",
    "upload_rate": 1000,
    "download_rate": 10000,
    "scheduler_type": "htb"
  }'
```

### Scenario 2: Office VPN with Department Limits

**IT Department (No Limits):**
```bash
# No rate limits - unrestricted access
```

**Development Team (50 Mbps):**
```bash
for peer_key in dev_peer_1 dev_peer_2 dev_peer_3; do
  curl -X POST http://localhost:8000/api/set_peer_rate_limit \
    -H "Content-Type: application/json" \
    -d "{
      \"interface\": \"MEMBERS\",
      \"peer_key\": \"$peer_key\",
      \"upload_rate\": 5000,
      \"download_rate\": 50000,
      \"scheduler_type\": \"cake\"
    }"
done
```

**Sales Team (20 Mbps):**
```bash
for peer_key in sales_peer_1 sales_peer_2 sales_peer_3; do
  curl -X POST http://localhost:8000/api/set_peer_rate_limit \
    -H "Content-Type: application/json" \
    -d "{
      \"interface\": \"MEMBERS\",
      \"peer_key\": \"$peer_key\",
      \"upload_rate\": 2000,
      \"download_rate\": 20000,
      \"scheduler_type\": \"cake\"
    }"
done
```

### Scenario 3: Family VPN with Per-Device Limits

**Parents (No Limits):**
```bash
# No rate limits
```

**Kids (Restricted During School Hours):**
```bash
# School hours: 8 AM - 3 PM - 5 Mbps
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "GUESTS",
    "peer_key": "kids_device_key",
    "upload_rate": 500,
    "download_rate": 5000,
    "scheduler_type": "cake"
  }'

# After school: 3 PM - 9 PM - 25 Mbps
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "GUESTS",
    "peer_key": "kids_device_key",
    "upload_rate": 2500,
    "download_rate": 25000,
    "scheduler_type": "cake"
  }'
```

### Scenario 4: Testing Environment

**Simulate Slow Connection (56K Modem):**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "test_peer_key",
    "upload_rate": 48,
    "download_rate": 56,
    "scheduler_type": "htb"
  }'
```

**Simulate 3G Connection:**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "test_peer_key",
    "upload_rate": 384,
    "download_rate": 7200,
    "scheduler_type": "cake"
  }'
```

**Simulate 4G LTE:**
```bash
curl -X POST http://localhost:8000/api/set_peer_rate_limit \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "ADMINS",
    "peer_key": "test_peer_key",
    "upload_rate": 10000,
    "download_rate": 50000,
    "scheduler_type": "cake"
  }'
```

---

## Batch Operations

### Python Script - Set Limits for Multiple Peers

```python
#!/usr/bin/env python3
import requests
import json

API_BASE = "http://localhost:8000/api"
AUTH_TOKEN = "your_auth_token_here"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}"
}

# Define peers and their limits
peers = [
    {"interface": "MEMBERS", "peer_key": "peer1_key", "upload": 5000, "download": 10000},
    {"interface": "MEMBERS", "peer_key": "peer2_key", "upload": 10000, "download": 20000},
    {"interface": "GUESTS", "peer_key": "peer3_key", "upload": 1000, "download": 5000},
]

for peer in peers:
    data = {
        "interface": peer["interface"],
        "peer_key": peer["peer_key"],
        "upload_rate": peer["upload"],
        "download_rate": peer["download"],
        "scheduler_type": "cake"
    }

    response = requests.post(f"{API_BASE}/set_peer_rate_limit",
                            headers=headers,
                            json=data)

    if response.status_code == 200:
        result = response.json()
        if result["status"]:
            print(f"✓ Set limits for {peer['peer_key'][:8]}...")
        else:
            print(f"✗ Failed for {peer['peer_key'][:8]}: {result['message']}")
    else:
        print(f"✗ HTTP Error {response.status_code} for {peer['peer_key'][:8]}")
```

### Bash Script - Apply Same Limits to All Peers on Interface

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api"
AUTH_TOKEN="your_auth_token_here"
INTERFACE="MEMBERS"
UPLOAD_RATE=5000
DOWNLOAD_RATE=10000
SCHEDULER="cake"

# Get all peers (you'd need to implement this based on your API)
PEER_KEYS=(
  "peer_key_1"
  "peer_key_2"
  "peer_key_3"
)

for PEER_KEY in "${PEER_KEYS[@]}"; do
  echo "Setting limits for peer: ${PEER_KEY:0:8}..."

  curl -s -X POST "${API_BASE}/set_peer_rate_limit" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -d "{
      \"interface\": \"${INTERFACE}\",
      \"peer_key\": \"${PEER_KEY}\",
      \"upload_rate\": ${UPLOAD_RATE},
      \"download_rate\": ${DOWNLOAD_RATE},
      \"scheduler_type\": \"${SCHEDULER}\"
    }" | jq -r '.message'
done
```

---

## Error Handling

### Handle Common Errors

```python
import requests
import json

def set_rate_limit(interface, peer_key, upload, download, scheduler="cake"):
    """Set rate limit with proper error handling"""

    API_BASE = "http://localhost:8000/api"
    AUTH_TOKEN = "your_token"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }

    data = {
        "interface": interface,
        "peer_key": peer_key,
        "upload_rate": upload,
        "download_rate": download,
        "scheduler_type": scheduler
    }

    try:
        response = requests.post(
            f"{API_BASE}/set_peer_rate_limit",
            headers=headers,
            json=data,
            timeout=30
        )

        # Check HTTP status
        if response.status_code == 401:
            return {"success": False, "error": "Authentication failed"}
        elif response.status_code == 404:
            return {"success": False, "error": "API endpoint not found"}
        elif response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}"}

        # Parse response
        result = response.json()

        if result["status"]:
            return {"success": True, "message": result["message"]}
        else:
            # Handle specific API errors
            error_msg = result.get("message", "Unknown error")

            if "not found" in error_msg.lower():
                return {"success": False, "error": "Peer or interface not found"}
            elif "scheduler" in error_msg.lower():
                return {"success": False, "error": "Scheduler conflict or not supported"}
            elif "rate" in error_msg.lower():
                return {"success": False, "error": "Invalid rate limit value"}
            else:
                return {"success": False, "error": error_msg}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to API"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON response"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

# Usage
result = set_rate_limit("ADMINS", "peer_key_here", 5000, 10000, "cake")
if result["success"]:
    print(f"✓ {result['message']}")
else:
    print(f"✗ Error: {result['error']}")
```

### Retry Logic with Exponential Backoff

```python
import time
import requests

def set_rate_limit_with_retry(interface, peer_key, upload, download,
                              scheduler="cake", max_retries=3):
    """Set rate limit with retry logic"""

    for attempt in range(max_retries):
        result = set_rate_limit(interface, peer_key, upload, download, scheduler)

        if result["success"]:
            return result

        # Don't retry on authentication or validation errors
        if any(err in result["error"].lower() for err in ["auth", "not found", "invalid"]):
            return result

        # Exponential backoff
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            print(f"Retry {attempt + 1}/{max_retries} in {wait_time}s...")
            time.sleep(wait_time)

    return {"success": False, "error": "Max retries exceeded"}
```

---

## Additional Notes

### Rate Limit Units
- All rates are in **Kilobits per second (Kbps)**
- Example conversions:
  - 1 Mbps = 1000 Kbps
  - 100 Mbps = 100000 Kbps
  - 1 Gbps = 1000000 Kbps

### URL Encoding
When using peer public keys in GET requests, ensure proper URL encoding:
```bash
# Encode + as %2B and / as %2F
PEER_KEY="AbCdEfGhIjKlMnOpQrStUvWxYz0123456789+/="
ENCODED_KEY="AbCdEfGhIjKlMnOpQrStUvWxYz0123456789%2B%2F%3D"

curl -X GET "http://localhost:8000/api/get_peer_rate_limit?interface=ADMINS&peer_key=${ENCODED_KEY}"
```

### Testing Rate Limits
Use `iperf3` to test bandwidth limits:

```bash
# On server
iperf3 -s

# On client (connected via WireGuard)
iperf3 -c server_ip -t 30 -i 1
```

Expected results should match configured rate limits (±5% variance).

---

For more information, see the [Traffic Shaping Guide](../TRAFFIC_SHAPING.md).
