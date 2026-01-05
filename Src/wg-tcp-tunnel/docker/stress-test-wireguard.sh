#!/bin/bash
# WireGuard Stress Test Script
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT
#
# This script runs WireGuard tests through the TCP tunnel.
# It tests real WireGuard protocol traffic for both TCP and WebSocket modes.

# Don't exit on first error - we want to run all tests
set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/stress-results}"

# Test parameters
MODE="${1:-tcp}"  # tcp or websocket
CLIENT_CONTAINER="${2:-wg-tcp-tunnel-client-wg}"
SERVER_WG_IP="${3:-10.0.0.1}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_test() { echo -e "${CYAN}[TEST]${NC} $1" >&2; }

# Create results directory
mkdir -p "${RESULTS_DIR}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/wireguard_stress_${MODE}_${TIMESTAMP}.json"

echo "========================================"
echo " WireGuard Stress Test Suite"
echo "========================================"
echo "Mode:             ${MODE}"
echo "Client Container: ${CLIENT_CONTAINER}"
echo "Server WG IP:     ${SERVER_WG_IP}"
echo "Results:          ${RESULT_FILE}"
echo "========================================"
echo ""

# Initialize counters
PASSED=0
FAILED=0

# Function to run command in container
run_in_container() {
    local container="$1"
    shift
    if ! command -v docker &> /dev/null; then
        log_error "docker command not found"
        return 1
    fi
    docker exec "${container}" bash -c "$*" 2>&1
}

# Function to check if container is running
check_container() {
    local container="$1"
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        return 0
    else
        return 1
    fi
}

# Wait for WireGuard to be ready
wait_for_wireguard() {
    log_info "Waiting for WireGuard to be ready..."
    
    local max_wait=60
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        if run_in_container "${CLIENT_CONTAINER}" "wg show wg0 2>/dev/null | grep -q 'interface'" 2>/dev/null; then
            # Check for handshake
            local handshake
            handshake=$(run_in_container "${CLIENT_CONTAINER}" "wg show wg0 latest-handshakes 2>/dev/null | awk '{print \$2}'" 2>/dev/null || echo "")
            if [ -n "$handshake" ] && [ "$handshake" != "0" ]; then
                log_info "WireGuard is ready (handshake: ${handshake}s ago)"
                return 0
            fi
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        log_info "Waiting... (${elapsed}s)"
    done
    
    log_error "Timeout waiting for WireGuard"
    return 1
}

# Test 1: WireGuard Handshake
test_handshake() {
    log_test "Test 1: WireGuard Handshake"
    
    local wg_output
    wg_output=$(run_in_container "${CLIENT_CONTAINER}" "wg show wg0 2>&1")
    
    if [ $? -ne 0 ] || [ -z "$wg_output" ]; then
        log_error "FAILED: Could not run wg show command"
        FAILED=$((FAILED + 1))
        echo '{"name": "handshake", "status": "failed", "reason": "wg_command_failed"}'
        return 1
    fi
    
    if echo "$wg_output" | grep -q "interface"; then
        local handshake
        handshake=$(run_in_container "${CLIENT_CONTAINER}" "wg show wg0 latest-handshakes 2>/dev/null | awk '{print \$2}'")
        
        if [ -n "$handshake" ] && [ "$handshake" != "0" ]; then
            log_info "PASSED: Handshake established (${handshake}s ago)"
            PASSED=$((PASSED + 1))
            echo '{"name": "handshake", "status": "passed", "handshake_age_seconds": '"${handshake}"'}'
            return 0
        else
            log_warn "FAILED: No handshake established yet"
            FAILED=$((FAILED + 1))
            echo '{"name": "handshake", "status": "failed", "reason": "no_handshake"}'
            return 1
        fi
    else
        log_error "FAILED: WireGuard interface not found"
        FAILED=$((FAILED + 1))
        echo '{"name": "handshake", "status": "failed", "reason": "no_interface"}'
        return 1
    fi
}

# Test 2: Ping Connectivity
test_ping() {
    log_test "Test 2: Ping Connectivity"
    
    local ping_result
    ping_result=$(run_in_container "${CLIENT_CONTAINER}" "ping -c 10 -i 0.2 ${SERVER_WG_IP} 2>&1")
    
    if [ $? -ne 0 ] || [ -z "$ping_result" ]; then
        log_error "FAILED: Could not run ping test"
        FAILED=$((FAILED + 1))
        echo '{"name": "ping", "status": "failed", "reason": "ping_command_failed"}'
        return 1
    fi
    
    local received loss
    received=$(echo "$ping_result" | grep -oP '\d+(?= received)' 2>/dev/null || echo "0")
    loss=$(echo "$ping_result" | grep -oP '\d+(?=% packet loss)' 2>/dev/null || echo "100")
    
    local avg_latency
    avg_latency=$(echo "$ping_result" | grep -oP '\d+\.\d+(?=/\d+\.\d+ ms)' 2>/dev/null | head -2 | tail -1 || echo "0")
    
    if [ "${received:-0}" -gt 5 ]; then
        log_info "PASSED: ${received}/10 packets received, ${loss}% loss, ${avg_latency}ms latency"
        PASSED=$((PASSED + 1))
        echo '{"name": "ping", "status": "passed", "packets_received": '"${received}"', "loss_percent": '"${loss}"', "avg_latency_ms": '"${avg_latency:-0}"'}'
        return 0
    else
        log_error "FAILED: Only ${received}/10 packets received"
        FAILED=$((FAILED + 1))
        echo '{"name": "ping", "status": "failed", "packets_received": '"${received:-0}"', "loss_percent": '"${loss:-100}"'}'
        return 1
    fi
}

# Test 3: Sustained Ping (1 minute)
test_sustained_ping() {
    log_test "Test 3: Sustained Ping (60 seconds)"
    
    local ping_result
    ping_result=$(run_in_container "${CLIENT_CONTAINER}" "ping -c 60 -i 1 ${SERVER_WG_IP} 2>&1")
    
    if [ $? -ne 0 ] || [ -z "$ping_result" ]; then
        log_error "FAILED: Could not run sustained ping test"
        FAILED=$((FAILED + 1))
        echo '{"name": "sustained_ping", "status": "failed", "reason": "ping_command_failed"}'
        return 1
    fi
    
    local transmitted received loss
    transmitted=$(echo "$ping_result" | grep -oP '\d+(?= packets transmitted)' 2>/dev/null || echo "0")
    received=$(echo "$ping_result" | grep -oP '\d+(?= received)' 2>/dev/null || echo "0")
    loss=$(echo "$ping_result" | grep -oP '\d+(?=% packet loss)' 2>/dev/null || echo "100")
    
    local avg_latency
    avg_latency=$(echo "$ping_result" | grep -oP '\d+\.\d+(?=/\d+\.\d+ ms)' 2>/dev/null | head -2 | tail -1 || echo "0")
    
    if [ "${loss:-100}" -lt 5 ]; then
        log_info "PASSED: ${loss}% loss over 60 seconds, ${avg_latency}ms latency"
        PASSED=$((PASSED + 1))
        echo '{"name": "sustained_ping", "status": "passed", "packets_transmitted": '"${transmitted}"', "packets_received": '"${received}"', "loss_percent": '"${loss}"', "avg_latency_ms": '"${avg_latency:-0}"'}'
        return 0
    else
        log_warn "FAILED: ${loss}% loss is too high"
        FAILED=$((FAILED + 1))
        echo '{"name": "sustained_ping", "status": "failed", "loss_percent": '"${loss:-100}"'}'
        return 1
    fi
}

# Test 4: TCP Throughput (iperf3)
test_tcp_throughput() {
    log_test "Test 4: TCP Throughput (30 seconds)"
    
    local iperf_result
    iperf_result=$(run_in_container "${CLIENT_CONTAINER}" "iperf3 -c ${SERVER_WG_IP} -t 30 -J 2>&1")
    
    if [ $? -ne 0 ] || [ -z "$iperf_result" ]; then
        log_error "FAILED: Could not run iperf3 TCP test"
        FAILED=$((FAILED + 1))
        echo '{"name": "tcp_throughput", "status": "failed", "reason": "iperf3_command_failed"}'
        return 1
    fi
    
    if echo "$iperf_result" | grep -q '"error"'; then
        log_error "FAILED: iperf3 error"
        FAILED=$((FAILED + 1))
        echo '{"name": "tcp_throughput", "status": "failed", "reason": "iperf3_error"}'
        return 1
    fi
    
    local bits_per_second
    bits_per_second=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum_sent',{}).get('bits_per_second',0))" 2>/dev/null || echo "0")
    
    local mbps
    mbps=$(echo "scale=2; $bits_per_second / 1000000" | bc)
    
    if [ "${mbps%.*}" -gt 1 ] 2>/dev/null; then
        log_info "PASSED: TCP throughput ${mbps} Mbps"
        PASSED=$((PASSED + 1))
        echo '{"name": "tcp_throughput", "status": "passed", "throughput_mbps": '"${mbps}"'}'
        return 0
    else
        log_warn "FAILED: TCP throughput too low (${mbps} Mbps)"
        FAILED=$((FAILED + 1))
        echo '{"name": "tcp_throughput", "status": "failed", "throughput_mbps": '"${mbps:-0}"'}'
        return 1
    fi
}

# Test 5: UDP Throughput (iperf3)
test_udp_throughput() {
    log_test "Test 5: UDP Throughput (30 seconds @ 50Mbps)"
    
    local iperf_result
    iperf_result=$(run_in_container "${CLIENT_CONTAINER}" "iperf3 -c ${SERVER_WG_IP} -u -b 50M -t 30 -J 2>&1")
    
    if [ $? -ne 0 ] || [ -z "$iperf_result" ]; then
        log_error "FAILED: Could not run iperf3 UDP test"
        FAILED=$((FAILED + 1))
        echo '{"name": "udp_throughput", "status": "failed", "reason": "iperf3_command_failed"}'
        return 1
    fi
    
    if echo "$iperf_result" | grep -q '"error"'; then
        log_error "FAILED: iperf3 error"
        FAILED=$((FAILED + 1))
        echo '{"name": "udp_throughput", "status": "failed", "reason": "iperf3_error"}'
        return 1
    fi
    
    local bits_per_second lost_percent jitter
    bits_per_second=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('bits_per_second',0))" 2>/dev/null || echo "0")
    lost_percent=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('lost_percent',0))" 2>/dev/null || echo "100")
    jitter=$(echo "$iperf_result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('end',{}).get('sum',{}).get('jitter_ms',0))" 2>/dev/null || echo "0")
    
    local mbps
    mbps=$(echo "scale=2; $bits_per_second / 1000000" | bc)
    
    if [ "${mbps%.*}" -gt 1 ] 2>/dev/null && [ $(echo "${lost_percent:-100} < 10" | bc -l) -eq 1 ]; then
        log_info "PASSED: UDP throughput ${mbps} Mbps, ${lost_percent}% loss, ${jitter}ms jitter"
        PASSED=$((PASSED + 1))
        echo '{"name": "udp_throughput", "status": "passed", "throughput_mbps": '"${mbps}"', "loss_percent": '"${lost_percent}"', "jitter_ms": '"${jitter}"'}'
        return 0
    else
        log_warn "FAILED: UDP throughput ${mbps} Mbps, ${lost_percent}% loss"
        FAILED=$((FAILED + 1))
        echo '{"name": "udp_throughput", "status": "failed", "throughput_mbps": '"${mbps:-0}"', "loss_percent": '"${lost_percent:-100}"'}'
        return 1
    fi
}

# Check if docker is available
if ! command -v docker &> /dev/null; then
    log_error "docker command not found. Please install docker CLI."
    exit 1
fi

# Check container is running
if ! check_container "${CLIENT_CONTAINER}"; then
    log_error "Container ${CLIENT_CONTAINER} is not running"
    log_info "Start it with: docker-compose -f docker-compose.stress.yml --profile wireguard up -d"
    exit 1
fi

# Wait for WireGuard
if ! wait_for_wireguard; then
    log_error "WireGuard is not ready, cannot run tests"
    exit 1
fi

echo ""

# Run tests and collect results
TESTS_RESULTS="["

# Helper function to run test, display output, and extract JSON
run_test_with_output() {
    local test_name="$1"
    shift
    log_info "Running ${test_name}..."
    
    # Run test and capture output (both stdout and stderr)
    local test_output
    local json_result
    
    test_output=$("$@" 2>&1) || true
    
    # Display all output to terminal
    echo "$test_output"
    
    # Extract JSON using Python (more reliable than grep)
    json_result=$(echo "$test_output" | python3 -c "
import sys
import re
import json

# Read all input
content = sys.stdin.read()

# Find JSON objects (handle nested objects)
# Look for lines that start with { and try to parse them
for line in content.split('\n'):
    line = line.strip()
    if line.startswith('{'):
        try:
            # Try to parse as JSON
            data = json.loads(line)
            # If it has 'name' and 'status', it's our test result JSON
            if 'name' in data and 'status' in data:
                print(line)
                break
        except:
            continue
" 2>/dev/null || echo "")
    
    if [ -n "$json_result" ]; then
        TESTS_RESULTS="${TESTS_RESULTS}${json_result},"
        # Check if test passed or failed from JSON
        if echo "$json_result" | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if d.get('status') == 'passed' else 1)" 2>/dev/null; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
    else
        log_warn "${test_name} produced no JSON output"
        local test_id
        test_id=$(echo "$test_name" | sed 's/.*test [0-9]*: //' | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
        TESTS_RESULTS="${TESTS_RESULTS}{\"name\": \"${test_id}\", \"status\": \"failed\", \"reason\": \"no_output\"},"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# Run all tests
run_test_with_output "test 1: Handshake check" test_handshake
run_test_with_output "test 2: Ping connectivity" test_ping
run_test_with_output "test 3: Sustained ping" test_sustained_ping
run_test_with_output "test 4: TCP throughput" test_tcp_throughput

# Last test - no trailing comma
log_info "Running test 5: UDP throughput..."
test_output=$(test_udp_throughput 2>&1) || true
echo "$test_output"
json_result=$(echo "$test_output" | python3 -c "
import sys
import json

content = sys.stdin.read()
for line in content.split('\n'):
    line = line.strip()
    if line.startswith('{'):
        try:
            data = json.loads(line)
            if 'name' in data and 'status' in data:
                print(line)
                break
        except:
            continue
" 2>/dev/null || echo "")

if [ -n "$json_result" ]; then
    TESTS_RESULTS="${TESTS_RESULTS}${json_result}"
    if echo "$json_result" | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if d.get('status') == 'passed' else 1)" 2>/dev/null; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
else
    log_warn "Test 5 produced no JSON output"
    TESTS_RESULTS="${TESTS_RESULTS}{\"name\": \"udp_throughput\", \"status\": \"failed\", \"reason\": \"no_output\"}"
    FAILED=$((FAILED + 1))
fi
echo ""

TESTS_RESULTS="${TESTS_RESULTS}]"

# Generate final results
echo "========================================"
echo " WireGuard Stress Test Results"
echo "========================================"
echo "Mode:   ${MODE}"
echo "Passed: ${PASSED}"
echo "Failed: ${FAILED}"
echo "========================================"

# Write results to JSON file
cat > "${RESULT_FILE}" << EOF
{
    "mode": "${MODE}",
    "timestamp": "${TIMESTAMP}",
    "client_container": "${CLIENT_CONTAINER}",
    "server_wg_ip": "${SERVER_WG_IP}",
    "tests_passed": ${PASSED},
    "tests_failed": ${FAILED},
    "tests": ${TESTS_RESULTS}
}
EOF

log_info "Results saved to ${RESULT_FILE}"

# Exit with appropriate code
if [ ${FAILED} -eq 0 ]; then
    log_info "All WireGuard tests passed!"
    exit 0
else
    log_warn "Some WireGuard tests failed"
    exit 1
fi

