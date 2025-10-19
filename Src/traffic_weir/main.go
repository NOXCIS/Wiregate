package main

import (
	"flag"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"traffic-weir/config"
	"traffic-weir/ifb"
	"traffic-weir/logger"
	"traffic-weir/qdisc"
	"traffic-weir/scheduler"
)

func init() {
	// Initialize logger
	if err := logger.InitLogger(); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
}

func main() {
	logger.Logger.Printf("Starting traffic-weir...")

	var iface string
	defer func() {
		if r := recover(); r != nil {
			logger.Logger.Printf("FATAL: Recovered from panic: %v", r)
			cleanupOnError(iface)
		}
	}()

	var (
		peerKey      string
		uploadRate   int64
		downloadRate int64
		protocol     string
		remove       bool
		nuke         bool
		allowedIPs   string // New flag for directly specifying allowed IPs
		err          error
	)

	flag.StringVar(&iface, "interface", "", "Interface name")
	flag.StringVar(&peerKey, "peer", "", "Peer ID")
	flag.Int64Var(&uploadRate, "upload-rate", 0, "Upload rate limit in Kb/s (0 for unlimited)")
	flag.Int64Var(&downloadRate, "download-rate", 0, "Download rate limit in Kb/s (0 for unlimited)")
	flag.StringVar(&protocol, "protocol", "wg", "Protocol (wg or awg)")
	flag.BoolVar(&remove, "remove", false, "Remove rate limits")
	flag.BoolVar(&nuke, "nuke", false, "Remove all traffic control qdiscs from interface")
	flag.StringVar(&config.SchedulerType, "scheduler", "htb", "Traffic scheduler type (htb, hfsc, or cake)")
	flag.StringVar(&allowedIPs, "allowed-ips", "", "Comma-separated list of allowed IPs (required)")
	flag.Parse()

	// Add nuke handling early in the execution
	if nuke {
		if iface == "" {
			logger.Logger.Printf("ERROR: interface flag is required for nuke operation")
			flag.Usage()
			os.Exit(1)
		}
		if err := qdisc.NukeInterface(iface); err != nil {
			logger.Logger.Printf("ERROR: Failed to nuke interface %s: %v", iface, err)
			os.Exit(1)
		}
		logger.Logger.Printf("Successfully nuked all traffic control on interface %s", iface)
		os.Exit(0)
	}

	// Detect 64-bit support before processing rates
	config.Supports64Bit = scheduler.Detect64BitSupport()
	if config.Supports64Bit {
		logger.Logger.Printf("System supports 64-bit rate limits")
	} else {
		logger.Logger.Printf("System does not support 64-bit rate limits")
	}

	// Add this near the start of main, after supports64Bit is set
	capabilities := scheduler.GetSystemCapabilities()
	logger.Logger.Printf("System capabilities: 64-bit rates: %v, max rate: %d Kbps, scheduler: %s",
		capabilities.Supports64BitRates,
		capabilities.MaximumRate,
		capabilities.SchedulerType)

	// Validate and adjust rates
	if uploadRate, err = scheduler.ValidateRate(uploadRate); err != nil {
		logger.Logger.Printf("ERROR: Invalid upload rate: %v", err)
		os.Exit(1)
	}
	if downloadRate, err = scheduler.ValidateRate(downloadRate); err != nil {
		logger.Logger.Printf("ERROR: Invalid download rate: %v", err)
		os.Exit(1)
	}

	// Rely solely on the manually selected scheduler type
	logger.Logger.Printf("Using manually selected scheduler type: %s", config.SchedulerType)

	logger.Logger.Printf("Configuration: interface=%s, peer=%s, upload-rate=%d, download-rate=%d, protocol=%s, remove=%v",
		iface, peerKey, uploadRate, downloadRate, protocol, remove)

	if iface == "" || peerKey == "" || protocol == "" || allowedIPs == "" {
		logger.Logger.Printf("ERROR: interface, peer, protocol, and allowed-ips flags are required")
		flag.Usage()
		os.Exit(1)
	}

	if protocol != "wg" && protocol != "awg" {
		logger.Logger.Printf("ERROR: Invalid protocol %s. Must be either 'wg' or 'awg'", protocol)
		os.Exit(1)
	}

	if _, err := exec.LookPath(config.TCPath); err != nil {
		logger.Logger.Printf("ERROR: tc command not found at %s. Please install iproute2.", config.TCPath)
		os.Exit(1)
	}

	// Parse and validate allowed IPs
	ips := strings.Split(allowedIPs, ",")
	// Trim whitespace from each IP
	for i, ip := range ips {
		ips[i] = strings.TrimSpace(ip)
	}

	logger.Logger.Printf("Using provided allowed IPs: %v", ips)
	allowedIP := ips[0]

	// If remove flag is specified, only remove filters/classes for this peer.
	if remove {
		logger.Logger.Printf("Resetting (removing) rate limits for peer %s on interface %s...", peerKey, iface)

		if config.SchedulerType == "cake" {
			// CAKE uses different removal logic
			if err := scheduler.RemoveCAKERateLimit(iface, allowedIP); err != nil {
				logger.Logger.Printf("ERROR: Error removing CAKE rate limits: %v", err)
				os.Exit(1)
			}
		} else {
			// Remove filters and classes on main interface (download side)
			if err := scheduler.RemovePeerRateLimitOnDevice(iface, allowedIP, peerKey); err != nil {
				logger.Logger.Printf("ERROR: Error removing rate limits on interface: %v", err)
				os.Exit(1)
			}
			// If the IFB device exists, remove upload filters from it.
			if _, err := exec.Command("ip", "link", "show", fmt.Sprintf(config.IFBFormat, iface)).CombinedOutput(); err == nil {
				if err := scheduler.RemovePeerRateLimitOnDevice(fmt.Sprintf(config.IFBFormat, iface), allowedIP, peerKey); err != nil {
					logger.Logger.Printf("ERROR: Error removing rate limits on IFB device: %v", err)
					os.Exit(1)
				}
				if err := scheduler.AddDefaultFilterOnDevice(fmt.Sprintf(config.IFBFormat, iface), allowedIP); err != nil {
					logger.Logger.Printf("ERROR: Error adding default filter on IFB device: %v", err)
					os.Exit(1)
				}
			}
			// Re-add the default filter on the main interface.
			if err := scheduler.AddDefaultFilterOnDevice(iface, allowedIP); err != nil {
				logger.Logger.Printf("ERROR: Error adding default filter on interface: %v", err)
				os.Exit(1)
			}
		}
		logger.Logger.Printf("Successfully removed rate limits for peer %s on interface %s", peerKey, iface)
		os.Exit(0)
	}

	// Remove the cleanup of existing qdisc - we want to preserve existing rules
	logger.Logger.Printf("Checking existing traffic control setup on main interface...")

	// Only set up root qdisc if it doesn't exist
	if err := qdisc.CheckAndSetupRootQdiscWithIPv6(iface, allowedIP); err != nil {
		logger.Logger.Printf("ERROR: Failed to set up root qdisc: %v", err)
		os.Exit(1)
	}

	// Ensure IPv6 support if needed
	if qdisc.NeedsIPv6Support(allowedIP) {
		if err := qdisc.EnsureIPv6Support(iface); err != nil {
			logger.Logger.Printf("WARNING: Could not ensure IPv6 support: %v", err)
		}
	}

	// Compute class IDs (different suffixes for upload vs. download)
	classBase := scheduler.PeerToClassBase(peerKey)
	downloadClassID := fmt.Sprintf("1:%x2", classBase) // download class on main iface
	uploadClassID := fmt.Sprintf("1:%x1", classBase)   // upload class on IFB device

	// Handle CAKE scheduler differently - it replaces the entire qdisc setup
	if config.SchedulerType == "cake" {
		// CAKE qdisc is already set up by checkAndSetupRootQdisc, so we just need to add per-peer limits
		if err := scheduler.SetupCAKEPerPeerLimits(iface, allowedIP, downloadRate, uploadRate); err != nil {
			logger.Logger.Printf("ERROR: Error setting up CAKE per-peer limits for peer %s: %v", peerKey, err)
			os.Exit(1)
		}
		logger.Logger.Printf("Successfully configured CAKE rate limiting for peer %s on interface %s", peerKey, iface)
		os.Exit(0) // CAKE handles everything, so we exit here
	}

	// Download shaping (remains on main interface) - for HTB/HFSC only
	if downloadRate > 0 {
		if err := scheduler.CreateClass(iface, downloadClassID, downloadRate); err != nil {
			logger.Logger.Printf("ERROR: Error creating download rate limit class: %v", err)
			os.Exit(1)
		}
		if err := scheduler.TryAddFiltersForIP(iface, downloadClassID, allowedIP, 0, downloadRate); err != nil {
			logger.Logger.Printf("ERROR: Error setting up download rate limits for peer %s: %v", peerKey, err)
			os.Exit(1)
		}
	} else if downloadRate == 0 {
		if err := scheduler.RemoveFilter(iface, allowedIP); err != nil {
			logger.Logger.Printf("ERROR: Error removing download filter: %v", err)
			os.Exit(1)
		}
	}

	// Upload shaping section - for HTB/HFSC only (CAKE is handled above)
	if uploadRate > 0 {
		ifbDev := fmt.Sprintf(config.IFBFormat, iface)
		err := ifb.SetupIFB(iface)
		if err != nil && err.Error() == "IFB is not supported on this system" {
			logger.Logger.Printf("WARNING: IFB not supported, falling back to basic tc shaping")
			// Basic tc shaping on the interface directly
			if err := ifb.SetupBasicTCShaping(iface, allowedIP, uploadRate); err != nil {
				logger.Logger.Printf("ERROR: Error setting up basic tc shaping: %v", err)
				os.Exit(1)
			}
		} else if err != nil {
			logger.Logger.Printf("ERROR: Error setting up IFB device: %v", err)
			os.Exit(1)
		} else {
			if err := ifb.AddIngressRedirect(iface, allowedIP, ifbDev); err != nil {
				logger.Logger.Printf("ERROR: Error adding ingress redirect: %v", err)
				os.Exit(1)
			}
			if err := qdisc.CheckAndSetupRootQdisc(ifbDev); err != nil {
				logger.Logger.Printf("ERROR: Error setting up root qdisc on IFB device: %v", err)
				os.Exit(1)
			}
			// Create upload class on the IFB device
			if err := scheduler.CreateClass(ifbDev, uploadClassID, uploadRate); err != nil {
				logger.Logger.Printf("ERROR: Error creating upload class on IFB device: %v", err)
				os.Exit(1)
			}
			// Add upload filter
			if err := scheduler.TryAddFiltersForIP(ifbDev, uploadClassID, allowedIP, uploadRate, 0); err != nil {
				logger.Logger.Printf("ERROR: Error setting up upload rate limits for peer %s on IFB device: %v", peerKey, err)
				os.Exit(1)
			}
		}
	} else if uploadRate == 0 {
		// Remove upload filter from IFB device if needed.
		if err := scheduler.RemoveFilter(fmt.Sprintf(config.IFBFormat, iface), allowedIP); err != nil {
			logger.Logger.Printf("ERROR: Error removing upload filter from IFB device: %v", err)
			os.Exit(1)
		}
	}

	logger.Logger.Printf("Successfully configured rate limiting for peer %s on interface %s", peerKey, iface)
}

// cleanupOnError performs emergency cleanup on the specified interface.
func cleanupOnError(dev string) {
	logger.Logger.Printf("WARN: Performing emergency cleanup...")
	// Clean up IFB cleanup code
	if err := exec.Command(config.TCPath, "filter", "del", "dev", dev, "parent", "1:").Run(); err != nil {
		logger.Logger.Printf("WARN: Failed to clean filters on %s: %v", dev, err)
	}
	if err := exec.Command(config.TCPath, "qdisc", "del", "dev", dev, "root").Run(); err != nil {
		logger.Logger.Printf("WARN: Failed to clean qdisc on %s: %v", dev, err)
	}
	// Clean up IFB device if it exists
	ifbDev := fmt.Sprintf(config.IFBFormat, dev)
	if err := exec.Command(config.TCPath, "qdisc", "del", "dev", ifbDev, "root").Run(); err != nil {
		logger.Logger.Printf("WARN: Failed to clean qdisc on %s: %v", ifbDev, err)
	}
}
