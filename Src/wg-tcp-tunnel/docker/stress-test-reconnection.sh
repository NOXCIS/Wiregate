#!/bin/bash
# Connection Interruption and Reconnection Test
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-51822}"
MODE="${3:-tcp}"  # tcp or websocket
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/stress-results}"

# Test parameters
RECONNECTION_CYCLES=10
PAUSE_DURATION=2
TRAFFIC_RATE=100
TEST_DURATION=60

# Container names (for Docker-based tests)
SERVER_CONTAINER="${SERVER_CONTAINER:-wg-tcp-tunnel-server}"
CLIENT_CONTAINER="${CLIENT_CONTAINER:-wg-tcp-tunnel-client}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_test() { echo -e "${CYAN}[TEST]${NC} $1"; }

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Result file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/reconnection_${MODE}_${TIMESTAMP}.json"

echo "========================================"
echo " Reconnection Stress Test"
echo "========================================"
echo "Target:     ${HOST}:${PORT}"
echo "Mode:       ${MODE}"
echo "Cycles:     ${RECONNECTION_CYCLES}"
echo "Results:    ${RESULT_FILE}"
echo "========================================"
echo ""

# Initialize results
cat > "${RESULT_FILE}" << EOF
{
    "mode": "${MODE}",
    "timestamp": "${TIMESTAMP}",
    "reconnection_cycles": ${RECONNECTION_CYCLES},
    "tests": []
}
EOF

# Check if we can control Docker containers
CAN_CONTROL_DOCKER=false
if command -v docker &> /dev/null; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${SERVER_CONTAINER}"; then
        CAN_CONTROL_DOCKER=true
        log_info "Docker control available for container: ${SERVER_CONTAINER}"
    fi
fi

# Test 1: Basic reconnection after clean disconnect
test_clean_reconnection() {
    log_test "Test 1: Clean Reconnection"
    
    local success=0
    local failure=0
    local total_latency=0
    
    for i in $(seq 1 ${RECONNECTION_CYCLES}); do
        log_info "  Cycle ${i}/${RECONNECTION_CYCLES}"
        
        # Start time
        local start=$(date +%s.%N)
        
        # Send a test packet and measure round-trip
        local result=$(echo "reconnect-test-${i}" | nc -u -w 2 "${HOST}" "${PORT}" 2>&1)
        local end=$(date +%s.%N)
        
        if [ -n "${result}" ]; then
            local latency=$(echo "${end} - ${start}" | bc)
            total_latency=$(echo "${total_latency} + ${latency}" | bc)
            success=$((success + 1))
            log_info "    OK (latency: ${latency}s)"
        else
            failure=$((failure + 1))
            log_warn "    FAILED"
        fi
        
        sleep 0.5
    done
    
    local avg_latency=0
    if [ ${success} -gt 0 ]; then
        avg_latency=$(echo "scale=3; ${total_latency} / ${success}" | bc)
    fi
    
    log_info "  Results: ${success} success, ${failure} failed, avg latency: ${avg_latency}s"
    
    # Append to results
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'name': 'clean_reconnection',
    'success': ${success},
    'failure': ${failure},
    'avg_latency_seconds': ${avg_latency}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
    
    # Return success if no failures
    [ ${failure} -eq 0 ]
}

# Test 2: Reconnection after container pause (if Docker available)
test_container_pause() {
    if [ "${CAN_CONTROL_DOCKER}" != "true" ]; then
        log_warn "Test 2: Container Pause - SKIPPED (Docker not available)"
        return 0
    fi
    
    log_test "Test 2: Container Pause/Unpause"
    
    local success=0
    local failure=0
    local recovery_times=()
    
    for i in $(seq 1 5); do
        log_info "  Cycle ${i}/5"
        
        # Start background traffic
        log_info "    Starting background traffic..."
        python3 -u "${SCRIPT_DIR}/stress-udp-client.py" \
            "${HOST}" "${PORT}" \
            --rate 10 \
            --duration 30 \
            --verbose \
            --json "${RESULTS_DIR}/pause_traffic_${i}.json" &
        local traffic_pid=$!
        sleep 2
        
        # Pause the server container
        log_info "    Pausing server container..."
        docker pause "${SERVER_CONTAINER}" 2>/dev/null || true
        sleep ${PAUSE_DURATION}
        
        # Unpause and measure recovery
        local unpause_start=$(date +%s.%N)
        log_info "    Unpausing server container..."
        docker unpause "${SERVER_CONTAINER}" 2>/dev/null || true
        
        # Wait for traffic to recover
        sleep 2
        
        # Check if traffic is flowing
        local test_result=$(echo "recovery-test-${i}" | timeout 5 nc -u -w 2 "${HOST}" "${PORT}" 2>&1)
        local recovery_end=$(date +%s.%N)
        
        if [ -n "${test_result}" ]; then
            local recovery_time=$(echo "${recovery_end} - ${unpause_start}" | bc)
            recovery_times+=("${recovery_time}")
            success=$((success + 1))
            log_info "    Recovery time: ${recovery_time}s"
        else
            failure=$((failure + 1))
            log_warn "    Failed to recover"
        fi
        
        # Stop background traffic
        kill ${traffic_pid} 2>/dev/null || true
        wait ${traffic_pid} 2>/dev/null || true
        
        sleep 2
    done
    
    # Calculate average recovery time
    local avg_recovery=0
    if [ ${#recovery_times[@]} -gt 0 ]; then
        local sum=0
        for t in "${recovery_times[@]}"; do
            sum=$(echo "${sum} + ${t}" | bc)
        done
        avg_recovery=$(echo "scale=3; ${sum} / ${#recovery_times[@]}" | bc)
    fi
    
    log_info "  Results: ${success} success, ${failure} failed, avg recovery: ${avg_recovery}s"
    
    # Append to results
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'name': 'container_pause',
    'success': ${success},
    'failure': ${failure},
    'avg_recovery_seconds': ${avg_recovery}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
    
    # Return success if no failures
    [ ${failure} -eq 0 ]
}

# Test 3: Rapid reconnection stress
test_rapid_reconnection() {
    log_test "Test 3: Rapid Reconnection"
    
    local success=0
    local failure=0
    local rapid_cycles=50
    
    log_info "  Sending ${rapid_cycles} rapid connection attempts..."
    
    for i in $(seq 1 ${rapid_cycles}); do
        # Very rapid fire test
        if result=$(echo "rapid-${i}" | timeout 1 nc -u -w 0.1 "${HOST}" "${PORT}" 2>&1); then
            success=$((success + 1))
        else
            failure=$((failure + 1))
        fi
    done
    
    # Give some time for async responses
    sleep 2
    
    log_info "  Results: ${success} success, ${failure} timeout"
    
    # Append to results
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'name': 'rapid_reconnection',
    'attempts': ${rapid_cycles},
    'success': ${success},
    'failure': ${failure}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
    
    # Allow some failures in rapid test (async nature)
    [ ${success} -gt $((rapid_cycles / 2)) ]
}

# Test 4: Sustained traffic with periodic interruptions
test_sustained_with_interruptions() {
    log_test "Test 4: Sustained Traffic with Interruptions"
    
    if [ "${CAN_CONTROL_DOCKER}" != "true" ]; then
        log_warn "  SKIPPED (Docker not available)"
        return 0
    fi
    
    log_info "  Running sustained traffic test with container pauses..."
    
    # Start sustained traffic in background
    python3 -u "${SCRIPT_DIR}/stress-udp-client.py" \
        "${HOST}" "${PORT}" \
        --rate "${TRAFFIC_RATE}" \
        --duration "${TEST_DURATION}" \
        --verbose \
        --json "${RESULTS_DIR}/sustained_traffic.json" &
    local traffic_pid=$!
    
    # Periodically pause the server
    local interruptions=0
    for i in $(seq 1 5); do
        sleep 10
        
        log_info "  Interruption ${i}/5: pausing for ${PAUSE_DURATION}s..."
        docker pause "${SERVER_CONTAINER}" 2>/dev/null || true
        sleep ${PAUSE_DURATION}
        docker unpause "${SERVER_CONTAINER}" 2>/dev/null || true
        interruptions=$((interruptions + 1))
    done
    
    # Wait for traffic to complete
    wait ${traffic_pid} 2>/dev/null || true
    
    # Analyze results
    if [ -f "${RESULTS_DIR}/sustained_traffic.json" ]; then
        local loss=$(python3 -c "import json; print(json.load(open('${RESULTS_DIR}/sustained_traffic.json')).get('loss_rate_percent', 100))")
        log_info "  Packet loss after ${interruptions} interruptions: ${loss}%"
        
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
with open('${RESULTS_DIR}/sustained_traffic.json', 'r') as f:
    traffic_data = json.load(f)
data['tests'].append({
    'name': 'sustained_with_interruptions',
    'interruptions': ${interruptions},
    'traffic_results': traffic_data
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
        
        # Allow up to 10% loss with interruptions
        [ $(echo "$loss < 10" | bc -l) -eq 1 ]
    else
        log_error "  No traffic results file"
        return 1
    fi
}

# Run all tests
# Disable set -e temporarily to allow tests to fail without stopping the script
set +e

PASSED=0
FAILED=0

if test_clean_reconnection; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_container_pause; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_rapid_reconnection; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_sustained_with_interruptions; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Re-enable set -e for final checks
set -e

# Summary
echo "========================================"
echo " Reconnection Test Summary"
echo "========================================"
echo "Passed: ${PASSED}"
echo "Failed: ${FAILED}"
echo "Results: ${RESULT_FILE}"
echo "========================================"

if [ "${FAILED}" -gt 0 ]; then
    log_error "Some tests failed!"
    exit 1
fi

log_info "All tests passed!"
exit 0

