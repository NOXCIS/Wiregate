package scheduler

import (
	"context"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"

	"traffic-weir/config"
	"traffic-weir/logger"
)

// Global mutex for scheduler operations to prevent race conditions
var schedulerMutex sync.Mutex

// CreateClass creates (or changes) a traffic class on the specified device.
func CreateClass(dev, classID string, rateKbps int64) error {
	// Lock to prevent concurrent class creation
	schedulerMutex.Lock()
	defer schedulerMutex.Unlock()

	logger.Logger.Printf("Acquired scheduler lock for device %s", dev)

	// Validate rate before creating class
	rate, err := ValidateRate(rateKbps)
	if err != nil {
		return fmt.Errorf("invalid rate for class creation: %v", err)
	}

	rateBits := rate * 1000 // Convert Kb/s to bits/s

	// Parse just the numeric part after the colon
	parts := strings.Split(classID, ":")
	if len(parts) != 2 {
		return fmt.Errorf("invalid class ID format: must be in format 'handle:number'")
	}

	classNum, err := strconv.ParseInt(parts[1], 16, 64)
	if err != nil {
		return fmt.Errorf("invalid class number: %v", err)
	}

	// Format class ID in proper hexadecimal format (1:xxxx where xxxx is a 4-digit hex number)
	classIDHex := fmt.Sprintf("1:%04x", classNum)
	logger.Logger.Printf("Creating class on device %s with classID %s and rate %d Kbps", dev, classIDHex, rate)

	switch config.SchedulerType {
	case "cake":
		// CAKE doesn't use classes - it manages flows automatically
		// We'll use filters to redirect traffic to CAKE with bandwidth limits
		logger.Logger.Printf("CAKE scheduler doesn't use classes - using filter-based rate limiting")
		return nil
	case "hfsc":
		modifyCmd := exec.Command(config.TCPath, "class", "change", "dev", dev,
			"parent", "1:", "classid", classIDHex,
			"hfsc", "sc", "rate", fmt.Sprintf("%dbit", rateBits),
			"ul", "rate", fmt.Sprintf("%dbit", rateBits))
		if err := modifyCmd.Run(); err != nil {
			createCmd := exec.Command(config.TCPath, "class", "add", "dev", dev,
				"parent", "1:", "classid", classIDHex,
				"hfsc", "sc", "rate", fmt.Sprintf("%dbit", rateBits),
				"ul", "rate", fmt.Sprintf("%dbit", rateBits))
			output, err := createCmd.CombinedOutput()
			if err != nil {
				return fmt.Errorf("failed to add hfsc traffic class on %s: %v\nOutput: %s", dev, err, output)
			}
		}
	default:
		modifyCmd := exec.Command(config.TCPath, "class", "change", "dev", dev,
			"parent", "1:", "classid", classIDHex,
			"htb", "rate", fmt.Sprintf("%dbit", rateBits),
			"burst", "15k", "ceil", fmt.Sprintf("%dbit", rateBits))
		if err := modifyCmd.Run(); err != nil {
			createCmd := exec.Command(config.TCPath, "class", "add", "dev", dev,
				"parent", "1:", "classid", classIDHex,
				"htb", "rate", fmt.Sprintf("%dbit", rateBits),
				"burst", "15k", "ceil", fmt.Sprintf("%dbit", rateBits))
			output, err := createCmd.CombinedOutput()
			if err != nil {
				return fmt.Errorf("failed to add htb traffic class on %s: %v\nOutput: %s", dev, err, output)
			}
		}
	}
	logger.Logger.Printf("Successfully created class %s on device %s", classIDHex, dev)
	return nil
}

// TryAddFiltersForIP adds u32 filters on the given device.
// For upload (uploadRate > 0) it matches src IP; for download (downloadRate > 0) it matches dst IP.
func TryAddFiltersForIP(dev, classID, peer string, uploadRate, downloadRate int64) error {
	logger.Logger.Printf("Adding filters on device %s for peer %s (upload: %d, download: %d)",
		dev, peer, uploadRate, downloadRate)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	ipOnly := strings.Split(peer, "/")[0]
	protocol := "ip"
	matchType := "ip"
	priority := "1" // IPv4 uses priority 1

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
		priority = "2" // IPv6 uses priority 2 (different from IPv4)
	}

	if uploadRate > 0 {
		logger.Logger.Printf("Adding upload filter for %s on %s", ipOnly, dev)
		filterCmd := exec.CommandContext(ctx, config.TCPath, "filter", "add", "dev", dev,
			"protocol", protocol, "parent", "1:", "prio", priority,
			"u32", "match", matchType, "src", ipOnly,
			"flowid", classID)
		if output, err := filterCmd.CombinedOutput(); err != nil {
			logger.Logger.Printf("Failed upload filter command: %s %s", config.TCPath,
				strings.Join(filterCmd.Args[1:], " "))
			return fmt.Errorf("failed to add upload filter on %s: %v\nCommand output: %s",
				dev, err, string(output))
		}
		logger.Logger.Printf("Successfully added upload filter for %s on %s", ipOnly, dev)
	}

	if downloadRate > 0 {
		logger.Logger.Printf("Adding download filter for %s on %s", ipOnly, dev)
		filterCmd := exec.CommandContext(ctx, config.TCPath, "filter", "add", "dev", dev,
			"protocol", protocol, "parent", "1:", "prio", priority,
			"u32", "match", matchType, "dst", ipOnly,
			"flowid", classID)
		if output, err := filterCmd.CombinedOutput(); err != nil {
			logger.Logger.Printf("Failed download filter command: %s %s", config.TCPath,
				strings.Join(filterCmd.Args[1:], " "))
			return fmt.Errorf("failed to add download filter on %s: %v\nCommand output: %s",
				dev, err, string(output))
		}
		logger.Logger.Printf("Successfully added download filter for %s on %s", ipOnly, dev)
	}

	if strings.Contains(ipOnly, ":") {
		if err := SetupIPv6Filters(dev, classID, peer); err != nil {
			return fmt.Errorf("failed to set up IPv6 filters on %s: %v", dev, err)
		}
	}

	logger.Logger.Printf("Successfully added all filters for peer %s on device %s", peer, dev)
	return nil
}

// SetupIPv6Filters adds IPv6-specific filters if needed.
func SetupIPv6Filters(dev, classID, peer string) error {
	ipOnly := strings.Split(peer, "/")[0]
	if !strings.Contains(ipOnly, ":") {
		return nil
	}
	cmd := exec.Command(config.TCPath, "filter", "add", "dev", dev,
		"protocol", "ipv6",
		"parent", "1:", "prio", "2",
		"u32", "match", "ip6", "src", ipOnly,
		"flowid", classID)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add IPv6 filter on %s: %v", dev, err)
	}
	return nil
}

// ValidateRate checks if the rate is within supported bounds
func ValidateRate(rate int64) (int64, error) {
	if rate < 0 {
		return 0, fmt.Errorf("rate cannot be negative")
	}

	maxRate := int64(config.MaxRate32)
	if config.Supports64Bit {
		maxRate = config.MaxRate64
	}

	if rate == 0 {
		return maxRate, nil // Convert 0 (unlimited) to max supported rate
	}

	if rate > maxRate {
		return 0, fmt.Errorf("rate %d exceeds maximum supported rate %d", rate, maxRate)
	}

	return rate, nil
}

// Detect64BitSupport checks if the kernel supports 64-bit rate limits
func Detect64BitSupport() bool {
	// Try to create a test class with a rate higher than 32-bit max
	testDev := "lo" // Use loopback device for testing
	testRate := int64(config.MaxRate32 + 1)

	cmd := exec.Command(config.TCPath, "class", "add", "dev", testDev,
		"parent", "1:", "classid", "1:999",
		"htb", "rate", fmt.Sprintf("%dbit", testRate*1000))

	output, err := cmd.CombinedOutput()

	// Clean up test class regardless of result
	cleanup := exec.Command(config.TCPath, "class", "del", "dev", testDev, "classid", "1:999")
	cleanup.Run()

	if err != nil {
		// Check if error is specifically about 32-bit overflow
		if strings.Contains(string(output), "invalid rate") ||
			strings.Contains(string(output), "overflow") {
			logger.Logger.Printf("Detected 32-bit rate limit support")
			return false
		}
	}

	logger.Logger.Printf("Detected 64-bit rate limit support")
	return true
}

// GetSystemCapabilities returns the system's traffic control capabilities
func GetSystemCapabilities() config.SystemCapabilities {
	maxRate := int64(config.MaxRate32)
	if config.Supports64Bit {
		maxRate = config.MaxRate64
	}
	return config.SystemCapabilities{
		Supports64BitRates: config.Supports64Bit,
		MaximumRate:        maxRate,
		SchedulerType:      config.SchedulerType,
	}
}
