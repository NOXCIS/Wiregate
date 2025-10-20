package scheduler

import (
	"fmt"
	"os/exec"
	"strings"

	"traffic-weir/config"
	"traffic-weir/logger"
)

// SetupCAKEPerPeerLimits sets up per-peer rate limiting on top of CAKE
func SetupCAKEPerPeerLimits(iface, allowedIP string, downloadRate, uploadRate int64) error {
	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	// Add ingress qdisc for download policing
	if downloadRate > 0 {
		ingressCmd := exec.Command(config.TCPath, "qdisc", "add", "dev", iface, "ingress")
		ingressCmd.Run() // Ignore errors as it might already exist

		rateBits := downloadRate * 1000
		burst := downloadRate * 125 // 1ms worth of traffic

		// Add download policing filter
		downloadFilterCmd := exec.Command(config.TCPath, "filter", "add", "dev", iface,
			"parent", "ffff:", "protocol", protocol, "prio", "1",
			"u32", "match", matchType, "dst", ipOnly,
			"police", "rate", fmt.Sprintf("%dbit", rateBits),
			"burst", fmt.Sprintf("%d", burst),
			"drop", "flowid", ":1")

		if output, err := downloadFilterCmd.CombinedOutput(); err != nil {
			return fmt.Errorf("failed to add CAKE download filter: %v, output: %s", err, output)
		}
		logger.Logger.Printf("Successfully added CAKE download filter for %s", ipOnly)
	}

	// Add upload policing filter on the CAKE qdisc
	if uploadRate > 0 {
		rateBits := uploadRate * 1000
		burst := uploadRate * 125

		// Add upload policing filter
		uploadFilterCmd := exec.Command(config.TCPath, "filter", "add", "dev", iface,
			"parent", "1:", "protocol", protocol, "prio", "1",
			"u32", "match", matchType, "src", ipOnly,
			"police", "rate", fmt.Sprintf("%dbit", rateBits),
			"burst", fmt.Sprintf("%d", burst),
			"drop", "flowid", ":1")

		if output, err := uploadFilterCmd.CombinedOutput(); err != nil {
			return fmt.Errorf("failed to add CAKE upload filter: %v, output: %s", err, output)
		}
		logger.Logger.Printf("Successfully added CAKE upload filter for %s", ipOnly)
	}

	return nil
}

// RemoveCAKERateLimit removes CAKE-based rate limiting for a peer
func RemoveCAKERateLimit(iface, allowedIP string) error {
	logger.Logger.Printf("Removing CAKE rate limiting for IP %s", allowedIP)

	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	// Remove download filters (ingress)
	downloadCmd := exec.Command(config.TCPath, "filter", "del", "dev", iface,
		"parent", "ffff:", "protocol", protocol, "prio", "1",
		"u32", "match", matchType, "dst", ipOnly)
	downloadCmd.Run() // Ignore errors

	// Remove upload filters (egress)
	uploadCmd := exec.Command(config.TCPath, "filter", "del", "dev", iface,
		"parent", "1:", "protocol", protocol, "prio", "1",
		"u32", "match", matchType, "src", ipOnly)
	uploadCmd.Run() // Ignore errors

	// Note: We don't remove the CAKE qdisc itself as it might be used by other peers
	// The CAKE qdisc will continue to work for other flows

	logger.Logger.Printf("Successfully removed CAKE rate limiting for %s", ipOnly)
	return nil
}
