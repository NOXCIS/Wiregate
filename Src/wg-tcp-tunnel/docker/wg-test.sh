#!/bin/bash
# WireGuard Test Runner Script
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT
#
# This script runs connectivity, ping, and iperf3 tests through the WireGuard tunnel.
# It can be run from the wg-tester container or directly in the client container.

set -e

# Configuration
CLIENT_CONTAINER="${1:-wg-tcp-tunnel-client-wg}"
SERVER_WG_IP="${2:-10.0.0.1}"
RESULTS_DIR="${3:-/results}"
PING_COUNT="${PING_COUNT:-100}"
IPERF_DURATION="${IPERF_DURATION:-30}"
IPERF_UDP_BANDWIDTH="${IPERF_UDP_BANDWIDTH:-100M}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_test() { echo -e "${CYAN}[TEST]${NC} $1"; }

# Create results directory
mkdir -p "${RESULTS_DIR}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/wireguard_test_${TIMESTAMP}.json"

echo "========================================"
echo " WireGuard Tunnel Test Suite"
echo "========================================"
echo "Client Container: ${CLIENT_CONTAINER}"
echo "Server WG IP:     ${SERVER_WG_IP}"
echo "Results:          ${RESULT_FILE}"
echo "========================================"
echo ""

# Function to run command in client container or locally
run_in_client() {
    if [ -n "${IN_CLIENT_CONTAINER}" ] || [ "$(hostname)" = "${CLIENT_CONTAINER}" ]; then
        # We're already in the client container
        eval "$@"
    elif command -v docker &> /dev/null; then
        docker exec "${CLIENT_CONTAINER}" bash -c "$@"
    else
        log_error "Docker not available and not running in client container"
        return 1
    fi
}

# Initialize results
TESTS_PASSED=0
TESTS_FAILED=0
RESULTS="[]"

# Test 1: WireGuard Interface Status
test_wg_interface() {
    log_test "Test 1: WireGuard Interface Status"
    
    local wg_output
    wg_output=$(run_in_client "wg show wg0 2>/dev/null || echo 'FAILED'")
    
    if echo "$wg_output" | grep -q "FAILED"; then
        log_error "WireGuard interface not found"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    log_info "WireGuard interface is up"
    echo "$wg_output"
    
    # Check for handshake
    local handshake
    handshake=$(run_in_client "wg show wg0 latest-handshakes 2>/dev/null | awk '{print \$2}'" || echo "")
    
    if [ -n "$handshake" ] && [ "$handshake" != "0" ]; then
        log_info "Handshake established (${handshake}s ago)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_warn "No handshake yet"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 2: Basic Connectivity (Ping)
test_ping_connectivity() {
    log_test "Test 2: Basic Connectivity (Ping to ${SERVER_WG_IP})"
    
    local ping_result
    ping_result=$(run_in_client "ping -c 5 -W 2 ${SERVER_WG_IP} 2>&1" || echo "FAILED")
    
    if echo "$ping_result" | grep -q "FAILED" || echo "$ping_result" | grep -q "100% packet loss"; then
        log_error "Ping test failed"
        echo "$ping_result"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    local packets_received
    packets_received=$(echo "$ping_result" | grep -oP '\d+(?= received)')
    
    if [ "${packets_received:-0}" -gt 0 ]; then
        log_info "Ping successful: ${packets_received}/5 packets received"
        echo "$ping_result" | tail -2
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_error "No ping responses received"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 3: Extended Ping Test (Latency and Loss)
test_ping_extended() {
    log_test "Test 3: Extended Ping Test (${PING_COUNT} packets)"
    
    local ping_result
    ping_result=$(run_in_client "ping -c ${PING_COUNT} -i 0.1 ${SERVER_WG_IP} 2>&1" || echo "")
    
    # Extract statistics
    local stats_line
    stats_line=$(echo "$ping_result" | grep -E "packets transmitted|rtt")
    
    if [ -z "$stats_line" ]; then
        log_error "Could not get ping statistics"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    # Parse results
    local transmitted received loss_percent
    transmitted=$(echo "$ping_result" | grep -oP '\d+(?= packets transmitted)')
    received=$(echo "$ping_result" | grep -oP '\d+(?= received)')
    loss_percent=$(echo "$ping_result" | grep -oP '\d+(?=% packet loss)')
    
    local rtt_line avg_latency
    rtt_line=$(echo "$ping_result" | grep "rtt")
    avg_latency=$(echo "$rtt_line" | grep -oP '\d+\.\d+(?=/\d+\.\d+ ms)' | head -2 | tail -1)
    
    log_info "Transmitted: ${transmitted}, Received: ${received}, Loss: ${loss_percent}%"
    log_info "Average latency: ${avg_latency:-N/A} ms"
    
    # Save to results
    PING_RESULT=$(cat << EOF
{
    "test": "ping_extended",
    "packets_transmitted": ${transmitted:-0},
    "packets_received": ${received:-0},
    "loss_percent": ${loss_percent:-100},
    "avg_latency_ms": ${avg_latency:-0}
}
EOF
)
    
    if [ "${loss_percent:-100}" -lt 5 ]; then
        log_info "Ping test passed (loss < 5%)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_warn "Ping test has high packet loss"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 4: iperf3 TCP Bandwidth Test
test_iperf_tcp() {
    log_test "Test 4: iperf3 TCP Bandwidth Test (${IPERF_DURATION}s)"
    
    local iperf_result
    iperf_result=$(run_in_client "iperf3 -c ${SERVER_WG_IP} -t ${IPERF_DURATION} -J 2>&1" || echo '{"error": "failed"}')
    
    if echo "$iperf_result" | grep -q '"error"'; then
        log_error "iperf3 TCP test failed"
        echo "$iperf_result"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    # Parse results
    local bits_per_second bytes_sent
    bits_per_second=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum_sent',{}).get('bits_per_second',0))" 2>/dev/null || echo "0")
    bytes_sent=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum_sent',{}).get('bytes',0))" 2>/dev/null || echo "0")
    
    local mbps
    mbps=$(echo "scale=2; $bits_per_second / 1000000" | bc)
    
    log_info "TCP Throughput: ${mbps} Mbps"
    log_info "Bytes sent: ${bytes_sent}"
    
    IPERF_TCP_RESULT=$(cat << EOF
{
    "test": "iperf_tcp",
    "throughput_mbps": ${mbps:-0},
    "bits_per_second": ${bits_per_second:-0},
    "bytes_sent": ${bytes_sent:-0},
    "duration_seconds": ${IPERF_DURATION}
}
EOF
)
    
    if [ "${mbps%.*}" -gt 0 ] 2>/dev/null; then
        log_info "TCP bandwidth test passed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_warn "TCP bandwidth test had issues"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 5: iperf3 UDP Bandwidth Test
test_iperf_udp() {
    log_test "Test 5: iperf3 UDP Bandwidth Test (${IPERF_DURATION}s @ ${IPERF_UDP_BANDWIDTH})"
    
    local iperf_result
    iperf_result=$(run_in_client "iperf3 -c ${SERVER_WG_IP} -u -b ${IPERF_UDP_BANDWIDTH} -t ${IPERF_DURATION} -J 2>&1" || echo '{"error": "failed"}')
    
    if echo "$iperf_result" | grep -q '"error"'; then
        log_error "iperf3 UDP test failed"
        echo "$iperf_result"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
    
    # Parse results
    local bits_per_second packets_sent packets_lost jitter_ms lost_percent
    bits_per_second=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('bits_per_second',0))" 2>/dev/null || echo "0")
    packets_sent=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('packets',0))" 2>/dev/null || echo "0")
    packets_lost=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('lost_packets',0))" 2>/dev/null || echo "0")
    jitter_ms=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('jitter_ms',0))" 2>/dev/null || echo "0")
    lost_percent=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('lost_percent',0))" 2>/dev/null || echo "0")
    
    local mbps
    mbps=$(echo "scale=2; $bits_per_second / 1000000" | bc)
    
    log_info "UDP Throughput: ${mbps} Mbps"
    log_info "Packets: ${packets_sent} sent, ${packets_lost} lost (${lost_percent}%)"
    log_info "Jitter: ${jitter_ms} ms"
    
    IPERF_UDP_RESULT=$(cat << EOF
{
    "test": "iperf_udp",
    "throughput_mbps": ${mbps:-0},
    "bits_per_second": ${bits_per_second:-0},
    "packets_sent": ${packets_sent:-0},
    "packets_lost": ${packets_lost:-0},
    "lost_percent": ${lost_percent:-0},
    "jitter_ms": ${jitter_ms:-0},
    "duration_seconds": ${IPERF_DURATION}
}
EOF
)
    
    if [ "${mbps%.*}" -gt 0 ] 2>/dev/null; then
        log_info "UDP bandwidth test passed"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        log_warn "UDP bandwidth test had issues"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Run all tests
echo ""
log_info "Starting WireGuard tunnel tests..."
echo ""

test_wg_interface || true
echo ""

test_ping_connectivity || true
echo ""

test_ping_extended || true
echo ""

test_iperf_tcp || true
echo ""

test_iperf_udp || true
echo ""

# Generate final results
echo "========================================"
echo " Test Results Summary"
echo "========================================"
echo "Passed: ${TESTS_PASSED}"
echo "Failed: ${TESTS_FAILED}"
echo "========================================"

# Write results to JSON file
cat > "${RESULT_FILE}" << EOF
{
    "timestamp": "${TIMESTAMP}",
    "client_container": "${CLIENT_CONTAINER}",
    "server_wg_ip": "${SERVER_WG_IP}",
    "tests_passed": ${TESTS_PASSED},
    "tests_failed": ${TESTS_FAILED},
    "tests": {
        "ping": ${PING_RESULT:-null},
        "iperf_tcp": ${IPERF_TCP_RESULT:-null},
        "iperf_udp": ${IPERF_UDP_RESULT:-null}
    }
}
EOF

log_info "Results saved to ${RESULT_FILE}"

# Exit with appropriate code
if [ ${TESTS_FAILED} -eq 0 ]; then
    log_info "All tests passed!"
    exit 0
else
    log_warn "Some tests failed"
    exit 1
fi

