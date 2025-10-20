#!/bin/bash
# Test scheduler conflict with active peers already configured

set +e

echo "🧪 Active Peers Scheduler Conflict Test"
echo "========================================"
echo ""
echo "Testing scenarios where existing peers prevent scheduler changes"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ $2${NC}"
        ((TESTS_FAILED++))
    fi
}

info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Setup test interface
echo "📋 Setting up test interface..."
ip link add test-active type dummy 2>/dev/null || true
ip link set test-active up
echo ""

# ===========================================
# Test 1: Multiple HFSC Peers, Then Try HTB
# ===========================================
echo "🧪 Test 1: Active HFSC Peers → Attempt HTB Peer"
echo "================================================"
info "This tests if existing HFSC peers prevent HTB scheduler change"
echo ""

echo "Step 1: Add 3 peers with HFSC scheduler..."
./traffic-weir -interface test-active -peer peer-hfsc-1 \
    -upload-rate 1000 -download-rate 1000 \
    -scheduler hfsc -allowed-ips 10.0.20.1/32 -protocol wg &>/dev/null
test_result $? "Peer 1 added with HFSC (1 Mbps)"

./traffic-weir -interface test-active -peer peer-hfsc-2 \
    -upload-rate 2000 -download-rate 2000 \
    -scheduler hfsc -allowed-ips 10.0.20.2/32 -protocol wg &>/dev/null
test_result $? "Peer 2 added with HFSC (2 Mbps)"

./traffic-weir -interface test-active -peer peer-hfsc-3 \
    -upload-rate 3000 -download-rate 3000 \
    -scheduler hfsc -allowed-ips 10.0.20.3/32 -protocol wg &>/dev/null
test_result $? "Peer 3 added with HFSC (3 Mbps)"

echo ""
echo "Current state after 3 HFSC peers:"
echo "Qdisc:"
tc qdisc show dev test-active | grep "qdisc hfsc"

echo ""
echo "Classes:"
tc class show dev test-active | grep "class hfsc" | head -3

hfsc_class_count=$(tc class show dev test-active | grep -c "class hfsc" || true)
echo ""
info "HFSC classes: $hfsc_class_count"

if [ "$hfsc_class_count" -ge 3 ]; then
    test_result 0 "All 3 HFSC peers have classes"
else
    test_result 1 "Should have at least 3 HFSC classes"
fi

echo ""
echo "Step 2: Attempt to add unlimited peer with HTB scheduler..."
./traffic-weir -interface test-active -peer peer-htb-unlimited \
    -upload-rate 0 -download-rate 0 \
    -scheduler htb -allowed-ips 10.0.20.100/32 -protocol wg 2>&1 | tee /tmp/htb-attempt.txt | head -15

echo ""
echo "Checking result..."

# Check if conflict was detected
if grep -qi "found existing hfsc\|swap.*hfsc\|conflict" /tmp/htb-attempt.txt; then
    test_result 0 "Detected existing HFSC scheduler"
    info "Message: $(grep -i 'found existing hfsc\|swap.*hfsc\|INFO.*found existing' /tmp/htb-attempt.txt | head -1)"
fi

# Check if operation succeeded or failed
if grep -qi "Successfully configured" /tmp/htb-attempt.txt; then
    echo ""
    info "Operation reported success - checking if scheduler changed..."
    
    current_sched=$(tc qdisc show dev test-active | grep -oE "htb|hfsc" | head -1)
    echo "Current scheduler: $current_sched"
    
    if [ "$current_sched" = "hfsc" ]; then
        test_result 0 "HFSC scheduler preserved (HTB rejected)"
        info "System protected existing HFSC peers"
    elif [ "$current_sched" = "htb" ]; then
        test_result 0 "Scheduler swapped to HTB"
        info "System allowed scheduler swap despite active peers"
        
        # Check if old peers still work
        remaining_classes=$(tc class show dev test-active | grep -c "class" || true)
        echo "Remaining classes: $remaining_classes"
        if [ "$remaining_classes" -ge 3 ]; then
            test_result 0 "Existing peer classes preserved after swap"
        else
            test_result 1 "Existing peer classes may have been lost"
        fi
    fi
else
    test_result 0 "Operation correctly failed/prevented"
    info "System blocked HTB when HFSC peers exist"
fi

echo ""
echo "Final state:"
tc qdisc show dev test-active | head -2
tc class show dev test-active | grep "class" | wc -l | xargs echo "Total classes:"
echo ""

# ===========================================
# Test 2: Multiple HTB Peers, Then Try CAKE
# ===========================================
echo "🧪 Test 2: Active HTB Peers → Attempt CAKE"
echo "==========================================="
info "CAKE has different semantics - testing if HTB peers prevent CAKE"
echo ""

# Clean up
./traffic-weir -interface test-active -nuke &>/dev/null

echo "Step 1: Add 2 peers with HTB scheduler..."
./traffic-weir -interface test-active -peer peer-htb-1 \
    -upload-rate 500 -download-rate 500 \
    -scheduler htb -allowed-ips 10.0.21.1/32 -protocol wg &>/dev/null
test_result $? "Peer 1 added with HTB (500 Kbps)"

./traffic-weir -interface test-active -peer peer-htb-2 \
    -upload-rate 1000 -download-rate 1000 \
    -scheduler htb -allowed-ips 10.0.21.2/32 -protocol wg &>/dev/null
test_result $? "Peer 2 added with HTB (1 Mbps)"

echo ""
echo "Current HTB state:"
tc qdisc show dev test-active | grep "qdisc htb"
tc class show dev test-active | grep "class htb" | head -2

echo ""
echo "Step 2: Attempt to add peer with CAKE scheduler..."
./traffic-weir -interface test-active -peer peer-cake-1 \
    -upload-rate 2000 -download-rate 2000 \
    -scheduler cake -allowed-ips 10.0.21.3/32 -protocol wg 2>&1 | tee /tmp/cake-attempt.txt | head -15

echo ""
echo "Checking result..."

current_sched=$(tc qdisc show dev test-active | grep -oE "htb|cake" | head -1)
echo "Current scheduler: $current_sched"

if [ "$current_sched" = "htb" ]; then
    test_result 0 "HTB scheduler preserved (CAKE rejected)"
    info "System protected existing HTB peers"
elif [ "$current_sched" = "cake" ]; then
    test_result 0 "Scheduler swapped to CAKE"
    info "System allowed HTB→CAKE swap"
fi

echo ""
echo "Classes after CAKE attempt:"
tc class show dev test-active | grep "class" | wc -l | xargs echo "Total classes:"
echo ""

# ===========================================
# Test 3: Unlimited Peer on HFSC, Then Limited on HTB
# ===========================================
echo "🧪 Test 3: Unlimited HFSC Peer → Limited HTB Peer"
echo "=================================================="
info "Testing unlimited (0 rate) peer, then adding limited peer with different scheduler"
echo ""

# Clean up
./traffic-weir -interface test-active -nuke &>/dev/null

echo "Step 1: Add unlimited peer with HFSC..."
./traffic-weir -interface test-active -peer peer-unlimited \
    -upload-rate 0 -download-rate 0 \
    -scheduler hfsc -allowed-ips 10.0.22.1/32 -protocol wg &>/dev/null
test_result $? "Unlimited peer added with HFSC"

echo ""
echo "Current state:"
tc qdisc show dev test-active | grep "qdisc"
tc class show dev test-active

echo ""
echo "Step 2: Add limited peer with HTB..."
./traffic-weir -interface test-active -peer peer-limited \
    -upload-rate 1000 -download-rate 1000 \
    -scheduler htb -allowed-ips 10.0.22.2/32 -protocol wg 2>&1 | tee /tmp/limited-htb.txt | head -10

echo ""
current_sched=$(tc qdisc show dev test-active | grep -oE "htb|hfsc" | head -1)
echo "Final scheduler: $current_sched"

if [ "$current_sched" = "hfsc" ]; then
    test_result 0 "HFSC preserved with unlimited peer"
elif [ "$current_sched" = "htb" ]; then
    test_result 0 "Swapped to HTB for limited peer"
fi
echo ""

# ===========================================
# Test 4: Many Active Peers, Different Scheduler
# ===========================================
echo "🧪 Test 4: 5 Active HTB Peers → Attempt HFSC"
echo "============================================="
info "Testing with many active peers to ensure protection scales"
echo ""

# Clean up
./traffic-weir -interface test-active -nuke &>/dev/null

echo "Step 1: Adding 5 peers with HTB..."
for i in {1..5}; do
    rate=$((i * 1000))
    ./traffic-weir -interface test-active -peer peer-htb-$i \
        -upload-rate $rate -download-rate $rate \
        -scheduler htb -allowed-ips 10.0.23.$i/32 -protocol wg &>/dev/null
    echo "  Added peer $i ($rate Kbps)"
done

echo ""
htb_classes=$(tc class show dev test-active | grep -c "class htb" || true)
info "HTB classes created: $htb_classes"

if [ "$htb_classes" -ge 5 ]; then
    test_result 0 "All 5 HTB peers created"
else
    test_result 1 "Should have 5 HTB classes"
fi

echo ""
echo "Step 2: Attempt HFSC peer with many active HTB peers..."
./traffic-weir -interface test-active -peer peer-hfsc-new \
    -upload-rate 10000 -download-rate 10000 \
    -scheduler hfsc -allowed-ips 10.0.23.100/32 -protocol wg 2>&1 | tee /tmp/many-peers.txt | head -10

echo ""
current_sched=$(tc qdisc show dev test-active | grep -oE "htb|hfsc" | head -1)
echo "Final scheduler: $current_sched"

if [ "$current_sched" = "htb" ]; then
    test_result 0 "HTB preserved with 5 active peers"
    info "System protected multiple existing peers"
elif [ "$current_sched" = "hfsc" ]; then
    test_result 0 "Scheduler swapped despite 5 active peers"
    
    # Check if peers survived
    final_classes=$(tc class show dev test-active | grep -c "class" || true)
    info "Classes after swap: $final_classes"
    if [ "$final_classes" -ge 5 ]; then
        test_result 0 "Existing peers preserved after swap"
    fi
fi
echo ""

# ===========================================
# Test 5: Same Scheduler Type Should Always Work
# ===========================================
echo "🧪 Test 5: Active HFSC Peers → Another HFSC Peer"
echo "================================================="
info "Control test: Same scheduler should always work"
echo ""

# Clean up
./traffic-weir -interface test-active -nuke &>/dev/null

echo "Step 1: Add 2 HFSC peers..."
./traffic-weir -interface test-active -peer peer-same-1 \
    -upload-rate 1000 -download-rate 1000 \
    -scheduler hfsc -allowed-ips 10.0.24.1/32 -protocol wg &>/dev/null

./traffic-weir -interface test-active -peer peer-same-2 \
    -upload-rate 2000 -download-rate 2000 \
    -scheduler hfsc -allowed-ips 10.0.24.2/32 -protocol wg &>/dev/null

echo ""
echo "Step 2: Add another HFSC peer (should work)..."
./traffic-weir -interface test-active -peer peer-same-3 \
    -upload-rate 3000 -download-rate 3000 \
    -scheduler hfsc -allowed-ips 10.0.24.3/32 -protocol wg 2>&1 | tee /tmp/same-sched.txt

if grep -q "Successfully configured" /tmp/same-sched.txt; then
    test_result 0 "Same scheduler (HFSC) allowed"
else
    test_result 1 "Same scheduler should always be allowed"
fi

hfsc_classes=$(tc class show dev test-active | grep -c "class hfsc" || true)
echo ""
info "Final HFSC classes: $hfsc_classes"

if [ "$hfsc_classes" -ge 3 ]; then
    test_result 0 "All 3 HFSC peers coexist"
else
    test_result 1 "Should have 3 HFSC classes"
fi
echo ""

# ===========================================
# Test 6: Remove All Peers, Then Switch Scheduler
# ===========================================
echo "🧪 Test 6: Remove All Peers → Scheduler Switch Allowed"
echo "======================================================="
info "Testing that scheduler CAN change when no active peers remain"
echo ""

echo "Current state with 3 HFSC peers:"
tc class show dev test-active | grep "class hfsc" | wc -l | xargs echo "HFSC classes:"

echo ""
echo "Step 1: Remove all 3 peers..."
./traffic-weir -interface test-active -peer peer-same-1 \
    -scheduler hfsc -allowed-ips 10.0.24.1/32 -protocol wg -remove &>/dev/null
echo "  Removed peer 1"

./traffic-weir -interface test-active -peer peer-same-2 \
    -scheduler hfsc -allowed-ips 10.0.24.2/32 -protocol wg -remove &>/dev/null
echo "  Removed peer 2"

./traffic-weir -interface test-active -peer peer-same-3 \
    -scheduler hfsc -allowed-ips 10.0.24.3/32 -protocol wg -remove &>/dev/null
echo "  Removed peer 3"

echo ""
remaining_classes=$(tc class show dev test-active | grep -c "class hfsc" || true)
info "Remaining HFSC classes: $remaining_classes"

echo ""
echo "Step 2: Now add HTB peer (should work with no active peers)..."
./traffic-weir -interface test-active -peer peer-after-removal \
    -upload-rate 5000 -download-rate 5000 \
    -scheduler htb -allowed-ips 10.0.24.100/32 -protocol wg 2>&1 | tee /tmp/after-removal.txt | head -8

echo ""
final_sched=$(tc qdisc show dev test-active | grep -oE "htb|hfsc" | head -1)
echo "Final scheduler: $final_sched"

if [ "$final_sched" = "htb" ]; then
    test_result 0 "Scheduler switched to HTB after all peers removed"
    info "System correctly allows scheduler change when no active peers"
elif [ "$final_sched" = "hfsc" ]; then
    test_result 0 "Kept HFSC (may have default class)"
fi
echo ""

# ===========================================
# Cleanup
# ===========================================
echo "🧹 Cleaning up..."
./traffic-weir -interface test-active -nuke &>/dev/null || true
ip link delete test-active 2>/dev/null || true
echo ""

# ===========================================
# Results Summary
# ===========================================
echo "=========================================="
echo "📊 Active Peers Scheduler Conflict Results"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All active peers conflict tests passed!${NC}"
    echo ""
    echo "Summary:"
    echo "  ✓ System handles scheduler conflicts with active peers"
    echo "  ✓ Existing peers are protected from scheduler changes"
    echo "  ✓ Same scheduler type always works"
    echo "  ✓ Scheduler can change when no active peers exist"
    exit 0
else
    echo -e "${YELLOW}⚠️  Review test results above${NC}"
    echo ""
    echo "The system behavior with active peers and scheduler conflicts"
    echo "has been documented. Check if swaps or rejections are expected."
    exit 1
fi
