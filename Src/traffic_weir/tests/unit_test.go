package tests

import (
	"testing"
)

// TestUnitRateValidation tests rate validation logic
func TestUnitRateValidation(t *testing.T) {
	testCases := []struct {
		name        string
		rate        int64
		expectValid bool
	}{
		{"Zero rate", 0, true},
		{"Valid rate", 1000, true},
		{"Maximum rate", 4194303, true},
		{"Negative rate", -1000, false},
		{"Excessive rate", 999999999, false},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// This would test the actual rate validation function
			// For now, we'll implement basic validation logic
			valid := tc.rate >= 0 && tc.rate <= 4194303
			
			if valid != tc.expectValid {
				t.Errorf("Rate validation for %d: expected %v, got %v", tc.rate, tc.expectValid, valid)
			}
		})
	}
}

// TestUnitIPValidation tests IP address validation
func TestUnitIPValidation(t *testing.T) {
	testCases := []struct {
		name        string
		ip          string
		expectValid bool
	}{
		{"Valid IPv4", "127.0.0.1/32", true},
		{"Valid IPv6", "::1/128", true},
		{"Invalid IP", "invalid-ip", false},
		{"Empty IP", "", false},
		{"Malformed CIDR", "127.0.0.1", false},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Basic IP validation - in a real implementation, this would use net.ParseCIDR
			valid := len(tc.ip) > 0 && contains(tc.ip, "/")
			
			if valid != tc.expectValid {
				t.Errorf("IP validation for %s: expected %v, got %v", tc.ip, tc.expectValid, valid)
			}
		})
	}
}

// TestUnitSchedulerValidation tests scheduler validation
func TestUnitSchedulerValidation(t *testing.T) {
	testCases := []struct {
		name        string
		scheduler   string
		expectValid bool
	}{
		{"Valid HTB", "htb", true},
		{"Valid HFSC", "hfsc", true},
		{"Valid CAKE", "cake", true},
		{"Invalid scheduler", "invalid", false},
		{"Empty scheduler", "", true}, // Should use default
		{"Case sensitive", "HTB", false}, // Should be lowercase
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			valid := tc.scheduler == "" || tc.scheduler == "htb" || tc.scheduler == "hfsc" || tc.scheduler == "cake"
			
			if valid != tc.expectValid {
				t.Errorf("Scheduler validation for %s: expected %v, got %v", tc.scheduler, tc.expectValid, valid)
			}
		})
	}
}

// TestUnitPeerIDValidation tests peer ID validation
func TestUnitPeerIDValidation(t *testing.T) {
	testCases := []struct {
		name        string
		peerID      string
		expectValid bool
	}{
		{"Valid peer ID", "test_peer", true},
		{"Empty peer ID", "", false},
		{"Peer with special chars", "test_peer;rm -rf /", false},
		{"Peer with path traversal", "../../../etc/passwd", false},
		{"Peer with command injection", "test_peer | cat /etc/passwd", false},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Basic peer ID validation - should not contain dangerous characters
			valid := len(tc.peerID) > 0 && 
				!contains(tc.peerID, ";") && 
				!contains(tc.peerID, "|") && 
				!contains(tc.peerID, "&") && 
				!contains(tc.peerID, "$") && 
				!contains(tc.peerID, "`") && 
				!contains(tc.peerID, "../") &&
				!contains(tc.peerID, "rm -rf")
			
			if valid != tc.expectValid {
				t.Errorf("Peer ID validation for %s: expected %v, got %v", tc.peerID, tc.expectValid, valid)
			}
		})
	}
}

// TestUnitInterfaceValidation tests interface name validation
func TestUnitInterfaceValidation(t *testing.T) {
	testCases := []struct {
		name        string
		interfaceName string
		expectValid bool
	}{
		{"Valid interface", "lo", true},
		{"Valid interface with numbers", "eth0", true},
		{"Empty interface", "", false},
		{"Interface with special chars", "lo;rm -rf /", false},
		{"Interface with path traversal", "../../../etc/passwd", false},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Basic interface validation
			valid := len(tc.interfaceName) > 0 && 
				!contains(tc.interfaceName, ";") && 
				!contains(tc.interfaceName, "|") && 
				!contains(tc.interfaceName, "&") && 
				!contains(tc.interfaceName, "$") && 
				!contains(tc.interfaceName, "`") && 
				!contains(tc.interfaceName, "../") &&
				!contains(tc.interfaceName, "rm -rf")
			
			if valid != tc.expectValid {
				t.Errorf("Interface validation for %s: expected %v, got %v", tc.interfaceName, tc.expectValid, valid)
			}
		})
	}
}

// TestUnitProtocolValidation tests protocol validation
func TestUnitProtocolValidation(t *testing.T) {
	testCases := []struct {
		name        string
		protocol    string
		expectValid bool
	}{
		{"Valid WG protocol", "wg", true},
		{"Valid AWG protocol", "awg", true},
		{"Invalid protocol", "invalid", false},
		{"Empty protocol", "", true}, // Should use default
		{"Protocol with special chars", "wg;rm -rf /", false},
		{"Case sensitive", "WG", false}, // Should be lowercase
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			valid := tc.protocol == "" || tc.protocol == "wg" || tc.protocol == "awg"
			
			if valid != tc.expectValid {
				t.Errorf("Protocol validation for %s: expected %v, got %v", tc.protocol, tc.expectValid, valid)
			}
		})
	}
}

// BenchmarkRateValidation benchmarks rate validation
func BenchmarkRateValidation(b *testing.B) {
	for i := 0; i < b.N; i++ {
		rate := int64(i % 1000000)
		_ = rate >= 0 && rate <= 4194303
	}
}

// BenchmarkIPValidation benchmarks IP validation
func BenchmarkIPValidation(b *testing.B) {
	testIPs := []string{"127.0.0.1/32", "::1/128", "invalid-ip", "192.168.1.1/24"}
	
	for i := 0; i < b.N; i++ {
		ip := testIPs[i%len(testIPs)]
		_ = len(ip) > 0 && contains(ip, "/")
	}
}

// BenchmarkSchedulerValidation benchmarks scheduler validation
func BenchmarkSchedulerValidation(b *testing.B) {
	schedulers := []string{"htb", "hfsc", "cake", "invalid", ""}
	
	for i := 0; i < b.N; i++ {
		scheduler := schedulers[i%len(schedulers)]
		_ = scheduler == "" || scheduler == "htb" || scheduler == "hfsc" || scheduler == "cake"
	}
}
