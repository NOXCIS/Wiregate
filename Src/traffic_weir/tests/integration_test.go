package tests

import (
	"os/exec"
	"strings"
	"testing"
	"time"
)

func TestEndToEndWorkflow(t *testing.T) {
	// Use test helper for proper cleanup
	helper := NewTestHelper(t, "lo")
	defer helper.Cleanup()
	
	interfaceName := "lo"
	peerID := "test_peer_e2e"
	allowedIP := "127.0.0.100/32"
	
	// Step 1: Set up rate limits
	t.Log("Step 1: Setting up rate limits")
	cmd1 := helper.RunTrafficWeir("-interface", interfaceName, "-peer", peerID, 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", allowedIP)
	
	AssertSuccess(t, cmd1, "Rate limit setup")
	
	// Step 2: Verify tc configuration
	t.Log("Step 2: Verifying tc configuration")
	cmd2 := exec.Command("tc", "qdisc", "show", "dev", interfaceName)
	output2, err2 := cmd2.CombinedOutput()
	if err2 != nil {
		t.Logf("tc qdisc show output: %s", string(output2))
	}
	
	// Verify HTB qdisc exists
	AssertContains(t, output2, "htb", "HTB qdisc verification")
	
	// Step 3: Remove rate limits
	t.Log("Step 3: Removing rate limits")
	cmd3 := exec.Command("/app/traffic-weir", "-interface", interfaceName, "-peer", peerID, 
		"-upload-rate", "4194303", "-download-rate", "4194303", "-scheduler", "htb", 
		"-allowed-ips", allowedIP, "-remove")
	
	AssertSuccess(t, cmd3, "Rate limit removal")
	
	// Step 4: Nuke interface
	t.Log("Step 4: Nuking interface")
	cmd4 := exec.Command("/app/traffic-weir", "-interface", interfaceName, "-nuke")
	AssertSuccess(t, cmd4, "Interface nuke")
}

func TestMultiSchedulerWorkflow(t *testing.T) {
	// Use test helper for proper cleanup
	helper := NewTestHelper(t, "lo")
	defer helper.Cleanup()
	
	interfaceName := "lo"
	
	// Test HTB workflow
	t.Log("Testing HTB workflow")
	cmd1 := helper.RunTrafficWeir("-interface", interfaceName, "-peer", "test_peer_htb_workflow", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.101/32")
	
	AssertSuccess(t, cmd1, "HTB workflow")
	
	// Test HFSC workflow
	t.Log("Testing HFSC workflow")
	cmd2 := helper.RunTrafficWeir("-interface", interfaceName, "-peer", "test_peer_hfsc_workflow", 
		"-upload-rate", "1500", "-download-rate", "3000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.102/32")
	
	AssertSuccess(t, cmd2, "HFSC workflow")
	
	// Test CAKE workflow
	t.Log("Testing CAKE workflow")
	cmd3 := helper.RunTrafficWeir("-interface", interfaceName, "-peer", "test_peer_cake_workflow", 
		"-upload-rate", "2000", "-download-rate", "4000", "-scheduler", "cake", 
		"-allowed-ips", "127.0.0.103/32")
	
	AssertSuccess(t, cmd3, "CAKE workflow")
}

func TestConcurrentOperations(t *testing.T) {
	// Test concurrent operations
	interfaceName := "lo"
	peers := []string{"127.0.0.110/32", "127.0.0.111/32", "127.0.0.112/32"}
	
	// Set up multiple peers concurrently
	done := make(chan bool, len(peers))
	
	for i, peerIP := range peers {
		go func(peerIP string, index int) {
			cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
				"-peer", "test_peer_concurrent_"+string(rune(index+'0')), 
				"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
				"-allowed-ips", peerIP)
			
			output, err := cmd.CombinedOutput()
			if err != nil {
				t.Logf("Concurrent operation %d output: %s", index, string(output))
			}
			
			done <- true
		}(peerIP, i)
	}
	
	// Wait for all operations to complete
	for i := 0; i < len(peers); i++ {
		select {
		case <-done:
			// Operation completed
		case <-time.After(5 * time.Second):
			t.Errorf("Concurrent operation %d timed out", i)
		}
	}
}

func TestStressTest(t *testing.T) {
	// Test stress scenarios
	interfaceName := "lo"
	
	// Rapid setup and teardown
	for i := 0; i < 10; i++ {
		peerID := "test_peer_stress_" + string(rune(i+'0'))
		peerIP := "127.0.0." + string(rune(120+i)) + "/32"
		
		// Setup
		cmd1 := exec.Command("/app/traffic-weir", "-interface", interfaceName, "-peer", peerID, 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", peerIP)
		
		output1, err1 := cmd1.CombinedOutput()
		if err1 != nil {
			t.Logf("Stress setup %d output: %s", i, string(output1))
		}
		
		// Immediate teardown
		cmd2 := exec.Command("/app/traffic-weir", "-interface", interfaceName, "-peer", peerID, 
			"-upload-rate", "4194303", "-download-rate", "4194303", "-scheduler", "htb", 
			"-allowed-ips", peerIP, "-remove")
		
		output2, err2 := cmd2.CombinedOutput()
		if err2 != nil {
			t.Logf("Stress teardown %d output: %s", i, string(output2))
		}
		
		// Small delay between iterations
		time.Sleep(10 * time.Millisecond)
	}
}

func TestErrorRecovery(t *testing.T) {
	// Test error recovery scenarios
	interfaceName := "lo"
	
	// Test 1: Invalid interface recovery
	t.Log("Testing invalid interface recovery")
	cmd1 := exec.Command("/app/traffic-weir", "-interface", "nonexistent", "-peer", "test_peer_error", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.130/32")
	
	_, err1 := cmd1.CombinedOutput()
	if err1 == nil {
		t.Errorf("Expected error for nonexistent interface")
	}
	
	// Test 2: Recovery with valid interface
	t.Log("Testing recovery with valid interface")
	cmd2 := exec.Command("/app/traffic-weir", "-interface", interfaceName, "-peer", "test_peer_recovery", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.131/32")
	
	output2, err2 := cmd2.CombinedOutput()
	if err2 != nil {
		t.Logf("Recovery output: %s", string(output2))
	}
	
	// Verify recovery
	outputStr2 := string(output2)
	if !strings.Contains(outputStr2, "Successfully configured rate limiting") {
		t.Errorf("Expected successful recovery, got: %s", outputStr2)
	}
}

func TestConfigurationValidation(t *testing.T) {
	// Test configuration validation
	testCases := []struct {
		name        string
		args        []string
		expectError bool
	}{
		{"Valid configuration", []string{"-interface", "lo", "-peer", "test_peer", 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.140/32"}, false},
		{"Missing interface", []string{"-peer", "test_peer", 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.141/32"}, true},
		{"Missing peer", []string{"-interface", "lo", 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", "127.0.0.142/32"}, true},
		{"Invalid scheduler", []string{"-interface", "lo", "-peer", "test_peer", 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "invalid", 
			"-allowed-ips", "127.0.0.143/32"}, true},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command("/app/traffic-weir", tc.args...)
			output, err := cmd.CombinedOutput()
			
			if tc.expectError && err == nil {
				t.Errorf("Expected error for %s, but command succeeded", tc.name)
			}
			
			if !tc.expectError && err != nil {
				t.Logf("Configuration validation %s output: %s", tc.name, string(output))
			}
		})
	}
}

func TestPerformanceBenchmarks(t *testing.T) {
	// Test performance benchmarks
	interfaceName := "lo"
	schedulers := []string{"htb", "hfsc", "cake"}
	
	for _, scheduler := range schedulers {
		t.Run("Benchmark_"+scheduler, func(t *testing.T) {
			start := time.Now()
			
			cmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, 
				"-peer", "test_peer_bench_"+scheduler, 
				"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", scheduler, 
				"-allowed-ips", "127.0.0.150/32")
			
			output, err := cmd.CombinedOutput()
			duration := time.Since(start)
			
			if err != nil {
				t.Logf("Benchmark %s output: %s", scheduler, string(output))
			}
			
			// Log performance
			t.Logf("Scheduler %s completed in %v", scheduler, duration)
			
			// Verify reasonable performance
			// HTB/HFSC with IFB setup can take ~220ms, CAKE is much faster
			threshold := 250 * time.Millisecond
			if scheduler == "cake" {
				threshold = 50 * time.Millisecond // CAKE should be very fast
			}
			if duration > threshold {
				t.Errorf("Scheduler %s took too long: %v (threshold: %v)", scheduler, duration, threshold)
			}
		})
	}
}
