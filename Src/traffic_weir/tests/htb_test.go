package tests

import (
	"os/exec"
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestHTBSchedulerValidation(t *testing.T) {
	// Test HTB scheduler validation
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.1/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HTB validation output: %s", string(output))
		// This is expected to work
	}
	
	// Verify HTB-specific output
	outputStr := string(output)
	if !strings.Contains(outputStr, "scheduler: htb") {
		t.Errorf("Expected HTB scheduler validation, got: %s", outputStr)
	}
}

func TestHTBClassCreation(t *testing.T) {
	// Test HTB class creation
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_htb", 
		"-upload-rate", "1500", "-download-rate", "3000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.2/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HTB class creation output: %s", string(output))
	}
	
	// Verify class creation
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully created class") {
		t.Errorf("Expected HTB class creation, got: %s", outputStr)
	}
}

func TestHTBRateLimits(t *testing.T) {
	// Test HTB rate limiting
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_htb_rates", 
		"-upload-rate", "5000", "-download-rate", "10000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.3/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HTB rate limits output: %s", string(output))
	}
	
	// Verify rate limiting setup
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully configured rate limiting") {
		t.Errorf("Expected HTB rate limiting setup, got: %s", outputStr)
	}
}

func TestHTBFilterManagement(t *testing.T) {
	// Test HTB filter management
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_htb_filters", 
		"-upload-rate", "2000", "-download-rate", "4000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.4/32")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HTB filter management output: %s", string(output))
	}
	
	// Verify filter setup
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully added download filter") {
		t.Errorf("Expected HTB filter setup, got: %s", outputStr)
	}
}

func TestHTBRemoval(t *testing.T) {
	// Test HTB rate limit removal
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_htb_removal", 
		"-upload-rate", "4194303", "-download-rate", "4194303", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.5/32", "-remove")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HTB removal output: %s", string(output))
	}
	
	// Verify removal
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully removed rate limits") {
		t.Errorf("Expected HTB rate limit removal, got: %s", outputStr)
	}
}

func TestHTBPerformance(t *testing.T) {
	// Test HTB performance
	start := time.Now()
	
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_htb_perf", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.6/32")
	
	output, err := cmd.CombinedOutput()
	duration := time.Since(start)
	
	if err != nil {
		t.Logf("HTB performance output: %s", string(output))
	}
	
	// Verify performance (should complete quickly)
	if duration > 100*time.Millisecond {
		t.Errorf("HTB setup took too long: %v", duration)
	}
	
	t.Logf("HTB scheduler completed in %v", duration)
}

func TestHTBErrorHandling(t *testing.T) {
	// Test HTB error handling
	cmd := exec.Command("/app/traffic-weir", "-interface", "nonexistent", "-peer", "test_peer", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "127.0.0.1/32")
	
	output, err := cmd.CombinedOutput()
	
	// This should fail
	if err == nil {
		t.Errorf("Expected HTB error for nonexistent interface, but command succeeded")
	}
	
	// Verify error message
	outputStr := string(output)
	if !strings.Contains(outputStr, "ERROR") {
		t.Errorf("Expected HTB error message, got: %s", outputStr)
	}
}

func TestHTBIPv6Support(t *testing.T) {
	// Test HTB IPv6 support
	cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_htb_ipv6", 
		"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
		"-allowed-ips", "::1/128")
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Logf("HTB IPv6 output: %s", string(output))
	}
	
	// Verify IPv6 handling
	outputStr := string(output)
	if !strings.Contains(outputStr, "Successfully added all filters") {
		t.Errorf("Expected HTB IPv6 support, got: %s", outputStr)
	}
}

func TestHTBMultiplePeers(t *testing.T) {
	// Test HTB with multiple peers
	peers := []string{"127.0.0.10/32", "127.0.0.11/32", "127.0.0.12/32"}
	
	for i, peerIP := range peers {
		cmd := exec.Command("/app/traffic-weir", "-interface", "lo", 
			"-peer", "test_peer_htb_multi_"+string(rune(i+'0')), 
			"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
			"-allowed-ips", peerIP)
		
		output, err := cmd.CombinedOutput()
		if err != nil {
			t.Logf("HTB multiple peers output %d: %s", i, string(output))
		}
		
		// Verify each peer setup
		outputStr := string(output)
		if !strings.Contains(outputStr, "Successfully configured rate limiting") {
			t.Errorf("Expected HTB multiple peer setup for peer %d, got: %s", i, outputStr)
		}
	}
}

func TestHTBEdgeCases(t *testing.T) {
	// Test HTB edge cases
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
				"-peer", "test_peer_htb_edge_"+tc.name, 
				"-upload-rate", strconv.Itoa(tc.uploadRate), 
				"-download-rate", strconv.Itoa(tc.downloadRate), 
				"-scheduler", "htb", "-allowed-ips", "127.0.0.20/32")
			
			output, err := cmd.CombinedOutput()
			
			if tc.expectedErr && err == nil {
				t.Errorf("Expected error for %s, but command succeeded", tc.name)
			}
			
			if !tc.expectedErr && err != nil {
				t.Logf("HTB edge case %s output: %s", tc.name, string(output))
			}
		})
	}
}
