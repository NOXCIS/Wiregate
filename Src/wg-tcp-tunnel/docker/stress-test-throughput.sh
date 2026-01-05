#!/bin/bash
# High-Throughput Stress Test
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${1:-127.0.0.1}"
PORT="${2:-51822}"
MODE="${3:-tcp}"  # tcp or websocket
DURATION="${4:-30}"
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/stress-results}"

# Test parameters
RATES=(100 500 1000 2000 5000)
PACKET_SIZES=(64 256 512 1024)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Result file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="${RESULTS_DIR}/throughput_${MODE}_${TIMESTAMP}.json"

echo "========================================"
echo " Throughput Stress Test"
echo "========================================"
echo "Target:    ${HOST}:${PORT}"
echo "Mode:      ${MODE}"
echo "Duration:  ${DURATION}s per test"
echo "Results:   ${RESULT_FILE}"
echo "========================================"
echo ""

# Initialize results JSON
echo '{"mode": "'${MODE}'", "timestamp": "'${TIMESTAMP}'", "tests": []}' > "${RESULT_FILE}"

run_udp_test() {
    local rate=$1
    local size=$2
    local duration=$3
    local test_name="rate_${rate}_size_${size}"
    local test_result_file="${RESULTS_DIR}/${test_name}_${TIMESTAMP}.json"
    
    log_info "Testing: ${rate} pps, ${size} bytes, ${duration}s"
    
    # Run the stress test client
    python3 -u "${SCRIPT_DIR}/stress-udp-client.py" \
        "${HOST}" "${PORT}" \
        --rate "${rate}" \
        --duration "${duration}" \
        --size "${size}" \
        --verbose \
        --json "${test_result_file}" \
        2>&1 | while read line; do
            echo "  $line"
        done
    
    # Check if test succeeded
    if [ -f "${test_result_file}" ]; then
        # Append to main results
        local json_error=""
        json_error=$(python3 -c "
import json, sys
try:
    with open('${RESULT_FILE}', 'r') as f:
        data = json.load(f)
    with open('${test_result_file}', 'r') as f:
        test = json.load(f)
    test['test_name'] = '${test_name}'
    test['rate_target'] = ${rate}
    test['packet_size'] = ${size}
    data['tests'].append(test)
    with open('${RESULT_FILE}.tmp', 'w') as f:
        json.dump(data, f, indent=2)
except Exception as e:
    print(f'Error processing JSON: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1) || {
            log_error "  Failed to process test results: ${json_error}"
            return 1
        }
        
        if [ -f "${RESULT_FILE}.tmp" ]; then
            mv "${RESULT_FILE}.tmp" "${RESULT_FILE}" || {
                log_error "  Failed to move result file"
                return 1
            }
        else
            log_error "  Result file not created"
            return 1
        fi
        
        # Check pass/fail
        local loss=$(python3 -c "import json; f=open('${test_result_file}'); d=json.load(f); f.close(); print(d.get('loss_rate_percent', 100))" 2>/dev/null || echo "100")
        if (( $(echo "$loss < 1" | bc -l) )); then
            log_info "  PASSED (loss: ${loss}%)"
            return 0
        else
            log_warn "  FAILED (loss: ${loss}%)"
            return 1
        fi
    else
        log_error "  Test failed - no results file"
        return 1
    fi
}

# Summary counters
PASSED=0
FAILED=0

# Run baseline test
log_info "=== Baseline Test ==="
if run_udp_test 100 256 10; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Run throughput tests with varying rates
log_info "=== Rate Scaling Tests ==="
for rate in "${RATES[@]}"; do
    if run_udp_test "${rate}" 256 "${DURATION}"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done
echo ""

# Run tests with varying packet sizes
log_info "=== Packet Size Tests ==="
for size in "${PACKET_SIZES[@]}"; do
    if run_udp_test 500 "${size}" "${DURATION}"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done
echo ""

# Run burst test
log_info "=== Burst Test ==="
if run_udp_test 10000 256 5; then
    PASSED=$((PASSED + 1))
else
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
echo "========================================"
echo " Throughput Test Summary"
echo "========================================"
echo "Passed: ${PASSED}"
echo "Failed: ${FAILED}"
echo "Results: ${RESULT_FILE}"
echo "========================================"

# Exit with error if any tests failed
if [ "${FAILED}" -gt 0 ]; then
    log_error "Some tests failed!"
    exit 1
fi

log_info "All tests passed!"
exit 0

