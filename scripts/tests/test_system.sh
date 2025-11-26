#!/bin/bash
# System Status and Dashboard API tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "System Status and Dashboard API Tests"
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

# Test: Get system status
test_name="Get system status"
if response=$(test_request "GET" "/api/systemStatus" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get dashboard configuration
test_name="Get dashboard configuration"
if response=$(test_request "GET" "/api/getDashboardConfiguration" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get dashboard update
test_name="Get dashboard update"
if response=$(test_request "GET" "/api/getDashboardUpdate" "" 200 "$test_name"); then
    # Update check might return status=false if check is in progress
    # This is valid behavior, so we just check that we got a response
    test_pass "$test_name"
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get dashboard version
test_name="Get dashboard version"
if response=$(test_request "GET" "/api/getDashboardVersion" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get dashboard proto
test_name="Get dashboard proto"
if response=$(test_request "GET" "/api/getDashboardProto" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Update dashboard configuration item
test_name="Update dashboard configuration item"
update_data='{"section":"Other","key":"test_key","value":"test_value"}'
if response=$(test_request "POST" "/api/updateDashboardConfigurationItem" "$update_data" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Update dashboard configuration item with missing fields
test_name="Update dashboard configuration item (missing fields)"
invalid_data='{"key":"test_key"}'
# This should return 422 (validation error) for missing required fields
if response=$(test_request "POST" "/api/updateDashboardConfigurationItem" "$invalid_data" 422 "$test_name"); then
    test_pass "$test_name"
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get locale
test_name="Get locale"
if response=$(test_request "GET" "/api/locale" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get current version changelog
test_name="Get current version changelog"
endpoint="/api/getCurrentVersionChangelog?version=flat-bridge-v1.5.0"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get current version changelog (missing version)
test_name="Get current version changelog (missing version)"
if response=$(test_request "GET" "/api/getCurrentVersionChangelog" "" 422 "$test_name"); then
    test_pass "$test_name"
else
    test_fail "$test_name" "Should return 422 for missing version"
fi

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "system" "$suite_start_time" "$suite_end_time" "test-results/api-tests-system.json" || true

# Print summary and exit with appropriate code
if print_summary "System Status and Dashboard API"; then
    exit 0
else
    exit 1
fi

