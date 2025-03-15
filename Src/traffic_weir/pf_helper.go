package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
)

type PFHelper struct {
	pfctlPath string
	logger    *log.Logger
}

// PFQueueConfig holds configuration for a PF queue
type PFQueueConfig struct {
	Name        string
	Interface   string
	Bandwidth   int64 // in Kbps
	IsDefault   bool
	Priority    int
	ParentQueue string
	BurstSize   int64 // in KB
	FlowID      string
}

// NewPFHelper creates a new PF helper instance
func NewPFHelper(logger *log.Logger) (*PFHelper, error) {
	pfctlPath := "/sbin/pfctl"
	if _, err := os.Stat(pfctlPath); err != nil {
		return nil, fmt.Errorf("pfctl not found at %s: %v", pfctlPath, err)
	}

	return &PFHelper{
		pfctlPath: pfctlPath,
		logger:    logger,
	}, nil
}

// SetupTrafficShaping configures PF traffic shaping for a peer
func (pf *PFHelper) SetupTrafficShaping(iface, allowedIP string, uploadRate, downloadRate int64) error {
	pf.logger.Printf("Setting up PF traffic shaping on %s for IP %s (up: %d, down: %d)",
		iface, allowedIP, uploadRate, downloadRate)

	// Create temporary PF configuration file
	tmpFile, err := os.CreateTemp("", "pf-conf-*")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Generate configuration
	config, err := pf.generateConfig(iface, allowedIP, uploadRate, downloadRate)
	if err != nil {
		return fmt.Errorf("failed to generate PF config: %v", err)
	}

	// Write configuration
	if _, err := tmpFile.WriteString(config); err != nil {
		return fmt.Errorf("failed to write PF config: %v", err)
	}
	tmpFile.Close()

	// Load the configuration
	if err := pf.loadConfig(tmpFile.Name()); err != nil {
		return fmt.Errorf("failed to load PF config: %v", err)
	}

	return nil
}

// generateConfig creates the PF configuration string
func (pf *PFHelper) generateConfig(iface, allowedIP string, uploadRate, downloadRate int64) (string, error) {
	var config strings.Builder

	// ALTQ configuration
	totalBandwidth := max(uploadRate, downloadRate)
	config.WriteString(fmt.Sprintf("altq on %s cbq bandwidth %dKb queue { root_queue }\n",
		iface, totalBandwidth))

	// Root queue
	config.WriteString(fmt.Sprintf("queue root_queue cbq(default) { upload_queue, download_queue }\n"))

	// Upload queue
	if uploadRate > 0 {
		config.WriteString(fmt.Sprintf("queue upload_queue bandwidth %dKb priority 1\n", uploadRate))
	}

	// Download queue
	if downloadRate > 0 {
		config.WriteString(fmt.Sprintf("queue download_queue bandwidth %dKb priority 1\n", downloadRate))
	}

	// Traffic rules
	isIPv6 := strings.Contains(allowedIP, ":")
	family := "inet"
	if isIPv6 {
		family = "inet6"
	}

	if uploadRate > 0 {
		config.WriteString(fmt.Sprintf("pass in quick on %s from %s to any family %s queue upload_queue\n",
			iface, allowedIP, family))
	}
	if downloadRate > 0 {
		config.WriteString(fmt.Sprintf("pass out quick on %s from any to %s family %s queue download_queue\n",
			iface, allowedIP, family))
	}

	return config.String(), nil
}

// loadConfig loads a PF configuration file
func (pf *PFHelper) loadConfig(configFile string) error {
	// First, try to enable PF if it's not already enabled
	enableCmd := exec.Command(pf.pfctlPath, "-e")
	if err := enableCmd.Run(); err != nil {
		pf.logger.Printf("Note: PF enable returned: %v (may already be enabled)", err)
	}

	// Load the configuration
	loadCmd := exec.Command(pf.pfctlPath, "-f", configFile)
	if output, err := loadCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to load PF config: %v, output: %s", err, output)
	}

	return nil
}

// RemoveTrafficShaping removes traffic shaping rules for a peer
func (pf *PFHelper) RemoveTrafficShaping(iface, allowedIP string) error {
	pf.logger.Printf("Removing PF traffic shaping for IP %s on %s", allowedIP, iface)

	// Create temporary file for minimal config
	tmpFile, err := os.CreateTemp("", "pf-clean-*")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	// Write minimal configuration that removes queues
	minConfig := fmt.Sprintf("altq on %s cbq bandwidth 1000Mb queue { default_queue }\n"+
		"queue default_queue cbq(default)\n", iface)
	if _, err := tmpFile.WriteString(minConfig); err != nil {
		return fmt.Errorf("failed to write minimal config: %v", err)
	}
	tmpFile.Close()

	// Load the minimal configuration
	if err := pf.loadConfig(tmpFile.Name()); err != nil {
		return fmt.Errorf("failed to load minimal config: %v", err)
	}

	return nil
}

// NukeAllRules removes all PF rules and queues
func (pf *PFHelper) NukeAllRules() error {
	pf.logger.Printf("Removing all PF rules and queues")

	// Flush all rules
	flushCmd := exec.Command(pf.pfctlPath, "-F", "all")
	if output, err := flushCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to flush PF rules: %v, output: %s", err, output)
	}

	return nil
}

// GetQueueStats retrieves current queue statistics
func (pf *PFHelper) GetQueueStats(iface string) (string, error) {
	cmd := exec.Command(pf.pfctlPath, "-vvq", "-i", iface)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("failed to get queue stats: %v", err)
	}
	return string(output), nil
}

func max(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}
