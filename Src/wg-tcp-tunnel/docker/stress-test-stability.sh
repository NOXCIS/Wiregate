#!/bin/bash
# Long-Running Stability Test
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-51822}"
MODE="${3:-tcp}"  # tcp or websocket
DURATION="${4:-3600}"  # Default 1 hour
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/stress-results}"

# Test parameters
SAMPLE_INTERVAL=60  # Collect stats every minute
PACKET_RATE=100
MEMORY_THRESHOLD_MB=500  # Alert if memory exceeds this

# Container names
SERVER_CONTAINER="${SERVER_CONTAINER:-wg-tcp-tunnel-server}"
CLIENT_CONTAINER="${CLIENT_CONTAINER:-wg-tcp-tunnel-client}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1"; }
log_test() { echo -e "${CYAN}[TEST]${NC} $(date '+%H:%M:%S') $1"; }

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Result file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/stability_${MODE}_${TIMESTAMP}.json"
METRICS_FILE="${RESULTS_DIR}/stability_metrics_${TIMESTAMP}.csv"

echo "========================================"
echo " Long-Running Stability Test"
echo "========================================"
echo "Target:        ${HOST}:${PORT}"
echo "Mode:          ${MODE}"
echo "Duration:      ${DURATION}s ($((DURATION/60)) minutes)"
echo "Sample Rate:   every ${SAMPLE_INTERVAL}s"
echo "Results:       ${RESULT_FILE}"
echo "========================================"
echo ""

# Initialize results
cat > "${RESULT_FILE}" << EOF
{
    "mode": "${MODE}",
    "timestamp": "${TIMESTAMP}",
    "duration_seconds": ${DURATION},
    "sample_interval_seconds": ${SAMPLE_INTERVAL},
    "samples": [],
    "summary": {}
}
EOF

# Initialize metrics CSV
echo "timestamp,elapsed_seconds,packets_sent,packets_received,packets_lost,loss_rate,latency_avg,latency_p99,server_memory_mb,client_memory_mb" > "${METRICS_FILE}"

# Check Docker availability
CAN_MONITOR_DOCKER=false
if command -v docker &> /dev/null; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${SERVER_CONTAINER}"; then
        CAN_MONITOR_DOCKER=true
        log_info "Docker monitoring available"
    fi
fi

# Get container memory usage
get_container_memory() {
    local container=$1
    if [ "${CAN_MONITOR_DOCKER}" = "true" ]; then
        docker stats --no-stream --format "{{.MemUsage}}" "${container}" 2>/dev/null | \
            sed 's/MiB.*//' | sed 's/GiB/*1024/' | bc 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Traffic generator PID
TRAFFIC_PID=""
MONITOR_PID=""

cleanup() {
    log_info "Cleaning up..."
    if [ -n "${TRAFFIC_PID}" ]; then
        kill "${TRAFFIC_PID}" 2>/dev/null || true
    fi
    if [ -n "${MONITOR_PID}" ]; then
        kill "${MONITOR_PID}" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
}

trap cleanup EXIT

# Start traffic generator
start_traffic() {
    log_info "Starting traffic generator at ${PACKET_RATE} pps..."
    
    python3 -u "${SCRIPT_DIR}/stress-udp-client.py" \
        "${HOST}" "${PORT}" \
        --rate "${PACKET_RATE}" \
        --duration "${DURATION}" \
        --size 256 \
        --verbose \
        --json "${RESULTS_DIR}/stability_traffic.json" \
        2>&1 | while read line; do
            echo "  [TRAFFIC] $line"
        done &
    
    TRAFFIC_PID=$!
    log_info "Traffic generator started (PID: ${TRAFFIC_PID})"
}

# Collect sample
collect_sample() {
    local elapsed=$1
    local sample_num=$2
    
    # Get memory usage
    local server_mem=$(get_container_memory "${SERVER_CONTAINER}")
    local client_mem=$(get_container_memory "${CLIENT_CONTAINER}")
    
    # Quick packet test
    local test_start=$(date +%s.%N)
    local test_result=$(echo "stability-sample-${sample_num}" | timeout 2 nc -u -w 1 "${HOST}" "${PORT}" 2>&1)
    local test_end=$(date +%s.%N)
    
    local latency=0
    if [ -n "${test_result}" ]; then
        latency=$(echo "scale=2; (${test_end} - ${test_start}) * 1000" | bc)
    fi
    
    # Log sample
    log_info "Sample ${sample_num}: elapsed=${elapsed}s, latency=${latency}ms, server_mem=${server_mem}MB, client_mem=${client_mem}MB"
    
    # Check memory threshold
    if [ "${server_mem}" != "0" ]; then
        if (( $(echo "${server_mem} > ${MEMORY_THRESHOLD_MB}" | bc -l) )); then
            log_warn "Server memory exceeds threshold: ${server_mem}MB > ${MEMORY_THRESHOLD_MB}MB"
        fi
    fi
    
    # Append to CSV
    echo "$(date +%s),${elapsed},0,0,0,0,${latency},0,${server_mem},${client_mem}" >> "${METRICS_FILE}"
    
    # Append to JSON
    python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['samples'].append({
    'sample_num': ${sample_num},
    'elapsed_seconds': ${elapsed},
    'latency_ms': ${latency},
    'server_memory_mb': ${server_mem},
    'client_memory_mb': ${client_mem}
})
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
"
}

# Monitor function
monitor() {
    local start_time=$(date +%s)
    local sample_num=0
    
    while true; do
        sleep "${SAMPLE_INTERVAL}"
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        ((sample_num++))
        
        if [ ${elapsed} -ge ${DURATION} ]; then
            break
        fi
        
        collect_sample ${elapsed} ${sample_num}
    done
}

# Main test
run_stability_test() {
    log_test "Starting stability test for ${DURATION} seconds..."
    
    local start_time=$(date +%s)
    
    # Start traffic
    start_traffic
    
    # Start monitoring
    monitor &
    MONITOR_PID=$!
    
    # Wait for traffic to complete
    wait "${TRAFFIC_PID}" 2>/dev/null || true
    
    local end_time=$(date +%s)
    local actual_duration=$((end_time - start_time))
    
    # Stop monitor
    kill "${MONITOR_PID}" 2>/dev/null || true
    
    log_info "Test completed after ${actual_duration} seconds"
    
    # Analyze results
    if [ -f "${RESULTS_DIR}/stability_traffic.json" ]; then
        local traffic_data=$(cat "${RESULTS_DIR}/stability_traffic.json")
        
        local packets_sent=$(echo "${traffic_data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('packets_sent', 0))")
        local packets_received=$(echo "${traffic_data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('packets_received', 0))")
        local packets_lost=$(echo "${traffic_data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('packets_lost', 0))")
        local loss_rate=$(echo "${traffic_data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('loss_rate_percent', 0))")
        local avg_latency=$(echo "${traffic_data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('latency_ms', {}).get('avg', 0))")
        local p99_latency=$(echo "${traffic_data}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('latency_ms', {}).get('p99', 0))")
        
        log_info "=== Stability Test Summary ==="
        log_info "Duration:         ${actual_duration}s"
        log_info "Packets Sent:     ${packets_sent}"
        log_info "Packets Received: ${packets_received}"
        log_info "Packets Lost:     ${packets_lost} (${loss_rate}%)"
        log_info "Avg Latency:      ${avg_latency}ms"
        log_info "P99 Latency:      ${p99_latency}ms"
        
        # Update summary in results
        python3 -c "
import json
with open('${RESULT_FILE}', 'r') as f:
    data = json.load(f)
data['summary'] = {
    'actual_duration_seconds': ${actual_duration},
    'packets_sent': ${packets_sent},
    'packets_received': ${packets_received},
    'packets_lost': ${packets_lost},
    'loss_rate_percent': ${loss_rate},
    'avg_latency_ms': ${avg_latency},
    'p99_latency_ms': ${p99_latency}
}
with open('${RESULT_FILE}', 'w') as f:
    json.dump(data, f, indent=2)
"
        
        # Check pass/fail criteria
        if (( $(echo "${loss_rate} < 1" | bc -l) )); then
            log_info "PASSED: Loss rate ${loss_rate}% is within acceptable range"
            return 0
        else
            log_error "FAILED: Loss rate ${loss_rate}% exceeds 1% threshold"
            return 1
        fi
    else
        log_error "No traffic results file found"
        return 1
    fi
}

# Run the test
if run_stability_test; then
    echo ""
    echo "========================================"
    echo " Stability Test PASSED"
    echo "========================================"
    echo "Results: ${RESULT_FILE}"
    echo "Metrics: ${METRICS_FILE}"
    echo "========================================"
    exit 0
else
    echo ""
    echo "========================================"
    echo " Stability Test FAILED"
    echo "========================================"
    echo "Results: ${RESULT_FILE}"
    echo "Metrics: ${METRICS_FILE}"
    echo "========================================"
    exit 1
fi

