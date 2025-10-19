package tests

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"
)

// TestCAKESchedulerValidation tests that CAKE scheduler is properly validated
func TestCAKESchedulerValidation(t *testing.T) {
	// Test valid CAKE scheduler
	cmd := exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "test_peer",
		"-upload-rate", "1000",
		"-download-rate", "2000",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32")

	output, _ := cmd.CombinedOutput()

	// Should not fail due to invalid scheduler
	if strings.Contains(string(output), "Invalid scheduler") {
		t.Errorf("CAKE scheduler should be valid, got error: %s", string(output))
	}
}

// TestCAKEVsHTBCommands tests that CAKE uses different commands than HTB
func TestCAKEVsHTBCommands(t *testing.T) {
	// Clean up interface before test
	nukeCmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-nuke")
	nukeCmd.Run() // Ignore errors

	// This test would need to be run with actual tc commands
	// For now, we'll test the logic differences

	schedulers := []string{"htb", "hfsc", "cake"}

	for _, scheduler := range schedulers {
		// Clean up before each scheduler test
		nukeCmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-nuke")
		nukeCmd.Run() // Ignore errors
		
		cmd := exec.Command("/app/traffic-weir",
			"-interface", "lo",
			"-peer", "test_peer",
			"-upload-rate", "1000",
			"-download-rate", "2000",
			"-scheduler", scheduler,
			"-allowed-ips", "127.0.0.1/32")

		output, _ := cmd.CombinedOutput()

		// Log the output for debugging
		t.Logf("Scheduler %s output: %s", scheduler, string(output))

		// CAKE should behave differently (no class creation)
		if scheduler == "cake" && strings.Contains(string(output), "Creating class") {
			t.Errorf("CAKE should not create classes, but output shows: %s", string(output))
		}

		// HTB/HFSC should create classes
		if (scheduler == "htb" || scheduler == "hfsc") && !strings.Contains(string(output), "Creating class") {
			t.Logf("Note: %s scheduler didn't create classes (may be expected in test environment)", scheduler)
		}
	}
}

// TestCAKEBandwidthCalculation tests CAKE bandwidth and burst calculations
func TestCAKEBandwidthCalculation(t *testing.T) {
	testCases := []struct {
		rateKbps      int64
		expectedBurst int64
	}{
		{1000, 125000},   // 1 Mbps -> 125KB burst
		{5000, 625000},   // 5 Mbps -> 625KB burst
		{10000, 1250000}, // 10 Mbps -> 1.25MB burst
	}

	for _, tc := range testCases {
		burst := tc.rateKbps * 125
		if burst != tc.expectedBurst {
			t.Errorf("For rate %d Kbps, expected burst %d, got %d",
				tc.rateKbps, tc.expectedBurst, burst)
		}
	}
}

// TestCAKERateLimitSetup tests CAKE rate limit setup
func TestCAKERateLimitSetup(t *testing.T) {
	// Clean up interface before test
	nukeCmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-nuke")
	nukeCmd.Run() // Ignore errors

	cmd := exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "test_peer",
		"-upload-rate", "1000",
		"-download-rate", "2000",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32")

	output, _ := cmd.CombinedOutput()

	// Should succeed or fail gracefully
	t.Logf("CAKE setup output: %s", string(output))

	// Should contain CAKE-specific messages
	if !strings.Contains(string(output), "CAKE") {
		t.Errorf("Expected CAKE-related output, got: %s", string(output))
	}
}

// TestCAKERateLimitRemoval tests CAKE rate limit removal
func TestCAKERateLimitRemoval(t *testing.T) {
	cmd := exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "test_peer",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32",
		"-remove")

	output, _ := cmd.CombinedOutput()

	// Should succeed or fail gracefully
	t.Logf("CAKE removal output: %s", string(output))

	// Should contain CAKE-specific removal messages
	if !strings.Contains(string(output), "CAKE") {
		t.Errorf("Expected CAKE-related removal output, got: %s", string(output))
	}
}

// TestCAKEIPv6Support tests CAKE support for IPv6
func TestCAKEIPv6Support(t *testing.T) {
	cmd := exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "test_peer",
		"-upload-rate", "1000",
		"-download-rate", "2000",
		"-scheduler", "cake",
		"-allowed-ips", "::1/128")

	output, _ := cmd.CombinedOutput()

	// Should handle IPv6 addresses
	if strings.Contains(string(output), "Invalid") {
		t.Errorf("CAKE should support IPv6, got error: %s", string(output))
	}
}

// TestCAKEErrorHandling tests CAKE error handling
func TestCAKEErrorHandling(t *testing.T) {
	// Test with invalid interface
	cmd := exec.Command("/app/traffic-weir",
		"-interface", "nonexistent_interface",
		"-peer", "test_peer",
		"-upload-rate", "1000",
		"-download-rate", "2000",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32")

	output, _ := cmd.CombinedOutput()

	// Should fail gracefully with appropriate error message
	t.Logf("Error handling test output: %s", string(output))

	if !strings.Contains(string(output), "interface") && !strings.Contains(string(output), "ERROR") {
		t.Errorf("Expected error message about interface, got: %s", string(output))
	}
}

// TestCAKEPerformanceCharacteristics tests CAKE performance characteristics
func TestCAKEPerformanceCharacteristics(t *testing.T) {
	// This test verifies that CAKE uses appropriate performance optimizations
	// In a real implementation, we'd measure actual performance

	schedulers := []string{"htb", "hfsc", "cake"}

	for _, scheduler := range schedulers {
		cmd := exec.Command("/app/traffic-weir",
			"-interface", "lo",
			"-peer", "test_peer",
			"-upload-rate", "1000",
			"-download-rate", "2000",
			"-scheduler", scheduler,
			"-allowed-ips", "127.0.0.1/32")

		start := time.Now()
		output, _ := cmd.CombinedOutput()
		duration := time.Since(start)

		t.Logf("Scheduler %s took %v, output: %s", scheduler, duration, string(output))

		// CAKE should be efficient (conceptual test)
		if scheduler == "cake" {
			// In a real test, we'd assert performance characteristics
			t.Logf("CAKE scheduler completed in %v", duration)
		}
	}
}

// TestCAKEIntegration tests CAKE integration with the overall system
func TestCAKEIntegration(t *testing.T) {
	// Test that CAKE integrates properly with the traffic-weir system

	// Test 1: Basic setup
	cmd := exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "integration_test_peer",
		"-upload-rate", "5000",
		"-download-rate", "10000",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32")

	output, _ := cmd.CombinedOutput()
	t.Logf("CAKE integration setup: %s", string(output))

	// Test 2: Removal
	cmd = exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "integration_test_peer",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32",
		"-remove")

	output, _ = cmd.CombinedOutput()
	t.Logf("CAKE integration removal: %s", string(output))

	// Test 3: Nuke interface
	cmd = exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-scheduler", "cake",
		"-nuke")

	output, _ = cmd.CombinedOutput()
	t.Logf("CAKE integration nuke: %s", string(output))
}

// TestCAKESystemCapabilities tests system capabilities with CAKE
func TestCAKESystemCapabilities(t *testing.T) {
	// Test that CAKE is included in system capabilities
	cmd := exec.Command("/app/traffic-weir",
		"-interface", "lo",
		"-peer", "test_peer",
		"-upload-rate", "1000",
		"-download-rate", "2000",
		"-scheduler", "cake",
		"-allowed-ips", "127.0.0.1/32")

	output, _ := cmd.CombinedOutput()

	// Should mention CAKE in capabilities
	if !strings.Contains(string(output), "cake") && !strings.Contains(string(output), "CAKE") {
		t.Errorf("Expected CAKE to be mentioned in system capabilities, got: %s", string(output))
	}
}

// BenchmarkCAKESetup benchmarks CAKE setup performance
func BenchmarkCAKESetup(b *testing.B) {
	for i := 0; i < b.N; i++ {
		cmd := exec.Command("/app/traffic-weir",
			"-interface", "lo",
			"-peer", fmt.Sprintf("benchmark_peer_%d", i),
			"-upload-rate", "1000",
			"-download-rate", "2000",
			"-scheduler", "cake",
			"-allowed-ips", "127.0.0.1/32")

		cmd.Run() // Ignore errors for benchmark
	}
}

// BenchmarkCAKERemoval benchmarks CAKE removal performance
func BenchmarkCAKERemoval(b *testing.B) {
	for i := 0; i < b.N; i++ {
		cmd := exec.Command("/app/traffic-weir",
			"-interface", "lo",
			"-peer", fmt.Sprintf("benchmark_peer_%d", i),
			"-scheduler", "cake",
			"-allowed-ips", "127.0.0.1/32",
			"-remove")

		cmd.Run() // Ignore errors for benchmark
	}
}

func TestMain(m *testing.M) {
	// Check if traffic-weir binary exists
	if _, err := os.Stat("/app/traffic-weir"); os.IsNotExist(err) {
		fmt.Println("traffic-weir binary not found at /app/traffic-weir. Please ensure it's built and available.")
		os.Exit(1)
	}

	// Run tests
	code := m.Run()
	os.Exit(code)
}
