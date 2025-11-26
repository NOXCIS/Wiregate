#!/bin/bash
# Test runner script that runs all tests with proper delays to avoid rate limiting

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Source test helpers for authentication
source "$SCRIPT_DIR/../test_helpers.sh"

echo "=========================================="
echo "Running All Test Suites"
echo "=========================================="
echo ""

# Authenticate once at the start to share session across all test suites
echo "Authenticating once for all test suites..."
rm -f "$COOKIE_FILE"  # Clear any stale cookies
if ! authenticate; then
    echo "Failed to authenticate" >&2
    exit 1
fi
echo "Authentication successful - session will be shared across all test suites"
echo ""

# Delay between test suites (reduced since we're using shared session)
TEST_DELAY="${TEST_DELAY:-5}"

# Track overall results
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
FAILED_SUITES=()

# Run each test suite
for test_script in scripts/tests/test_*.sh; do
    test_name=$(basename "$test_script" .sh)
    echo "=========================================="
    echo "Running $test_name"
    echo "=========================================="
    
    # Run the test and capture output (capture regardless of exit code)
    set +e  # Temporarily disable exit on error to capture output even if test fails
    output=$(bash "$test_script" 2>&1)
    exit_code=$?
    set -e  # Re-enable exit on error
    
    # Extract summary from output (macOS-compatible: use sed instead of grep -P)
    passed=$(echo "$output" | sed -n 's/.*Passed: \([0-9]*\).*/\1/p' | head -1 || echo "0")
    failed=$(echo "$output" | sed -n 's/.*Failed: \([0-9]*\).*/\1/p' | head -1 || echo "0")
    skipped=$(echo "$output" | sed -n 's/.*Skipped: \([0-9]*\).*/\1/p' | head -1 || echo "0")
    
    # Check if we got valid test results (has "Test Summary" in output)
    if echo "$output" | grep -q "Test Summary"; then
        # Test suite ran successfully, even if some tests failed
        TOTAL_PASSED=$((TOTAL_PASSED + passed))
        TOTAL_FAILED=$((TOTAL_FAILED + failed))
        TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
        
        if [ "$failed" -gt 0 ]; then
            FAILED_SUITES+=("$test_name")
        fi
        
        # Show summary
        echo "$output" | grep -A 4 "Test Summary" || echo "$output" | tail -5
    else
        # Test suite failed to run (no summary found)
        echo "Test suite failed to run (exit code: $exit_code)"
        FAILED_SUITES+=("$test_name")
        TOTAL_FAILED=$((TOTAL_FAILED + 1))
        echo "$output" | tail -10
    fi
    
    echo ""
    
    # Check if rate limiting occurred and wait longer if needed
    if echo "$output" | grep -qi "rate limit"; then
        echo "Rate limit detected, waiting ${TEST_DELAY}s for reset..."
        sleep "$TEST_DELAY"
    fi
    
    # Wait between tests to avoid rate limiting (except after last test)
    if [ "$test_script" != "$(ls -t scripts/tests/test_*.sh | tail -1)" ]; then
        echo "Waiting ${TEST_DELAY}s before next test suite..."
        sleep "$TEST_DELAY"
        echo ""
    fi
done

# Print overall summary
echo "=========================================="
echo "Overall Test Summary"
echo "=========================================="
echo "Total Passed: $TOTAL_PASSED"
echo "Total Failed: $TOTAL_FAILED"
echo "Total Skipped: $TOTAL_SKIPPED"
if [ ${#FAILED_SUITES[@]} -gt 0 ]; then
    echo ""
    echo "Failed Suites:"
    for suite in "${FAILED_SUITES[@]}"; do
        echo "  - $suite"
    done
fi
echo "=========================================="
echo ""

# Exit with error if any tests failed
if [ $TOTAL_FAILED -gt 0 ]; then
    exit 1
else
    exit 0
fi

