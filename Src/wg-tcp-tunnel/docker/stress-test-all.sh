#!/bin/bash
# Master Stress Test Runner
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${RESULTS_DIR:-${SCRIPT_DIR}/stress-results}"

# Default settings
HOST="${HOST:-127.0.0.1}"
UDP_PORT="${UDP_PORT:-51822}"
WS_PORT="${WS_PORT:-51820}"
MODE="${MODE:-all}"  # all, tcp, websocket
QUICK="${QUICK:-false}"  # Quick mode skips long tests

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_header() { echo -e "\n${BOLD}${CYAN}$1${NC}\n"; }

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST      Target host (default: 127.0.0.1)"
    echo "  -p, --port PORT      UDP tunnel port (default: 51822)"
    echo "  -w, --ws-port PORT   WebSocket port (default: 51820)"
    echo "  -m, --mode MODE      Test mode: all, tcp, websocket, wireguard (default: all)"
    echo "  -q, --quick          Quick mode - skip long-running tests"
    echo "  --help               Show this help"
    echo ""
    echo "Environment variables:"
    echo "  HOST          Target host"
    echo "  UDP_PORT      UDP tunnel port"
    echo "  WS_PORT       WebSocket port"
    echo "  MODE          Test mode"
    echo "  QUICK         Set to 'true' for quick mode"
    echo ""
    echo "Examples:"
    echo "  $0                           # Run all tests"
    echo "  $0 --quick                   # Quick mode"
    echo "  $0 --mode tcp                # TCP tests only"
    echo "  $0 --mode websocket          # WebSocket tests only"
    echo "  $0 --mode wireguard          # WireGuard live tests only"
    echo "  $0 -h server -p 51822        # Custom host and port"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            UDP_PORT="$2"
            shift 2
            ;;
        -w|--ws-port)
            WS_PORT="$2"
            shift 2
            ;;
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -q|--quick)
            QUICK="true"
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Create results directory
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_RESULTS_DIR="${RESULTS_DIR}/run_${TIMESTAMP}"
mkdir -p "${RUN_RESULTS_DIR}"

# Log file
LOG_FILE="${RUN_RESULTS_DIR}/test_run.log"

echo "========================================"
echo " wg-tcp-tunnel Stress Test Suite"
echo "========================================"
echo "Host:        ${HOST}"
echo "UDP Port:    ${UDP_PORT}"
echo "WS Port:     ${WS_PORT}"
echo "Mode:        ${MODE}"
echo "Quick Mode:  ${QUICK}"
echo "Results:     ${RUN_RESULTS_DIR}"
echo "========================================"
echo ""

# Redirect output to log file as well
exec > >(tee -a "${LOG_FILE}") 2>&1

# Track test results
declare -A TEST_RESULTS
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0

run_test() {
    # Temporarily disable set -e for the entire function to prevent premature exits
    # We'll handle errors manually and let the script continue
    set +e
    
    local test_name="$1"
    local test_script="$2"
    shift 2
    local test_args="$@"
    
    log_header "Running: ${test_name}"
    
    local start_time=$(date +%s)
    local exit_code=0
    
    # Run the test
    bash "${test_script}" ${test_args} 2>&1
    exit_code=$?
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ ${exit_code} -eq 0 ]; then
        TEST_RESULTS["${test_name}"]="PASSED"
        TOTAL_PASSED=$((TOTAL_PASSED + 1))
        log_info "${test_name}: PASSED (${duration}s)"
    else
        TEST_RESULTS["${test_name}"]="FAILED"
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        log_error "${test_name}: FAILED (${duration}s)"
    fi
    
    echo ""
    # Note: We don't re-enable set -e here - it stays disabled for the rest of the script
    # This ensures tests can fail without stopping the entire suite
}

skip_test() {
    local test_name="$1"
    local reason="$2"
    
    TEST_RESULTS["${test_name}"]="SKIPPED"
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + 1))
    log_warn "Skipping ${test_name}: ${reason}"
}

# Run TCP/UDP tests
run_tcp_tests() {
    log_header "=== TCP/UDP Transport Tests ==="
    
    # Throughput test
    run_test "TCP Throughput" "${SCRIPT_DIR}/stress-test-throughput.sh" "${HOST}" "${UDP_PORT}" "tcp" "15"
    
    # Reconnection test
    run_test "TCP Reconnection" "${SCRIPT_DIR}/stress-test-reconnection.sh" "${HOST}" "${UDP_PORT}" "tcp"
    
    # Concurrent connections test
    run_test "TCP Concurrent" "${SCRIPT_DIR}/stress-test-concurrent.sh" "${HOST}" "${UDP_PORT}" "tcp"
    
    # Network conditions test
    run_test "TCP Network Conditions" "${SCRIPT_DIR}/stress-test-network.sh" "${HOST}" "${UDP_PORT}" "tcp"
    
    # Stability test (skip in quick mode)
    if [ "${QUICK}" = "true" ]; then
        skip_test "TCP Stability" "Quick mode enabled"
    else
        run_test "TCP Stability" "${SCRIPT_DIR}/stress-test-stability.sh" "${HOST}" "${UDP_PORT}" "tcp" "300"
    fi
}

# Run WebSocket tests
run_websocket_tests() {
    log_header "=== WebSocket Transport Tests ==="
    
    # Check if WebSocket services are available
    local ws_server_host="server-ws"
    local ws_client_host="${WS_HOST:-client-ws}"
    
    if ! getent hosts "${ws_server_host}" >/dev/null 2>&1 || ! getent hosts "${ws_client_host}" >/dev/null 2>&1; then
        log_warn "WebSocket services not available (server-ws or client-ws not found)"
        log_warn "Skipping WebSocket tests. Use --profile websocket to enable WebSocket services."
        skip_test "WebSocket Stress" "WebSocket services not available"
        skip_test "WebSocket Throughput" "WebSocket services not available"
        skip_test "WebSocket Reconnection" "WebSocket services not available"
        skip_test "WebSocket Network Conditions" "WebSocket services not available"
        skip_test "WebSocket Stability" "WebSocket services not available"
        return 0
    fi
    
    # WebSocket-specific tests
    # WebSocket server is at server-ws:51820 for handshake tests
    local ws_server_port="51820"
    run_test "WebSocket Stress" "${SCRIPT_DIR}/stress-test-websocket.sh" "${ws_server_host}" "${ws_server_port}"
    
    # WebSocket UDP tests should use client-ws:51822 (the WebSocket client's UDP port)
    local ws_client_port="${WS_PORT:-51822}"
    # Also run general tests in WebSocket mode
    run_test "WebSocket Throughput" "${SCRIPT_DIR}/stress-test-throughput.sh" "${ws_client_host}" "${ws_client_port}" "websocket" "15"
    
    # Reconnection test
    run_test "WebSocket Reconnection" "${SCRIPT_DIR}/stress-test-reconnection.sh" "${ws_client_host}" "${ws_client_port}" "websocket"
    
    # Network conditions test
    run_test "WebSocket Network Conditions" "${SCRIPT_DIR}/stress-test-network.sh" "${ws_client_host}" "${ws_client_port}" "websocket"
    
    # Stability test (skip in quick mode)
    if [ "${QUICK}" = "true" ]; then
        skip_test "WebSocket Stability" "Quick mode enabled"
    else
        run_test "WebSocket Stability" "${SCRIPT_DIR}/stress-test-stability.sh" "${ws_client_host}" "${ws_client_port}" "websocket" "300"
    fi
}

# Run WireGuard live tests
run_wireguard_tests() {
    log_header "=== WireGuard Live Tests ==="
    
    # Check if WireGuard services are available
    local wg_client_container="wg-tcp-tunnel-client-wg"
    local wg_server_ip="10.0.0.1"
    
    # Check if docker is available and the container is running
    if ! command -v docker &> /dev/null; then
        log_warn "Docker not available, skipping WireGuard tests"
        skip_test "WireGuard TCP" "Docker not available"
        return 0
    fi
    
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${wg_client_container}"; then
        log_warn "WireGuard client container not running"
        log_warn "Start it with: docker-compose -f docker-compose.stress.yml --profile wireguard up -d"
        skip_test "WireGuard TCP" "WireGuard services not running"
        return 0
    fi
    
    # Run WireGuard stress tests
    run_test "WireGuard TCP" "${SCRIPT_DIR}/stress-test-wireguard.sh" "tcp" "${wg_client_container}" "${wg_server_ip}"
    
    # Note: WireGuard over WebSocket would require a separate set of containers
    # with WEBSOCKET=true, which we could add as a future enhancement
}

# Make all test scripts executable
chmod +x "${SCRIPT_DIR}"/*.sh 2>/dev/null || true
chmod +x "${SCRIPT_DIR}"/*.py 2>/dev/null || true

# Disable set -e for test execution so we can continue even if individual tests fail
# We'll check for failures at the end and exit appropriately
set +e

# Run tests based on mode
case "${MODE}" in
    tcp)
        run_tcp_tests
        ;;
    websocket|ws)
        run_websocket_tests
        ;;
    wireguard|wg)
        run_wireguard_tests
        ;;
    all|*)
        run_tcp_tests
        run_websocket_tests
        run_wireguard_tests
        ;;
esac

# Re-enable set -e for final checks
set -e

# Generate metrics report
log_header "=== Generating Reports ==="

# Copy individual test results to run directory
cp -r "${RESULTS_DIR}"/*.json "${RUN_RESULTS_DIR}/" 2>/dev/null || true

# Generate metrics report
python3 "${SCRIPT_DIR}/stress-metrics.py" "${RESULTS_DIR}" \
    --csv "${RUN_RESULTS_DIR}/results.csv" \
    --json "${RUN_RESULTS_DIR}/results.json" \
    --html "${RUN_RESULTS_DIR}/report.html" \
    2>&1 || log_warn "Failed to generate metrics report"

# Print final summary
echo ""
echo "========================================"
echo " STRESS TEST SUITE COMPLETE"
echo "========================================"
echo ""
echo "Results by Test:"
for test_name in "${!TEST_RESULTS[@]}"; do
    result="${TEST_RESULTS[$test_name]}"
    case "${result}" in
        PASSED)
            echo -e "  ${GREEN}✓${NC} ${test_name}"
            ;;
        FAILED)
            echo -e "  ${RED}✗${NC} ${test_name}"
            ;;
        SKIPPED)
            echo -e "  ${YELLOW}○${NC} ${test_name}"
            ;;
    esac
done
echo ""
echo "Summary:"
echo -e "  Passed:  ${GREEN}${TOTAL_PASSED}${NC}"
echo -e "  Failed:  ${RED}${TOTAL_FAILED}${NC}"
echo -e "  Skipped: ${YELLOW}${TOTAL_SKIPPED}${NC}"
echo ""
echo "Results Directory: ${RUN_RESULTS_DIR}"
echo "HTML Report:       ${RUN_RESULTS_DIR}/report.html"
echo "Log File:          ${LOG_FILE}"
echo "========================================"

# Exit with error if any tests failed
if [ ${TOTAL_FAILED} -gt 0 ]; then
    log_error "Some tests failed!"
    exit 1
fi

log_info "All tests passed!"
exit 0

