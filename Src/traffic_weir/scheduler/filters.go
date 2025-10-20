package scheduler

import (
	"fmt"
	"os/exec"
	"strings"

	"traffic-weir/config"
	"traffic-weir/logger"
)

// RemoveFilter removes u32 filters for the given peer (matched by allowed IP) on a device.
func RemoveFilter(dev, ip string) error {
	ipOnly := strings.Split(ip, "/")[0]
	protocol := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
	}

	// List all filters and find the ones matching our IP
	listCmd := exec.Command(config.TCPath, "filter", "show", "dev", dev, "parent", "1:")
	output, err := listCmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to list filters on %s: %v", dev, err)
	}

	// Parse the output to find filter handles
	filters := ParseFilterOutput(string(output), ipOnly)
	logger.Logger.Printf("Found %d filters to remove on %s for IP %s", len(filters), dev, ipOnly)

	// Remove each matching filter by its handle
	for _, handle := range filters {
		cmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
			"parent", "1:",
			"handle", handle, "prio", "1",
			"protocol", protocol)

		if output, err := cmd.CombinedOutput(); err != nil {
			logger.Logger.Printf("NOTE: Filter removal (handle %s) on %s returned: %v\nOutput: %s (usually safe to ignore)",
				handle, dev, err, string(output))
		} else {
			logger.Logger.Printf("Successfully removed filter handle %s on %s", handle, dev)
		}
	}

	// If we're removing filters from the main interface, also clean up the corresponding IFB device
	if !strings.HasPrefix(dev, "ifb-") {
		ifbDev := fmt.Sprintf(config.IFBFormat, dev)
		if err := RemoveFilter(ifbDev, ip); err != nil {
			logger.Logger.Printf("NOTE: Error removing filter on IFB device %s: %v (usually safe to ignore)", ifbDev, err)
		}
	}

	return nil
}

// ParseFilterOutput parses the output of 'tc filter show' to find filter handles matching our IP
func ParseFilterOutput(output, targetIP string) []string {
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

// AddDefaultFilterOnDevice adds default filters to steer traffic to the unrestricted class (1:99)
func AddDefaultFilterOnDevice(dev, allowedIP string) error {
	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"
	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	// Add default upload filter
	uploadCmd := exec.Command(config.TCPath, "filter", "add", "dev", dev,
		"parent", "1:",
		"protocol", protocol,
		"prio", "9999",
		"u32", "match", matchType, "src", ipOnly,
		"flowid", "1:99")
	if output, err := uploadCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add default upload filter on %s: %v, output: %s", dev, err, output)
	}

	// Add default download filter
	downloadCmd := exec.Command(config.TCPath, "filter", "add", "dev", dev,
		"parent", "1:",
		"protocol", protocol,
		"prio", "9999",
		"u32", "match", matchType, "dst", ipOnly,
		"flowid", "1:99")
	if output, err := downloadCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add default download filter on %s: %v, output: %s", dev, err, output)
	}
	return nil
}
