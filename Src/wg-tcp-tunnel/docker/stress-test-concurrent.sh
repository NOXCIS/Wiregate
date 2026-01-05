#!/bin/bash
# Concurrent Connections Stress Test
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
MAX_CONCURRENT=50
DURATION_PER_TEST=30
PACKET_RATE=50

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
RESULT_FILE="${RESULTS_DIR}/concurrent_${MODE}_${TIMESTAMP}.json"

echo "========================================"
echo " Concurrent Connections Stress Test"
echo "========================================"
echo "Target:         ${HOST}:${PORT}"
echo "Mode:           ${MODE}"
echo "Max Concurrent: ${MAX_CONCURRENT}"
echo "Results:        ${RESULT_FILE}"
echo "========================================"
echo ""

# Initialize results
cat > "${RESULT_FILE}" << EOF
{
    "mode": "${MODE}",
    "timestamp": "${TIMESTAMP}",
    "max_concurrent": ${MAX_CONCURRENT},
    "tests": []
}
EOF

# Track child PIDs
declare -a CLIENT_PIDS=()

cleanup() {
    log_info "Cleaning up..."
    for pid in "${CLIENT_PIDS[@]}"; do
        kill "${pid}" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}

trap cleanup EXIT

# Test: Multiple concurrent UDP clients
test_concurrent_udp_clients() {
    local num_clients=$1
    local duration=$2
    
    log_test "Testing ${num_clients} concurrent UDP clients for ${duration}s"
    
    CLIENT_PIDS=()
    local client_results_dir="${RESULTS_DIR}/concurrent_${num_clients}_clients"
    mkdir -p "${client_results_dir}"
    
    # Start all clients
    for i in $(seq 1 ${num_clients}); do
        # Each client uses a different source port by binding to different local ports
        local result_file="${client_results_dir}/client_${i}.json"
        
        python3 -u "${SCRIPT_DIR}/stress-udp-client.py" \
            "${HOST}" "${PORT}" \
            --rate "${PACKET_RATE}" \
            --duration "${duration}" \
            --size 256 \
            --verbose \
            --json "${result_file}" \
            2>&1 | sed "s/^/    [Client $i] /" &
        
        CLIENT_PIDS+=($!)
        
        # Small stagger to avoid burst
        sleep 0.1
    done
    
    log_info "  Started ${#CLIENT_PIDS[@]} clients"
    
    # Wait for all clients to complete
    local success=0
    local failure=0
    
    for i in "${!CLIENT_PIDS[@]}"; do
        local pid="${CLIENT_PIDS[$i]}"
        if wait "${pid}" 2>/dev/null; then
            ((success++))
        else
            ((failure++))
        fi
    done
    
    log_info "  Clients completed: ${success} success, ${failure} failed"
    
    # Aggregate results
    local total_sent=0
    local total_received=0
    local total_lost=0
    local total_latency=0
    local latency_count=0
    
    for result_file in "${client_results_dir}"/client_*.json; do
        if [ -f "${result_file}" ]; then
            local data=$(cat "${result_file}")
            local sent=$(echo "${data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('packets_sent', 0))")
            local received=$(echo "${data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('packets_received', 0))")
            local lost=$(echo "${data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('packets_lost', 0))")
            local latency=$(echo "${data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('latency_ms', {}).get('avg', 0))")
            
            total_sent=$((total_sent + sent))
            total_received=$((total_received + received))
            total_lost=$((total_lost + lost))
            if [ "${latency}" != "0" ]; then
                total_latency=$(echo "${total_latency} + ${latency}" | bc)
                ((latency_count++))
            fi
        fi
    done
    
    local loss_rate=0
    if [ ${total_sent} -gt 0 ]; then
        loss_rate=$(echo "scale=2; ${total_lost} * 100 / ${total_sent}" | bc)
    fi
    
    local avg_latency=0
    if [ ${latency_count} -gt 0 ]; then
        avg_latency=$(echo "scale=2; ${total_latency} / ${latency_count}" | bc)
    fi
    
    log_info "  Aggregate: sent=${total_sent}, received=${total_received}, lost=${total_lost} (${loss_rate}%), avg_latency=${avg_latency}ms"
    
    # Append to results
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'name': 'concurrent_${num_clients}_clients',
    'num_clients': ${num_clients},
    'duration': ${duration},
    'packets_sent': ${total_sent},
    'packets_received': ${total_received},
    'packets_lost': ${total_lost},
    'loss_rate_percent': ${loss_rate},
    'avg_latency_ms': ${avg_latency},
    'clients_success': ${success},
    'clients_failed': ${failure}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
"
    
    # Pass if loss rate is acceptable
    [ $(echo "$loss_rate < 5" | bc -l) -eq 1 ]
}

# Test: Scaling concurrent connections
test_connection_scaling() {
    log_test "Connection Scaling Test"
    
    local scales=(1 5 10 20 50)
    local passed=0
    local failed=0
    
    for num in "${scales[@]}"; do
        if [ ${num} -gt ${MAX_CONCURRENT} ]; then
            break
        fi
        
        if test_concurrent_udp_clients ${num} 15; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
        fi
        
        # Cool down between tests
        sleep 2
    done
    
    log_info "Scaling test: ${passed} passed, ${failed} failed"
    
    [ ${failed} -eq 0 ]
}

# Test: Rapid connection creation
test_rapid_connection_creation() {
    log_test "Rapid Connection Creation Test"
    
    local num_connections=100
    local timeout=3.0
    
    log_info "  Testing ${num_connections} rapid UDP connections..."
    
    # Use Python-based test that properly handles UDP send/receive
    # Capture stderr separately to show any errors, but get JSON from stdout
    local json_output=$(python3 "${SCRIPT_DIR}/test-rapid-connection.py" \
        "${HOST}" "${PORT}" \
        --num-attempts ${num_connections} \
        --timeout ${timeout} \
        --json 2>/dev/null)
    
    # Parse results from JSON
    local success=0
    local failure=0
    local success_rate=0
    
    if [ -n "${json_output}" ]; then
        success=$(echo "${json_output}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('success', 0))" 2>/dev/null || echo "0")
        failure=$(echo "${json_output}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('failure', 0))" 2>/dev/null || echo "0")
        success_rate=$(echo "${json_output}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('success_rate_percent', 0))" 2>/dev/null || echo "0")
    fi
    
    # If parsing failed, try to get from non-JSON output as fallback
    if [ "${success}" = "0" ] && [ "${failure}" = "0" ]; then
        local test_output=$(python3 "${SCRIPT_DIR}/test-rapid-connection.py" \
            "${HOST}" "${PORT}" \
            --num-attempts ${num_connections} \
            --timeout ${timeout} 2>&1)
        success=$(echo "${test_output}" | grep -E 'success: [0-9]+' | grep -oE '[0-9]+' | head -1 || echo "0")
        failure=$(echo "${test_output}" | grep -E 'failed: [0-9]+' | grep -oE '[0-9]+' | head -1 || echo "0")
        if [ "${num_connections}" -gt 0 ]; then
            success_rate=$(echo "scale=2; ${success} * 100 / ${num_connections}" | bc 2>/dev/null || echo "0")
        fi
    fi
    
    log_info "  Results: ${success} success, ${failure} failed (${success_rate}% success rate)"
    
    # Show test output if verbose
    if [ "${VERBOSE:-}" = "1" ]; then
        echo "${test_result}"
    fi
    
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'name': 'rapid_connection_creation',
    'attempts': ${num_connections},
    'success': ${success},
    'failure': ${failure},
    'success_rate_percent': ${success_rate}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
"
    
    # Allow some failures due to async nature, but require >50% success
    [ ${success} -gt $((num_connections / 2)) ]
}

# Test: Mixed load patterns
test_mixed_load() {
    log_test "Mixed Load Pattern Test"
    
    CLIENT_PIDS=()
    local mixed_results_dir="${RESULTS_DIR}/mixed_load"
    mkdir -p "${mixed_results_dir}"
    
    # Start clients with different rates
    local rates=(10 50 100 200 500)
    
    for i in "${!rates[@]}"; do
        local rate="${rates[$i]}"
        local result_file="${mixed_results_dir}/client_rate_${rate}.json"
        
        python3 "${SCRIPT_DIR}/stress-udp-client.py" \
            "${HOST}" "${PORT}" \
            --rate "${rate}" \
            --duration 20 \
            --size 256 \
            --json "${result_file}" \
            2>/dev/null &
        
        CLIENT_PIDS+=($!)
    done
    
    log_info "  Started ${#CLIENT_PIDS[@]} clients with different rates"
    
    # Wait for completion
    for pid in "${CLIENT_PIDS[@]}"; do
        wait "${pid}" 2>/dev/null || true
    done
    
    # Analyze results
    local total_sent=0
    local total_received=0
    
    for result_file in "${mixed_results_dir}"/client_rate_*.json; do
        if [ -f "${result_file}" ]; then
            local sent=$(python3 -c "import json; print(json.load(open('${result_file}')).get('packets_sent', 0))")
            local received=$(python3 -c "import json; print(json.load(open('${result_file}')).get('packets_received', 0))")
            total_sent=$((total_sent + sent))
            total_received=$((total_received + received))
        fi
    done
    
    local loss_rate=0
    if [ ${total_sent} -gt 0 ]; then
        loss_rate=$(echo "scale=2; (${total_sent} - ${total_received}) * 100 / ${total_sent}" | bc)
    fi
    
    log_info "  Mixed load: sent=${total_sent}, received=${total_received}, loss=${loss_rate}%"
    
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['tests'].append({
    'name': 'mixed_load',
    'rates': [10, 50, 100, 200, 500],
    'packets_sent': ${total_sent},
    'packets_received': ${total_received},
    'loss_rate_percent': ${loss_rate}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
"
    
    (( $(echo "$loss_rate < 10" | bc -l) ))
}

# Run all tests
# Disable set -e temporarily to allow tests to fail without stopping the script
set +e

PASSED=0
FAILED=0

if test_connection_scaling; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_rapid_connection_creation; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

if test_mixed_load; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Re-enable set -e for final checks
set -e

# Summary
echo "========================================"
echo " Concurrent Connections Test Summary"
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

