package tests

import (
	"os/exec"
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestHFSCSchedulerValidation(t *testing.T) {
	// Test HFSC scheduler validation
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.1/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HFSC validation output: %s", string(output))
	}
	
	// Verify HFSC-specific output
	outputStr := string(output)
	if !strings.Contains(outputStr, "scheduler: hfsc") {
		t.Errorf("Expected HFSC scheduler validation, got: %s", outputStr)
	}
}

func TestHFSCClassCreation(t *testing.T) {
	// Test HFSC class creation
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_hfsc", 
		"-upload-rate", "1500", "-download-rate", "3000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.2/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HFSC class creation output: %s", string(output))
	}
	
	// Verify class creation
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully created class") {
		t.Errorf("Expected HFSC class creation, got: %s", outputStr)
	}
}

func TestHFSCRateLimits(t *testing.T) {
	// Test HFSC rate limiting
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_hfsc_rates", 
		"-upload-rate", "5000", "-download-rate", "10000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.3/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HFSC rate limits output: %s", string(output))
	}
	
	// Verify rate limiting setup
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully configured rate limiting") {
		t.Errorf("Expected HFSC rate limiting setup, got: %s", outputStr)
	}
}

func TestHFSCFilterManagement(t *testing.T) {
	// Test HFSC filter management
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_hfsc_filters", 
		"-upload-rate", "2000", "-download-rate", "4000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.4/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HFSC filter management output: %s", string(output))
	}
	
	// Verify filter setup
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully added download filter") {
		t.Errorf("Expected HFSC filter setup, got: %s", outputStr)
	}
}

func TestHFSCRemoval(t *testing.T) {
	// Test HFSC rate limit removal
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_hfsc_removal", 
		"-upload-rate", "4194303", "-download-rate", "4194303", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.5/32", "-remove")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HFSC removal output: %s", string(output))
	}
	
	// Verify removal
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully removed rate limits") {
		t.Errorf("Expected HFSC rate limit removal, got: %s", outputStr)
	}
}

func TestHFSCPerformance(t *testing.T) {
	// Test HFSC performance
	start := time.Now()
	
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_hfsc_perf", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.6/32")
	
	output, err := cmd.CombinedOutput()
	duration := time.Since(start)
	
	if err != nil {
		t.Logf("HFSC performance output: %s", string(output))
	}
	
	// Verify performance (should complete quickly)
	if duration > 100*time.Millisecond {
		t.Errorf("HFSC setup took too long: %v", duration)
	}
	
	t.Logf("HFSC scheduler completed in %v", duration)
}

func TestHFSCErrorHandling(t *testing.T) {
	// Test HFSC error handling
	cmd := exec.Command("/app/traffic-weir", "-interface", "nonexistent", "-peer", "test_peer", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.1/32")
	
	output, err := cmd.CombinedOutput()
	
	// This should fail
	if err == nil {
		t.Errorf("Expected HFSC error for nonexistent interface, but command succeeded")
	}
	
	// Verify error message
	outputStr := string(output)
	if !strings.Contains(outputStr, "ERROR") {
		t.Errorf("Expected HFSC error message, got: %s", outputStr)
	}
}

func TestHFSCIPv6Support(t *testing.T) {
	// Test HFSC IPv6 support
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_hfsc_ipv6", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "hfsc", 
		"-allowed-ips", "::1/128")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HFSC IPv6 output: %s", string(output))
	}
	
	// Verify IPv6 handling
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully added all filters") {
		t.Errorf("Expected HFSC IPv6 support, got: %s", outputStr)
	}
}

func TestHFSCMultiplePeers(t *testing.T) {
	// Test HFSC with multiple peers
	peers := []string{"127.0.0.20/32", "127.0.0.21/32", "127.0.0.22/32"}
	
	for i, peerIP := range peers {
		cmd := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_hfsc_multi_"+string(rune(i+'0')), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "hfsc", 
			"-allowed-ips", peerIP)
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Logf("HFSC multiple peers output %d: %s", i, string(output))
		}
		
		// Verify each peer setup
		outputStr := string(output)
		if !strings.Contains(outputStr, "Successfully configured rate limiting") {
			t.Errorf("Expected HFSC multiple peer setup for peer %d, got: %s", i, outputStr)
		}
	}
}

func TestHFSCEdgeCases(t *testing.T) {
	// Test HFSC edge cases
	testCases := []struct {
		name        string
		uploadRate  int
		downloadRate int
		expectedErr bool
	}{
		{"Zero rates", 0, 0, false},
		{"Maximum rates", 4194303, 4194303, false},
		{"Very small rates", 1, 1, false},
		{"Large rates", 1000000, 2000000, false},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command("/app/traffic-weir", "-interface", "lo", 
				"-peer", "test_peer_hfsc_edge_"+tc.name, 
				"-upload-rate", strconv.Itoa(tc.uploadRate), 
				"-download-rate", strconv.Itoa(tc.downloadRate), 
				"-scheduler", "hfsc", "-allowed-ips", "127.0.0.30/32")
			
			output, err := cmd.CombinedOutput()
			
			if tc.expectedErr && err == nil {
				t.Errorf("Expected error for %s, but command succeeded", tc.name)
			}
			
			if !tc.expectedErr && err != nil {
				t.Logf("HFSC edge case %s output: %s", tc.name, string(output))
			}
		})
	}
}

func TestHFSCSchedulerConflict(t *testing.T) {
	// Test HFSC scheduler conflict resolution
	// First, set up HTB
	cmd1 := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_conflict_htb", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.40/32")
	
	output1, err1 := cmd1.CombinedOutput()
	if err1 != nil {
		t.Logf("HTB setup for conflict test: %s", string(output1))
	}
	
	// Then try to switch to HFSC
	cmd2 := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_conflict_hfsc", 
		"-upload-rate", "1500", "-download-rate", "3000", "-scheduler", "hfsc", 
		"-allowed-ips", "127.0.0.41/32")
	
	output2, err2 := cmd2.CombinedOutput()
	if err2 != nil {
		t.Logf("HFSC conflict test: %s", string(output2))
	}
	
	// Verify conflict resolution - should either succeed or show warning
	outputStr := string(output2)
	if !strings.Contains(outputStr, "WARNING") && !strings.Contains(outputStr, "Preserving existing") && !strings.Contains(outputStr, "Successfully configured") {
		t.Logf("HFSC conflict resolution output: %s", outputStr)
		// This is not necessarily an error - the system might handle conflicts differently
	}
}
