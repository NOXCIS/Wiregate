#!/bin/bash
# Test helper functions for API testing

# Default test configuration
TEST_APP_URL="${TEST_APP_URL:-http://localhost:8090}"
COOKIE_FILE="${COOKIE_FILE:-/tmp/wiregate_test_cookies.txt}"
CSRF_TOKEN_FILE="${CSRF_TOKEN_FILE:-/tmp/wiregate_test_csrf_token.txt}"

# Test results tracking
declare -a TEST_RESULTS
TEST_RESULTS=()

# Initialize test results
init_test_results() {
    TEST_RESULTS=()
}

# Get CSRF token (exported for use in test scripts)
get_csrf_token() {
    if [ -f "$CSRF_TOKEN_FILE" ]; then
        cat "$CSRF_TOKEN_FILE" 2>/dev/null || echo ""
    else
        # Try to get CSRF token from API
        local csrf_resp=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
            -H "Content-Type: application/json" \
            "${TEST_APP_URL}/api/csrf-token" 2>&1)
        local csrf_token=$(echo "$csrf_resp" | jq -r '.data.csrf_token // .data.token // empty' 2>/dev/null)
        if [ -n "$csrf_token" ] && [ "$csrf_token" != "null" ]; then
            echo "$csrf_token" > "$CSRF_TOKEN_FILE"
            echo "$csrf_token"
        else
            echo ""
        fi
    fi
}

# Make an API request
test_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local expected_status="$4"
    local test_name="$5"
    
    local url="${TEST_APP_URL}${endpoint}"
    local curl_opts=(-s -w "\n%{http_code}" -c "$COOKIE_FILE" -b "$COOKIE_FILE" -H "Content-Type: application/json")
    
    # For POST and DELETE requests, include CSRF token if available
    if [ "$method" = "POST" ] || [ "$method" = "DELETE" ]; then
        local csrf_token=$(get_csrf_token)
        if [ -n "$csrf_token" ]; then
            curl_opts+=(-H "X-CSRF-Token: $csrf_token")
        fi
    fi
    
    if [ "$method" = "GET" ]; then
        response=$(curl "${curl_opts[@]}" "$url" 2>&1)
    elif [ "$method" = "POST" ]; then
        response=$(curl "${curl_opts[@]}" -X POST -d "$data" "$url" 2>&1)
    elif [ "$method" = "DELETE" ]; then
        response=$(curl "${curl_opts[@]}" -X DELETE "$url" 2>&1)
    else
        echo "Error: Unsupported method $method" >&2
        return 1
    fi
    
    # Extract HTTP status code (last line)
    http_code=$(echo "$response" | tail -1)
    # Extract response body (all but last line)
    body=$(echo "$response" | sed '$d')
    
    # Check if we got the expected status code
    if [ "$http_code" = "$expected_status" ]; then
        echo "$body"
        return 0
    else
        echo "Error: Expected status $expected_status, got $http_code" >&2
        echo "$body" >&2
        return 1
    fi
}

# Assert JSON response has status=true
assert_json_status() {
    local response="$1"
    local test_name="$2"
    
    local status=$(echo "$response" | jq -r '.status // false' 2>/dev/null)
    if [ "$status" = "true" ]; then
        return 0
    else
        local message=$(echo "$response" | jq -r '.message // "Unknown error"' 2>/dev/null)
        echo "  ${RED}Error:${NC} API returned status=false: $message" >&2
        return 1
    fi
}

# Assert JSON field exists
assert_json_field_exists() {
    local response="$1"
    local field="$2"
    local test_name="$3"
    
    local value=$(echo "$response" | jq -r "$field // empty" 2>/dev/null)
    if [ -n "$value" ] && [ "$value" != "null" ]; then
        return 0
    else
        echo "  ${RED}Error:${NC} Field $field not found in response" >&2
        return 1
    fi
}

# Record test pass
test_pass() {
    local test_name="$1"
    TEST_RESULTS+=("PASS:$test_name")
    echo -e "${GREEN}✓${NC} $test_name"
}

# Record test fail
test_fail() {
    local test_name="$1"
    local message="${2:-}"
    TEST_RESULTS+=("FAIL:$test_name:$message")
    echo -e "${RED}✗${NC} $test_name"
    if [ -n "$message" ]; then
        echo "  ${RED}Error:${NC} $message" >&2
    fi
}

# Record test skip
test_skip() {
    local test_name="$1"
    local reason="${2:-}"
    TEST_RESULTS+=("SKIP:$test_name:$reason")
    echo -e "${YELLOW}⊘${NC} $test_name${reason:+ ($reason)}"
}

# Check if we have a valid session (without re-authenticating)
check_session() {
    # Check if cookie file exists and has content
    if [ ! -f "$COOKIE_FILE" ] || [ ! -s "$COOKIE_FILE" ]; then
        return 1
    fi
    
    # Try to validate the session by checking authentication status
    local validate_resp=$(curl -s -b "$COOKIE_FILE" \
        -H "Content-Type: application/json" \
        "${TEST_APP_URL}/api/validateAuthentication" 2>&1)
    
    # API returns {"status":true,"data":true} where data is a boolean
    local is_authenticated=$(echo "$validate_resp" | jq -r '.data // false' 2>/dev/null)
    
    if [ "$is_authenticated" = "true" ]; then
        # Session is valid, ensure CSRF token is available
        if [ ! -f "$CSRF_TOKEN_FILE" ] || [ ! -s "$CSRF_TOKEN_FILE" ]; then
            # Get CSRF token if we don't have it
            local csrf_resp=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
                -H "Content-Type: application/json" \
                "${TEST_APP_URL}/api/csrf-token" 2>&1)
            
            local csrf_token=$(echo "$csrf_resp" | jq -r '.data.csrf_token // .data.token // empty' 2>/dev/null)
            
            if [ -n "$csrf_token" ] && [ "$csrf_token" != "null" ]; then
                echo "$csrf_token" > "$CSRF_TOKEN_FILE"
            fi
        fi
        return 0
    fi
    
    return 1
}

# Authenticate and get session cookie
authenticate() {
    # Check if we already have a valid session
    if check_session; then
        return 0
    fi
    
    # Clear CSRF token file when starting new authentication
    rm -f "$CSRF_TOKEN_FILE"
    
    # Authenticate first (doesn't require CSRF token)
    local username="${TEST_USERNAME:-admin}"
    local password="${TEST_PASSWORD:-admin}"
    
    # Retry authentication with exponential backoff if rate limited
    local max_retries=3
    local retry_delay=2
    local attempt=0
    
    while [ $attempt -lt $max_retries ]; do
        local auth_resp=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"$username\",\"password\":\"$password\"}" \
            "${TEST_APP_URL}/api/authenticate" 2>&1)
        
        local auth_status=$(echo "$auth_resp" | jq -r '.status // false' 2>/dev/null)
        local message=$(echo "$auth_resp" | jq -r '.message // "Authentication failed"' 2>/dev/null)
        
        if [ "$auth_status" = "true" ]; then
            break  # Success, exit retry loop
        fi
        
        # Check if rate limited
        if echo "$message" | grep -qi "rate limit"; then
            attempt=$((attempt + 1))
            if [ $attempt -lt $max_retries ]; then
                echo "Rate limited, waiting ${retry_delay}s before retry ($attempt/$max_retries)..." >&2
                sleep $retry_delay
                retry_delay=$((retry_delay * 2))  # Exponential backoff
            else
                echo "Authentication failed: $message" >&2
                return 1
            fi
        else
            # Not rate limited, but authentication failed for another reason
            echo "Authentication failed: $message" >&2
            return 1
        fi
    done
    
    if [ "$auth_status" != "true" ]; then
        echo "Authentication failed after $max_retries attempts" >&2
        return 1
    fi
    
    # Now get CSRF token (requires authentication)
    local csrf_resp=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
        -H "Content-Type: application/json" \
        "${TEST_APP_URL}/api/csrf-token" 2>&1)
    
    local csrf_token=$(echo "$csrf_resp" | jq -r '.data.csrf_token // .data.token // empty' 2>/dev/null)
    
    if [ -z "$csrf_token" ] || [ "$csrf_token" = "null" ]; then
        echo "Failed to get CSRF token after authentication" >&2
        return 1
    fi
    
    # Store CSRF token in file for use by test_request
    echo "$csrf_token" > "$CSRF_TOKEN_FILE"
    
    return 0
}

# Generate JSON test report
generate_json_report() {
    local suite="$1"
    local start_time="$2"
    local end_time="$3"
    local output_file="$4"
    
    local duration=$((end_time - start_time))
    local passed=0
    local failed=0
    local skipped=0
    
    declare -a tests_json
    tests_json=()
    
    for result in "${TEST_RESULTS[@]}"; do
        IFS=':' read -r status name message <<< "$result"
        case "$status" in
            PASS)
                ((passed++))
                tests_json+=("{\"name\":\"$name\",\"status\":\"pass\",\"message\":\"\"}")
                ;;
            FAIL)
                ((failed++))
                local msg_escaped=$(echo "$message" | sed 's/"/\\"/g')
                tests_json+=("{\"name\":\"$name\",\"status\":\"fail\",\"message\":{\"message\":\"$msg_escaped\",\"details\":\"\"}}")
                ;;
            SKIP)
                ((skipped++))
                local reason_escaped=$(echo "$message" | sed 's/"/\\"/g')
                tests_json+=("{\"name\":\"$name\",\"status\":\"skip\",\"message\":\"$reason_escaped\"}")
                ;;
        esac
    done
    
    local tests_array=$(IFS=','; echo "${tests_json[*]}")
    
    cat > "$output_file" <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "suite": "$suite",
  "total_tests": ${#TEST_RESULTS[@]},
  "passed": $passed,
  "failed": $failed,
  "skipped": $skipped,
  "duration_seconds": $duration,
  "tests": [$tests_array]
}
EOF
}

# Print test summary
print_summary() {
    local suite_name="$1"
    
    local passed=0
    local failed=0
    local skipped=0
    
    for result in "${TEST_RESULTS[@]}"; do
        IFS=':' read -r status name message <<< "$result"
        case "$status" in
            PASS) ((passed++)) ;;
            FAIL) ((failed++)) ;;
            SKIP) ((skipped++)) ;;
        esac
    done
    
    echo ""
    echo "=========================================="
    echo "Test Summary: $suite_name"
    echo "=========================================="
    echo "Total:  ${#TEST_RESULTS[@]}"
    echo -e "${GREEN}Passed: $passed${NC}"
    echo -e "${RED}Failed: $failed${NC}"
    if [ $skipped -gt 0 ]; then
        echo -e "${YELLOW}Skipped: $skipped${NC}"
    fi
    echo "=========================================="
    echo ""
    
    if [ $failed -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

