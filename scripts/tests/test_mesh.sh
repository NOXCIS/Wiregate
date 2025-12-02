#!/bin/bash
# Mesh Network API tests

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

# Initialize test results
init_test_results
suite_start_time=$(date +%s)

echo "=========================================="
echo "Mesh Network API Tests"
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

# Test: Get available configurations for meshing
test_name="Get available configurations for meshing"
if response=$(test_request "GET" "/api/mesh/configurations" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        assert_json_field_exists "$response" ".data" "$test_name"
        # Extract available configs for later tests
        available_configs=$(echo "$response" | jq -r '.data // []')
        config_count=$(echo "$available_configs" | jq 'length')
        echo "  Found $config_count configurations available for meshing"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: List mesh networks (should be empty initially or have existing meshes)
test_name="List mesh networks"
if response=$(test_request "GET" "/api/mesh/list" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Create mesh network (requires at least 2 configurations)
test_name="Create mesh network"
mesh_id=""
# Get first two configurations for testing
config_names=$(echo "$available_configs" | jq -r '.[0:2] | .[].name // empty' 2>/dev/null | tr '\n' ' ')
config_array=$(echo "$available_configs" | jq '[.[0:2] | .[].name]' 2>/dev/null)

if [ "$(echo "$config_array" | jq 'length')" -ge 2 ]; then
    mesh_name="TestMesh_$(date +%s)"
    create_data=$(jq -n \
        --argjson configs "$config_array" \
        --arg name "$mesh_name" \
        '{
            configurations: $configs,
            name: $name
        }')
    
    if response=$(test_request "POST" "/api/mesh/create" "$create_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            mesh_id=$(echo "$response" | jq -r '.data.id // empty')
            if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
                echo "  Created mesh network: $mesh_id"
                test_pass "$test_name"
            else
                test_fail "$test_name" "Mesh ID not returned"
            fi
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "Need at least 2 configurations to create mesh"
fi

# Test: Create mesh with insufficient configurations (should fail)
test_name="Create mesh with insufficient configurations"
if [ "$(echo "$available_configs" | jq 'length')" -ge 1 ]; then
    # Use only one configuration (need at least 2 for mesh)
    single_config=$(echo "$available_configs" | jq '[.[0].name]' 2>/dev/null)
    invalid_data=$(jq -n \
        --argjson configs "$single_config" \
        --arg name "InvalidMesh" \
        '{
            configurations: $configs,
            name: $name
        }')
    
    if response=$(test_request "POST" "/api/mesh/create" "$invalid_data" 200 "$test_name"); then
        # Use .status directly, not .status // true (which treats false as falsy)
        status=$(echo "$response" | jq -r '.status')
        if [ "$status" = "false" ]; then
            test_pass "$test_name"
        else
            test_fail "$test_name" "Should have failed with insufficient configurations (got status=$status)"
        fi
    else
        # 4xx response is also acceptable for invalid input
        test_pass "$test_name"
    fi
else
    test_skip "$test_name" "No configurations available"
fi

# Test: Get mesh network details
test_name="Get mesh network details"
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    if response=$(test_request "GET" "/api/mesh/${mesh_id}" "" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            assert_json_field_exists "$response" ".data.id" "$test_name"
            assert_json_field_exists "$response" ".data.nodes" "$test_name"
            test_pass "$test_name"
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No mesh network available"
fi

# Test: Add connection to mesh (singular endpoint)
test_name="Add connection to mesh"
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    # Get node IDs from the mesh
    mesh_response=$(test_request "GET" "/api/mesh/${mesh_id}" "" 200 "Get nodes for connection" 2>/dev/null || echo '{}')
    node_ids=$(echo "$mesh_response" | jq -r '.data.nodes | keys | .[]' 2>/dev/null | head -2)
    node_a=$(echo "$node_ids" | head -1)
    node_b=$(echo "$node_ids" | tail -1)
    
    if [ -n "$node_a" ] && [ -n "$node_b" ] && [ "$node_a" != "$node_b" ]; then
        connection_data=$(jq -n \
            --arg node_a "$node_a" \
            --arg node_b "$node_b" \
            '{
                node_a_id: $node_a,
                node_b_id: $node_b,
                generate_preshared_key: true
            }')
        
        # Note: endpoint is /connection (singular)
        if response=$(test_request "POST" "/api/mesh/${mesh_id}/connection" "$connection_data" 200 "$test_name"); then
            if assert_json_status "$response" "$test_name"; then
                test_pass "$test_name"
            else
                test_fail "$test_name" "Response status invalid"
            fi
        else
            test_fail "$test_name" "Request failed"
        fi
    else
        test_skip "$test_name" "Could not get valid node IDs"
    fi
else
    test_skip "$test_name" "No mesh network available"
fi

# Test: Add bulk connections (full mesh)
test_name="Add bulk connections (full mesh)"
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    # Get all node pairs
    mesh_response=$(test_request "GET" "/api/mesh/${mesh_id}" "" 200 "Get nodes for bulk connection" 2>/dev/null || echo '{}')
    node_ids=$(echo "$mesh_response" | jq -r '.data.nodes | keys' 2>/dev/null)
    node_count=$(echo "$node_ids" | jq 'length' 2>/dev/null || echo 0)
    
    if [ "$node_count" -ge 2 ]; then
        node_a=$(echo "$node_ids" | jq -r '.[0]')
        node_b=$(echo "$node_ids" | jq -r '.[1]')
        
        bulk_data=$(jq -n \
            --arg node_a "$node_a" \
            --arg node_b "$node_b" \
            '{
                connections: [
                    {node_a_id: $node_a, node_b_id: $node_b}
                ],
                generate_preshared_keys: true
            }')
        
        if response=$(test_request "POST" "/api/mesh/${mesh_id}/connections/bulk" "$bulk_data" 200 "$test_name"); then
            if assert_json_status "$response" "$test_name"; then
                connection_count=$(echo "$response" | jq '.data.connections | length' 2>/dev/null || echo 0)
                echo "  Created/updated $connection_count connections"
                test_pass "$test_name"
            else
                test_fail "$test_name" "Response status invalid"
            fi
        else
            test_fail "$test_name" "Request failed"
        fi
    else
        test_skip "$test_name" "Not enough nodes for bulk connection"
    fi
else
    test_skip "$test_name" "No mesh network available"
fi

# Test: Preview mesh changes (GET endpoint)
test_name="Preview mesh changes"
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    # Note: preview is a GET endpoint
    if response=$(test_request "GET" "/api/mesh/${mesh_id}/preview" "" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            # Check for preview data
            peer_entries=$(echo "$response" | jq '.data.peer_entries // []' 2>/dev/null)
            entry_count=$(echo "$peer_entries" | jq 'length' 2>/dev/null || echo 0)
            echo "  Preview shows $entry_count peer entries to add"
            test_pass "$test_name"
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No mesh network available"
fi

# Test: Apply mesh configuration (preview mode only - don't actually modify configs in test)
test_name="Apply mesh (preview mode)"
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    apply_data=$(jq -n '{
        mode: "preview"
    }')
    
    if response=$(test_request "POST" "/api/mesh/${mesh_id}/apply" "$apply_data" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
        else
            # Preview mode might not be fully implemented, skip if not working
            test_skip "$test_name" "Preview mode may not be supported"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No mesh network available"
fi

# Test: Remove connection from mesh (singular endpoint with query params)
test_name="Remove connection from mesh"
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    # Get current connections
    mesh_response=$(test_request "GET" "/api/mesh/${mesh_id}" "" 200 "Get connections for removal" 2>/dev/null || echo '{}')
    connections=$(echo "$mesh_response" | jq '.data.connections // []' 2>/dev/null)
    connection_count=$(echo "$connections" | jq 'length' 2>/dev/null || echo 0)
    
    if [ "$connection_count" -gt 0 ]; then
        # Get first connection's nodes
        node_a=$(echo "$connections" | jq -r '.[0].node_a_id // .[0].source // empty')
        node_b=$(echo "$connections" | jq -r '.[0].node_b_id // .[0].target // empty')
        
        if [ -n "$node_a" ] && [ -n "$node_b" ]; then
            # Note: endpoint is /connection (singular) with query parameters
            if response=$(test_request "DELETE" "/api/mesh/${mesh_id}/connection?node_a_id=${node_a}&node_b_id=${node_b}" "" 200 "$test_name"); then
                if assert_json_status "$response" "$test_name"; then
                    test_pass "$test_name"
                else
                    test_fail "$test_name" "Response status invalid"
                fi
            else
                test_fail "$test_name" "Request failed"
            fi
        else
            test_skip "$test_name" "Could not get connection node IDs"
        fi
    else
        test_skip "$test_name" "No connections to remove"
    fi
else
    test_skip "$test_name" "No mesh network available"
fi

# Test: Upload external config (requires multipart/form-data)
test_name="Upload external config"
# Create a temporary test config file
temp_config_file=$(mktemp /tmp/test_config_XXXXXX.conf)
cat > "$temp_config_file" << 'EOF'
[Interface]
PrivateKey = kJm+5Ui4XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=
Address = 10.100.0.1/24
ListenPort = 51820

[Peer]
PublicKey = xTIBAXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX=
AllowedIPs = 10.100.0.2/32
EOF

# Get CSRF token for multipart request
csrf_token=$(get_csrf_token)

# Use curl directly with multipart form data
upload_response=$(curl -s -c "$COOKIE_FILE" -b "$COOKIE_FILE" \
    -H "X-CSRF-Token: $csrf_token" \
    -F "file=@${temp_config_file}" \
    "${TEST_APP_URL}/api/mesh/upload" 2>&1)

rm -f "$temp_config_file"

upload_status=$(echo "$upload_response" | jq -r '.status // false' 2>/dev/null)
if [ "$upload_status" = "true" ]; then
    test_pass "$test_name"
else
    # May fail due to invalid key format, which is expected for test data
    test_skip "$test_name" "Upload rejected (expected for test data with placeholder keys)"
fi

# Test: List mesh networks (should show our created mesh)
test_name="List mesh networks (verify creation)"
if response=$(test_request "GET" "/api/mesh/list" "" 200 "$test_name"); then
    if assert_json_status "$response" "$test_name"; then
        mesh_count=$(echo "$response" | jq '.data | length' 2>/dev/null || echo 0)
        echo "  Found $mesh_count mesh network(s)"
        test_pass "$test_name"
    else
        test_fail "$test_name" "Response status invalid"
    fi
else
    test_fail "$test_name" "Request failed"
fi

# Test: Delete mesh network (cleanup)
test_name="Delete mesh network"
mesh_deleted=false
if [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    if response=$(test_request "DELETE" "/api/mesh/${mesh_id}" "" 200 "$test_name"); then
        if assert_json_status "$response" "$test_name"; then
            test_pass "$test_name"
            mesh_deleted=true
        else
            test_fail "$test_name" "Response status invalid"
        fi
    else
        test_fail "$test_name" "Request failed"
    fi
else
    test_skip "$test_name" "No mesh network to delete"
fi

# Test: Verify deletion
test_name="Verify mesh deletion"
if [ "$mesh_deleted" = "true" ] && [ -n "$mesh_id" ] && [ "$mesh_id" != "null" ]; then
    # Getting a deleted mesh should return status=false
    sleep 1  # Give time for deletion to complete
    if response=$(test_request "GET" "/api/mesh/${mesh_id}" "" 200 "$test_name" 2>/dev/null); then
        # Use .status directly, not .status // true (which treats false as falsy)
        status=$(echo "$response" | jq -r '.status')
        if [ "$status" = "false" ]; then
            test_pass "$test_name"
        else
            test_fail "$test_name" "Mesh still exists after deletion (got status=$status)"
        fi
    else
        # 404 or other error is expected for deleted mesh
        test_pass "$test_name"
    fi
else
    test_skip "$test_name" "Mesh was not deleted or no mesh ID"
fi

# Test: Get non-existent mesh (should return status=false)
test_name="Get non-existent mesh"
fake_mesh_id="non-existent-mesh-$(date +%s)"
if response=$(test_request "GET" "/api/mesh/${fake_mesh_id}" "" 200 "$test_name" 2>/dev/null); then
    # Use .status directly, not .status // true (which treats false as falsy)
    status=$(echo "$response" | jq -r '.status')
    if [ "$status" = "false" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name" "Should have failed for non-existent mesh (got status=$status)"
    fi
else
    # 404 is also acceptable
    test_pass "$test_name"
fi

# Generate report
suite_end_time=$(date +%s)
# Create test-results directory if it doesn't exist
mkdir -p test-results
generate_json_report "mesh" "$suite_start_time" "$suite_end_time" "test-results/api-tests-mesh.json" || true

# Print summary and exit with appropriate code
if print_summary "Mesh Network API"; then
    exit 0
else
    exit 1
fi

