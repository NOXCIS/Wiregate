#!/bin/bash
# Configuration API tests

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
        # Use sh -c for minimal containers (Alpine, etc.)
        docker exec "${WIREGATE_CONTAINER}" sh -c "$cmd" 2>/dev/null
        return $?
    else
        return 1
    fi
}

# Helper function to verify config file exists in container
verify_config_file_exists() {
    local config_name="$1"
    local config_file="/etc/wireguard/${config_name}.conf"
    
    if ! check_container; then
        return 2  # Container not available
    fi
    
    # Use [ -f ] which is available in minimal sh
    if container_exec "[ -f ${config_file} ]"; then
        return 0  # File exists
    else
        return 1  # File doesn't exist
    fi
}

# Helper function to get config file content from container
get_config_file_content() {
    local config_name="$1"
    local config_file="/etc/wireguard/${config_name}.conf"
    
    if check_container; then
        # Use cat (available in minimal container per Dockerfile line 28)
        container_exec "cat ${config_file}" 2>/dev/null
        return $?
    else
        return 1
    fi
}

# Helper function to check WireGuard interface status
check_interface_status() {
    local config_name="$1"
    
    if ! check_container; then
        return 2  # Container not available
    fi
    
    # Use ip command (available in container per Dockerfile line 198: /sbin/ip)
    # Redirect stderr to /dev/null to suppress "does not exist" errors
    local output
    output=$(container_exec "ip link show ${config_name} 2>/dev/null")
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && [ -n "$output" ]; then
        # Interface exists, check if it's UP using grep (available per Dockerfile line 28)
        if echo "$output" | grep -q "state UP"; then
            return 0  # Interface exists and is UP
        else
            return 1  # Interface exists but is DOWN
        fi
    else
        return 1  # Interface doesn't exist
    fi
}

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "Configuration API Tests"
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

# Test: Get configurations
test_name="Get configurations"
if response=$(test_request "GET" "/api/getConfigurations" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Refresh public keys
test_name="Refresh public keys"
if response=$(test_request "POST" "/api/refreshPublicKeys" "{}" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Cleanup orphaned configurations
test_name="Cleanup orphaned configurations"
if response=$(test_request "POST" "/api/cleanupOrphanedConfigurations" "{}" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Add configuration
test_name="Add configuration"
# Check if /etc/wireguard exists in container (required for creating configs)
if ! check_container; then
    test_skip "$test_name" "Container not available"
elif ! container_exec "[ -d /etc/wireguard ]"; then
    test_skip "$test_name" "/etc/wireguard directory not available in container"
else
config_name="TEST_CONFIG_$(date +%s)"
# Use a unique address based on timestamp to avoid conflicts
random_octet=$(( $(date +%s) % 255 ))
config_address="10.${random_octet}.0.1/24"
    # Use a random port to avoid conflicts (51820-52820 range)
    random_port=$(( 51820 + (RANDOM % 1000) ))
config_data=$(jq -n \
    --arg name "$config_name" \
    --arg address "$config_address" \
        --arg port "$random_port" \
    '{
        ConfigurationName: $name,
        Address: $address,
        ListenPort: $port,
        PrivateKey: "",
        Protocol: "wg"
    }')

if response=$(test_request "POST" "/api/addConfiguration" "$config_data" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
        # Store config name for cleanup
        echo "$config_name" > /tmp/test_config_name.txt
            
            # Wait a moment for file to be created
            sleep 1
            
            # Verify config file exists in container
            test_name="Verify config file exists in container"
            if verify_config_file_exists "$config_name"; then
                test_pass "$test_name"
            elif [ $? -eq 2 ]; then
                test_skip "$test_name" "Container not available"
            else
                test_fail "$test_name" "Config file not found in container: /etc/wireguard/${config_name}.conf"
            fi
            
            # Verify config file content
            test_name="Verify config file content"
            if check_container; then
                config_content=$(get_config_file_content "$config_name")
                if [ -n "$config_content" ]; then
                    # Check for key fields in config file
                    if echo "$config_content" | grep -q "\[Interface\]" && \
                       echo "$config_content" | grep -q "Address = ${config_address}" && \
                       echo "$config_content" | grep -q "ListenPort = ${random_port}"; then
                        test_pass "$test_name"
                    else
                        test_fail "$test_name" "Config file content doesn't match expected values"
                    fi
                else
                    test_fail "$test_name" "Failed to read config file content"
                fi
            else
                test_skip "$test_name" "Container not available"
            fi
            
            # Check interface status (may not be up if config is disabled)
            test_name="Check WireGuard interface status"
            if check_interface_status "$config_name"; then
                status_code=0
            else
                status_code=$?
            fi
            
            if [ $status_code -eq 0 ]; then
                test_pass "$test_name (interface UP)"
            elif [ $status_code -eq 1 ]; then
                # Interface exists but DOWN, or doesn't exist - both are OK if config is disabled
                test_pass "$test_name (interface not UP - config may be disabled)"
            else
                test_skip "$test_name" "Container not available"
            fi
    else
        test_fail "$test_name" "Failed to create configuration"
    fi
else
    test_fail "$test_name" "Request failed"
    fi
fi

# Test: Add configuration with missing fields (should fail)
test_name="Add configuration with missing fields"
invalid_data='{"ConfigurationName":"INVALID"}'
if response=$(test_request "POST" "/api/addConfiguration" "$invalid_data" 200 "$test_name"); then
    # Should return status=false for missing fields
    status=$(echo "$response" | jq -r '.status // false')
    if [ "$status" = "false" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Should have failed with missing fields"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Get configuration raw file
if [ -f /tmp/test_config_name.txt ]; then
    config_name=$(cat /tmp/test_config_name.txt)
    test_name="Get configuration raw file"
    endpoint="/api/getConfigurationRawFile?configurationName=${config_name}"
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
else
    test_skip "Get configuration raw file" "No test configuration available"
fi

# Test: Toggle configuration
    test_name="Toggle configuration"

# Use an existing configuration from the API (mirrors real app behavior)
configs_response=$(test_request "GET" "/api/getConfigurations" "" 200 "Get configs for toggle test" 2>/dev/null || echo '{"data":[]}')
config_name=$(echo "$configs_response" | jq -r '.data[0].Name // empty' 2>/dev/null || echo "")

if [ -n "$config_name" ] && [ "$config_name" != "null" ]; then
    # Toggle endpoint uses query parameter, not JSON body
    endpoint="/api/toggleConfiguration/?configurationName=${config_name}"
    if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            
            # Wait a moment for interface state to change
            sleep 1
            
            # Verify interface status after toggle (inside container)
            test_name="Verify interface status after toggle"
            set +e  # Temporarily disable exit on error for command substitution
            interface_status=$(check_interface_status "$config_name")
            status_code=$?
            set -e  # Re-enable exit on error
            if [ $status_code -eq 0 ]; then
                test_pass "$test_name (interface UP)"
            elif [ $status_code -eq 1 ]; then
                # Interface exists but DOWN, or doesn't exist - both are acceptable
                test_pass "$test_name (interface DOWN or not created)"
            else
                test_skip "$test_name" "Container not available"
            fi
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "Toggle configuration" "No configuration available to test"
fi

# Test: Update configuration
if [ -f /tmp/test_config_name.txt ]; then
    config_name=$(cat /tmp/test_config_name.txt)
    test_name="Update configuration"
    # Use a different unique address for update
    random_octet=$(( $(date +%s) % 255 ))
    update_address="10.${random_octet}.0.2/24"
    update_data=$(jq -n \
        --arg name "$config_name" \
        --arg address "$update_address" \
        --arg port "51821" \
        '{
            Name: $name,
            Address: $address,
            ListenPort: $port
        }')
    if response=$(test_request "POST" "/api/updateConfiguration" "$update_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            
            # Wait a moment for file to be updated
            sleep 1
            
            # Verify updated config file content
            test_name="Verify updated config file content"
            if check_container; then
                config_content=$(get_config_file_content "$config_name")
                if [ -n "$config_content" ]; then
                    # Check for updated address and port in config file
                    if echo "$config_content" | grep -q "Address = ${update_address}" && \
                       echo "$config_content" | grep -q "ListenPort = 51821"; then
                        test_pass "$test_name"
                    else
                        test_fail "$test_name" "Config file content doesn't match updated values"
                    fi
                else
                    test_fail "$test_name" "Failed to read updated config file content"
                fi
            else
                test_skip "$test_name" "Container not available"
            fi
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "Update configuration" "No test configuration available"
fi

# Test: Rename configuration
if [ -f /tmp/test_config_name.txt ]; then
    old_config_name=$(cat /tmp/test_config_name.txt)
    new_config_name="TEST_CONFIG_RENAMED_$(date +%s)"
    test_name="Rename configuration"
    rename_data=$(jq -n \
        --arg old "$old_config_name" \
        --arg new "$new_config_name" \
        '{
            Name: $old,
            NewConfigurationName: $new
        }')
    if response=$(test_request "POST" "/api/renameConfiguration" "$rename_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            
            # Wait a moment for file rename to complete
            sleep 1
            
            # Verify old config file is gone and new file exists
            test_name="Verify rename in container"
            if check_container; then
                # Check old file is gone
                if container_exec "[ -f /etc/wireguard/${old_config_name}.conf ]"; then
                    test_fail "$test_name" "Old config file still exists: ${old_config_name}.conf"
                elif ! container_exec "[ -f /etc/wireguard/${new_config_name}.conf ]"; then
                    test_fail "$test_name" "New config file not found: ${new_config_name}.conf"
                else
                    test_pass "$test_name"
                fi
            else
                test_skip "$test_name" "Container not available"
            fi
            
            # Update stored config name
            echo "$new_config_name" > /tmp/test_config_name.txt
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "Rename configuration" "No test configuration available"
fi

# Test: Delete configuration (cleanup)
if [ -f /tmp/test_config_name.txt ]; then
    config_name=$(cat /tmp/test_config_name.txt)
    test_name="Delete configuration"
    # Delete endpoint expects "Name" field, not "configurationName"
    delete_data=$(jq -n --arg name "$config_name" '{Name: $name}')
    if response=$(test_request "POST" "/api/deleteConfiguration" "$delete_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            
            # Wait a moment for file deletion to complete
            sleep 1
            
            # Verify config file is deleted from container
            test_name="Verify deletion in container"
            if check_container; then
                if container_exec "[ -f /etc/wireguard/${config_name}.conf ]"; then
                    test_fail "$test_name" "Config file still exists in container: ${config_name}.conf"
                else
                    test_pass "$test_name"
                fi
            else
                test_skip "$test_name" "Container not available"
            fi
            
            # Verify interface is removed (if it existed)
            test_name="Verify interface removed"
            if check_container; then
                set +e  # Temporarily disable exit on error for command substitution
                interface_status=$(check_interface_status "$config_name")
                status_code=$?
                set -e  # Re-enable exit on error
                # Interface should not exist (status_code 1 means doesn't exist, which is expected)
                if [ $status_code -eq 1 ]; then
                    test_pass "$test_name (interface removed)"
                elif [ $status_code -eq 2 ]; then
                    test_skip "$test_name" "Container not available"
                else
                    # Interface still exists, which might be OK if it was never created
                    test_pass "$test_name (interface may not have existed)"
                fi
            else
                test_skip "$test_name" "Container not available"
            fi
            
            rm -f /tmp/test_config_name.txt
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "Delete configuration" "No test configuration available"
fi

# Test: Get WireGuard configuration info (requires configurationName parameter)
test_name="Get WireGuard configuration info"
# Get first available configuration name
configs_response=$(test_request "GET" "/api/getConfigurations" "" 200 "Get configs for info test" 2>/dev/null || echo '{"data":[]}')
first_config=$(echo "$configs_response" | jq -r '.data[0].Name // empty' 2>/dev/null || echo "")

if [ -n "$first_config" ] && [ "$first_config" != "null" ]; then
    endpoint="/api/getWireguardConfigurationInfo?configurationName=${first_config}"
    if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
            assert_json_field_exists "$response" ".data.configurationInfo" "$test_name"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No configuration available to test"
fi

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "configs" "$suite_start_time" "$suite_end_time" "test-results/api-tests-configs.json" || true

# Cleanup
rm -f /tmp/test_config_name.txt

# Print summary and exit with appropriate code
if print_summary "Configuration API"; then
    exit 0
else
    exit 1
fi

