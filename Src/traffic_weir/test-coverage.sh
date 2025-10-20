#!/bin/bash
set -e

echo "📊 Generating traffic-weir test coverage report..."
echo "================================================="
echo ""

# Function to run coverage for specific test
run_coverage() {
    local test_name="$1"
    local test_pattern="$2"
    
    echo "🔍 Running coverage for $test_name..."
    cd tests
    
    # Run tests with coverage
    go test -v -coverprofile="${test_name}_coverage.out" -run "$test_pattern"
    
    # Generate coverage report
    go tool cover -html="${test_name}_coverage.out" -o "${test_name}_coverage.html"
    
    # Show coverage percentage
    coverage_percent=$(go tool cover -func="${test_name}_coverage.out" | grep total | awk '{print $3}')
    echo "📈 $test_name coverage: $coverage_percent"
    
    cd ..
    echo ""
}

# Create coverage directory
mkdir -p coverage_reports

# Run coverage for each test suite
run_coverage "HTB" "TestHTB"
run_coverage "HFSC" "TestHFSC"
run_coverage "CAKE" "TestCAKE"
run_coverage "Integration" "TestIntegration"
run_coverage "Security" "TestSecurity"
run_coverage "Performance" "TestPerformance"

# Generate overall coverage report
echo "📊 Generating overall coverage report..."
cd tests

# Combine all coverage files
echo "mode: set" > overall_coverage.out
for file in *_coverage.out; do
    if [ -f "$file" ]; then
        tail -n +2 "$file" >> overall_coverage.out
    fi
done

# Generate overall coverage report
go tool cover -html=overall_coverage.out -o overall_coverage.html
go tool cover -func=overall_coverage.out

cd ..

echo ""
echo "📁 Coverage reports generated:"
echo "   - tests/overall_coverage.html (overall coverage)"
echo "   - tests/*_coverage.html (individual test coverage)"
echo ""
echo "🎯 Open tests/overall_coverage.html in your browser to view detailed coverage"
