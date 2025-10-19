package scheduler

import (
	"fmt"
	"hash/fnv"
	"os/exec"
	"strings"
	"time"

	"traffic-weir/config"
	"traffic-weir/logger"
)

// RemovePeerRateLimitOnDevice removes filters and classes for a given peer on a specified device.
func RemovePeerRateLimitOnDevice(dev, allowedIP, peerKey string) error {
	logger.Logger.Printf("Removing rate limits on device %s for peer %s (IP: %s)", dev, peerKey, allowedIP)

	// Calculate class IDs
	classBase := PeerToClassBase(peerKey)
	uploadClassID := fmt.Sprintf("1:%x1", classBase)
	downloadClassID := fmt.Sprintf("1:%x2", classBase)

	logger.Logger.Printf("Calculated class IDs: upload=%s, download=%s", uploadClassID, downloadClassID)

	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"
	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	// Multiple attempts for removal
	maxAttempts := 3
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		if attempt > 1 {
			logger.Logger.Printf("Attempt %d of %d to remove filters and classes", attempt, maxAttempts)
		}

		if !strings.HasPrefix(dev, "ifb-") {
			// Main interface: Handle download filters and class
			logger.Logger.Printf("Removing download filters for IP %s on %s", ipOnly, dev)

			// First remove all matching filters - try multiple approaches
			output, _ := exec.Command(config.TCPath, "filter", "show", "dev", dev, "parent", "1:").CombinedOutput()
			filters := ParseFilterOutput(string(output), ipOnly)
			logger.Logger.Printf("Found %d filters to remove on %s for IP %s", len(filters), dev, ipOnly)

			// Remove filters by handle
			for _, handle := range filters {
				removeCmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
					"parent", "1:", "handle", handle, "prio", "1",
					"protocol", protocol)
				if output, err := removeCmd.CombinedOutput(); err != nil {
					logger.Logger.Printf("Warning: Error removing filter handle %s: %v, output: %s", handle, err, string(output))
				} else {
					logger.Logger.Printf("Successfully removed filter handle %s", handle)
				}
			}

			// Also try to remove filters by matching criteria (more aggressive approach)
			removeByMatchCmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
				"parent", "1:", "protocol", protocol, "prio", "1",
				"u32", "match", matchType, "dst", ipOnly)
			if output, err := removeByMatchCmd.CombinedOutput(); err != nil {
				logger.Logger.Printf("Note: Filter removal by match criteria returned: %v, output: %s (may not exist)", err, string(output))
			} else {
				logger.Logger.Printf("Successfully removed filters by match criteria")
			}

			// Check if class exists before trying to remove it
			checkCmd := exec.Command(config.TCPath, "class", "show", "dev", dev)
			checkOutput, _ := checkCmd.CombinedOutput()
			classExists := strings.Contains(string(checkOutput), downloadClassID)

			if classExists {
				// Wait a bit for filters to be fully processed
				time.Sleep(200 * time.Millisecond)

				// Then remove the class
				logger.Logger.Printf("Removing download class %s on main interface", downloadClassID)
				classCmd := exec.Command(config.TCPath, "class", "del", "dev", dev, "classid", downloadClassID)
				if output, err := classCmd.CombinedOutput(); err != nil {
					logger.Logger.Printf("Warning: Error removing class %s: %v, output: %s", downloadClassID, err, string(output))

					// If class is "in use", try to force remove it by first removing all filters again
					if strings.Contains(string(output), "in use") {
						logger.Logger.Printf("Class %s is in use, attempting to remove remaining filters", downloadClassID)

						// Try to remove any remaining filters that might be using this class
						forceRemoveCmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
							"parent", "1:", "protocol", protocol, "prio", "1",
							"u32", "match", matchType, "dst", ipOnly)
						forceRemoveCmd.Run() // Ignore errors

						// Wait and try class removal again
						time.Sleep(100 * time.Millisecond)
						classCmd2 := exec.Command(config.TCPath, "class", "del", "dev", dev, "classid", downloadClassID)
						if output2, err2 := classCmd2.CombinedOutput(); err2 != nil {
							logger.Logger.Printf("Warning: Still unable to remove class %s: %v, output: %s", downloadClassID, err2, string(output2))
						} else {
							logger.Logger.Printf("Successfully removed class %s on second attempt", downloadClassID)
						}
					}
				} else {
					logger.Logger.Printf("Successfully removed class %s", downloadClassID)
				}

				// Verify removal
				verifyCmd := exec.Command(config.TCPath, "class", "show", "dev", dev)
				verifyOutput, _ := verifyCmd.CombinedOutput()
				if strings.Contains(string(verifyOutput), downloadClassID) {
					if attempt == maxAttempts {
						logger.Logger.Printf("Class %s still exists after removal attempts, but continuing", downloadClassID)
						// Don't fail here, just log and continue
					} else {
						time.Sleep(100 * time.Millisecond)
						continue
					}
				}
			} else {
				logger.Logger.Printf("Class %s does not exist on %s, skipping removal", downloadClassID, dev)
			}
		} else {
			// IFB device: Handle upload filters and class
			logger.Logger.Printf("Removing upload filters for IP %s on %s", ipOnly, dev)

			// Remove all matching filters - try multiple approaches
			output, _ := exec.Command(config.TCPath, "filter", "show", "dev", dev, "parent", "1:").CombinedOutput()
			filters := ParseFilterOutput(string(output), ipOnly)
			logger.Logger.Printf("Found %d filters to remove on %s for IP %s", len(filters), dev, ipOnly)

			// Remove filters by handle
			for _, handle := range filters {
				removeCmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
					"parent", "1:", "handle", handle, "prio", "1",
					"protocol", protocol)
				if output, err := removeCmd.CombinedOutput(); err != nil {
					logger.Logger.Printf("Warning: Error removing filter handle %s: %v, output: %s", handle, err, string(output))
				} else {
					logger.Logger.Printf("Successfully removed filter handle %s", handle)
				}
			}

			// Also try to remove filters by matching criteria (more aggressive approach)
			removeByMatchCmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
				"parent", "1:", "protocol", protocol, "prio", "1",
				"u32", "match", matchType, "src", ipOnly)
			if output, err := removeByMatchCmd.CombinedOutput(); err != nil {
				logger.Logger.Printf("Note: Filter removal by match criteria returned: %v, output: %s (may not exist)", err, string(output))
			} else {
				logger.Logger.Printf("Successfully removed filters by match criteria")
			}

			// Check if class exists before trying to remove it
			checkCmd := exec.Command(config.TCPath, "class", "show", "dev", dev)
			checkOutput, _ := checkCmd.CombinedOutput()
			classExists := strings.Contains(string(checkOutput), uploadClassID)

			if classExists {
				// Wait a bit for filters to be fully processed
				time.Sleep(200 * time.Millisecond)

				// Remove the class
				logger.Logger.Printf("Removing upload class %s on IFB device", uploadClassID)
				classCmd := exec.Command(config.TCPath, "class", "del", "dev", dev, "classid", uploadClassID)
				if output, err := classCmd.CombinedOutput(); err != nil {
					logger.Logger.Printf("Warning: Error removing class %s: %v, output: %s", uploadClassID, err, string(output))

					// If class is "in use", try to force remove it by first removing all filters again
					if strings.Contains(string(output), "in use") {
						logger.Logger.Printf("Class %s is in use, attempting to remove remaining filters", uploadClassID)

						// Try to remove any remaining filters that might be using this class
						forceRemoveCmd := exec.Command(config.TCPath, "filter", "del", "dev", dev,
							"parent", "1:", "protocol", protocol, "prio", "1",
							"u32", "match", matchType, "src", ipOnly)
						forceRemoveCmd.Run() // Ignore errors

						// Wait and try class removal again
						time.Sleep(100 * time.Millisecond)
						classCmd2 := exec.Command(config.TCPath, "class", "del", "dev", dev, "classid", uploadClassID)
						if output2, err2 := classCmd2.CombinedOutput(); err2 != nil {
							logger.Logger.Printf("Warning: Still unable to remove class %s: %v, output: %s", uploadClassID, err2, string(output2))
						} else {
							logger.Logger.Printf("Successfully removed class %s on second attempt", uploadClassID)
						}
					}
				} else {
					logger.Logger.Printf("Successfully removed class %s", uploadClassID)
				}

				// Clean up ingress redirect on the main interface
				realDev := strings.TrimPrefix(dev, "ifb-")
				logger.Logger.Printf("Cleaning up ingress redirect on %s", realDev)

				// Remove all ingress redirect filters
				ingressOutput, _ := exec.Command(config.TCPath, "filter", "show", "dev", realDev, "parent", "ffff:").CombinedOutput()
				ingressFilters := ParseFilterOutput(string(ingressOutput), ipOnly)
				for _, handle := range ingressFilters {
					removeCmd := exec.Command(config.TCPath, "filter", "del", "dev", realDev,
						"parent", "ffff:", "handle", handle, "prio", "1")
					removeCmd.Run() // Ignore errors
				}

				// Verify removal
				verifyCmd := exec.Command(config.TCPath, "class", "show", "dev", dev)
				verifyOutput, _ := verifyCmd.CombinedOutput()
				if strings.Contains(string(verifyOutput), uploadClassID) {
					if attempt == maxAttempts {
						logger.Logger.Printf("Class %s still exists after removal attempts, but continuing", uploadClassID)
						// Don't fail here, just log and continue
					} else {
						time.Sleep(100 * time.Millisecond)
						continue
					}
				}
			} else {
				logger.Logger.Printf("Class %s does not exist on %s, skipping removal", uploadClassID, dev)
			}
		}

		// If we get here, the removal was successful
		break
	}

	// Ensure the default class exists with high bandwidth
	logger.Logger.Printf("Ensuring default class exists on %s", dev)
	defaultCmd := exec.Command(config.TCPath, "class", "replace", "dev", dev,
		"parent", "1:", "classid", "1:99",
		config.SchedulerType, "rate", fmt.Sprintf("%d000bit", config.MaxRate64))
	defaultCmd.Run() // Ignore errors
	logger.Logger.Printf("Default class verified on %s", dev)

	logger.Logger.Printf("Completed removal of rate limits on device %s for peer %s", dev, peerKey)
	return nil
}

// PeerToClassBase converts the peer string into a base number that will result in a valid
// hexadecimal class ID when combined with a suffix.
// The class ID in TC must be a 16-bit hexadecimal number (0x0001-0xffff).
// We'll use the first 3 hex digits (0x001-0xfff) for the base, leaving the last digit
// for the class type (1 for upload, 2 for download).
func PeerToClassBase(peer string) int {
	h := fnv.New64a()
	_, _ = h.Write([]byte(peer))
	// Use modulo 0xfff (4095) to ensure we only use the first 3 hex digits
	return int(h.Sum64() % 0xfff)
}
