# Packet Loss Fix Plan

## Root Causes Identified

1. **Serialized UDP receive**: `m_udp_recv_in_progress` flag prevents overlapping receives
2. **Small buffer**: 4096 bytes buffer can't hold many packets
3. **No UDP receive queue**: Packets are dropped if TCP send is busy
4. **Single TCP connection**: All UDP clients share one connection
5. **No socket buffer tuning**: Default UDP receive buffer may be too small

## Fix Strategy (Priority Order)

### Priority 1: Immediate Fixes (Can be done now)

#### 1.1 Remove UDP Receive Serialization
**Problem**: `m_udp_recv_in_progress` flag prevents processing multiple UDP packets concurrently.

**Solution**: Remove the flag and allow overlapping UDP receives. The async operations are already thread-safe.

**Impact**: High - Allows multiple packets to be queued for TCP send

#### 1.2 Increase UDP Receive Buffer Size
**Problem**: 4096 byte buffer can only hold ~16 packets (256 bytes each).

**Solution**: 
- Increase buffer to 64KB or 128KB
- Configure UDP socket receive buffer size using `SO_RCVBUF`

**Impact**: High - Can buffer more packets before dropping

#### 1.3 Add UDP Receive Queue
**Problem**: If TCP send is in progress, new UDP packets are dropped.

**Solution**: Add a queue to buffer UDP packets while TCP send is busy:
```cpp
std::queue<std::pair<asio::ip::udp::endpoint, std::vector<char>>> m_udp_queue;
```

**Impact**: Very High - Prevents packet drops during TCP send

#### 1.4 Configure Socket Buffer Sizes
**Problem**: Default OS UDP receive buffer may be too small (often 200KB).

**Solution**: Set `SO_RCVBUF` to 1MB or more:
```cpp
asio::socket_base::receive_buffer_size option(1024 * 1024); // 1MB
m_socket_udp_acc.set_option(option);
```

**Impact**: High - OS can buffer more packets before dropping

### Priority 2: Medium-term Improvements

#### 2.1 Connection Pooling
**Problem**: Single TCP connection is a bottleneck.

**Solution**: Maintain a pool of 2-4 TCP connections and round-robin packets across them.

**Impact**: Very High - Distributes load across multiple connections

#### 2.2 Per-Source Connection Management
**Problem**: All UDP sources share one connection.

**Solution**: Create separate TCP connection for each unique UDP source address (with connection reuse).

**Impact**: Very High - Eliminates cross-client interference

### Priority 3: Long-term Architectural Changes

#### 3.1 Full Per-Client Connection Model
**Problem**: Current architecture doesn't scale.

**Solution**: Complete rewrite to match Go implementation - one TCP connection per UDP client.

**Impact**: Highest - Best performance but requires major refactoring

## Recommended Implementation Order

1. ✅ **Remove UDP receive serialization** (easiest, high impact) - **DONE**
2. ✅ **Increase buffer sizes** (easy, high impact) - **DONE** (4096 → 65536 bytes)
3. ✅ **Configure socket buffers** (easy, high impact) - **DONE** (1MB UDP receive buffer)
4. ✅ **Add UDP receive queue** (medium complexity, very high impact) - **DONE**
5. ✅ **Connection pooling** (medium complexity, very high impact) - **DONE** (Combined with #6)
6. ✅ **Per-source connections** (complex, very high impact) - **DONE**

## Implemented Fixes

### ✅ Fix 1.1: Removed UDP Receive Serialization
- **File**: `src/udp2tcp.cpp`, `src/udp2tcp.h`
- **Change**: Removed `m_udp_recv_in_progress` flag that prevented overlapping UDP receives
- **Impact**: Multiple UDP packets can now be queued for TCP send concurrently

### ✅ Fix 1.2: Increased Buffer Sizes
- **File**: `src/udp2tcp.h`
- **Change**: Increased `m_buffer_send` and `m_buffer_udp_send` from 4096 to 65536 bytes (64KB)
- **Impact**: Can buffer ~256 packets (256 bytes each) instead of ~16 packets

### ✅ Fix 1.4: Configured Socket Buffer Sizes
- **File**: `src/udp2tcp.cpp`
- **Change**: Set UDP socket receive buffer to 1MB using `SO_RCVBUF`
- **Impact**: OS can buffer more packets before dropping (default is often ~200KB)

### ✅ Fix 1.3: Added UDP Receive Queue
- **File**: `src/udp2tcp.cpp`, `src/udp2tcp.h`
- **Change**: Added `queued_packet` struct and `m_udp_queue` to buffer packets when TCP send is busy
- **Impact**: Packets are queued instead of dropped when TCP connection is busy

### ✅ Fix 2.1 & 2.2: Per-Source Connection Management (Combined with Connection Pooling)
- **File**: `src/udp2tcp.cpp`, `src/udp2tcp.h`
- **Change**: 
  - Added `source_connection` struct with per-source TCP socket, buffers, and state
  - Added `m_source_connections` unordered_map keyed by UDP source endpoint
  - Created dedicated TCP connection for each unique UDP source (WireGuard peer)
  - Each connection has its own send queue, buffers, and WebSocket stream
  - Added automatic cleanup of idle connections (120 second timeout)
  - Maintains WireGuard/AmneziaWG compatibility by preserving source endpoints
- **Impact**: Each WireGuard peer gets isolated connection, eliminating cross-client interference

## Expected Results

- **Priority 1 fixes**: Should reduce loss from 60% to <10% for 5-10 concurrent clients
- **Priority 2 fixes**: Should reduce loss to <1% for 20-50 concurrent clients
- **All fixes combined**: Should eliminate loss for any number of clients (up to MAX_CONNECTIONS=100)

