#!/bin/bash
set -e

echo "🧪 Starting comprehensive traffic-weir test suite..."
echo ""

# Setup test environment
./setup-test-interfaces.sh
echo ""

# Test 1: Basic functionality tests
echo "📋 Test 1: Basic functionality tests"
cd tests && go test -v -run TestCAKESchedulerValidation
echo ""

# Test 2: HTB scheduler tests
echo "📋 Test 2: HTB scheduler tests"
cd tests && go test -v -run TestHTB
echo ""

# Test 3: HFSC scheduler tests
echo "📋 Test 3: HFSC scheduler tests"
cd tests && go test -v -run TestHFSC
echo ""

# Test 4: CAKE scheduler tests
echo "📋 Test 4: CAKE scheduler tests"
cd tests && go test -v -run TestCAKE
echo ""

# Test 5: Integration tests
echo "📋 Test 5: Integration tests"
cd tests && go test -v -run TestIntegration
echo ""

# Test 6: Security tests
echo "📋 Test 6: Security tests"
cd tests && go test -v -run TestSecurity
echo ""

# Test 7: Performance tests
echo "📋 Test 7: Performance tests"
cd tests && go test -v -run TestPerformance
echo ""

# Test 8: Scheduler comparison tests
echo "📋 Test 8: Scheduler comparison tests"
cd tests && go test -v -run TestCAKEVsHTBCommands
echo ""

# Test 9: Manual tc command verification
echo "📋 Test 9: Manual tc command verification"
echo "Testing HTB scheduler..."
cd /app && ./traffic-weir -interface test-wg0 -peer test-peer-htb -upload-rate 1000 -download-rate 2000 -scheduler htb -allowed-ips 10.0.0.1/32
echo "HTB qdisc status:"
tc qdisc show dev test-wg0
echo "HTB classes:"
tc class show dev test-wg0
echo "HTB filters:"
tc filter show dev test-wg0
echo ""

echo "Testing HFSC scheduler..."
cd /app && ./traffic-weir -interface test-wg1 -peer test-peer-hfsc -upload-rate 1500 -download-rate 3000 -scheduler hfsc -allowed-ips 10.0.0.2/32
echo "HFSC qdisc status:"
tc qdisc show dev test-wg1
echo "HFSC classes:"
tc class show dev test-wg1
echo "HFSC filters:"
tc filter show dev test-wg1
echo ""

# Test 10: CAKE scheduler (if supported)
echo "📋 Test 10: CAKE scheduler test"
echo "Testing CAKE scheduler..."
cd /app && ./traffic-weir -interface test-wg0 -peer test-peer-cake -upload-rate 2000 -download-rate 4000 -scheduler cake -allowed-ips 10.0.0.3/32
echo "CAKE qdisc status:"
tc qdisc show dev test-wg0
echo "CAKE filters:"
tc filter show dev test-wg0
echo ""

# Test 11: Rate limit removal
echo "📋 Test 11: Rate limit removal tests"
echo "Removing HTB rate limits..."
cd /app && ./traffic-weir -interface test-wg0 -peer test-peer-htb -scheduler htb -allowed-ips 10.0.0.1/32 -remove
echo "HTB qdisc after removal:"
tc qdisc show dev test-wg0
echo "HTB classes after removal:"
tc class show dev test-wg0
echo ""

echo "Removing HFSC rate limits..."
cd /app && ./traffic-weir -interface test-wg1 -peer test-peer-hfsc -scheduler hfsc -allowed-ips 10.0.0.2/32 -remove
echo "HFSC qdisc after removal:"
tc qdisc show dev test-wg1
echo "HFSC classes after removal:"
tc class show dev test-wg1
echo ""

# Test 12: Interface nuking
echo "📋 Test 12: Interface nuking tests"
echo "Nuking test-wg0 interface..."
cd /app && ./traffic-weir -interface test-wg0 -nuke
echo "Interface status after nuke:"
tc qdisc show dev test-wg0
echo ""

# Test 13: Error handling
echo "📋 Test 13: Error handling tests"
echo "Testing invalid interface..."
cd /app && ./traffic-weir -interface nonexistent -peer test-peer -upload-rate 1000 -download-rate 2000 -scheduler htb -allowed-ips 10.0.0.1/32 || echo "Expected error for nonexistent interface"
echo ""

# Test 14: IPv6 support
echo "📋 Test 14: IPv6 support tests"
echo "Testing IPv6 addresses..."
cd /app && ./traffic-weir -interface test-wg0 -peer test-peer-ipv6 -upload-rate 1000 -download-rate 2000 -scheduler htb -allowed-ips 2001:db8::1/128
echo "IPv6 qdisc status:"
tc qdisc show dev test-wg0
echo "IPv6 filters:"
tc filter show dev test-wg0
echo ""

# Test 15: Scheduler conflict resolution
echo "📋 Test 15: Scheduler conflict resolution tests"
echo "Testing scheduler conflict (HTB -> HFSC)..."
cd /app && ./traffic-weir -interface test-wg0 -peer test-peer-conflict1 -upload-rate 1000 -download-rate 2000 -scheduler htb -allowed-ips 10.0.0.10/32
echo "Attempting to switch to HFSC on same interface..."
cd /app && ./traffic-weir -interface test-wg0 -peer test-peer-conflict2 -upload-rate 1500 -download-rate 3000 -scheduler hfsc -allowed-ips 10.0.0.11/32
echo "Final qdisc status:"
tc qdisc show dev test-wg0
echo ""

# Test 16: Performance benchmarks
echo "📋 Test 16: Performance benchmarks"
cd tests && go test -v -run BenchmarkCAKESetup -bench=.
echo ""

# Cleanup
echo "🧹 Cleaning up test environment..."
./cleanup-test-interfaces.sh
echo ""

echo "✅ All tests completed successfully!"
