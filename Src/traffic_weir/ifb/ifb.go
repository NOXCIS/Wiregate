package ifb

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"time"

	"traffic-weir/config"
	"traffic-weir/logger"
	"traffic-weir/qdisc"
)

// CheckIFBSupport checks if IFB is supported on the system
func CheckIFBSupport() bool {
	// Check if the IFB module is available
	if _, err := os.Stat("/sys/module/ifb"); err == nil {
		return true
	}

	// Try to load the IFB module
	modprobeCmd := exec.Command("modprobe", "ifb")
	if err := modprobeCmd.Run(); err == nil {
		return true
	}

	// Check if we can create an IFB device
	testCmd := exec.Command("ip", "link", "add", "test_ifb", "type", "ifb")
	if err := testCmd.Run(); err == nil {
		// Clean up the test device
		exec.Command("ip", "link", "del", "test_ifb").Run()
		return true
	}

	return false
}

// SetupIFB creates and brings up the IFB device if it doesn't already exist.
func SetupIFB(realDev string) error {
	// Create IFB device name based on interface
	ifbDev := fmt.Sprintf(config.IFBFormat, realDev)
	logger.Logger.Printf("Setting up IFB device %s for interface %s", ifbDev, realDev)

	// Check if IFB is supported
	if !CheckIFBSupport() {
		return fmt.Errorf("IFB is not supported on this system")
	}

	// Check if the IFB device exists
	if _, err := exec.Command("ip", "link", "show", ifbDev).CombinedOutput(); err != nil {
		logger.Logger.Printf("IFB device %s does not exist, creating...", ifbDev)
		cmdAdd := exec.Command("ip", "link", "add", ifbDev, "type", "ifb")
		if output, err := cmdAdd.CombinedOutput(); err != nil {
			logger.Logger.Printf("ERROR: Failed to create IFB device: %v\nOutput: %s", err, output)
			return fmt.Errorf("failed to create IFB device %s: %v, output: %s", ifbDev, err, output)
		}
	}

	// Ensure IFB device is up
	cmdUp := exec.Command("ip", "link", "set", "dev", ifbDev, "up")
	if output, err := cmdUp.CombinedOutput(); err != nil {
		logger.Logger.Printf("ERROR: Failed to bring up IFB device: %v\nOutput: %s", err, output)
		return fmt.Errorf("failed to set IFB device %s up: %v, output: %s", ifbDev, err, output)
	}

	// Check if ingress qdisc exists
	ingressExists := false
	if output, err := exec.Command(config.TCPath, "qdisc", "show", "dev", realDev, "ingress").CombinedOutput(); err == nil {
		ingressExists = strings.Contains(string(output), "ingress")
	}

	// Add ingress qdisc only if it doesn't exist
	if !ingressExists {
		logger.Logger.Printf("Adding ingress qdisc to %s", realDev)
		ingressCmd := exec.Command(config.TCPath, "qdisc", "add", "dev", realDev, "handle", "ffff:", "ingress")
		if output, err := ingressCmd.CombinedOutput(); err != nil {
			logger.Logger.Printf("ERROR: Failed to add ingress qdisc: %v\nOutput: %s", err, output)
			return fmt.Errorf("failed to add ingress qdisc on %s: %v", realDev, err)
		}
		// Verify ingress qdisc was created
		time.Sleep(100 * time.Millisecond)
		if output, err := exec.Command(config.TCPath, "qdisc", "show", "dev", realDev, "ingress").CombinedOutput(); err != nil || !strings.Contains(string(output), "ingress") {
			return fmt.Errorf("failed to verify ingress qdisc creation on %s", realDev)
		}
	}

	// Only set up root qdisc if it doesn't exist
	return qdisc.CheckAndSetupRootQdisc(ifbDev)
}

// AddIngressRedirect with improved error handling and verification
func AddIngressRedirect(realDev, allowedIP, ifb string) error {
	logger.Logger.Printf("Adding ingress redirect from %s to %s for IP %s", realDev, ifb, allowedIP)

	// Verify ingress qdisc exists
	if output, err := exec.Command(config.TCPath, "qdisc", "show", "dev", realDev, "ingress").CombinedOutput(); err != nil || !strings.Contains(string(output), "ingress") {
		logger.Logger.Printf("ERROR: Ingress qdisc not found on %s", realDev)
		return fmt.Errorf("ingress qdisc not found on %s", realDev)
	}

	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"
	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	// Remove any existing redirect filters for this IP
	listCmd := exec.Command(config.TCPath, "filter", "show", "dev", realDev, "parent", "ffff:")
	output, _ := listCmd.CombinedOutput()
	filters := parseFilterOutput(string(output), ipOnly)
	for _, handle := range filters {
		removeCmd := exec.Command(config.TCPath, "filter", "del", "dev", realDev,
			"parent", "ffff:", "handle", handle, "prio", "1")
		if output, err := removeCmd.CombinedOutput(); err != nil {
			logger.Logger.Printf("NOTE: Filter removal (handle %s) returned: %v\nOutput: %s",
				handle, err, string(output))
		}
	}

	// Add new redirect filter with retries
	for i := 0; i < 3; i++ {
		filterCmd := exec.Command(config.TCPath, "filter", "add", "dev", realDev,
			"parent", "ffff:",
			"protocol", protocol,
			"prio", "1",
			"u32",
			"match", matchType, "src", ipOnly,
			"action", "mirred", "egress", "redirect", "dev", ifb)

		if output, err := filterCmd.CombinedOutput(); err == nil {
			logger.Logger.Printf("Successfully added ingress redirect")
			return nil
		} else if i == 2 {
			return fmt.Errorf("failed to add ingress redirect filter after retries: %v, output: %s", err, output)
		}
		time.Sleep(100 * time.Millisecond)
	}

	return nil
}

// SetupBasicTCShaping sets up basic traffic shaping without IFB
func SetupBasicTCShaping(dev, allowedIP string, rateKbps int64) error {
	logger.Logger.Printf("Setting up basic tc shaping on %s for IP %s at %d Kbps", dev, allowedIP, rateKbps)

	// Add ingress qdisc
	ingressCmd := exec.Command(config.TCPath, "qdisc", "add", "dev", dev, "ingress")
	if output, err := ingressCmd.CombinedOutput(); err != nil {
		logger.Logger.Printf("NOTE: Adding ingress qdisc returned: %v\nOutput: %s (may already exist)", err, output)
	}

	// Add filter to police incoming traffic
	rateBits := rateKbps * 1000
	burst := rateKbps * 125 // burst size in bytes (roughly 1ms worth of traffic)

	// Determine protocol and match type based on IP version
	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"
	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	filterCmd := exec.Command(config.TCPath, "filter", "add", "dev", dev, "parent", "ffff:",
		"protocol", protocol, "prio", "1", "u32",
		"match", matchType, "src", allowedIP,
		"police", "rate", fmt.Sprintf("%dbit", rateBits),
		"burst", fmt.Sprintf("%d", burst),
		"drop", "flowid", ":1")

	if output, err := filterCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add policing filter: %v, output: %s", err, output)
	}

	return nil
}

// parseFilterOutput parses the output of 'tc filter show' to find filter handles matching our IP
func parseFilterOutput(output, targetIP string) []string {
	var handles []string
	lines := strings.Split(output, "\n")

	var currentHandle string
	for _, line := range lines {
		// Filter handle lines start with "filter"
		if strings.HasPrefix(line, "filter") {
			parts := strings.Fields(line)
			for i, part := range parts {
				if part == "handle" && i+1 < len(parts) {
					currentHandle = parts[i+1]
					break
				}
			}
		}
		// Check if this filter matches our target IP
		if currentHandle != "" && (strings.Contains(line, "match "+targetIP) ||
			strings.Contains(line, "src "+targetIP) ||
			strings.Contains(line, "dst "+targetIP)) {
			handles = append(handles, currentHandle)
			currentHandle = ""
		}
	}

	return handles
}
