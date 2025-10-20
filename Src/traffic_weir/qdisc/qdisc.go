package qdisc

import (
	"fmt"
	"os/exec"
	"strings"
	"sync"
	"time"

	"traffic-weir/config"
	"traffic-weir/logger"
)

// Global mutex to prevent concurrent access to interfaces
var interfaceMutex sync.Mutex

// CheckIPv6Support checks if the current qdisc supports IPv6 filters
func CheckIPv6Support(dev string) bool {
	// Check if there are any existing IPv6 filters
	listCmd := exec.Command(config.TCPath, "filter", "show", "dev", dev, "parent", "1:")
	output, err := listCmd.CombinedOutput()
	if err != nil {
		return false
	}
	
	// If we find any IPv6 filters, the qdisc supports IPv6
	return strings.Contains(string(output), "protocol ipv6")
}

// NeedsIPv6Support checks if the current operation requires IPv6 support
func NeedsIPv6Support(allowedIP string) bool {
	return strings.Contains(allowedIP, ":")
}

// EnsureIPv6Support ensures that the qdisc supports IPv6 by adding base IPv6 filter if needed
func EnsureIPv6Support(dev string) error {
	// Check if IPv6 support already exists
	if CheckIPv6Support(dev) {
		logger.Logger.Printf("IPv6 support already exists on %s", dev)
		return nil
	}
	
	// Add IPv6 base filter at priority 2 to establish IPv6 filter chain
	// IPv6 must use a different priority than IPv4 (which uses priority 1)
	// Use ip6 src ::/0 to match all IPv6 traffic (correct IPv6 syntax)
	logger.Logger.Printf("Adding IPv6 base filter at priority 2 to enable IPv6 support on %s...", dev)
	ipv6Cmd := exec.Command(config.TCPath, "filter", "add", "dev", dev,
		"protocol", "ipv6", "parent", "1:", "prio", "2",
		"u32", "match", "ip6", "src", "::/0", "flowid", "1:99")
	if output, err := ipv6Cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add IPv6 base filter: %v, output: %s", err, string(output))
	}
	
	logger.Logger.Printf("Successfully added IPv6 support to %s", dev)
	return nil
}

// AddDualStackSupport adds both IPv4 and IPv6 filter support to the qdisc
func AddDualStackSupport(dev string) error {
	// Add IPv4 base filter at priority 1 to establish IPv4 filter chain
	ipv4Cmd := exec.Command(config.TCPath, "filter", "add", "dev", dev,
		"protocol", "ip", "parent", "1:", "prio", "1",
		"u32", "match", "u32", "0", "0", "flowid", "1:99")
	if output, err := ipv4Cmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("WARNING: Could not add IPv4 base filter: %v, output: %s", err, string(output))
	}
	
	// Add IPv6 base filter at priority 2 (different from IPv4 priority)
	// IPv6 and IPv4 cannot share the same priority level
	// Use ip6 src ::/0 to match all IPv6 traffic (correct IPv6 syntax)
	ipv6Cmd := exec.Command(config.TCPath, "filter", "add", "dev", dev,
		"protocol", "ipv6", "parent", "1:", "prio", "2",
		"u32", "match", "ip6", "src", "::/0", "flowid", "1:99")
	if output, err := ipv6Cmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("WARNING: Could not add IPv6 base filter at priority 2: %v, output: %s", err, string(output))
		// Don't return error - IPv6 might not be supported on this system
	}
	
	logger.Logger.Printf("Successfully added dual-stack support to qdisc on %s", dev)
	return nil
}

// CheckAndSetupRootQdisc checks for existing qdisc and creates one if needed
func CheckAndSetupRootQdisc(dev string) error {
	return CheckAndSetupRootQdiscWithIPv6(dev, "")
}

// CheckAndSetupRootQdiscWithIPv6 checks for existing qdisc and creates one if needed, with IPv6 support if required
func CheckAndSetupRootQdiscWithIPv6(dev, allowedIP string) error {
	// Lock to prevent concurrent access to the same interface
	interfaceMutex.Lock()
	defer interfaceMutex.Unlock()

	logger.Logger.Printf("Acquired lock for interface %s", dev)

	// Check current qdisc
	checkCmd := exec.Command(config.TCPath, "qdisc", "show", "dev", dev)
	output, err := checkCmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to check qdisc on %s: %v", dev, err)
	}

	outputStr := string(output)

	// If the desired qdisc already exists, we're done
	if strings.Contains(outputStr, "qdisc "+config.SchedulerType) {
		logger.Logger.Printf("Desired %s qdisc already exists on %s, preserving existing setup", config.SchedulerType, dev)
		return nil
	}

	// Check if any other qdisc exists (excluding noqueue which is default)
	hasQdisc := false
	existingQdiscType := ""

	// Parse qdisc output to find existing qdisc type
	lines := strings.Split(outputStr, "\n")
	for _, line := range lines {
		if strings.Contains(line, "qdisc") && strings.Contains(line, "root") && !strings.Contains(line, "qdisc noqueue") {
			// Extract qdisc type
			parts := strings.Fields(line)
			if len(parts) >= 2 && parts[0] == "qdisc" {
				existingQdiscType = parts[1]
				hasQdisc = true
				break
			}
		}
	}

	// If another qdisc exists, check if it has active classes before deciding to preserve or swap
	if hasQdisc && existingQdiscType != "" && existingQdiscType != config.SchedulerType {
		// Check if the existing qdisc has any active classes (peers with rate limits)
		classCmd := exec.Command(config.TCPath, "class", "show", "dev", dev)
		classOutput, classErr := classCmd.CombinedOutput()

		hasActiveClasses := false
		if classErr == nil {
			classStr := string(classOutput)
			// Check for any class definitions (excluding the root/default class)
			// Look for patterns like "class htb 1:XXX" or "class hfsc 1:XXX" where XXX is not 99 (default)
			lines := strings.Split(classStr, "\n")
			for _, line := range lines {
				if strings.Contains(line, "class ") && !strings.Contains(line, "1:99") && !strings.Contains(line, "root") {
					hasActiveClasses = true
					break
				}
			}
		}

		if hasActiveClasses {
			// Qdisc has active classes from other peers, preserve it
			logger.Logger.Printf("WARNING: Interface %s has %s qdisc but -scheduler %s was specified",
				dev, existingQdiscType, config.SchedulerType)
			logger.Logger.Printf("INFO: Preserving existing %s qdisc (has active peer rate limits)", existingQdiscType)
			logger.Logger.Printf("TIP: Remove all peer rate limits first or use --nuke to switch scheduler types")

			// Override the global schedulerType to use the existing one
			config.SchedulerType = existingQdiscType
			logger.Logger.Printf("Using existing %s qdisc for rate limiting operations", config.SchedulerType)
			return nil
		} else {
			// Qdisc exists but has no active classes, safe to swap
			logger.Logger.Printf("INFO: Found existing %s qdisc on %s with no active classes", existingQdiscType, dev)
			logger.Logger.Printf("INFO: Swapping to %s qdisc as requested", config.SchedulerType)

			// Remove the empty qdisc
			delCmd := exec.Command(config.TCPath, "qdisc", "del", "dev", dev, "root")
			if delOutput, delErr := delCmd.CombinedOutput(); delErr != nil {
				logger.Logger.Printf("WARNING: Could not remove existing qdisc: %v, output: %s", delErr, string(delOutput))
			} else {
				logger.Logger.Printf("Successfully removed empty %s qdisc from %s", existingQdiscType, dev)
			}

			// Wait for deletion to take effect
			time.Sleep(100 * time.Millisecond)
			// Fall through to create new qdisc below
		}
	}

	logger.Logger.Printf("Setting up %s qdisc on %s...", config.SchedulerType, dev)

	// Try to set up the new qdisc
	err = SetupRootQdisc(dev)
	if err == nil {
		return nil
	}

	// If we still get exclusivity flag error, try removing and retrying
	if strings.Contains(err.Error(), "Exclusivity flag on") || strings.Contains(err.Error(), "File exists") {
		logger.Logger.Printf("Exclusivity flag detected, attempting forced cleanup and retry...")

		// Force remove any existing qdisc
		exec.Command(config.TCPath, "qdisc", "del", "dev", dev, "root").Run()
		exec.Command(config.TCPath, "qdisc", "del", "dev", dev, "ingress").Run()

		// Wait and retry
		time.Sleep(500 * time.Millisecond)

		err = SetupRootQdisc(dev)
		if err == nil {
			return nil
		}
	}

	return fmt.Errorf("failed to set up qdisc on %s: %v", dev, err)
}

// SetupRootQdisc creates the qdisc on the given device with better error handling
func SetupRootQdisc(dev string) error {
	var cmd *exec.Cmd
	switch config.SchedulerType {
	case "cake":
		logger.Logger.Printf("Setting up root CAKE qdisc on %s...", dev)
		cmd = exec.Command(config.TCPath, "qdisc", "add", "dev", dev,
			"root", "handle", "1:", "cake", "bandwidth", "1Gbit", "besteffort")

		_, err := cmd.CombinedOutput()
		if err != nil {
			// CAKE not available, fall back to HTB
			logger.Logger.Printf("CAKE not available, falling back to HTB: %v", err)
			cmd = exec.Command(config.TCPath, "qdisc", "add", "dev", dev,
				"root", "handle", "1:", "htb", "default", "99")
		} else {
			logger.Logger.Printf("Successfully set up CAKE qdisc on %s", dev)
			return nil
		}
	case "hfsc":
		logger.Logger.Printf("Setting up root HFSC qdisc on %s...", dev)
		cmd = exec.Command(config.TCPath, "qdisc", "add", "dev", dev,
			"root", "handle", "1:", "hfsc", "default", "99")
	default:
		logger.Logger.Printf("Setting up root HTB qdisc on %s...", dev)
		cmd = exec.Command(config.TCPath, "qdisc", "add", "dev", dev,
			"root", "handle", "1:", "htb", "default", "99")
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to set up root qdisc on %s: %v\nOutput: %s", dev, err, output)
	}

	// Add dual-stack support immediately after creating the qdisc
	if err := AddDualStackSupport(dev); err != nil {
		logger.Logger.Printf("WARNING: Could not add dual-stack support: %v", err)
	}

	logger.Logger.Printf("Successfully set up root qdisc on %s", dev)
	return nil
}

// NukeInterface removes all traffic control qdiscs from the specified interface
func NukeInterface(dev string) error {
	// Lock to prevent concurrent access to the same interface
	interfaceMutex.Lock()
	defer interfaceMutex.Unlock()

	logger.Logger.Printf("Acquired lock for nuking interface %s", dev)
	logger.Logger.Printf("Nuking all traffic control on interface %s...", dev)

	// Calculate the corresponding IFB device name
	ifbDev := fmt.Sprintf(config.IFBFormat, dev)

	// First try to remove ingress qdisc
	ingressCmd := exec.Command(config.TCPath, "qdisc", "del", "dev", dev, "ingress")
	if output, err := ingressCmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("NOTE: Removing ingress qdisc returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Logger.Printf("Successfully removed ingress qdisc from %s", dev)
	}

	// Then remove root qdisc (this will remove all classes and filters)
	rootCmd := exec.Command(config.TCPath, "qdisc", "del", "dev", dev, "root")
	if output, err := rootCmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("NOTE: Removing root qdisc returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Logger.Printf("Successfully removed root qdisc from %s", dev)
	}

	// Clean up the corresponding IFB device
	// First remove its qdisc
	ifbQdiscCmd := exec.Command(config.TCPath, "qdisc", "del", "dev", ifbDev, "root")
	if output, err := ifbQdiscCmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("NOTE: Removing IFB qdisc returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Logger.Printf("Successfully removed root qdisc from IFB device %s", ifbDev)
	}

	// Then try to remove the IFB device itself
	ifbCmd := exec.Command("ip", "link", "del", ifbDev)
	if output, err := ifbCmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("NOTE: Removing IFB device returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Logger.Printf("Successfully removed IFB device %s", ifbDev)
	}

	return nil
}
