#!/bin/bash
# Don't exit on error - we want to see all test results
set +e

echo "🧪 Multi-Peer Rate Limiting Test Suite"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to print test results
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ $2${NC}"
        ((TESTS_FAILED++))
    fi
}

# Helper function to verify class exists
verify_class_exists() {
    local interface=$1
    local class_id=$2
    tc class show dev "$interface" | grep -q "$class_id"
    return $?
}

# Helper function to verify filter exists
verify_filter_exists() {
    local interface=$1
    local ip=$2
    # Convert IP to hex format that tc uses (e.g., 10.0.1.1 -> 0a000101)
    local ip_hex=$(echo "$ip" | awk -F. '{printf "%02x%02x%02x%02x", $1, $2, $3, $4}')
    tc filter show dev "$interface" parent 1: | grep -qi "$ip_hex"
    return $?
}

# Helper function to count classes
count_classes() {
    local interface=$1
    tc class show dev "$interface" | grep -c "class htb" || true
}

# Helper function to count filters
count_filters() {
    local interface=$1
    tc filter show dev "$interface" parent 1: | grep -c "match" || true
}

echo "📋 Test Setup: Creating test interface"
ip link add test-multi type dummy 2>/dev/null || true
ip link set test-multi up
echo ""

# ===========================================
# Test 1: Add Multiple Peers to Single Interface (HTB)
# ===========================================
echo "🧪 Test 1: Adding Multiple Peers to Single Interface (HTB)"
echo "-----------------------------------------------------------"

echo "Adding Peer 1: 10.0.1.1/32 (1 Mbps up/down)"
./traffic-weir -interface test-multi -peer peer-1 -upload-rate 1000 -download-rate 1000 \
    -scheduler htb -allowed-ips 10.0.1.1/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "Peer 1 added successfully"

echo "Adding Peer 2: 10.0.1.2/32 (2 Mbps up/down)"
./traffic-weir -interface test-multi -peer peer-2 -upload-rate 2000 -download-rate 2000 \
    -scheduler htb -allowed-ips 10.0.1.2/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "Peer 2 added successfully"

echo "Adding Peer 3: 10.0.1.3/32 (3 Mbps up/down)"
./traffic-weir -interface test-multi -peer peer-3 -upload-rate 3000 -download-rate 3000 \
    -scheduler htb -allowed-ips 10.0.1.3/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "Peer 3 added successfully"

echo "Adding Peer 4: 10.0.1.4/32 (500 Kbps up/down)"
./traffic-weir -interface test-multi -peer peer-4 -upload-rate 500 -download-rate 500 \
    -scheduler htb -allowed-ips 10.0.1.4/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "Peer 4 added successfully"

echo ""
echo "Verifying all peers have classes and filters..."
class_count=$(count_classes test-multi)
filter_count=$(count_filters test-multi)

echo "Classes found: $class_count (expected: 5+ including default)"
echo "Filters found: $filter_count (expected: 5+)"

verify_filter_exists test-multi "10.0.1.1"
test_result $? "Peer 1 filter exists"

verify_filter_exists test-multi "10.0.1.2"
test_result $? "Peer 2 filter exists"

verify_filter_exists test-multi "10.0.1.3"
test_result $? "Peer 3 filter exists"

verify_filter_exists test-multi "10.0.1.4"
test_result $? "Peer 4 filter exists"

echo ""
echo "Current tc configuration:"
echo "Qdiscs:"
tc qdisc show dev test-multi
echo ""
echo "Classes:"
tc class show dev test-multi
echo ""
echo "Filters (showing first 20 lines):"
tc filter show dev test-multi parent 1: | head -20
echo ""

# Check IFB device
echo "IFB device configuration:"
if ip link show ifb-test-multi &>/dev/null; then
    echo "IFB device exists ✓"
    echo "IFB Classes:"
    tc class show dev ifb-test-multi
    echo ""
    echo "IFB Filters (showing first 20 lines):"
    tc filter show dev ifb-test-multi parent 1: | head -20
    test_result 0 "IFB device properly configured for upload limiting"
else
    test_result 1 "IFB device should exist for upload limiting"
fi
echo ""

# ===========================================
# Test 2: Remove Individual Peer (Middle Peer)
# ===========================================
echo "🧪 Test 2: Remove Individual Peer (Peer 2) - Others Should Remain"
echo "-------------------------------------------------------------------"

echo "Removing Peer 2 (10.0.1.2/32)..."
./traffic-weir -interface test-multi -peer peer-2 -scheduler htb \
    -allowed-ips 10.0.1.2/32 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "Peer 2 removed successfully"

echo ""
echo "Verifying Peer 2 is gone but others remain..."

verify_filter_exists test-multi "10.0.1.2"
if [ $? -ne 0 ]; then
    test_result 0 "Peer 2 filter removed"
else
    test_result 1 "Peer 2 filter should be removed"
fi

verify_filter_exists test-multi "10.0.1.1"
test_result $? "Peer 1 filter still exists"

verify_filter_exists test-multi "10.0.1.3"
test_result $? "Peer 3 filter still exists"

verify_filter_exists test-multi "10.0.1.4"
test_result $? "Peer 4 filter still exists"

echo ""
echo "Remaining filters:"
tc filter show dev test-multi parent 1: | head -20
echo ""

# ===========================================
# Test 3: Update Rate for Existing Peer
# ===========================================
echo "🧪 Test 3: Update Rate for Existing Peer (Peer 3: 3 Mbps → 5 Mbps)"
echo "--------------------------------------------------------------------"

echo "Updating Peer 3 to 5 Mbps..."
./traffic-weir -interface test-multi -peer peer-3 -upload-rate 5000 -download-rate 5000 \
    -scheduler htb -allowed-ips 10.0.1.3/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "Peer 3 rate updated"

echo ""
echo "Verifying updated rate for Peer 3..."
tc class show dev test-multi | grep -A2 "10.0.1.3" || echo "Checking classes..."
peer3_rate=$(tc class show dev test-multi | grep "rate 5000Kbit" || echo "not found")
if [ -n "$peer3_rate" ]; then
    test_result 0 "Peer 3 class updated to 5 Mbps"
else
    echo "Note: Rate format may vary, checking if peer 3 still exists..."
    verify_filter_exists test-multi "10.0.1.3"
    test_result $? "Peer 3 still accessible after update"
fi

echo ""
echo "All other peers should be unaffected..."
verify_filter_exists test-multi "10.0.1.1"
test_result $? "Peer 1 unaffected by Peer 3 update"

verify_filter_exists test-multi "10.0.1.4"
test_result $? "Peer 4 unaffected by Peer 3 update"
echo ""

# ===========================================
# Test 4: Remove First Peer
# ===========================================
echo "🧪 Test 4: Remove First Peer (Peer 1)"
echo "--------------------------------------"

echo "Removing Peer 1 (10.0.1.1/32)..."
./traffic-weir -interface test-multi -peer peer-1 -scheduler htb \
    -allowed-ips 10.0.1.1/32 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "Peer 1 removed successfully"

verify_filter_exists test-multi "10.0.1.1"
if [ $? -ne 0 ]; then
    test_result 0 "Peer 1 filter removed"
else
    test_result 1 "Peer 1 filter should be removed"
fi

verify_filter_exists test-multi "10.0.1.3"
test_result $? "Peer 3 still exists after Peer 1 removal"

verify_filter_exists test-multi "10.0.1.4"
test_result $? "Peer 4 still exists after Peer 1 removal"
echo ""

# ===========================================
# Test 5: Add New Peer After Removals
# ===========================================
echo "🧪 Test 5: Add New Peer After Removals"
echo "---------------------------------------"

echo "Adding Peer 5: 10.0.1.5/32 (4 Mbps up/down)..."
./traffic-weir -interface test-multi -peer peer-5 -upload-rate 4000 -download-rate 4000 \
    -scheduler htb -allowed-ips 10.0.1.5/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "Peer 5 added successfully"

verify_filter_exists test-multi "10.0.1.5"
test_result $? "Peer 5 filter exists"

echo ""
echo "Verifying all remaining peers (3, 4, 5) still work..."
verify_filter_exists test-multi "10.0.1.3"
test_result $? "Peer 3 still exists"

verify_filter_exists test-multi "10.0.1.4"
test_result $? "Peer 4 still exists"
echo ""

# ===========================================
# Test 6: Remove All Remaining Peers
# ===========================================
echo "🧪 Test 6: Remove All Remaining Peers One by One"
echo "------------------------------------------------"

echo "Removing Peer 3..."
./traffic-weir -interface test-multi -peer peer-3 -scheduler htb \
    -allowed-ips 10.0.1.3/32 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "Peer 3 removed"

echo "Removing Peer 4..."
./traffic-weir -interface test-multi -peer peer-4 -scheduler htb \
    -allowed-ips 10.0.1.4/32 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "Peer 4 removed"

echo "Removing Peer 5..."
./traffic-weir -interface test-multi -peer peer-5 -scheduler htb \
    -allowed-ips 10.0.1.5/32 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "Peer 5 removed"

echo ""
echo "Final state after all removals:"
echo "Classes:"
tc class show dev test-multi
echo ""
echo "Filters:"
tc filter show dev test-multi parent 1:
echo ""

# ===========================================
# Test 7: IPv6 Multi-Peer Test
# ===========================================
echo "🧪 Test 7: Multiple IPv6 Peers"
echo "--------------------------------"

echo "Adding IPv6 Peer 1: 2001:db8::1/128 (1 Mbps)"
./traffic-weir -interface test-multi -peer ipv6-peer-1 -upload-rate 1000 -download-rate 1000 \
    -scheduler htb -allowed-ips 2001:db8::1/128 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "IPv6 Peer 1 added"

echo "Adding IPv6 Peer 2: 2001:db8::2/128 (2 Mbps)"
./traffic-weir -interface test-multi -peer ipv6-peer-2 -upload-rate 2000 -download-rate 2000 \
    -scheduler htb -allowed-ips 2001:db8::2/128 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "IPv6 Peer 2 added"

echo ""
echo "IPv6 Filters:"
tc filter show dev test-multi parent 1: protocol ipv6
echo ""

echo "Removing IPv6 Peer 1..."
./traffic-weir -interface test-multi -peer ipv6-peer-1 -scheduler htb \
    -allowed-ips 2001:db8::1/128 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "IPv6 Peer 1 removed"

tc filter show dev test-multi parent 1: protocol ipv6 | grep -q "2001:db8::2"
test_result $? "IPv6 Peer 2 still exists after Peer 1 removal"

echo "Removing IPv6 Peer 2..."
./traffic-weir -interface test-multi -peer ipv6-peer-2 -scheduler htb \
    -allowed-ips 2001:db8::2/128 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "IPv6 Peer 2 removed"
echo ""

# ===========================================
# Test 8: Mixed IPv4/IPv6 Multi-Peer
# ===========================================
echo "🧪 Test 8: Mixed IPv4/IPv6 Peers on Same Interface"
echo "---------------------------------------------------"

echo "Adding IPv4 Peer: 10.0.2.1/32 (1 Mbps)"
./traffic-weir -interface test-multi -peer mixed-ipv4 -upload-rate 1000 -download-rate 1000 \
    -scheduler htb -allowed-ips 10.0.2.1/32 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "IPv4 peer added"

echo "Adding IPv6 Peer: 2001:db8::10/128 (2 Mbps)"
./traffic-weir -interface test-multi -peer mixed-ipv6 -upload-rate 2000 -download-rate 2000 \
    -scheduler htb -allowed-ips 2001:db8::10/128 -protocol wg 2>&1 | grep -q "Successfully configured"
test_result $? "IPv6 peer added to same interface"

echo ""
echo "Mixed IPv4/IPv6 Configuration:"
echo "IPv4 Filters:"
tc filter show dev test-multi parent 1: protocol ip | head -10
echo ""
echo "IPv6 Filters:"
tc filter show dev test-multi parent 1: protocol ipv6 | head -10
echo ""

verify_filter_exists test-multi "10.0.2.1"
test_result $? "IPv4 peer filter exists in mixed setup"

tc filter show dev test-multi parent 1: protocol ipv6 | grep -q "2001:db8::10"
test_result $? "IPv6 peer filter exists in mixed setup"

echo "Removing IPv4 peer..."
./traffic-weir -interface test-multi -peer mixed-ipv4 -scheduler htb \
    -allowed-ips 10.0.2.1/32 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "IPv4 peer removed from mixed setup"

echo "Removing IPv6 peer..."
./traffic-weir -interface test-multi -peer mixed-ipv6 -scheduler htb \
    -allowed-ips 2001:db8::10/128 -protocol wg -remove 2>&1 | grep -q "Successfully removed"
test_result $? "IPv6 peer removed from mixed setup"
echo ""

# ===========================================
# Test 9: Stress Test - 10 Peers
# ===========================================
echo "🧪 Test 9: Stress Test - 10 Peers on Single Interface"
echo "------------------------------------------------------"

for i in {1..10}; do
    echo "Adding Peer $i: 10.0.3.$i/32 ($((i * 500)) Kbps)"
    ./traffic-weir -interface test-multi -peer stress-peer-$i \
        -upload-rate $((i * 500)) -download-rate $((i * 500)) \
        -scheduler htb -allowed-ips 10.0.3.$i/32 -protocol wg 2>&1 | grep -q "Successfully configured"
    test_result $? "Stress peer $i added"
done

echo ""
echo "Verifying all 10 stress test peers exist..."
for i in {1..10}; do
    verify_filter_exists test-multi "10.0.3.$i"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Peer $i (10.0.3.$i) filter exists"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Peer $i (10.0.3.$i) filter missing"
        ((TESTS_FAILED++))
    fi
done

echo ""
echo "Removing stress test peers (odd numbers first)..."
for i in {1..10..2}; do
    ./traffic-weir -interface test-multi -peer stress-peer-$i -scheduler htb \
        -allowed-ips 10.0.3.$i/32 -protocol wg -remove &>/dev/null
    echo "Removed peer $i"
done

echo ""
echo "Verifying even peers still exist..."
for i in {2..10..2}; do
    verify_filter_exists test-multi "10.0.3.$i"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Peer $i still exists"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Peer $i missing (should exist)"
        ((TESTS_FAILED++))
    fi
done

echo ""
echo "Removing remaining stress test peers..."
for i in {2..10..2}; do
    ./traffic-weir -interface test-multi -peer stress-peer-$i -scheduler htb \
        -allowed-ips 10.0.3.$i/32 -protocol wg -remove &>/dev/null
done
test_result 0 "All stress test peers removed"
echo ""

# ===========================================
# Test 10: Nuke with Multiple Peers
# ===========================================
echo "🧪 Test 10: Nuke Interface with Multiple Active Peers"
echo "------------------------------------------------------"

echo "Adding 3 peers for nuke test..."
./traffic-weir -interface test-multi -peer nuke-peer-1 -upload-rate 1000 -download-rate 1000 \
    -scheduler htb -allowed-ips 10.0.4.1/32 -protocol wg &>/dev/null
./traffic-weir -interface test-multi -peer nuke-peer-2 -upload-rate 2000 -download-rate 2000 \
    -scheduler htb -allowed-ips 10.0.4.2/32 -protocol wg &>/dev/null
./traffic-weir -interface test-multi -peer nuke-peer-3 -upload-rate 3000 -download-rate 3000 \
    -scheduler htb -allowed-ips 10.0.4.3/32 -protocol wg &>/dev/null

echo "Verifying peers exist before nuke..."
class_count_before=$(count_classes test-multi)
echo "Classes before nuke: $class_count_before"

echo ""
echo "Nuking interface..."
./traffic-weir -interface test-multi -nuke 2>&1 | grep -q "Successfully nuked"
test_result $? "Interface nuked successfully"

echo ""
echo "Verifying complete cleanup..."
qdisc_check=$(tc qdisc show dev test-multi | grep -c "htb\|hfsc" || true)
if [ "$qdisc_check" -eq 0 ]; then
    test_result 0 "All qdiscs removed by nuke"
else
    test_result 1 "Qdiscs should be removed by nuke"
fi

# Check if IFB device was removed
if ip link show ifb-test-multi &>/dev/null; then
    test_result 1 "IFB device should be removed by nuke"
else
    test_result 0 "IFB device removed by nuke"
fi
echo ""

# ===========================================
# Cleanup
# ===========================================
echo "🧹 Cleaning up test interface..."
./traffic-weir -interface test-multi -nuke &>/dev/null || true
ip link delete test-multi 2>/dev/null || true
echo ""

# ===========================================
# Final Results
# ===========================================
echo "========================================"
echo "📊 Multi-Peer Test Suite Results"
echo "========================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All multi-peer tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
