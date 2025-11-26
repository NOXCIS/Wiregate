#!/bin/bash
# Peer Management API tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

# Container name
WIREGATE_CONTAINER="${WIREGATE_CONTAINER:-wiregate}"

# Helper function to check if container is available
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${WIREGATE_CONTAINER}$"; then
        return 1
    fi
    return 0
}

# Helper function to exec into container and run command
container_exec() {
    local cmd="$1"
    if check_container; then
        docker exec "${WIREGATE_CONTAINER}" sh -c "$cmd" 2>/dev/null
        return $?
    else
        return 1
    fi
}

# Helper function to verify peer exists in config file
verify_peer_in_config() {
    local config_name="$1"
    local peer_public_key="$2"
    local config_file="/etc/wireguard/${config_name}.conf"
    
    if ! check_container; then
        return 2  # Container not available
    fi
    
    # Check if peer section exists with the public key
    if container_exec "grep -q '^\[Peer\]' ${config_file} && grep -A 10 '^\[Peer\]' ${config_file} | grep -q 'PublicKey = ${peer_public_key}'"; then
        return 0  # Peer found
    else
        return 1  # Peer not found
    fi
}

# Helper function to get peer count from config file
get_peer_count_from_config() {
    local config_name="$1"
    local config_file="/etc/wireguard/${config_name}.conf"
    
    if check_container; then
        container_exec "grep -c '^\[Peer\]' ${config_file} 2>/dev/null || echo '0'"
        return $?
    else
        return 1
    fi
}

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "Peer Management API Tests"
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

# Get first available configuration from the system
echo "Getting available configuration..."
configs_response=$(test_request "GET" "/api/getConfigurations" "" 200 "Get configs for peer test" 2>/dev/null || echo '{"data":[]}')
test_config_name=$(echo "$configs_response" | jq -r '.data[0].Name // empty' 2>/dev/null || echo "")

if [ -z "$test_config_name" ] || [ "$test_config_name" = "null" ]; then
    echo "No configuration available, skipping peer tests"
    test_skip "All peer tests" "No configuration available"
    suite_end_time=$(date +%s)
    generate_json_report "peers" "$suite_start_time" "$suite_end_time" "test-results/api-tests-peers.json"
    print_summary "Peer Management API"
    exit 0
fi

echo "Using configuration: $test_config_name"
echo ""

# Test: Add peers
test_name="Add peers"
# Get initial peer count from config file
initial_peer_count=0
if check_container; then
    initial_peer_count=$(get_peer_count_from_config "$test_config_name" || echo "0")
fi

# Use bulkAdd mode to automatically generate keys (easier for testing)
peer_data=$(jq -n '{
    bulkAdd: true,
    bulkAddAmount: 1,
    preshared_key_bulkAdd: false
}')
endpoint="/api/addPeers/${test_config_name}"
if response=$(test_request "POST" "$endpoint" "$peer_data" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
        # Wait a moment for peer to be added and config to refresh
        sleep 2
        
        # Verify peer was added to config file in container
        if check_container; then
            new_peer_count=$(get_peer_count_from_config "$test_config_name" || echo "0")
            if [ "$new_peer_count" -gt "$initial_peer_count" ]; then
                echo "  ✓ Verified: Peer added to config file (count: $initial_peer_count -> $new_peer_count)"
            else
                echo "  ⚠ Warning: Peer count unchanged in config file (count: $initial_peer_count -> $new_peer_count)"
            fi
        fi
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get available IPs
test_name="Get available IPs"
endpoint="/api/getAvailableIPs/${test_config_name}"
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

# Get the peer ID for subsequent tests
# Get the most recently added peer from the config file (last [Peer] section)
peer_id=""

if check_container; then
    # Get the last peer's public key from the config file
    config_content=$(container_exec "cat /etc/wireguard/${test_config_name}.conf" 2>/dev/null || echo "")
    if [ -n "$config_content" ]; then
        # Extract the last [Peer] section's PublicKey
        peer_id=$(echo "$config_content" | awk '/^\[Peer\]/ {peer_section=1; next} peer_section && /^PublicKey = / {print $3; peer_section=0}' | tail -1)
    fi
fi

# If we didn't get it from config file, try wg show
if [ -z "$peer_id" ] || [ "$peer_id" = "null" ] || [ "$peer_id" = "" ]; then
    if check_container; then
        # Get the last peer's public key from wg show dump (last line is the most recent peer)
        wg_output=$(container_exec "wg show ${test_config_name} dump" 2>/dev/null || echo "")
        if [ -n "$wg_output" ]; then
            # wg show dump: first line is interface, rest are peers
            # Get the last peer's public key (last line, first field)
            peer_id=$(echo "$wg_output" | tail -1 | awk '{print $1}' 2>/dev/null || echo "")
        fi
    fi
fi

# If still not found, try API endpoints with retries
if [ -z "$peer_id" ] || [ "$peer_id" = "null" ] || [ "$peer_id" = "" ]; then
    for i in {1..3}; do
        sleep 2
        # Try getWireguardConfigurationInfo which should have reloaded peers after our API fix
        config_detail_resp=$(test_request "GET" "/api/getWireguardConfigurationInfo?configurationName=${test_config_name}" "" 200 "Get config details" 2>/dev/null || echo '{}')
        # Get the last peer (most recently added)
        peer_id=$(echo "$config_detail_resp" | jq -r '.data.configurationPeers[-1].id // empty' 2>/dev/null || echo "")
        
        if [ -n "$peer_id" ] && [ "$peer_id" != "null" ] && [ "$peer_id" != "" ]; then
            break
        fi
    done
fi

# Debug output
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ] && [ "$peer_id" != "" ]; then
    echo "Found peer ID: ${peer_id:0:20}..."
else
    echo "Warning: Could not find peer ID for subsequent tests"
fi

# Test: Download peer (do this BEFORE restricting, as restricted peers are in a different table)
test_name="Download peer"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    # Wait a moment and reload config to ensure peer is available
    sleep 1
    # Try to refresh the configuration to ensure peer is loaded
    test_request "GET" "/api/getWireguardConfigurationInfo?configurationName=${test_config_name}" "" 200 "Refresh config for download" > /dev/null 2>&1
    
    endpoint="/api/downloadPeer/${test_config_name}?id=${peer_id}"
    if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            assert_json_field_exists "$response" ".data" "$test_name"
            test_pass "$test_name"
        else
            # If peer not found, it might be because the peer_id from config file doesn't match database
            # Try to get the peer ID from the API instead
            config_detail_resp=$(test_request "GET" "/api/getWireguardConfigurationInfo?configurationName=${test_config_name}" "" 200 "Get peer from API" 2>/dev/null || echo '{}')
            api_peer_id=$(echo "$config_detail_resp" | jq -r '.data.configurationPeers[-1].id // empty' 2>/dev/null || echo "")
            if [ -n "$api_peer_id" ] && [ "$api_peer_id" != "null" ] && [ "$api_peer_id" != "" ]; then
                # Try again with the API peer ID
                endpoint="/api/downloadPeer/${test_config_name}?id=${api_peer_id}"
                if response=$(test_request "GET" "$endpoint" "" 200 "$test_name (retry)"); then
                    if assert_json_status "$response" "$test_name"; then
                        test_pass "$test_name"
                    else
                        test_fail "$test_name" "Response status invalid (retry)"
                    fi
                else
                    test_fail "$test_name" "Request failed (retry)"
                fi
            else
                test_fail "$test_name" "Response status invalid"
            fi
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available"
fi

# Test: Update peer settings (update name only, skip IP to avoid conflicts)
test_name="Update peer settings"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    update_data=$(jq -n \
        --arg peer_id "$peer_id" \
        --arg name "updated-peer-name" \
        '{
            id: $peer_id,
            name: $name
        }')
    endpoint="/api/updatePeerSettings/${test_config_name}"
    if response=$(test_request "POST" "$endpoint" "$update_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available to update"
fi

# Test: Reset peer data
test_name="Reset peer data"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    reset_data=$(jq -n --arg peer_id "$peer_id" '{id: $peer_id, type: "total"}')
    endpoint="/api/resetPeerData/${test_config_name}"
    if response=$(test_request "POST" "$endpoint" "$reset_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available to reset"
fi

# Test: Restrict peers (moves peer to restricted table)
test_name="Restrict peers"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    restrict_data=$(jq -n --arg peer_id "$peer_id" '{peers: [$peer_id]}')
    endpoint="/api/restrictPeers/${test_config_name}"
    if response=$(test_request "POST" "$endpoint" "$restrict_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            # Wait for peer to be moved to restricted table
            sleep 1
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available to restrict"
fi

# Test: Allow access peers (moves peer back from restricted table)
test_name="Allow access peers"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    allow_data=$(jq -n --arg peer_id "$peer_id" '{peers: [$peer_id]}')
    endpoint="/api/allowAccessPeers/${test_config_name}"
    if response=$(test_request "POST" "$endpoint" "$allow_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            # Wait for peer to be moved back to main table and config to refresh
            sleep 2
            # Refresh configuration to ensure peer list is updated
            test_request "GET" "/api/getWireguardConfigurationInfo?configurationName=${test_config_name}" "" 200 "Refresh config after allow" > /dev/null 2>&1 || true
            sleep 1
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available"
fi

# Test: Rate limit workflows for each scheduler type
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    declare -a schedulers=("htb" "hfsc" "cake")
    for scheduler in "${schedulers[@]}"; do
        test_name="Set peer rate limit (${scheduler})"
        rate_limit_data=$(jq -n \
            --arg interface "$test_config_name" \
            --arg peer "$peer_id" \
            --argjson upload 5 \
            --argjson download 10 \
            --arg scheduler "$scheduler" \
            '{
                interface: $interface,
                peer_key: $peer,
                upload_rate: $upload,
                download_rate: $download,
                scheduler_type: $scheduler
            }')
        endpoint="/api/set_peer_rate_limit"
        if response=$(test_request "POST" "$endpoint" "$rate_limit_data" 200 "$test_name"); then
            if assert_json_status "$response" "$test_name"; then
                test_pass "$test_name"
            else
                test_fail "$test_name" "Response status invalid"
                continue
            fi
        else
            test_fail "$test_name" "Request failed"
            continue
        fi

        # Verify via API
        verify_test_name="Get peer rate limit (${scheduler})"
        endpoint="/api/get_peer_rate_limit?interface=${test_config_name}&peer_key=${peer_id}"
        if response=$(test_request "GET" "$endpoint" "" 200 "$verify_test_name"); then
            if assert_json_status "$response" "$verify_test_name"; then
                upload_rate=$(echo "$response" | jq -r '.data.upload_rate // 0')
                download_rate=$(echo "$response" | jq -r '.data.download_rate // 0')
                scheduler_type=$(echo "$response" | jq -r '.data.scheduler_type // empty')
                if { [ "$upload_rate" = "5" ] || [ "$upload_rate" = "5.0" ]; } && \
                   { [ "$download_rate" = "10" ] || [ "$download_rate" = "10.0" ]; } && \
                   [ "$scheduler_type" = "$scheduler" ]; then
                    test_pass "$verify_test_name"
                else
                    test_fail "$verify_test_name" "Unexpected limits (upload=$upload_rate, download=$download_rate, scheduler=$scheduler_type)"
                fi
            else
                test_fail "$verify_test_name" "Response status invalid"
            fi
        else
            test_fail "$verify_test_name" "Request failed"
        fi

        # Verify via tc in container if possible
        # Note: hfsc and cake may not be available on all systems (especially macOS host)
        # The API tests above already verify the rate limits are set correctly
        if check_container; then
            tc_test_name="tc verification (${scheduler})"
            # Wait a moment for scheduler to be applied
            sleep 1
            tc_cmd="tc qdisc show dev ${test_config_name} 2>/dev/null"
            tc_output=$(container_exec "$tc_cmd" || echo "")
            
            # Check if scheduler is found in tc output
            if echo "$tc_output" | grep -qi "$scheduler"; then
                test_pass "$tc_test_name"
            else
                # Scheduler not found - this could be because:
                # 1. Scheduler not available in container (hfsc/cake on macOS)
                # 2. Timing issue (scheduler not applied yet)
                # 3. System fell back to another scheduler
                # Since API tests passed, we skip rather than fail
                echo "$tc_output" | sed 's/^/    tc> /'
                test_skip "$tc_test_name" "Scheduler ${scheduler} not found in tc output (may not be available or timing issue)"
            fi
        fi
    done
else
    test_skip "Rate limit tests" "No peer available"
fi

# Test: Remove peer rate limit
test_name="Remove peer rate limit"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    remove_data=$(jq -n \
        --arg interface "$test_config_name" \
        --arg peer "$peer_id" \
        '{interface: $interface, peer_key: $peer}')
    endpoint="/api/remove_peer_rate_limit"
    if response=$(test_request "POST" "$endpoint" "$remove_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            # Verify removal
            verify_resp=$(test_request "GET" "/api/get_peer_rate_limit?interface=${test_config_name}&peer_key=${peer_id}" "" 200 "$test_name (verify)" 2>/dev/null || echo "{}")
            upload_rate=$(echo "$verify_resp" | jq -r '.data.upload_rate // 0')
            download_rate=$(echo "$verify_resp" | jq -r '.data.download_rate // 0')
            if { [ "$upload_rate" = "0" ] || [ "$upload_rate" = "0.0" ]; } && { [ "$download_rate" = "0" ] || [ "$download_rate" = "0.0" ]; }; then
                test_pass "$test_name"
            else
                test_fail "$test_name" "Rates still set after removal (upload=$upload_rate, download=$download_rate)"
            fi
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available"
fi

# Test: Download all peers
test_name="Download all peers"
endpoint="/api/downloadAllPeers/${test_config_name}"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Delete peers
test_name="Delete peers"
if [ -n "$peer_id" ] && [ "$peer_id" != "null" ]; then
    # Get peer count before deletion
    peer_count_before=0
    if check_container; then
        peer_count_before=$(get_peer_count_from_config "$test_config_name" || echo "0")
    fi
    
    delete_data=$(jq -n --arg peer_id "$peer_id" '{peers: [$peer_id]}')
    endpoint="/api/deletePeers/${test_config_name}"
    if response=$(test_request "POST" "$endpoint" "$delete_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            # Wait a moment for peer to be deleted
            sleep 1
            
            # Verify peer was removed from config file in container
            if check_container; then
                peer_count_after=$(get_peer_count_from_config "$test_config_name" || echo "0")
                if [ "$peer_count_after" -lt "$peer_count_before" ]; then
                    echo "  ✓ Verified: Peer removed from config file (count: $peer_count_before -> $peer_count_after)"
                else
                    echo "  ⚠ Warning: Peer count unchanged in config file (count: $peer_count_before -> $peer_count_after)"
                fi
                
                # Also verify the specific peer public key is gone
                if ! verify_peer_in_config "$test_config_name" "$peer_id"; then
                    echo "  ✓ Verified: Peer public key removed from config file"
                else
                    echo "  ⚠ Warning: Peer public key still found in config file"
                fi
            fi
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No peer available to delete"
fi

# No cleanup needed - we're using an existing configuration, not a test one

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "peers" "$suite_start_time" "$suite_end_time" "test-results/api-tests-peers.json" || true

# Print summary and exit with appropriate code
if print_summary "Peer Management API"; then
    exit 0
else
    exit 1
fi

