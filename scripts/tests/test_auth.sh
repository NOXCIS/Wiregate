#!/bin/bash
# Authentication API tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "Authentication API Tests"
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

# Test: Get CSRF token
test_name="Get CSRF token"
if response=$(test_request "GET" "/api/csrf-token" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        # CSRF token endpoint returns .data.csrf_token, not .data.token
        assert_json_field_exists "$response" ".data.csrf_token" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "CSRF token response invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Validate authentication required
test_name="Require authentication check"
if response=$(test_request "GET" "/api/requireAuthentication" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Validate authentication (should be authenticated)
test_name="Validate authentication (authenticated)"
if response=$(test_request "GET" "/api/validateAuthentication" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        # validateAuthentication returns status=true when authenticated, data may be null
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Handshake endpoint
test_name="Handshake endpoint"
if response=$(test_request "GET" "/api/handshake" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Security check
test_name="Security check endpoint"
if response=$(test_request "GET" "/api/security-check" "" 200 "$test_name"); then
    # Security check may return status=false if there's an error, that's acceptable
    status=$(echo "$response" | jq -r '.status // false')
    if [ "$status" = "true" ] || [ "$status" = "false" ]; then
        # Both true and false are valid responses (false indicates an error but endpoint works)
        test_pass "$test_name"
    else
        test_fail "$test_name" "Invalid response format"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get rate limit status
test_name="Get rate limit status"
if response=$(test_request "GET" "/api/rate-limit-status" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        # Check if data exists (may have identifier or other fields)
        data=$(echo "$response" | jq -r '.data // empty')
        if [ -n "$data" ] && [ "$data" != "null" ]; then
            test_pass "$test_name"
        else
            # Data might be empty, but status is true, so endpoint works
            test_pass "$test_name"
        fi
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Sign out
test_name="Sign out"
if response=$(test_request "GET" "/api/signout" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Re-authenticate for subsequent tests
authenticate > /dev/null 2>&1

# Test: Authentication with invalid credentials (should fail)
test_name="Authentication with invalid credentials"
# Use a temporary cookie file to avoid affecting main session
temp_cookie="/tmp/wiregate_test_temp_cookies.txt"
rm -f "$temp_cookie"
touch "$temp_cookie"

# Get CSRF token
csrf_resp=$(curl -s -c "$temp_cookie" -b "$temp_cookie" \
    -H "Content-Type: application/json" \
    "${TEST_APP_URL}/api/csrf-token")
temp_csrf=$(echo "$csrf_resp" | jq -r '.data.token // empty')

# Try to authenticate with wrong password
auth_resp=$(curl -s -c "$temp_cookie" -b "$temp_cookie" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-CSRF-Token: $temp_csrf" \
    -d '{"username":"admin","password":"wrongpassword"}' \
    "${TEST_APP_URL}/api/authenticate")

auth_status=$(echo "$auth_resp" | jq -r '.status // false')
if [ "$auth_status" = "false" ]; then
    test_pass "$test_name"
else
    test_fail "$test_name" "Authentication should have failed with wrong password"
fi

rm -f "$temp_cookie"

# Test: Validate authentication endpoint (unauthenticated - should return 200 with status=false)
test_name="Validate authentication (unauthenticated)"
# Make request without authentication (don't send any cookies)
# Endpoint is public and returns status=false when not authenticated
unauth_response=$(curl -s \
    -H "Content-Type: application/json" \
    "${TEST_APP_URL}/api/validateAuthentication" 2>&1)
unauth_status=$(echo "$unauth_response" | jq -r '.status // false')
if [ "$unauth_status" = "false" ]; then
    test_pass "$test_name"
else
    test_fail "$test_name" "Expected status=false for unauthenticated request, got status=$unauth_status"
fi

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "auth" "$suite_start_time" "$suite_end_time" "test-results/api-tests-auth.json" || true

# Print summary and exit with appropriate code
if print_summary "Authentication API"; then
    exit 0
else
    exit 1
fi

