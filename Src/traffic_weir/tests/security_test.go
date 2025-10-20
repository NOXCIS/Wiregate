package tests

import (
	"os/exec"
	"strings"
	"testing"
)

func TestInputValidation(t *testing.T) {
	// Test input validation and sanitization
	testCases := []struct {
		name        string
		args        []string
		expectError bool
		description string
	}{
		{
			"Valid IPv4", 
			[]string{"-interface", "lo", "-peer", "test_peer", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32"}, 
			false, 
			"Valid IPv4 address should work"},
		{
			"Valid IPv6", 
			[]string{"-interface", "lo", "-peer", "test_peer", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "::1/128"}, 
			false, 
			"Valid IPv6 address should work"},
		{
			"Invalid IP format", 
			[]string{"-interface", "lo", "-peer", "test_peer", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "invalid-ip"}, 
			true, 
			"Invalid IP format should fail"},
		{
			"Negative rate", 
			[]string{"-interface", "lo", "-peer", "test_peer", "-upload-rate", "-1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32"}, 
			true, 
			"Negative rates should fail"},
		{
			"Excessive rate", 
			[]string{"-interface", "lo", "-peer", "test_peer", "-upload-rate", "999999999", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32"}, 
			true, 
			"Excessive rates should be rejected"},
		{
			"Empty peer ID", 
			[]string{"-interface", "lo", "-peer", "", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32"}, 
			true, 
			"Empty peer ID should fail"},
		{
			"Special characters in peer", 
			[]string{"-interface", "lo", "-peer", "test_peer;rm -rf /", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32"}, 
			true, 
			"Special characters should be rejected for security"},
		{
			"Path traversal attempt", 
			[]string{"-interface", "lo", "-peer", "../../../etc/passwd", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32"}, 
			true, 
			"Path traversal attempts should be rejected for security"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command("/app/traffic-weir", tc.args...)
			output, err := cmd.CombinedOutput()
			outputStr := string(output)
			
			if tc.expectError && err == nil {
				t.Errorf("Expected error for %s (%s), but command succeeded. Output: %s", tc.name, tc.description, outputStr)
			}
			
			if !tc.expectError && err != nil {
				t.Logf("Input validation %s output: %s", tc.name, outputStr)
			}
			
			// Verify no dangerous operations were performed (security check)
			if strings.Contains(outputStr, "rm -rf") || strings.Contains(outputStr, "/etc/passwd") {
				t.Errorf("SECURITY ISSUE: Dangerous operation detected in %s: %s", tc.name, outputStr)
			}
			
			// Verify command injection attempts are blocked
			if strings.Contains(outputStr, "injected") || strings.Contains(outputStr, "uid=") {
				t.Errorf("SECURITY ISSUE: Command injection successful in %s: %s", tc.name, outputStr)
			}
		})
	}
}

func TestCommandInjection(t *testing.T) {
	// Test command injection prevention - these should ALL be rejected
	testCases := []struct {
		name        string
		peerID      string
		description string
	}{
		{"Basic injection", "test_peer; echo 'injected'", "Basic command injection attempt"},
		{"Pipe injection", "test_peer | cat /etc/passwd", "Pipe-based injection attempt"},
		{"Redirect injection", "test_peer > /tmp/test", "Redirect-based injection attempt"},
		{"Backtick injection", "test_peer `whoami`", "Backtick-based injection attempt"},
		{"Dollar injection", "test_peer $(id)", "Dollar substitution injection attempt"},
		{"Newline injection", "test_peer\nrm -rf /", "Newline-based injection attempt"},
		{"Tab injection", "test_peer\tcat /etc/passwd", "Tab-based injection attempt"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", tc.peerID, 
				"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
				"-allowed-ips", "127.0.0.1/32")
			
			output, err := cmd.CombinedOutput()
			outputStr := string(output)
			
			// Command injection attempts should be rejected (error expected)
			if err == nil {
				t.Errorf("SECURITY ISSUE: Command injection %s should have been rejected, but succeeded. Output: %s", tc.name, outputStr)
			}
			
			// Verify no injection was successful
			if strings.Contains(outputStr, "injected") || 
			   strings.Contains(outputStr, "root:") || 
			   strings.Contains(outputStr, "uid=") ||
			   strings.Contains(outputStr, "rm -rf") ||
			   strings.Contains(outputStr, "whoami") {
				t.Errorf("SECURITY ISSUE: Command injection successful in %s: %s", tc.name, outputStr)
			}
			
			// Log the output for analysis
			t.Logf("Command injection test %s output: %s", tc.name, outputStr)
		})
	}
}

func TestResourceLimits(t *testing.T) {
	// Test resource limit handling
	testCases := []struct {
		name        string
		uploadRate  string
		downloadRate string
		description string
	}{
		{"Zero rates", "0", "0", "Zero rates should be handled"},
		{"Maximum rates", "4194303", "4194303", "Maximum rates should be handled"},
		{"Very large rates", "999999999", "999999999", "Very large rates should be handled"},
		{"Negative rates", "-1000", "-2000", "Negative rates should be rejected"},
		{"Non-numeric rates", "abc", "def", "Non-numeric rates should be rejected"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command("/app/traffic-weir", "-interface", "lo", "-peer", "test_peer_resource", 
				"-upload-rate", tc.uploadRate, "-download-rate", tc.downloadRate, 
				"-scheduler", "htb", "-allowed-ips", "127.0.0.1/32")
			
			output, err := cmd.CombinedOutput()
			outputStr := string(output)
			
			// Log output for analysis
			t.Logf("Resource limit test %s output: %s", tc.name, outputStr)
			
			// Verify appropriate handling
			if tc.name == "Negative rates" || tc.name == "Non-numeric rates" {
				if err == nil {
					t.Errorf("Expected error for %s, but command succeeded", tc.name)
				}
			}
		})
	}
}

func TestInterfaceSecurity(t *testing.T) {
	// Test interface security
	testCases := []struct {
		name        string
		interfaceName string
		expectError bool
		description string
	}{
		{"Valid interface", "lo", false, "Valid interface should work"},
		{"Nonexistent interface", "nonexistent", true, "Nonexistent interface should fail"},
		{"System interface", "eth0", false, "System interface should be handled"},
		{"Special characters", "lo; rm -rf /", true, "Special characters should be rejected"},
		{"Path traversal", "../../../etc/passwd", true, "Path traversal should be rejected"},
		{"Empty interface", "", true, "Empty interface should fail"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			cmd := exec.Command("/app/traffic-weir", "-interface", tc.interfaceName, 
				"-peer", "test_peer_interface", "-upload-rate", "1000", 
				"-download-rate", "2000", "-scheduler", "htb", "-allowed-ips", "127.0.0.1/32")
			
			output, err := cmd.CombinedOutput()
			outputStr := string(output)
			
			if tc.expectError && err == nil {
				t.Errorf("Expected error for %s (%s), but command succeeded. Output: %s", tc.name, tc.description, outputStr)
			}
			
			if !tc.expectError && err != nil {
				t.Logf("Interface security test %s output: %s", tc.name, outputStr)
			}
			
			// Verify no dangerous operations
			if strings.Contains(outputStr, "rm -rf") || strings.Contains(outputStr, "/etc/passwd") {
				t.Errorf("SECURITY ISSUE: Dangerous operation detected in %s: %s", tc.name, outputStr)
			}
		})
	}
}

func TestProtocolValidation(t *testing.T) {
	// Test protocol validation
	testCases := []struct {
		name        string
		protocol    string
		expectError bool
		description string
	}{
		{"Valid WG protocol", "wg", false, "Valid WG protocol should work"},
		{"Valid AWG protocol", "awg", false, "Valid AWG protocol should work"},
		{"Invalid protocol", "invalid", true, "Invalid protocol should fail"},
		{"Empty protocol", "", false, "Empty protocol should use default"},
		{"Special characters", "wg; rm -rf /", true, "Special characters should be rejected"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			args := []string{"-interface", "lo", "-peer", "test_peer_protocol", 
				"-upload-rate", "1000", "-download-rate", "2000", "-scheduler", "htb", 
				"-allowed-ips", "127.0.0.1/32"}
			
			if tc.protocol != "" {
				args = append(args, "-protocol", tc.protocol)
			}
			
			cmd := exec.Command("/app/traffic-weir", args...)
			output, err := cmd.CombinedOutput()
			outputStr := string(output)
			
			if tc.expectError && err == nil {
				t.Errorf("Expected error for %s (%s), but command succeeded. Output: %s", tc.name, tc.description, outputStr)
			}
			
			if !tc.expectError && err != nil {
				t.Logf("Protocol validation test %s output: %s", tc.name, outputStr)
			}
			
			// Verify no dangerous operations
			if strings.Contains(outputStr, "rm -rf") {
				t.Errorf("SECURITY ISSUE: Dangerous operation detected in %s: %s", tc.name, outputStr)
			}
		})
	}
}

func TestSchedulerSecurity(t *testing.T) {
	// Test scheduler security
	testCases := []struct {
		name        string
		scheduler   string
		expectError bool
		description string
	}{
		{"Valid HTB", "htb", false, "Valid HTB scheduler should work"},
		{"Valid HFSC", "hfsc", false, "Valid HFSC scheduler should work"},
		{"Valid CAKE", "cake", false, "Valid CAKE scheduler should work"},
		{"Invalid scheduler", "invalid", true, "Invalid scheduler should fail"},
		{"Empty scheduler", "", false, "Empty scheduler should use default"},
		{"Command injection", "htb; rm -rf /", true, "Command injection should be rejected"},
		{"Path traversal", "../../../etc/passwd", true, "Path traversal should be rejected"},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			args := []string{"-interface", "lo", "-peer", "test_peer_scheduler", 
				"-upload-rate", "1000", "-download-rate", "2000", "-allowed-ips", "127.0.0.1/32"}
			
			if tc.scheduler != "" {
				args = append(args, "-scheduler", tc.scheduler)
			}
			
			cmd := exec.Command("/app/traffic-weir", args...)
			output, err := cmd.CombinedOutput()
			outputStr := string(output)
			
			if tc.expectError && err == nil {
				t.Errorf("Expected error for %s (%s), but command succeeded. Output: %s", tc.name, tc.description, outputStr)
			}
			
			if !tc.expectError && err != nil {
				t.Logf("Scheduler security test %s output: %s", tc.name, outputStr)
			}
			
			// Verify no dangerous operations
			if strings.Contains(outputStr, "rm -rf") || strings.Contains(outputStr, "/etc/passwd") {
				t.Errorf("SECURITY ISSUE: Dangerous operation detected in %s: %s", tc.name, outputStr)
			}
		})
	}
}
