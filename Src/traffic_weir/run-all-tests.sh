#!/bin/bash
set -e

echo "🧪 Running comprehensive traffic-weir test suite..."
echo "=================================================="
echo ""

# Function to run tests with timing
run_test_suite() {
    local test_name="$1"
    local test_command="$2"
    
    echo "📋 $test_name"
    echo "----------------------------------------"
    
    start_time=$(date +%s.%N)
    
    if eval "$test_command"; then
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc)
        echo "✅ $test_name completed in ${duration}s"
    else
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc)
        echo "❌ $test_name failed after ${duration}s"
        return 1
    fi
    
    echo ""
}

# Check if bc is available for timing
if ! command -v bc &> /dev/null; then
    echo "⚠️  Warning: bc not available, timing will be approximate"
    TIMING_AVAILABLE=false
else
    TIMING_AVAILABLE=true
fi

# Test 1: Basic functionality
run_test_suite "Basic Functionality Tests" "cd /app/tests && go test -v -run TestCAKESchedulerValidation"

# Test 2: HTB scheduler
run_test_suite "HTB Scheduler Tests" "cd /app/tests && go test -v -run TestHTB"

# Test 3: HFSC scheduler
run_test_suite "HFSC Scheduler Tests" "cd /app/tests && go test -v -run TestHFSC"

# Test 4: CAKE scheduler
run_test_suite "CAKE Scheduler Tests" "cd /app/tests && go test -v -run TestCAKE"

# Test 5: Integration tests
run_test_suite "Integration Tests" "cd /app/tests && go test -v -run TestIntegration"

# Test 6: Security tests
run_test_suite "Security Tests" "cd /app/tests && go test -v -run TestSecurity"

# Test 7: Performance tests
run_test_suite "Performance Tests" "cd /app/tests && go test -v -run TestPerformance"

# Test 8: Scheduler comparison
run_test_suite "Scheduler Comparison Tests" "cd /app/tests && go test -v -run TestCAKEVsHTBCommands"

# Test 9: Manual tc verification
run_test_suite "Manual TC Command Verification" "./run-comprehensive-tests.sh"

# Test 10: Benchmark tests
run_test_suite "Benchmark Tests" "cd /app/tests && go test -v -bench=. -run=^$"

echo "🎉 All test suites completed!"
echo "=================================================="

# Summary
echo ""
echo "📊 Test Summary:"
echo "✅ Basic Functionality: PASSED"
echo "✅ HTB Scheduler: PASSED"
echo "✅ HFSC Scheduler: PASSED"
echo "✅ CAKE Scheduler: PASSED"
echo "✅ Integration Tests: PASSED"
echo "✅ Security Tests: PASSED"
echo "✅ Performance Tests: PASSED"
echo "✅ Scheduler Comparison: PASSED"
echo "✅ Manual TC Verification: PASSED"
echo "✅ Benchmark Tests: PASSED"
echo ""
echo "🚀 traffic-weir is ready for production!"
