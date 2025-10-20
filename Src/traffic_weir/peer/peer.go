package peer

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"

	"traffic-weir/config"
	"traffic-weir/logger"
)

// FindExecutable searches for an executable in multiple common locations
func FindExecutable(names []string, commonPaths []string) (string, error) {
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

// InitExecutables finds and initializes WireGuard and AmneziaWG executables
func InitExecutables() {
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
	if path, err := FindExecutable(wgNames, commonPaths); err == nil {
		config.WGPath = path
		logger.Logger.Printf("Found WireGuard at: %s", config.WGPath)
	} else {
		logger.Logger.Printf("WARNING: WireGuard executable not found: %v", err)
	}

	// Find AmneziaWG executable
	awgNames := []string{"awg", "amneziawg"}
	if path, err := FindExecutable(awgNames, commonPaths); err == nil {
		config.AWGPath = path
		logger.Logger.Printf("Found AmneziaWG at: %s", config.AWGPath)
	} else {
		logger.Logger.Printf("WARNING: AmneziaWG executable not found: %v", err)
	}
}

// GetWgPeerInfo retrieves peer information from WireGuard
func GetWgPeerInfo(interfaceName, peerKey string) (*config.PeerInfo, error) {
	if config.WGPath == "" {
		return nil, fmt.Errorf("WireGuard executable not found")
	}
	logger.Logger.Printf("Executing: %s show %s", config.WGPath, interfaceName)
	cmd := exec.Command(config.WGPath, "show", interfaceName)
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Logger.Printf("ERROR: wg show command failed: %v\nOutput: %s", err, output)
		return nil, fmt.Errorf("failed to execute wg show: %v", err)
	}
	return ParsePeerInfo(string(output), peerKey)
}

// GetAwgPeerInfo retrieves peer information from AmneziaWG
func GetAwgPeerInfo(interfaceName, peerKey string) (*config.PeerInfo, error) {
	if config.AWGPath == "" {
		return nil, fmt.Errorf("AmneziaWG executable not found")
	}
	logger.Logger.Printf("Executing: %s show %s", config.AWGPath, interfaceName)
	cmd := exec.Command(config.AWGPath, "show", interfaceName)
	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Logger.Printf("ERROR: awg show command failed: %v\nOutput: %s", err, output)
		return nil, fmt.Errorf("failed to execute awg show: %v", err)
	}
	return ParsePeerInfo(string(output), peerKey)
}

// ParsePeerInfo parses peer information from command output
func ParsePeerInfo(output, targetPeerKey string) (*config.PeerInfo, error) {
	scanner := bufio.NewScanner(strings.NewReader(output))
	peer := &config.PeerInfo{AllowedIPs: make([]string, 0)}
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
