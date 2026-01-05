#!/bin/bash
# WebSocket-Specific Stress Test
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-51820}"  # WebSocket port
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/stress-results}"

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
RESULT_FILE="${RESULTS_DIR}/websocket_stress_${TIMESTAMP}.json"

echo "========================================"
echo " WebSocket-Specific Stress Test"
echo "========================================"
echo "Target:    ${HOST}:${PORT}"
echo "Results:   ${RESULT_FILE}"
echo "========================================"
echo ""

# Initialize results
cat > "${RESULT_FILE}" << EOF
{
    "timestamp": "${TIMESTAMP}",
    "target": "${HOST}:${PORT}",
    "tests": []
}
EOF

# Check if WebSocket test utility is available
if [ ! -f "${SCRIPT_DIR}/stress-websocket-test.py" ]; then
    log_error "WebSocket test utility not found: ${SCRIPT_DIR}/stress-websocket-test.py"
    exit 1
fi

# Test 1: Handshake Stress
test_handshake_stress() {
    log_test "Test 1: WebSocket Handshake Stress"
    
    local result_file="${RESULTS_DIR}/ws_handshake_${TIMESTAMP}.json"
    
    log_info "  Running 100 handshake attempts..."
    
    python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
        "${HOST}" "${PORT}" \
        --handshake 100 \
        --json "${result_file}" \
        2>&1 | while read line; do
            echo "    $line"
        done
    
    if [ -f "${result_file}" ]; then
        local success=$(python3 -c "import json; print(json.load(open('${result_file}')).get('handshake_success', 0))")
        local failure=$(python3 -c "import json; print(json.load(open('${result_file}')).get('handshake_failure', 0))")
        local rate=$(python3 -c "import json; print(json.load(open('${result_file}')).get('handshake_success_rate', 0))")
        
        log_info "  Results: ${success} success, ${failure} failed, ${rate}% success rate"
        
        # Append to main results
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
with open('${result_file}', 'r') as f:
    test_data = json.load(f)
test_data['test_name'] = 'handshake_stress'
data['tests'].append(test_data)
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
        
        # Return success if no failures
        [ ${failure} -eq 0 ]
    else
        log_error "  No results file"
        return 1
    fi
}

# Test 2: Binary Frame Transmission
test_binary_frames() {
    log_test "Test 2: Binary Frame Transmission"
    
    local result_file="${RESULTS_DIR}/ws_frames_${TIMESTAMP}.json"
    
    log_info "  Sending 500 binary frames..."
    
    python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
        "${HOST}" "${PORT}" \
        --frames 500 \
        --frame-size 1024 \
        --json "${result_file}" \
        2>&1 | while read line; do
            echo "    $line"
        done
    
    if [ -f "${result_file}" ]; then
        local sent=$(python3 -c "import json; print(json.load(open('${result_file}')).get('frames_sent', 0))")
        local received=$(python3 -c "import json; print(json.load(open('${result_file}')).get('frames_received', 0))")
        local errors=$(python3 -c "import json; print(len(json.load(open('${result_file}')).get('errors', [])))")
        
        log_info "  Results: ${sent} sent, ${received} received, ${errors} errors"
        
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
with open('${result_file}', 'r') as f:
    test_data = json.load(f)
test_data['test_name'] = 'binary_frames'
data['tests'].append(test_data)
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
        
        # Return success if no errors
        [ ${errors} -eq 0 ]
    else
        log_error "  No results file"
        return 1
    fi
}

# Test 3: Large Frames
test_large_frames() {
    log_test "Test 3: Large Frame Transmission"
    
    local result_file="${RESULTS_DIR}/ws_large_frames_${TIMESTAMP}.json"
    local frame_sizes=(1024 4096 16384 65536)
    
    for size in "${frame_sizes[@]}"; do
        log_info "  Testing ${size} byte frames..."
        
        python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
            "${HOST}" "${PORT}" \
            --frames 20 \
            --frame-size "${size}" \
            --json "${result_file}.${size}" \
            2>&1 | grep -E "(Results|success|failed)" | while read line; do
                echo "    $line"
            done
    done
    
    log_info "  Large frame tests completed"
    return 0
}

# Test 4: Ping/Pong Keep-Alive
test_ping_pong() {
    log_test "Test 4: Ping/Pong Keep-Alive"
    
    local result_file="${RESULTS_DIR}/ws_pingpong_${TIMESTAMP}.json"
    
    log_info "  Testing 50 ping/pong exchanges..."
    
    python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
        "${HOST}" "${PORT}" \
        --ping 50 \
        --json "${result_file}" \
        2>&1 | while read line; do
            echo "    $line"
        done
    
    if [ -f "${result_file}" ]; then
        local success=$(python3 -c "import json; print(json.load(open('${result_file}')).get('ping_pong_success', 0))")
        local failure=$(python3 -c "import json; print(json.load(open('${result_file}')).get('ping_pong_failure', 0))")
        
        log_info "  Results: ${success} success, ${failure} failed"
        
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
with open('${result_file}', 'r') as f:
    test_data = json.load(f)
test_data['test_name'] = 'ping_pong'
data['tests'].append(test_data)
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
        
        # Return success if no failures
        [ ${failure} -eq 0 ]
    else
        log_error "  No results file"
        return 1
    fi
}

# Test 5: Reconnection Stability
test_reconnection() {
    log_test "Test 5: Reconnection Stability"
    
    local result_file="${RESULTS_DIR}/ws_reconnect_${TIMESTAMP}.json"
    
    log_info "  Testing 20 reconnection cycles..."
    
    python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
        "${HOST}" "${PORT}" \
        --reconnect 20 \
        --json "${result_file}" \
        2>&1 | while read line; do
            echo "    $line"
        done
    
    if [ -f "${result_file}" ]; then
        local reconnections=$(python3 -c "import json; print(json.load(open('${result_file}')).get('reconnections', 0))")
        local failures=$(python3 -c "import json; print(json.load(open('${result_file}')).get('handshake_failure', 0))")
        
        log_info "  Results: ${reconnections} successful reconnections, ${failures} failures"
        
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
with open('${result_file}', 'r') as f:
    test_data = json.load(f)
test_data['test_name'] = 'reconnection'
data['tests'].append(test_data)
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
        
        # Return success if no failures
        [ ${failures} -eq 0 ]
    else
        log_error "  No results file"
        return 1
    fi
}

# Test 6: Concurrent WebSocket Connections
test_concurrent_websocket() {
    log_test "Test 6: Concurrent WebSocket Connections"
    
    local num_connections=10
    local pids=()
    
    log_info "  Starting ${num_connections} concurrent WebSocket connections..."
    
    for i in $(seq 1 ${num_connections}); do
        python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
            "${HOST}" "${PORT}" \
            --handshake 10 \
            --json "${RESULTS_DIR}/ws_concurrent_${i}_${TIMESTAMP}.json" \
            >/dev/null 2>&1 &
        pids+=($!)
    done
    
    local success=0
    local failure=0
    
    for pid in "${pids[@]}"; do
        if wait "${pid}" 2>/dev/null; then
            success=$((success + 1))
        else
            failure=$((failure + 1))
        fi
    done
    
    log_info "  Results: ${success} connections succeeded, ${failure} failed"
    
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'test_name': 'concurrent_websocket',
    'num_connections': ${num_connections},
    'success': ${success},
    'failure': ${failure}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
    
    # Return success if no failures
    [ ${failure} -eq 0 ]
}

# Test 7: Full Integration Test
test_full_integration() {
    log_test "Test 7: Full WebSocket Integration"
    
    local result_file="${RESULTS_DIR}/ws_integration_${TIMESTAMP}.json"
    
    log_info "  Running full WebSocket test suite..."
    
    python3 "${SCRIPT_DIR}/stress-websocket-test.py" \
        "${HOST}" "${PORT}" \
        --all \
        --json "${result_file}" \
        2>&1 | while read line; do
            echo "    $line"
        done
    
    if [ -f "${result_file}" ]; then
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
with open('${result_file}', 'r') as f:
    test_data = json.load(f)
test_data['test_name'] = 'full_integration'
data['tests'].append(test_data)
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
" || true
        return 0
    else
        log_error "  No results file"
        return 1
    fi
}

# Run all tests
# Disable set -e temporarily to allow tests to fail without stopping the script
set +e

PASSED=0
FAILED=0

if test_handshake_stress; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_binary_frames; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_large_frames; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_ping_pong; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_reconnection; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_concurrent_websocket; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_full_integration; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Re-enable set -e for final checks
set -e

# Summary
echo "========================================"
echo " WebSocket Stress Test Summary"
echo "========================================"
echo "Passed: ${PASSED}"
echo "Failed: ${FAILED}"
echo "Results: ${RESULT_FILE}"
echo "========================================"

if [ "${FAILED}" -gt 0 ]; then
    log_error "Some WebSocket tests failed!"
    exit 1
fi

log_info "All WebSocket tests passed!"
exit 0

