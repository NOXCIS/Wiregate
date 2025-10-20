package tests

import (
	"os/exec"
	"testing"
)

// TestHelper provides common test utilities
type TestHelper struct {
	interfaceName string
	cleanupCmds   []*exec.Cmd
}

// NewTestHelper creates a new test helper with cleanup
func NewTestHelper(t *testing.T, interfaceName string) *TestHelper {
	helper := &TestHelper{
		interfaceName: interfaceName,
		cleanupCmds:   make([]*exec.Cmd, 0),
	}
	
	// Clean up any existing traffic control on the interface
	nukeCmd := exec.Command("/app/traffic-weir", "-interface", interfaceName, "-nuke")
	nukeCmd.Run() // Ignore errors
	
	return helper
}

// Cleanup runs all cleanup commands
func (h *TestHelper) Cleanup() {
	// Run cleanup commands in reverse order
	for i := len(h.cleanupCmds) - 1; i >= 0; i-- {
		h.cleanupCmds[i].Run() // Ignore errors
	}
	
	// Final nuke to ensure clean state
	nukeCmd := exec.Command("/app/traffic-weir", "-interface", h.interfaceName, "-nuke")
	nukeCmd.Run() // Ignore errors
}

// AddCleanup adds a cleanup command
func (h *TestHelper) AddCleanup(cmd *exec.Cmd) {
	h.cleanupCmds = append(h.cleanupCmds, cmd)
}

// RunTrafficWeir runs traffic-weir with the given arguments and adds cleanup
func (h *TestHelper) RunTrafficWeir(args ...string) *exec.Cmd {
	cmd := exec.Command("/app/traffic-weir", args...)
	
	// Add cleanup command for removal
	cleanupArgs := make([]string, 0, len(args))
	for i, arg := range args {
		if arg == "-peer" && i+1 < len(args) {
			// Add peer ID to cleanup
			cleanupArgs = append(cleanupArgs, arg, args[i+1])
		} else if arg == "-interface" && i+1 < len(args) {
			// Add interface to cleanup
			cleanupArgs = append(cleanupArgs, arg, args[i+1])
		} else if arg == "-scheduler" && i+1 < len(args) {
			// Add scheduler to cleanup
			cleanupArgs = append(cleanupArgs, arg, args[i+1])
		} else if arg == "-allowed-ips" && i+1 < len(args) {
			// Add allowed IPs to cleanup
			cleanupArgs = append(cleanupArgs, arg, args[i+1])
		}
	}
	
	// Add remove flag for cleanup
	cleanupArgs = append(cleanupArgs, "-remove")
	cleanupCmd := exec.Command("/app/traffic-weir", cleanupArgs...)
	h.AddCleanup(cleanupCmd)
	
	return cmd
}

// SetupTestInterface creates a test interface for testing
func SetupTestInterface(t *testing.T, interfaceName string) {
	// Create dummy interface for testing
	createCmd := exec.Command("ip", "link", "add", interfaceName, "type", "dummy")
	if err := createCmd.Run(); err != nil {
		t.Logf("Could not create test interface %s: %v", interfaceName, err)
		return
	}
	
	upCmd := exec.Command("ip", "link", "set", interfaceName, "up")
	if err := upCmd.Run(); err != nil {
		t.Logf("Could not bring up test interface %s: %v", interfaceName, err)
	}
}

// TeardownTestInterface removes a test interface
func TeardownTestInterface(t *testing.T, interfaceName string) {
	// Remove dummy interface
	delCmd := exec.Command("ip", "link", "del", interfaceName)
	if err := delCmd.Run(); err != nil {
		t.Logf("Could not remove test interface %s: %v", interfaceName, err)
	}
}

// AssertSuccess checks if a command succeeded and logs output
func AssertSuccess(t *testing.T, cmd *exec.Cmd, testName string) {
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Errorf("%s failed: %v\nOutput: %s", testName, err, string(output))
		return
	}
	t.Logf("%s succeeded. Output: %s", testName, string(output))
}

// AssertFailure checks if a command failed as expected
func AssertFailure(t *testing.T, cmd *exec.Cmd, testName string) {
	output, err := cmd.CombinedOutput()
	if err == nil {
		t.Errorf("%s should have failed, but succeeded. Output: %s", testName, string(output))
		return
	}
	t.Logf("%s failed as expected. Output: %s", testName, string(output))
}

// AssertContains checks if output contains expected text
func AssertContains(t *testing.T, output []byte, expected string, testName string) {
	outputStr := string(output)
	if !contains(outputStr, expected) {
		t.Errorf("%s: Expected output to contain '%s', but got: %s", testName, expected, outputStr)
	}
}

// AssertNotContains checks if output does not contain unexpected text
func AssertNotContains(t *testing.T, output []byte, unexpected string, testName string) {
	outputStr := string(output)
	if contains(outputStr, unexpected) {
		t.Errorf("%s: Expected output to NOT contain '%s', but got: %s", testName, unexpected, outputStr)
	}
}

// Helper function for case-insensitive contains
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || 
		(len(s) > len(substr) && (s[:len(substr)] == substr || 
		s[len(s)-len(substr):] == substr || 
		containsSubstring(s, substr))))
}

func containsSubstring(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
