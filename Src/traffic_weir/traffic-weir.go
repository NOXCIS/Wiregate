package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"hash/fnv"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const (
	tcPath    = "/sbin/tc"
	ifbFormat = "ifb-%s" // Will be formatted with interface name
	logFile   = "traffic-weir.log"
	// Maximum rates in Kb/s
	maxRate32 = 4194303 // 32-bit max: ~4.2 Gb/s
	maxRate64 = 4194303 // 64-bit max: ~18.4 Pb/s
)

var (
	schedulerType string
	logger        *log.Logger
	supports64Bit bool
	wgPath        string // Dynamic path for wg
	awgPath       string // Dynamic path for awg
)

type PeerInfo struct {
	PublicKey  string
	AllowedIPs []string
}

// Early initialization of logger so that it is available to all init() functions.
func init() {
	// Note: Placing this init immediately ensures logger is set up before other init() functions are executed
	if err := initLogger(); err != nil {
		// If logger initialization fails, write to stderr and continue (or exit if you prefer)
		fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
	}

}

func initLogger() error {
	file, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		return fmt.Errorf("failed to open log file: %v", err)
	}
	logger = log.New(io.MultiWriter(os.Stdout, file), "", log.Ldate|log.Ltime|log.Lmicroseconds)
	return nil
}

func init() {

	// Define common paths based on OS
	var commonPaths []string
	switch runtime.GOOS {
	case "linux":
		commonPaths = []string{
			"/usr/bin",
			"/usr/local/bin",
			"/usr/sbin",
			"/usr/local/sbin",
			"/opt/bin",
			"/opt/local/bin",
		}
	}

	// Find WireGuard executable
	wgNames := []string{"wg", "wireguard-go"}
	if path, err := findExecutable(wgNames, commonPaths); err == nil {
		wgPath = path
		logger.Printf("Found WireGuard at: %s", wgPath)
	} else {
		logger.Printf("WARNING: WireGuard executable not found: %v", err)
	}

	// Find AmneziaWG executable
	awgNames := []string{"awg", "amneziawg"}
	if path, err := findExecutable(awgNames, commonPaths); err == nil {
		awgPath = path
		logger.Printf("Found AmneziaWG at: %s", awgPath)
	} else {
		logger.Printf("WARNING: AmneziaWG executable not found: %v", err)
	}
}

// findExecutable searches for an executable in multiple common locations
func findExecutable(names []string, commonPaths []string) (string, error) {
	// First check if it's in PATH
	for _, name := range names {
		if path, err := exec.LookPath(name); err == nil {
			return path, nil
		}
	}

	// Check common paths
	for _, name := range names {
		for _, basePath := range commonPaths {
			path := filepath.Join(basePath, name)
			if _, err := os.Stat(path); err == nil {
				if err := exec.Command(path, "--version").Run(); err == nil {
					return path, nil
				}
			}
		}
	}

	return "", fmt.Errorf("executable not found in PATH or common locations")
}

// setupCAKEPerPeerLimits sets up per-peer rate limiting on top of CAKE
func setupCAKEPerPeerLimits(iface, allowedIP string, downloadRate, uploadRate int64) error {
	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	matchType := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	// Add ingress qdisc for download policing
	if downloadRate > 0 {
		ingressCmd := exec.Command(tcPath, "qdisc", "add", "dev", iface, "ingress")
		ingressCmd.Run() // Ignore errors as it might already exist

		rateBits := downloadRate * 1000
		burst := downloadRate * 125 // 1ms worth of traffic

		// Add download policing filter
		downloadFilterCmd := exec.Command(tcPath, "filter", "add", "dev", iface,
			"parent", "ffff:", "protocol", protocol, "prio", "1",
			"u32", "match", matchType, "dst", ipOnly,
			"police", "rate", fmt.Sprintf("%dbit", rateBits),
			"burst", fmt.Sprintf("%d", burst),
			"drop", "flowid", ":1")

		if output, err := downloadFilterCmd.CombinedOutput(); err != nil {
			return fmt.Errorf("failed to add CAKE download filter: %v, output: %s", err, output)
		}
		logger.Printf("Successfully added CAKE download filter for %s", ipOnly)
	}

	// Add upload policing filter on the CAKE qdisc
	if uploadRate > 0 {
		rateBits := uploadRate * 1000
		burst := uploadRate * 125

		// Add upload policing filter
		uploadFilterCmd := exec.Command(tcPath, "filter", "add", "dev", iface,
			"parent", "1:", "protocol", protocol, "prio", "1",
			"u32", "match", matchType, "src", ipOnly,
			"police", "rate", fmt.Sprintf("%dbit", rateBits),
			"burst", fmt.Sprintf("%d", burst),
			"drop", "flowid", ":1")

		if output, err := uploadFilterCmd.CombinedOutput(); err != nil {
			return fmt.Errorf("failed to add CAKE upload filter: %v, output: %s", err, output)
		}
		logger.Printf("Successfully added CAKE upload filter for %s", ipOnly)
	}

	return nil
}

// removeCAKERateLimit removes CAKE-based rate limiting for a peer
func removeCAKERateLimit(iface, allowedIP string) error {
	logger.Printf("Removing CAKE rate limiting for IP %s", allowedIP)

	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
	}

	// Remove download filters (ingress)
	downloadCmd := exec.Command(tcPath, "filter", "del", "dev", iface,
		"parent", "ffff:", "protocol", protocol, "prio", "1",
		"u32", "match", "ip", "dst", ipOnly)
	downloadCmd.Run() // Ignore errors

	// Remove upload filters (egress)
	uploadCmd := exec.Command(tcPath, "filter", "del", "dev", iface,
		"parent", "1:", "protocol", protocol, "prio", "1",
		"u32", "match", "ip", "src", ipOnly)
	uploadCmd.Run() // Ignore errors

	// Note: We don't remove the CAKE qdisc itself as it might be used by other peers
	// The CAKE qdisc will continue to work for other flows

	logger.Printf("Successfully removed CAKE rate limiting for %s", ipOnly)
	return nil
}

func main() {
	logger.Printf("Starting traffic-weir...")

	var iface string
	defer func() {
		if r := recover(); r != nil {
			logger.Printf("FATAL: Recovered from panic: %v", r)
			cleanupOnError(iface)
		}
	}()

	var (
		peer         string
		uploadRate   int64
		downloadRate int64
		protocol     string
		remove       bool
		nuke         bool
		allowedIPs   string // New flag for directly specifying allowed IPs
		err          error
	)

	flag.StringVar(&iface, "interface", "", "Interface name")
	flag.StringVar(&peer, "peer", "", "Peer ID")
	flag.Int64Var(&uploadRate, "upload-rate", 0, "Upload rate limit in Kb/s (0 for unlimited)")
	flag.Int64Var(&downloadRate, "download-rate", 0, "Download rate limit in Kb/s (0 for unlimited)")
	flag.StringVar(&protocol, "protocol", "wg", "Protocol (wg or awg)")
	flag.BoolVar(&remove, "remove", false, "Remove rate limits")
	flag.BoolVar(&nuke, "nuke", false, "Remove all traffic control qdiscs from interface")
	flag.StringVar(&schedulerType, "scheduler", "htb", "Traffic scheduler type (htb, hfsc, or cake)")
	flag.StringVar(&allowedIPs, "allowed-ips", "", "Comma-separated list of allowed IPs (optional, overrides peer lookup)") // New flag
	flag.Parse()

	// Add nuke handling early in the execution
	if nuke {
		if iface == "" {
			logger.Printf("ERROR: interface flag is required for nuke operation")
			flag.Usage()
			os.Exit(1)
		}
		if err := nukeInterface(iface); err != nil {
			logger.Printf("ERROR: Failed to nuke interface %s: %v", iface, err)
			os.Exit(1)
		}
		logger.Printf("Successfully nuked all traffic control on interface %s", iface)
		os.Exit(0)
	}

	// Detect 64-bit support before processing rates
	supports64Bit = detect64BitSupport()
	if supports64Bit {
		logger.Printf("System supports 64-bit rate limits")
	} else {
		logger.Printf("System does not support 64-bit rate limits")
	}

	// Add this near the start of main, after supports64Bit is set
	capabilities := getSystemCapabilities()
	logger.Printf("System capabilities: 64-bit rates: %v, max rate: %d Kbps, scheduler: %s",
		capabilities.Supports64BitRates,
		capabilities.MaximumRate,
		capabilities.SchedulerType)

	// Validate and adjust rates
	if uploadRate, err = validateRate(uploadRate); err != nil {
		logger.Printf("ERROR: Invalid upload rate: %v", err)
		os.Exit(1)
	}
	if downloadRate, err = validateRate(downloadRate); err != nil {
		logger.Printf("ERROR: Invalid download rate: %v", err)
		os.Exit(1)
	}

	// Rely solely on the manually selected scheduler type
	logger.Printf("Using manually selected scheduler type: %s", schedulerType)

	logger.Printf("Configuration: interface=%s, peer=%s, upload-rate=%d, download-rate=%d, protocol=%s, remove=%v",
		iface, peer, uploadRate, downloadRate, protocol, remove)

	if iface == "" || peer == "" || protocol == "" {
		logger.Printf("ERROR: interface, peer, and protocol flags are required")
		flag.Usage()
		os.Exit(1)
	}

	if protocol != "wg" && protocol != "awg" {
		logger.Printf("ERROR: Invalid protocol %s. Must be either 'wg' or 'awg'", protocol)
		os.Exit(1)
	}

	if _, err := exec.LookPath(tcPath); err != nil {
		logger.Printf("ERROR: tc command not found at %s. Please install iproute2.", tcPath)
		os.Exit(1)
	}

	// Modified peer info retrieval logic
	logger.Printf("Fetching peer information for %s...", peer)
	var peerInfo *PeerInfo
	if allowedIPs != "" {
		// Use directly provided allowed IPs
		ips := strings.Split(allowedIPs, ",")
		// Trim whitespace from each IP
		for i, ip := range ips {
			ips[i] = strings.TrimSpace(ip)
		}
		peerInfo = &PeerInfo{
			PublicKey:  peer,
			AllowedIPs: ips,
		}
		logger.Printf("Using provided allowed IPs: %v", peerInfo.AllowedIPs)
	} else {
		// Use existing peer lookup logic
		switch protocol {
		case "wg":
			peerInfo, err = getWgPeerInfo(iface, peer)
		case "awg":
			peerInfo, err = getAwgPeerInfo(iface, peer)
		}
		if err != nil {
			logger.Printf("ERROR: Failed to get peer information: %v", err)
			os.Exit(1)
		}
	}

	if len(peerInfo.AllowedIPs) == 0 {
		logger.Printf("ERROR: No allowed IPs found for peer %s", peer)
		os.Exit(1)
	}

	allowedIP := peerInfo.AllowedIPs[0]

	// If remove flag is specified, only remove filters/classes for this peer.
	if remove {
		logger.Printf("Resetting (removing) rate limits for peer %s on interface %s...", peer, iface)

		if schedulerType == "cake" {
			// CAKE uses different removal logic
			if err := removeCAKERateLimit(iface, allowedIP); err != nil {
				logger.Printf("ERROR: Error removing CAKE rate limits: %v", err)
				os.Exit(1)
			}
		} else {
			// Remove filters and classes on main interface (download side)
			if err := removePeerRateLimitOnDevice(iface, allowedIP, peer); err != nil {
				logger.Printf("ERROR: Error removing rate limits on interface: %v", err)
				os.Exit(1)
			}
			// If the IFB device exists, remove upload filters from it.
			if _, err := exec.Command("ip", "link", "show", fmt.Sprintf(ifbFormat, iface)).CombinedOutput(); err == nil {
				if err := removePeerRateLimitOnDevice(fmt.Sprintf(ifbFormat, iface), allowedIP, peer); err != nil {
					logger.Printf("ERROR: Error removing rate limits on IFB device: %v", err)
					os.Exit(1)
				}
				if err := addDefaultFilterOnDevice(fmt.Sprintf(ifbFormat, iface), allowedIP); err != nil {
					logger.Printf("ERROR: Error adding default filter on IFB device: %v", err)
					os.Exit(1)
				}
			}
			// Re-add the default filter on the main interface.
			if err := addDefaultFilterOnDevice(iface, allowedIP); err != nil {
				logger.Printf("ERROR: Error adding default filter on interface: %v", err)
				os.Exit(1)
			}
		}
		logger.Printf("Successfully removed rate limits for peer %s on interface %s", peer, iface)
		os.Exit(0)
	}

	// Remove the cleanup of existing qdisc - we want to preserve existing rules
	logger.Printf("Checking existing traffic control setup on main interface...")

	// Only set up root qdisc if it doesn't exist
	if err := checkAndSetupRootQdisc(iface); err != nil {
		logger.Printf("ERROR: Failed to set up root qdisc: %v", err)
		os.Exit(1)
	}

	// Compute class IDs (different suffixes for upload vs. download)
	classBase := peerToClassBase(peer)
	downloadClassID := fmt.Sprintf("1:%x2", classBase) // download class on main iface
	uploadClassID := fmt.Sprintf("1:%x1", classBase)   // upload class on IFB device

	// Handle CAKE scheduler differently - it replaces the entire qdisc setup
	if schedulerType == "cake" {
		// CAKE qdisc is already set up by checkAndSetupRootQdisc, so we just need to add per-peer limits
		if err := setupCAKEPerPeerLimits(iface, allowedIP, downloadRate, uploadRate); err != nil {
			logger.Printf("ERROR: Error setting up CAKE per-peer limits for peer %s: %v", peer, err)
			os.Exit(1)
		}
		logger.Printf("Successfully configured CAKE rate limiting for peer %s on interface %s", peer, iface)
		os.Exit(0) // CAKE handles everything, so we exit here
	}

	// Download shaping (remains on main interface) - for HTB/HFSC only
	if downloadRate > 0 {
		if err := createClass(iface, downloadClassID, downloadRate); err != nil {
			logger.Printf("ERROR: Error creating download rate limit class: %v", err)
			os.Exit(1)
		}
		if err := tryAddFiltersForIP(iface, downloadClassID, allowedIP, 0, downloadRate); err != nil {
			logger.Printf("ERROR: Error setting up download rate limits for peer %s: %v", peer, err)
			os.Exit(1)
		}
	} else if downloadRate == 0 {
		if err := removeFilter(iface, allowedIP); err != nil {
			logger.Printf("ERROR: Error removing download filter: %v", err)
			os.Exit(1)
		}
	}

	// Upload shaping section - for HTB/HFSC only (CAKE is handled above)
	if uploadRate > 0 {
		ifbDev := fmt.Sprintf(ifbFormat, iface)
		err := setupIFB(iface)
		if err != nil && err.Error() == "IFB is not supported on this system" {
			logger.Printf("WARNING: IFB not supported, falling back to basic tc shaping")
			// Basic tc shaping on the interface directly
			if err := setupBasicTCShaping(iface, allowedIP, uploadRate); err != nil {
				logger.Printf("ERROR: Error setting up basic tc shaping: %v", err)
				os.Exit(1)
			}
		} else if err != nil {
			logger.Printf("ERROR: Error setting up IFB device: %v", err)
			os.Exit(1)
		} else {
			if err := addIngressRedirect(iface, allowedIP, ifbDev); err != nil {
				logger.Printf("ERROR: Error adding ingress redirect: %v", err)
				os.Exit(1)
			}
			if err := checkAndSetupRootQdisc(ifbDev); err != nil {
				logger.Printf("ERROR: Error setting up root qdisc on IFB device: %v", err)
				os.Exit(1)
			}
			// Create upload class on the IFB device
			if err := createClass(ifbDev, uploadClassID, uploadRate); err != nil {
				logger.Printf("ERROR: Error creating upload class on IFB device: %v", err)
				os.Exit(1)
			}
			// Add upload filter
			if err := tryAddFiltersForIP(ifbDev, uploadClassID, allowedIP, uploadRate, 0); err != nil {
				logger.Printf("ERROR: Error setting up upload rate limits for peer %s on IFB device: %v", peer, err)
				os.Exit(1)
			}
		}
	} else if uploadRate == 0 {
		// Remove upload filter from IFB device if needed.
		if err := removeFilter(fmt.Sprintf(ifbFormat, iface), allowedIP); err != nil {
			logger.Printf("ERROR: Error removing upload filter from IFB device: %v", err)
			os.Exit(1)
		}
	}

	logger.Printf("Successfully configured rate limiting for peer %s on interface %s", peer, iface)
}

// checkAndSetupRootQdisc checks for existing qdisc and creates one if needed
func checkAndSetupRootQdisc(dev string) error {
	// Check current qdisc
	checkCmd := exec.Command(tcPath, "qdisc", "show", "dev", dev)
	output, err := checkCmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to check qdisc on %s: %v", dev, err)
	}

	// If no appropriate qdisc exists, set it up
	if !strings.Contains(string(output), "qdisc "+schedulerType) {
		logger.Printf("No %s qdisc found on %s, setting up...", schedulerType, dev)

		// Try multiple times with increasing delays
		for i := 0; i < 3; i++ {
			err := setupRootQdisc(dev)
			if err == nil {
				return nil
			}

			if strings.Contains(err.Error(), "Exclusivity flag on") {
				logger.Printf("Attempt %d: Exclusivity flag detected, waiting before retry...", i+1)
				time.Sleep(time.Duration(i+1) * time.Second)
				continue
			}

			return err // Return other errors immediately
		}

		return fmt.Errorf("failed to set up qdisc after multiple attempts: exclusivity flag persists")
	}

	logger.Printf("Root qdisc already exists on %s, preserving existing setup", dev)
	return nil
}

// setupRootQdisc creates the qdisc on the given device with better error handling
func setupRootQdisc(dev string) error {
	var cmd *exec.Cmd
	switch schedulerType {
	case "cake":
		logger.Printf("Setting up root CAKE qdisc on %s...", dev)
		cmd = exec.Command(tcPath, "qdisc", "add", "dev", dev,
			"root", "handle", "1:", "cake", "bandwidth", "1Gbit", "besteffort")

		_, err := cmd.CombinedOutput()
		if err != nil {
			// CAKE not available, fall back to HTB
			logger.Printf("CAKE not available, falling back to HTB: %v", err)
			cmd = exec.Command(tcPath, "qdisc", "add", "dev", dev,
				"root", "handle", "1:", "htb", "default", "99")
		} else {
			logger.Printf("Successfully set up CAKE qdisc on %s", dev)
			return nil
		}
	case "hfsc":
		logger.Printf("Setting up root HFSC qdisc on %s...", dev)
		cmd = exec.Command(tcPath, "qdisc", "add", "dev", dev,
			"root", "handle", "1:", "hfsc", "default", "99")
	default:
		logger.Printf("Setting up root HTB qdisc on %s...", dev)
		cmd = exec.Command(tcPath, "qdisc", "add", "dev", dev,
			"root", "handle", "1:", "htb", "default", "99")
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to set up root qdisc on %s: %v\nOutput: %s", dev, err, output)
	}

	logger.Printf("Successfully set up root qdisc on %s", dev)
	return nil
}

// createClass creates (or changes) a traffic class on the specified device.
func createClass(dev, classID string, rateKbps int64) error {
	// Validate rate before creating class
	rate, err := validateRate(rateKbps)
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
	logger.Printf("Creating class on device %s with classID %s and rate %d Kbps", dev, classIDHex, rate)

	switch schedulerType {
	case "cake":
		// CAKE doesn't use classes - it manages flows automatically
		// We'll use filters to redirect traffic to CAKE with bandwidth limits
		logger.Printf("CAKE scheduler doesn't use classes - using filter-based rate limiting")
		return nil
	case "hfsc":
		modifyCmd := exec.Command(tcPath, "class", "change", "dev", dev,
			"parent", "1:", "classid", classIDHex,
			"hfsc", "sc", "rate", fmt.Sprintf("%dbit", rateBits),
			"ul", "rate", fmt.Sprintf("%dbit", rateBits))
		if err := modifyCmd.Run(); err != nil {
			createCmd := exec.Command(tcPath, "class", "add", "dev", dev,
				"parent", "1:", "classid", classIDHex,
				"hfsc", "sc", "rate", fmt.Sprintf("%dbit", rateBits),
				"ul", "rate", fmt.Sprintf("%dbit", rateBits))
			output, err := createCmd.CombinedOutput()
			if err != nil {
				return fmt.Errorf("failed to add hfsc traffic class on %s: %v\nOutput: %s", dev, err, output)
			}
		}
	default:
		modifyCmd := exec.Command(tcPath, "class", "change", "dev", dev,
			"parent", "1:", "classid", classIDHex,
			"htb", "rate", fmt.Sprintf("%dbit", rateBits),
			"burst", "15k", "ceil", fmt.Sprintf("%dbit", rateBits))
		if err := modifyCmd.Run(); err != nil {
			createCmd := exec.Command(tcPath, "class", "add", "dev", dev,
				"parent", "1:", "classid", classIDHex,
				"htb", "rate", fmt.Sprintf("%dbit", rateBits),
				"burst", "15k", "ceil", fmt.Sprintf("%dbit", rateBits))
			output, err := createCmd.CombinedOutput()
			if err != nil {
				return fmt.Errorf("failed to add htb traffic class on %s: %v\nOutput: %s", dev, err, output)
			}
		}
	}
	logger.Printf("Successfully created class %s on device %s", classIDHex, dev)
	return nil
}

// tryAddFiltersForIP adds u32 filters on the given device.
// For upload (uploadRate > 0) it matches src IP; for download (downloadRate > 0) it matches dst IP.
func tryAddFiltersForIP(dev, classID, peer string, uploadRate, downloadRate int64) error {
	logger.Printf("Adding filters on device %s for peer %s (upload: %d, download: %d)",
		dev, peer, uploadRate, downloadRate)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	ipOnly := strings.Split(peer, "/")[0]
	protocol := "ip"
	matchType := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
		matchType = "ip6"
	}

	if uploadRate > 0 {
		logger.Printf("Adding upload filter for %s on %s", ipOnly, dev)
		filterCmd := exec.CommandContext(ctx, tcPath, "filter", "add", "dev", dev,
			"protocol", protocol, "parent", "1:", "prio", "1",
			"u32", "match", matchType, "src", ipOnly,
			"flowid", classID)
		if output, err := filterCmd.CombinedOutput(); err != nil {
			logger.Printf("Failed upload filter command: %s %s", tcPath,
				strings.Join(filterCmd.Args[1:], " "))
			return fmt.Errorf("failed to add upload filter on %s: %v\nCommand output: %s",
				dev, err, string(output))
		}
		logger.Printf("Successfully added upload filter for %s on %s", ipOnly, dev)
	}

	if downloadRate > 0 {
		logger.Printf("Adding download filter for %s on %s", ipOnly, dev)
		filterCmd := exec.CommandContext(ctx, tcPath, "filter", "add", "dev", dev,
			"protocol", protocol, "parent", "1:", "prio", "1",
			"u32", "match", matchType, "dst", ipOnly,
			"flowid", classID)
		if output, err := filterCmd.CombinedOutput(); err != nil {
			logger.Printf("Failed download filter command: %s %s", tcPath,
				strings.Join(filterCmd.Args[1:], " "))
			return fmt.Errorf("failed to add download filter on %s: %v\nCommand output: %s",
				dev, err, string(output))
		}
		logger.Printf("Successfully added download filter for %s on %s", ipOnly, dev)
	}

	if strings.Contains(ipOnly, ":") {
		if err := setupIPv6Filters(dev, classID, peer); err != nil {
			return fmt.Errorf("failed to set up IPv6 filters on %s: %v", dev, err)
		}
	}

	logger.Printf("Successfully added all filters for peer %s on device %s", peer, dev)
	return nil
}

// Update getWgPeerInfo to handle missing executable
func getWgPeerInfo(interfaceName, peerKey string) (*PeerInfo, error) {
	if wgPath == "" {
		return nil, fmt.Errorf("WireGuard executable not found")
	}
	logger.Printf("Executing: %s show %s", wgPath, interfaceName)
	cmd := exec.Command("wg", "show", interfaceName)
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Printf("ERROR: wg show command failed: %v\nOutput: %s", err, output)
		return nil, fmt.Errorf("failed to execute wg show: %v", err)
	}
	return parsePeerInfo(string(output), peerKey)
}

// Update getAwgPeerInfo to handle missing executable
func getAwgPeerInfo(interfaceName, peerKey string) (*PeerInfo, error) {
	if awgPath == "" {
		return nil, fmt.Errorf("AmneziaWG executable not found")
	}
	//logger.Printf("Executing: %s show %s", awgPath, interfaceName)
	cmd := exec.Command("awg", "show", interfaceName)
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Printf("ERROR: awg show command failed: %v\nOutput: %s", err, output)
		return nil, fmt.Errorf("failed to execute awg show: %v", err)
	}
	return parsePeerInfo(string(output), peerKey)
}

func parsePeerInfo(output, targetPeerKey string) (*PeerInfo, error) {
	scanner := bufio.NewScanner(strings.NewReader(output))
	peer := &PeerInfo{AllowedIPs: make([]string, 0)}
	foundPeer := false
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if strings.Contains(line, targetPeerKey) {
			foundPeer = true
			peer.PublicKey = targetPeerKey
			continue
		}
		if foundPeer && (strings.Contains(line, "allowed ip") || strings.Contains(line, "allowed_ip")) {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				ips := strings.Split(strings.TrimSpace(parts[1]), ",")
				for _, ip := range ips {
					ip = strings.TrimSpace(ip)
					if ip != "" {
						peer.AllowedIPs = append(peer.AllowedIPs, ip)
					}
				}
			}
		}
	}
	if !foundPeer {
		return nil, fmt.Errorf("peer not found in output: %s", output)
	}
	return peer, nil
}

// peerToClassBase converts the peer string into a base number that will result in a valid
// hexadecimal class ID when combined with a suffix.
// The class ID in TC must be a 16-bit hexadecimal number (0x0001-0xffff).
// We'll use the first 3 hex digits (0x001-0xfff) for the base, leaving the last digit
// for the class type (1 for upload, 2 for download).
func peerToClassBase(peer string) int {
	h := fnv.New64a()
	_, _ = h.Write([]byte(peer))
	// Use modulo 0xfff (4095) to ensure we only use the first 3 hex digits
	return int(h.Sum64() % 0xfff)
}

// removeFilter removes u32 filters for the given peer (matched by allowed IP) on a device.
func removeFilter(dev, ip string) error {
	ipOnly := strings.Split(ip, "/")[0]
	protocol := "ip"

	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
	}

	// List all filters and find the ones matching our IP
	listCmd := exec.Command(tcPath, "filter", "show", "dev", dev, "parent", "1:")
	output, err := listCmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to list filters on %s: %v", dev, err)
	}

	// Parse the output to find filter handles
	filters := parseFilterOutput(string(output), ipOnly)
	logger.Printf("Found %d filters to remove on %s for IP %s", len(filters), dev, ipOnly)

	// Remove each matching filter by its handle
	for _, handle := range filters {
		cmd := exec.Command(tcPath, "filter", "del", "dev", dev,
			"parent", "1:",
			"handle", handle, "prio", "1",
			"protocol", protocol)

		if output, err := cmd.CombinedOutput(); err != nil {
			logger.Printf("NOTE: Filter removal (handle %s) on %s returned: %v\nOutput: %s (usually safe to ignore)",
				handle, dev, err, string(output))
		} else {
			logger.Printf("Successfully removed filter handle %s on %s", handle, dev)
		}
	}

	// If we're removing filters from the main interface, also clean up the corresponding IFB device
	if !strings.HasPrefix(dev, "ifb-") {
		ifbDev := fmt.Sprintf(ifbFormat, dev)
		if err := removeFilter(ifbDev, ip); err != nil {
			logger.Printf("NOTE: Error removing filter on IFB device %s: %v (usually safe to ignore)", ifbDev, err)
		}
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

// addDefaultFilterOnDevice adds default filters to steer traffic to the unrestricted class (1:99)
func addDefaultFilterOnDevice(dev, allowedIP string) error {
	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
	}

	// Add default upload filter
	uploadCmd := exec.Command(tcPath, "filter", "add", "dev", dev,
		"parent", "1:",
		"protocol", protocol,
		"prio", "9999",
		"u32", "match", "ip", "src", ipOnly,
		"flowid", "1:99")
	if output, err := uploadCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add default upload filter on %s: %v, output: %s", dev, err, output)
	}

	// Add default download filter
	downloadCmd := exec.Command(tcPath, "filter", "add", "dev", dev,
		"parent", "1:",
		"protocol", protocol,
		"prio", "9999",
		"u32", "match", "ip", "dst", ipOnly,
		"flowid", "1:99")
	if output, err := downloadCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add default download filter on %s: %v, output: %s", dev, err, output)
	}
	return nil
}

// removePeerRateLimitOnDevice removes filters and classes for a given peer on a specified device.
func removePeerRateLimitOnDevice(dev, allowedIP, peerKey string) error {
	logger.Printf("Removing rate limits on device %s for peer %s (IP: %s)", dev, peerKey, allowedIP)

	// Calculate class IDs
	classBase := peerToClassBase(peerKey)
	uploadClassID := fmt.Sprintf("1:%x1", classBase)
	downloadClassID := fmt.Sprintf("1:%x2", classBase)

	logger.Printf("Calculated class IDs: upload=%s, download=%s", uploadClassID, downloadClassID)

	ipOnly := strings.Split(allowedIP, "/")[0]
	protocol := "ip"
	if strings.Contains(ipOnly, ":") {
		protocol = "ipv6"
	}

	// Multiple attempts for removal
	maxAttempts := 3
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		if attempt > 1 {
			logger.Printf("Attempt %d of %d to remove filters and classes", attempt, maxAttempts)
		}

		if !strings.HasPrefix(dev, "ifb-") {
			// Main interface: Handle download filters and class
			logger.Printf("Removing download filters for IP %s on %s", ipOnly, dev)

			// First remove all matching filters - try multiple approaches
			output, _ := exec.Command(tcPath, "filter", "show", "dev", dev, "parent", "1:").CombinedOutput()
			filters := parseFilterOutput(string(output), ipOnly)
			logger.Printf("Found %d filters to remove on %s for IP %s", len(filters), dev, ipOnly)

			// Remove filters by handle
			for _, handle := range filters {
				removeCmd := exec.Command(tcPath, "filter", "del", "dev", dev,
					"parent", "1:", "handle", handle, "prio", "1",
					"protocol", protocol)
				if output, err := removeCmd.CombinedOutput(); err != nil {
					logger.Printf("Warning: Error removing filter handle %s: %v, output: %s", handle, err, string(output))
				} else {
					logger.Printf("Successfully removed filter handle %s", handle)
				}
			}

			// Also try to remove filters by matching criteria (more aggressive approach)
			removeByMatchCmd := exec.Command(tcPath, "filter", "del", "dev", dev,
				"parent", "1:", "protocol", protocol, "prio", "1",
				"u32", "match", "ip", "dst", ipOnly)
			if output, err := removeByMatchCmd.CombinedOutput(); err != nil {
				logger.Printf("Note: Filter removal by match criteria returned: %v, output: %s (may not exist)", err, string(output))
			} else {
				logger.Printf("Successfully removed filters by match criteria")
			}

			// Check if class exists before trying to remove it
			checkCmd := exec.Command(tcPath, "class", "show", "dev", dev)
			checkOutput, _ := checkCmd.CombinedOutput()
			classExists := strings.Contains(string(checkOutput), downloadClassID)

			if classExists {
				// Wait a bit for filters to be fully processed
				time.Sleep(200 * time.Millisecond)

				// Then remove the class
				logger.Printf("Removing download class %s on main interface", downloadClassID)
				classCmd := exec.Command(tcPath, "class", "del", "dev", dev, "classid", downloadClassID)
				if output, err := classCmd.CombinedOutput(); err != nil {
					logger.Printf("Warning: Error removing class %s: %v, output: %s", downloadClassID, err, string(output))

					// If class is "in use", try to force remove it by first removing all filters again
					if strings.Contains(string(output), "in use") {
						logger.Printf("Class %s is in use, attempting to remove remaining filters", downloadClassID)

						// Try to remove any remaining filters that might be using this class
						forceRemoveCmd := exec.Command(tcPath, "filter", "del", "dev", dev,
							"parent", "1:", "protocol", protocol, "prio", "1",
							"u32", "match", "ip", "dst", ipOnly)
						forceRemoveCmd.Run() // Ignore errors

						// Wait and try class removal again
						time.Sleep(100 * time.Millisecond)
						classCmd2 := exec.Command(tcPath, "class", "del", "dev", dev, "classid", downloadClassID)
						if output2, err2 := classCmd2.CombinedOutput(); err2 != nil {
							logger.Printf("Warning: Still unable to remove class %s: %v, output: %s", downloadClassID, err2, string(output2))
						} else {
							logger.Printf("Successfully removed class %s on second attempt", downloadClassID)
						}
					}
				} else {
					logger.Printf("Successfully removed class %s", downloadClassID)
				}

				// Verify removal
				verifyCmd := exec.Command(tcPath, "class", "show", "dev", dev)
				verifyOutput, _ := verifyCmd.CombinedOutput()
				if strings.Contains(string(verifyOutput), downloadClassID) {
					if attempt == maxAttempts {
						logger.Printf("Class %s still exists after removal attempts, but continuing", downloadClassID)
						// Don't fail here, just log and continue
					} else {
						time.Sleep(100 * time.Millisecond)
						continue
					}
				}
			} else {
				logger.Printf("Class %s does not exist on %s, skipping removal", downloadClassID, dev)
			}
		} else {
			// IFB device: Handle upload filters and class
			logger.Printf("Removing upload filters for IP %s on %s", ipOnly, dev)

			// Remove all matching filters - try multiple approaches
			output, _ := exec.Command(tcPath, "filter", "show", "dev", dev, "parent", "1:").CombinedOutput()
			filters := parseFilterOutput(string(output), ipOnly)
			logger.Printf("Found %d filters to remove on %s for IP %s", len(filters), dev, ipOnly)

			// Remove filters by handle
			for _, handle := range filters {
				removeCmd := exec.Command(tcPath, "filter", "del", "dev", dev,
					"parent", "1:", "handle", handle, "prio", "1",
					"protocol", protocol)
				if output, err := removeCmd.CombinedOutput(); err != nil {
					logger.Printf("Warning: Error removing filter handle %s: %v, output: %s", handle, err, string(output))
				} else {
					logger.Printf("Successfully removed filter handle %s", handle)
				}
			}

			// Also try to remove filters by matching criteria (more aggressive approach)
			removeByMatchCmd := exec.Command(tcPath, "filter", "del", "dev", dev,
				"parent", "1:", "protocol", protocol, "prio", "1",
				"u32", "match", "ip", "src", ipOnly)
			if output, err := removeByMatchCmd.CombinedOutput(); err != nil {
				logger.Printf("Note: Filter removal by match criteria returned: %v, output: %s (may not exist)", err, string(output))
			} else {
				logger.Printf("Successfully removed filters by match criteria")
			}

			// Check if class exists before trying to remove it
			checkCmd := exec.Command(tcPath, "class", "show", "dev", dev)
			checkOutput, _ := checkCmd.CombinedOutput()
			classExists := strings.Contains(string(checkOutput), uploadClassID)

			if classExists {
				// Wait a bit for filters to be fully processed
				time.Sleep(200 * time.Millisecond)

				// Remove the class
				logger.Printf("Removing upload class %s on IFB device", uploadClassID)
				classCmd := exec.Command(tcPath, "class", "del", "dev", dev, "classid", uploadClassID)
				if output, err := classCmd.CombinedOutput(); err != nil {
					logger.Printf("Warning: Error removing class %s: %v, output: %s", uploadClassID, err, string(output))

					// If class is "in use", try to force remove it by first removing all filters again
					if strings.Contains(string(output), "in use") {
						logger.Printf("Class %s is in use, attempting to remove remaining filters", uploadClassID)

						// Try to remove any remaining filters that might be using this class
						forceRemoveCmd := exec.Command(tcPath, "filter", "del", "dev", dev,
							"parent", "1:", "protocol", protocol, "prio", "1",
							"u32", "match", "ip", "src", ipOnly)
						forceRemoveCmd.Run() // Ignore errors

						// Wait and try class removal again
						time.Sleep(100 * time.Millisecond)
						classCmd2 := exec.Command(tcPath, "class", "del", "dev", dev, "classid", uploadClassID)
						if output2, err2 := classCmd2.CombinedOutput(); err2 != nil {
							logger.Printf("Warning: Still unable to remove class %s: %v, output: %s", uploadClassID, err2, string(output2))
						} else {
							logger.Printf("Successfully removed class %s on second attempt", uploadClassID)
						}
					}
				} else {
					logger.Printf("Successfully removed class %s", uploadClassID)
				}

				// Clean up ingress redirect on the main interface
				realDev := strings.TrimPrefix(dev, "ifb-")
				logger.Printf("Cleaning up ingress redirect on %s", realDev)

				// Remove all ingress redirect filters
				ingressOutput, _ := exec.Command(tcPath, "filter", "show", "dev", realDev, "parent", "ffff:").CombinedOutput()
				ingressFilters := parseFilterOutput(string(ingressOutput), ipOnly)
				for _, handle := range ingressFilters {
					removeCmd := exec.Command(tcPath, "filter", "del", "dev", realDev,
						"parent", "ffff:", "handle", handle, "prio", "1")
					removeCmd.Run() // Ignore errors
				}

				// Verify removal
				verifyCmd := exec.Command(tcPath, "class", "show", "dev", dev)
				verifyOutput, _ := verifyCmd.CombinedOutput()
				if strings.Contains(string(verifyOutput), uploadClassID) {
					if attempt == maxAttempts {
						logger.Printf("Class %s still exists after removal attempts, but continuing", uploadClassID)
						// Don't fail here, just log and continue
					} else {
						time.Sleep(100 * time.Millisecond)
						continue
					}
				}
			} else {
				logger.Printf("Class %s does not exist on %s, skipping removal", uploadClassID, dev)
			}
		}

		// If we get here, the removal was successful
		break
	}

	// Ensure the default class exists with high bandwidth
	logger.Printf("Ensuring default class exists on %s", dev)
	defaultCmd := exec.Command(tcPath, "class", "replace", "dev", dev,
		"parent", "1:", "classid", "1:99",
		schedulerType, "rate", fmt.Sprintf("%d000bit", maxRate64))
	defaultCmd.Run() // Ignore errors
	logger.Printf("Default class verified on %s", dev)

	logger.Printf("Completed removal of rate limits on device %s for peer %s", dev, peerKey)
	return nil
}

// setupIPv6Filters adds IPv6-specific filters if needed.
func setupIPv6Filters(dev, classID, peer string) error {
	ipOnly := strings.Split(peer, "/")[0]
	if !strings.Contains(ipOnly, ":") {
		return nil
	}
	cmd := exec.Command(tcPath, "filter", "add", "dev", dev,
		"protocol", "ipv6",
		"parent", "1:", "prio", "1",
		"u32", "match", "ip6", "src", ipOnly,
		"flowid", classID)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to add IPv6 filter on %s: %v", dev, err)
	}
	return nil
}

// checkIFBSupport checks if IFB is supported on the system
func checkIFBSupport() bool {
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

// setupIFB creates and brings up the IFB device if it doesn't already exist.
func setupIFB(realDev string) error {
	// Create IFB device name based on interface
	ifbDev := fmt.Sprintf(ifbFormat, realDev)
	logger.Printf("Setting up IFB device %s for interface %s", ifbDev, realDev)

	// Check if IFB is supported
	if !checkIFBSupport() {
		return fmt.Errorf("IFB is not supported on this system")
	}

	// Check if the IFB device exists
	if _, err := exec.Command("ip", "link", "show", ifbDev).CombinedOutput(); err != nil {
		logger.Printf("IFB device %s does not exist, creating...", ifbDev)
		cmdAdd := exec.Command("ip", "link", "add", ifbDev, "type", "ifb")
		if output, err := cmdAdd.CombinedOutput(); err != nil {
			logger.Printf("ERROR: Failed to create IFB device: %v\nOutput: %s", err, output)
			return fmt.Errorf("failed to create IFB device %s: %v, output: %s", ifbDev, err, output)
		}
	}

	// Ensure IFB device is up
	cmdUp := exec.Command("ip", "link", "set", "dev", ifbDev, "up")
	if output, err := cmdUp.CombinedOutput(); err != nil {
		logger.Printf("ERROR: Failed to bring up IFB device: %v\nOutput: %s", err, output)
		return fmt.Errorf("failed to set IFB device %s up: %v, output: %s", ifbDev, err, output)
	}

	// Check if ingress qdisc exists
	ingressExists := false
	if output, err := exec.Command(tcPath, "qdisc", "show", "dev", realDev, "ingress").CombinedOutput(); err == nil {
		ingressExists = strings.Contains(string(output), "ingress")
	}

	// Add ingress qdisc only if it doesn't exist
	if !ingressExists {
		logger.Printf("Adding ingress qdisc to %s", realDev)
		ingressCmd := exec.Command(tcPath, "qdisc", "add", "dev", realDev, "handle", "ffff:", "ingress")
		if output, err := ingressCmd.CombinedOutput(); err != nil {
			logger.Printf("ERROR: Failed to add ingress qdisc: %v\nOutput: %s", err, output)
			return fmt.Errorf("failed to add ingress qdisc on %s: %v", realDev, err)
		}
		// Verify ingress qdisc was created
		time.Sleep(100 * time.Millisecond)
		if output, err := exec.Command(tcPath, "qdisc", "show", "dev", realDev, "ingress").CombinedOutput(); err != nil || !strings.Contains(string(output), "ingress") {
			return fmt.Errorf("failed to verify ingress qdisc creation on %s", realDev)
		}
	}

	// Only set up root qdisc if it doesn't exist
	return checkAndSetupRootQdisc(ifbDev)
}

// addIngressRedirect with improved error handling and verification
func addIngressRedirect(realDev, allowedIP, ifb string) error {
	logger.Printf("Adding ingress redirect from %s to %s for IP %s", realDev, ifb, allowedIP)

	// Verify ingress qdisc exists
	if output, err := exec.Command(tcPath, "qdisc", "show", "dev", realDev, "ingress").CombinedOutput(); err != nil || !strings.Contains(string(output), "ingress") {
		logger.Printf("ERROR: Ingress qdisc not found on %s", realDev)
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
	listCmd := exec.Command(tcPath, "filter", "show", "dev", realDev, "parent", "ffff:")
	output, _ := listCmd.CombinedOutput()
	filters := parseFilterOutput(string(output), ipOnly)
	for _, handle := range filters {
		removeCmd := exec.Command(tcPath, "filter", "del", "dev", realDev,
			"parent", "ffff:", "handle", handle, "prio", "1")
		if output, err := removeCmd.CombinedOutput(); err != nil {
			logger.Printf("NOTE: Filter removal (handle %s) returned: %v\nOutput: %s",
				handle, err, string(output))
		}
	}

	// Add new redirect filter with retries
	for i := 0; i < 3; i++ {
		filterCmd := exec.Command(tcPath, "filter", "add", "dev", realDev,
			"parent", "ffff:",
			"protocol", protocol,
			"prio", "1",
			"u32",
			"match", matchType, "src", ipOnly,
			"action", "mirred", "egress", "redirect", "dev", ifb)

		if output, err := filterCmd.CombinedOutput(); err == nil {
			logger.Printf("Successfully added ingress redirect")
			return nil
		} else if i == 2 {
			return fmt.Errorf("failed to add ingress redirect filter after retries: %v, output: %s", err, output)
		}
		time.Sleep(100 * time.Millisecond)
	}

	return nil
}

// cleanupOnError performs emergency cleanup on the specified interface.
func cleanupOnError(dev string) {
	logger.Printf("WARN: Performing emergency cleanup...")
	// Clean up IFB cleanup code
	if err := exec.Command(tcPath, "filter", "del", "dev", dev, "parent", "1:").Run(); err != nil {
		logger.Printf("WARN: Failed to clean filters on %s: %v", dev, err)
	}
	if err := exec.Command(tcPath, "qdisc", "del", "dev", dev, "root").Run(); err != nil {
		logger.Printf("WARN: Failed to clean qdisc on %s: %v", dev, err)
	}
	// Clean up IFB device if it exists
	ifbDev := fmt.Sprintf(ifbFormat, dev)
	if err := exec.Command(tcPath, "qdisc", "del", "dev", ifbDev, "root").Run(); err != nil {
		logger.Printf("WARN: Failed to clean qdisc on %s: %v", ifbDev, err)
	}
}

// setupBasicTCShaping sets up basic traffic shaping without IFB
func setupBasicTCShaping(dev, allowedIP string, rateKbps int64) error {
	logger.Printf("Setting up basic tc shaping on %s for IP %s at %d Kbps", dev, allowedIP, rateKbps)

	// Add ingress qdisc
	ingressCmd := exec.Command(tcPath, "qdisc", "add", "dev", dev, "ingress")
	if output, err := ingressCmd.CombinedOutput(); err != nil {
		logger.Printf("NOTE: Adding ingress qdisc returned: %v\nOutput: %s (may already exist)", err, output)
	}

	// Add filter to police incoming traffic
	rateBits := rateKbps * 1000
	burst := rateKbps * 125 // burst size in bytes (roughly 1ms worth of traffic)
	filterCmd := exec.Command(tcPath, "filter", "add", "dev", dev, "parent", "ffff:",
		"protocol", "ip", "prio", "1", "u32",
		"match", "ip", "src", allowedIP,
		"police", "rate", fmt.Sprintf("%dbit", rateBits),
		"burst", fmt.Sprintf("%d", burst),
		"drop", "flowid", ":1")

	if output, err := filterCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to add policing filter: %v, output: %s", err, output)
	}

	return nil
}

// detect64BitSupport checks if the kernel supports 64-bit rate limits
func detect64BitSupport() bool {
	// Try to create a test class with a rate higher than 32-bit max
	testDev := "lo" // Use loopback device for testing
	testRate := int64(maxRate32 + 1)

	cmd := exec.Command(tcPath, "class", "add", "dev", testDev,
		"parent", "1:", "classid", "1:999",
		"htb", "rate", fmt.Sprintf("%dbit", testRate*1000))

	output, err := cmd.CombinedOutput()

	// Clean up test class regardless of result
	cleanup := exec.Command(tcPath, "class", "del", "dev", testDev, "classid", "1:999")
	cleanup.Run()

	if err != nil {
		// Check if error is specifically about 32-bit overflow
		if strings.Contains(string(output), "invalid rate") ||
			strings.Contains(string(output), "overflow") {
			logger.Printf("Detected 32-bit rate limit support")
			return false
		}
	}

	logger.Printf("Detected 64-bit rate limit support")
	return true
}

// validateRate checks if the rate is within supported bounds
func validateRate(rate int64) (int64, error) {
	if rate < 0 {
		return 0, fmt.Errorf("rate cannot be negative")
	}

	maxRate := int64(maxRate32)
	if supports64Bit {
		maxRate = maxRate64
	}

	if rate == 0 {
		return maxRate, nil // Convert 0 (unlimited) to max supported rate
	}

	if rate > maxRate {
		return 0, fmt.Errorf("rate %d exceeds maximum supported rate %d", rate, maxRate)
	}

	return rate, nil
}

// Update API response to include rate limit capabilities
type SystemCapabilities struct {
	Supports64BitRates bool   `json:"supports_64bit_rates"`
	MaximumRate        int64  `json:"maximum_rate_kbps"`
	SchedulerType      string `json:"scheduler_type"`
}

func getSystemCapabilities() SystemCapabilities {
	maxRate := int64(maxRate32)
	if supports64Bit {
		maxRate = maxRate64
	}
	return SystemCapabilities{
		Supports64BitRates: supports64Bit,
		MaximumRate:        maxRate,
		SchedulerType:      schedulerType,
	}
}

// nukeInterface removes all traffic control qdiscs from the specified interface
func nukeInterface(dev string) error {
	logger.Printf("Nuking all traffic control on interface %s...", dev)

	// Calculate the corresponding IFB device name
	ifbDev := fmt.Sprintf(ifbFormat, dev)

	// First try to remove ingress qdisc
	ingressCmd := exec.Command(tcPath, "qdisc", "del", "dev", dev, "ingress")
	if output, err := ingressCmd.CombinedOutput(); err != nil {
		logger.Printf("NOTE: Removing ingress qdisc returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Printf("Successfully removed ingress qdisc from %s", dev)
	}

	// Then remove root qdisc (this will remove all classes and filters)
	rootCmd := exec.Command(tcPath, "qdisc", "del", "dev", dev, "root")
	if output, err := rootCmd.CombinedOutput(); err != nil {
		logger.Printf("NOTE: Removing root qdisc returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Printf("Successfully removed root qdisc from %s", dev)
	}

	// Clean up the corresponding IFB device
	// First remove its qdisc
	ifbQdiscCmd := exec.Command(tcPath, "qdisc", "del", "dev", ifbDev, "root")
	if output, err := ifbQdiscCmd.CombinedOutput(); err != nil {
		logger.Printf("NOTE: Removing IFB qdisc returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Printf("Successfully removed root qdisc from IFB device %s", ifbDev)
	}

	// Then try to remove the IFB device itself
	ifbCmd := exec.Command("ip", "link", "del", ifbDev)
	if output, err := ifbCmd.CombinedOutput(); err != nil {
		logger.Printf("NOTE: Removing IFB device returned: %v\nOutput: %s (may not exist)", err, output)
	} else {
		logger.Printf("Successfully removed IFB device %s", ifbDev)
	}

	return nil
}
