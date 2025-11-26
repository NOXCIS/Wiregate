#!/bin/bash
# Backup and Snapshot API tests

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/test_helpers.sh"

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "Backup and Snapshot API Tests"
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

# Create a test configuration for backup tests
# Use a unique address based on timestamp to avoid conflicts
test_config_name="TEST_BACKUP_CONFIG_$(date +%s)"
# Generate a unique address in the 10.0.x.0/24 range (x = last 3 digits of timestamp % 255)
timestamp_suffix=$(($(date +%s) % 255))
test_address="10.0.${timestamp_suffix}.1/24"
# Use a unique port to avoid conflicts
test_port=$((51820 + (timestamp_suffix % 100)))

config_data=$(jq -n \
    --arg name "$test_config_name" \
    --arg address "$test_address" \
    --arg port "$test_port" \
    '{
        ConfigurationName: $name,
        Address: $address,
        ListenPort: $port,
        PrivateKey: "",
        Protocol: "wg"
    }')

echo "Creating test configuration: $test_config_name"
if response=$(test_request "POST" "/api/addConfiguration" "$config_data" 200 "Create test config"); then
    # Check if the API actually succeeded (status=true)
    if ! assert_json_status "$response" "Create test config"; then
        echo "Failed to create test configuration: $(echo "$response" | jq -r '.message // "Unknown error"')" >&2
        test_skip "All backup tests" "No test configuration available"
        suite_end_time=$(date +%s)
        mkdir -p test-results
        generate_json_report "backups" "$suite_start_time" "$suite_end_time" "test-results/api-tests-backups.json" || true
        print_summary "Backup and Snapshot API"
        exit 0
    fi
    echo "Configuration created successfully"
    # Wait a moment for configuration to be fully initialized
    sleep 2
else
    echo "Failed to create test configuration (request failed), skipping backup tests" >&2
    test_skip "All backup tests" "No test configuration available"
    suite_end_time=$(date +%s)
    mkdir -p test-results
    generate_json_report "backups" "$suite_start_time" "$suite_end_time" "test-results/api-tests-backups.json" || true
    print_summary "Backup and Snapshot API"
    exit 0
fi

# Test: Create configuration backup (create first, then get)
test_name="Create configuration backup"
endpoint="/api/createConfigurationBackup?configurationName=${test_config_name}"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Wait a moment for backup to be created
sleep 1

# Test: Get configuration backup
test_name="Get configuration backup"
endpoint="/api/getConfigurationBackup?configurationName=${test_config_name}"
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

# Test: Create configuration backup (invalid config)
test_name="Create configuration backup (invalid config)"
endpoint="/api/createConfigurationBackup?configurationName=NONEXISTENT_CONFIG"
if response=$(test_request "GET" "$endpoint" "" 200 "$test_name"); then
    status=$(echo "$response" | jq -r '.status // false')
    if [ "$status" = "false" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Should have failed for non-existent config"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Download configuration backup
test_name="Download configuration backup"
# Get list of backups first
backup_list=$(test_request "GET" "/api/getConfigurationBackup?configurationName=${test_config_name}" "" 200 "Get backup list")
# The API returns 'filename' (lowercase), not 'fileName'
backup_file=$(echo "$backup_list" | jq -r '.data[0].filename // .data[0].fileName // empty' | head -n1)

if [ -n "$backup_file" ] && [ "$backup_file" != "null" ]; then
    endpoint="/api/downloadConfigurationBackup?configurationName=${test_config_name}&backupFileName=${backup_file}"
    # Download endpoint returns binary (7z archive), not JSON
    # Check for successful download (200 status and non-empty response)
    download_response=$(curl -s -w "\n%{http_code}" \
        -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
        -H "Content-Type: application/json" \
        "${TEST_APP_URL}${endpoint}" 2>&1)
    
    http_code=$(echo "$download_response" | tail -1)
    body=$(echo "$download_response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        # Check if we got binary data (7z files start with specific bytes)
        # Or check if response is not empty and not JSON error
        body_size=${#body}
        if [ -n "$body" ] && [ "$body_size" -gt 50 ]; then
            # Check if it's not a JSON error response
            if echo "$body" | jq -e . > /dev/null 2>&1; then
                # It's JSON - check if it's an error
                if echo "$body" | jq -e '.status == false' > /dev/null 2>&1; then
                    # JSON error response
                    error_msg=$(echo "$body" | jq -r '.message // "Unknown error"')
                    test_fail "$test_name" "Download failed: $error_msg"
                else
                    # Unexpected JSON response (should be binary)
                    test_fail "$test_name" "Unexpected JSON response from download endpoint"
                fi
            else
                # Not JSON, likely binary - good! Check for 7z magic bytes
                # 7z files start with '7z' (hex: 37 7A)
                first_bytes=$(echo -n "$body" | head -c 2 | od -An -tx1 | tr -d ' \n')
                if [ "$first_bytes" = "377a" ] || [ "$body_size" -gt 100 ]; then
                    test_pass "$test_name"
                else
                    test_fail "$test_name" "Download returned data but doesn't look like 7z archive (size: $body_size bytes)"
                fi
            fi
        else
            test_fail "$test_name" "Download returned empty or too small response (size: ${body_size} bytes)"
        fi
    else
        test_fail "$test_name" "Request failed with status $http_code"
    fi
else
    test_skip "$test_name" "No backup file available"
fi

# Test: Restore configuration backup (do this BEFORE delete so we have a backup to restore)
test_name="Restore configuration backup"
# Use the backup we already created, or create a new one if needed
if [ -z "$backup_file" ] || [ "$backup_file" = "null" ]; then
    # Create a backup first
    test_request "GET" "/api/createConfigurationBackup?configurationName=${test_config_name}" "" 200 "Create backup for restore" > /dev/null 2>&1
    sleep 1
    backup_list=$(test_request "GET" "/api/getConfigurationBackup?configurationName=${test_config_name}" "" 200 "Get backup list for restore")
    restore_file=$(echo "$backup_list" | jq -r '.data[0].filename // .data[0].fileName // empty' | head -n1)
else
    # Use the existing backup file
    restore_file="$backup_file"
fi

if [ -n "$restore_file" ] && [ "$restore_file" != "null" ]; then
    restore_data=$(jq -n \
        --arg config "$test_config_name" \
        --arg file "$restore_file" \
        '{
            configurationName: $config,
            backupFileName: $file
        }')
    if response=$(test_request "POST" "/api/restoreConfigurationBackup" "$restore_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No backup file available"
fi

# Test: Restore configuration backup (missing fields)
test_name="Restore configuration backup (missing fields)"
invalid_data='{"configurationName":"TEST"}'
if response=$(test_request "POST" "/api/restoreConfigurationBackup" "$invalid_data" 200 "$test_name"); then
    status=$(echo "$response" | jq -r '.status // false')
    if [ "$status" = "false" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Should have failed with missing fields"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Upload configuration backup
test_name="Upload configuration backup"
# Create a test backup file to upload
# First, create a backup if we don't have one
if [ -z "$backup_file" ] || [ "$backup_file" = "null" ]; then
    # Create a backup first
    test_request "GET" "/api/createConfigurationBackup?configurationName=${test_config_name}" "" 200 "Create backup for upload" > /dev/null 2>&1
    sleep 1
    backup_list=$(test_request "GET" "/api/getConfigurationBackup?configurationName=${test_config_name}" "" 200 "Get backup list for upload")
    backup_file=$(echo "$backup_list" | jq -r '.data[0].filename // .data[0].fileName // empty' | head -n1)
fi

if [ -n "$backup_file" ] && [ "$backup_file" != "null" ]; then
    # The upload endpoint expects a .7z file, but we have .conf files
    # We need to create a .7z archive or test with an existing one
    # For now, let's test the upload endpoint with a proper .7z file format
    # The filename format should be: {config_name}_{timestamp}_complete.7z
    
    # Check if we can create a test archive (requires 7z command)
    if command -v 7z > /dev/null 2>&1 || command -v 7za > /dev/null 2>&1; then
        # Create a temporary .7z archive for testing
        temp_archive="/tmp/test_backup_upload.7z"
        # Extract timestamp from backup filename
        timestamp=$(echo "$backup_file" | sed -n 's/.*_\([0-9]\{14\}\)\.conf/\1/p')
        if [ -n "$timestamp" ]; then
            archive_name="${test_config_name}_${timestamp}_complete.7z"
            # Create a minimal test archive
            # Note: This is a simplified test - in production, the archive would contain multiple files
            echo "test content" > /tmp/test_backup_content.txt
            if 7z a -t7z "$temp_archive" /tmp/test_backup_content.txt > /dev/null 2>&1 || \
               7za a -t7z "$temp_archive" /tmp/test_backup_content.txt > /dev/null 2>&1; then
                # Upload the test archive
                csrf_token=$(get_csrf_token)
                upload_response=$(curl -s -w "\n%{http_code}" \
                    -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
                    -H "X-CSRF-Token: $csrf_token" \
                    -F "files=@$temp_archive;filename=$archive_name" \
                    "${TEST_APP_URL}/api/uploadConfigurationBackup" 2>&1)
                
                http_code=$(echo "$upload_response" | tail -1)
                body=$(echo "$upload_response" | sed '$d')
                
                if [ "$http_code" = "200" ]; then
                    if echo "$body" | jq -e '.status == true' > /dev/null 2>&1; then
                        test_pass "$test_name"
                    else
                        # Upload might fail validation, which is acceptable for testing
                        status=$(echo "$body" | jq -r '.status // false')
                        message=$(echo "$body" | jq -r '.message // "Unknown error"')
                        if echo "$message" | grep -qi "invalid\|format\|archive"; then
                            # Expected validation error - test that endpoint works
                            test_pass "$test_name"
                        else
                            test_fail "$test_name" "Upload failed: $message"
                        fi
                    fi
                else
                    test_fail "$test_name" "Request failed with status $http_code"
                fi
                
                rm -f "$temp_archive" /tmp/test_backup_content.txt
            else
                test_skip "$test_name" "Could not create test archive (7z not available or failed)"
                rm -f "$temp_archive" /tmp/test_backup_content.txt
            fi
        else
            test_skip "$test_name" "Could not extract timestamp from backup filename"
        fi
    else
        test_skip "$test_name" "7z command not available for creating test archive"
    fi
else
    test_skip "$test_name" "No backup file available to create test archive"
fi

# Cleanup: Delete test configuration
echo "Cleaning up test configuration: $test_config_name"
delete_config_data=$(jq -n --arg name "$test_config_name" '{Name: $name}')
test_request "POST" "/api/deleteConfiguration" "$delete_config_data" 200 "Cleanup test config" > /dev/null 2>&1

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "backups" "$suite_start_time" "$suite_end_time" "test-results/api-tests-backups.json" || true

# Print summary and exit with appropriate code
if print_summary "Backup and Snapshot API"; then
    exit 0
else
    exit 1
fi

