# Concurrent Test Results Analysis

## Important Note on Test Results

**Bug Found**: The test results show `packets_sent` = `packets_received` but `packets_lost` > 0, which is mathematically inconsistent. This indicates a bug in the test client where duplicate packets are being counted as "received" even though the original packet is still marked as lost.

**Fix Applied**: Updated `stress-udp-client.py` to only count unique packets (those in `pending_packets`) as received. Duplicate packets are no longer counted in `packets_received`, ensuring `packets_lost = packets_sent - packets_received`.

## Summary of Issues

### 1. High Packet Loss with Concurrent Clients (60%+)

**Problem:**
- 1 client: 0% loss ✅
- 5 clients: 59.94% loss ❌
- 10 clients: 64.16% loss ❌
- 20 clients: 60.3% loss ❌
- 50 clients: 63.54% loss ❌

**Root Cause:**
The `wg-tcp-tunnel` client (`udp2tcp`) uses a **single shared TCP connection** for all UDP clients. The architecture is:

```
Multiple UDP Clients → Single UDP Listener → Single TCP Connection → Server
```

**Bottlenecks:**
1. **Single UDP receive handler**: The `m_udp_recv_in_progress` flag prevents overlapping UDP receives, meaning only one UDP packet can be processed at a time
2. **Single TCP connection**: All UDP packets from different source addresses share the same TCP connection
3. **UDP buffer overflow**: When packets arrive faster than they can be sent over TCP, the UDP receive buffer overflows and packets are dropped
4. **TCP send queue saturation**: The single TCP connection becomes a bottleneck when handling multiple concurrent UDP streams

**Evidence:**
- Buffer size: 4096 bytes (fixed)
- No per-client session management on client side
- Single `m_socket_tcp_dest` connection shared by all UDP sources

### 2. Rapid Connection Creation Test (100% Failure) - FIXED

**Problem:**
- All 100 rapid connection attempts failed (0% success)

**Root Cause:**
The original test used `nc -u -w 0.1` with a 1-second timeout:
```bash
echo "rapid-${i}" | timeout 1 nc -u -w 0.1 "${HOST}" "${PORT}"
```

**Issues:**
1. **TCP connection establishment delay**: Each UDP packet from a new source triggers TCP connection establishment (if not already connected), which takes time (3-way handshake)
2. **Timeout too short**: 0.1s wait time + 1s total timeout is insufficient for:
   - UDP packet to arrive at client
   - TCP connection to be established (if needed)
   - Packet to be tunneled over TCP
   - Server to echo back
   - Response to be tunneled back
   - UDP response to arrive back at test client
3. **`nc` limitations**: `nc` doesn't properly wait for UDP responses - it's connectionless and doesn't handle UDP properly
4. **Shared connection bottleneck**: Even if connected, the single TCP connection is handling all 100 rapid requests simultaneously

**Fix Applied:**
Created a proper Python-based UDP test (`test-rapid-connection.py`) that:
- Properly sends UDP packets and waits for responses
- Uses appropriate timeouts (3 seconds default) to account for tunnel overhead
- Verifies echo responses match sent packets
- Uses threading to send packets rapidly while properly receiving responses
- Reports accurate success/failure rates

The test now properly validates rapid UDP packet handling through the tunnel.

### 3. Mixed Load Test (0% Loss - Works!)

**Why it works:**
- **Staggered start times**: Clients start at different times (0.1s stagger in concurrent test, but mixed load has different rates)
- **Lower total rate**: 5 clients with rates 10, 50, 100, 200, 500 pps = 860 pps total, but spread over 20 seconds
- **Longer duration**: 20 seconds vs 15 seconds gives more time for processing
- **Different rate distribution**: Lower rates (10, 50 pps) give the system time to catch up
- **Less simultaneous burst**: Different rates mean packets don't all arrive at once

**Key difference from concurrent test:**
- Concurrent test: All clients send at 50 pps simultaneously = 250 pps (5 clients) to 2500 pps (50 clients)
- Mixed load: Average rate is lower, and bursts are less synchronized

## Architecture Limitation

The current `wg-tcp-tunnel` client architecture is:

```
┌─────────────┐
│ UDP Client 1│──┐
└─────────────┘  │
┌─────────────┐  │
│ UDP Client 2│──┤
└─────────────┘  │
      ...        │    ┌──────────────┐    ┌──────────────┐
┌─────────────┐  │    │              │    │              │
│ UDP Client N│──┼───▶│ udp2tcp      │───▶│ Single TCP   │──▶ Server
└─────────────┘  │    │ (Single      │    │ Connection   │
                 │    │  Instance)   │    │              │
                 └───▶│              │    └──────────────┘
                      └──────────────┘
```

**Problems:**
1. All UDP clients share one TCP connection
2. UDP receive is serialized (one packet at a time)
3. No per-client queuing or buffering
4. TCP connection becomes bottleneck under load

## Recommendations

### Short-term fixes:
1. ✅ **Increase UDP receive buffer size**: ~~Currently 4096 bytes~~ **DONE** - Increased to 64KB
2. ✅ **Add connection pooling**: ~~Allow multiple TCP connections~~ **DONE** - Implemented per-source connections
3. ✅ **Improve rapid connection test**: ~~Use proper UDP client that waits for responses, increase timeouts~~ **DONE** - Created `test-rapid-connection.py` with proper UDP send/receive handling

### Long-term improvements:
1. ✅ **Per-client TCP connections**: ~~Each UDP source address gets its own TCP connection~~ **DONE** - Implemented in `source_connection` struct
2. ✅ **UDP receive queue**: ~~Buffer incoming UDP packets~~ **DONE** - Added `send_queue` per connection
3. ✅ **Connection multiplexing**: ~~Use a connection pool~~ **DONE** - Per-source connection pool with automatic cleanup
4. **Adaptive rate limiting**: Slow down UDP receive when TCP connection is saturated (not needed with per-source connections)

## Test Improvements Needed

1. ✅ **Rapid connection test**: 
   - ~~Use proper UDP client (not `nc`)~~ **DONE** - Created `test-rapid-connection.py`
   - ~~Increase timeouts to account for TCP connection setup~~ **DONE** - Default 3s timeout
   - ~~Test should verify connection establishment, not just packet send~~ **DONE** - Verifies echo responses

2. **Concurrent test**:
   - Add metrics for TCP connection utilization
   - Monitor UDP buffer drops
   - Measure TCP send queue depth
   - Test with different packet sizes

3. **Mixed load test**:
   - This test is actually validating the system works under realistic conditions
   - Consider making this the primary concurrent test

## Conclusion

~~The high packet loss (60%+) with concurrent clients is expected given the current architecture. The system is designed for single-client or low-concurrency scenarios. For high-concurrency use cases, architectural changes are needed to support per-client TCP connections or connection pooling.~~

**UPDATE**: The architecture has been updated to support per-source TCP connections. Each unique UDP source address (WireGuard peer) now gets its own dedicated TCP connection with:
- Independent send queue
- Dedicated buffers (64KB send, 64KB receive)
- Automatic cleanup of idle connections (120 second timeout)
- Maximum of 100 concurrent connections
- Full WireGuard/AmneziaWG compatibility maintained

This should significantly reduce or eliminate packet loss for concurrent clients.

