#!/bin/bash
# CPS Pattern API tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "CPS Pattern API Tests"
echo "=========================================="
echo ""

# Check for existing session first, authenticate only if needed
if ! check_session 2>/dev/null; then
    echo "Authenticating..."
    rm -f "$COOKIE_FILE"  # Clear any stale cookies
    if ! authenticate; then
        echo "Failed to authenticate" >&2
        exit 1
    fi
    echo "Authentication successful"
else
    echo "Using existing session"
fi
echo ""

# Test: Get CPS pattern for quic
test_name="Get CPS pattern (quic)"
endpoint="/api/cps-patterns/quic"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get CPS pattern for http_get
test_name="Get CPS pattern (http_get)"
endpoint="/api/cps-patterns/http_get"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get CPS pattern for dns
test_name="Get CPS pattern (dns)"
endpoint="/api/cps-patterns/dns"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get CPS pattern for json (may not exist)
test_name="Get CPS pattern (json)"
endpoint="/api/cps-patterns/json"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    # This may return empty data if pattern doesn't exist
    test_pass "$test_name"
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get CPS pattern for http_response (may not exist)
test_name="Get CPS pattern (http_response)"
endpoint="/api/cps-patterns/http_response"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    # This may return empty data if pattern doesn't exist
    test_pass "$test_name"
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get CPS patterns statistics
test_name="Get CPS patterns statistics"
endpoint="/api/cps-patterns/statistics"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Add CPS pattern (use a valid protocol that we can test with)
test_name="Add CPS pattern"
# Use http_get as the protocol since it's a valid one and we can test adding a custom pattern
# Note: The API expects 'cps_pattern' not 'pattern'
test_pattern="<b 0xc0><c><t><r 16>"
pattern_data=$(jq -n \
    --arg protocol "http_get" \
    --arg pattern "$test_pattern" \
    '{
        protocol: $protocol,
        cps_pattern: $pattern
    }')
if response=$(test_request "POST" "/api/cps-patterns" "$pattern_data" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
        # Store pattern and protocol for cleanup
        echo "$test_pattern" > /tmp/test_cps_pattern.txt
        echo "http_get" > /tmp/test_cps_protocol.txt
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Add CPS pattern (missing fields)
test_name="Add CPS pattern (missing fields)"
invalid_data='{"protocol":"http_get"}'
if response=$(test_request "POST" "/api/cps-patterns" "$invalid_data" 200 "$test_name"); then
    status=$(echo "$response" | jq -r '.status // false')
    if [ "$status" = "false" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Should have failed with missing fields"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Delete CPS pattern
# Find the pattern ID we just added by getting all patterns and matching the pattern string
test_name="Delete CPS pattern"
if [ -f /tmp/test_cps_pattern.txt ] && [ -f /tmp/test_cps_protocol.txt ]; then
    test_pattern=$(cat /tmp/test_cps_pattern.txt)
    test_protocol=$(cat /tmp/test_cps_protocol.txt)
    
    # Get all patterns for the protocol to find the one we added
    all_patterns_resp=$(test_request "GET" "/api/cps-patterns/${test_protocol}/all" "" 200 "Get all patterns for deletion" 2>/dev/null || echo '{}')
    pattern_id=$(echo "$all_patterns_resp" | jq -r --arg pattern "$test_pattern" '.data.patterns[]? | select(.cps_pattern == $pattern) | .id // empty' | head -1)
    
    if [ -n "$pattern_id" ] && [ "$pattern_id" != "null" ] && [ "$pattern_id" != "" ]; then
        # Delete the pattern we just added
        endpoint="/api/cps-patterns/${pattern_id}"
        if response=$(test_request "DELETE" "$endpoint" "" 200 "$test_name"); then
            if assert_json_status "$response" "$test_name"; then
                test_pass "$test_name"
            else
                test_fail "$test_name" "Response status invalid"
            fi
        else
            test_fail "$test_name" "Request failed"
        fi
    else
        test_skip "$test_name" "Could not find pattern ID for deletion"
    fi
    rm -f /tmp/test_cps_pattern.txt /tmp/test_cps_protocol.txt
else
    test_skip "$test_name" "No test pattern available to delete"
fi

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "cps" "$suite_start_time" "$suite_end_time" "test-results/api-tests-cps.json" || true

# Cleanup
rm -f /tmp/test_cps_protocol.txt

# Print summary and exit with appropriate code
if print_summary "CPS Pattern API"; then
    exit 0
else
    exit 1
fi

