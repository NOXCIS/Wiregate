// Copyright(C) 2025 NOXCIS [https://github.com/NOXCIS]
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"crypto/tls"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"time"
)

const (
	dashboardHTTPPort  = 80
	dashboardHTTPSPort = 443
	torControlPort1    = 9051
	torControlPort2    = 9054
	socketTimeout      = 5 * time.Second
	httpTimeout        = 10 * time.Second
)

type HealthCheckResult struct {
	Service string
	Status  string
	Message string
	Healthy bool
}

// checkPort checks if a port is listening
func checkPort(host string, port int, timeout time.Duration) bool {
	address := net.JoinHostPort(host, fmt.Sprintf("%d", port))
	conn, err := net.DialTimeout("tcp", address, timeout)
	if err != nil {
		return false
	}
	conn.Close()
	return true
}

// checkHTTP checks if HTTP service is responding
func checkHTTP(url string, timeout time.Duration) (bool, string) {
	client := &http.Client{
		Timeout: timeout,
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: false,
			},
		},
	}

	resp, err := client.Get(url)
	if err != nil {
		return false, fmt.Sprintf("Connection failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 400 {
		return true, fmt.Sprintf("HTTP %d", resp.StatusCode)
	}
	return false, fmt.Sprintf("HTTP %d", resp.StatusCode)
}

// checkTorControl checks if Tor control port is accessible
func checkTorControl(port int, password string) (bool, string) {
	address := net.JoinHostPort("127.0.0.1", fmt.Sprintf("%d", port))
	conn, err := net.DialTimeout("tcp", address, socketTimeout)
	if err != nil {
		return false, fmt.Sprintf("Connection failed: %v", err)
	}
	defer conn.Close()

	conn.SetDeadline(time.Now().Add(socketTimeout))

	// Try to authenticate
	if password != "" {
		authCmd := fmt.Sprintf("AUTHENTICATE \"%s\"\r\n", password)
		fmt.Fprint(conn, authCmd)

		buf := make([]byte, 1024)
		n, err := conn.Read(buf)
		if err != nil {
			return false, fmt.Sprintf("Auth read failed: %v", err)
		}
		response := string(buf[:n])
		if !strings.Contains(response, "250") {
			return false, "Authentication failed"
		}
	}

	// Get version info
	fmt.Fprint(conn, "GETINFO version\r\n")
	buf := make([]byte, 1024)
	n, err := conn.Read(buf)
	if err != nil {
		return false, fmt.Sprintf("Read failed: %v", err)
	}
	response := string(buf[:n])
	if strings.Contains(response, "250") {
		return true, "Tor control port accessible"
	}

	return false, "Invalid response from Tor"
}

// checkWireGuardInterfaces checks if WireGuard or AmneziaWG interfaces are up
func checkWireGuardInterfaces() (bool, string) {
	var totalInterfaces int
	var wgInterfaces, awgInterfaces int
	var errors []string

	// Check WireGuard interfaces
	cmd := exec.Command("wg", "show")
	output, err := cmd.Output()
	if err == nil {
		interfaces := strings.TrimSpace(string(output))
		if interfaces != "" {
			lines := strings.Split(interfaces, "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "interface:") {
					wgInterfaces++
				}
			}
		}
	} else {
		errors = append(errors, fmt.Sprintf("wg: %v", err))
	}

	// Check AmneziaWG interfaces
	cmd = exec.Command("awg", "show")
	output, err = cmd.Output()
	if err == nil {
		interfaces := strings.TrimSpace(string(output))
		if interfaces != "" {
			lines := strings.Split(interfaces, "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "interface:") {
					awgInterfaces++
				}
			}
		}
	} else {
		// awg might not be available, which is fine if wg interfaces exist
		if wgInterfaces == 0 {
			errors = append(errors, fmt.Sprintf("awg: %v", err))
		}
	}

	totalInterfaces = wgInterfaces + awgInterfaces

	if totalInterfaces > 0 {
		var msg strings.Builder
		msg.WriteString(fmt.Sprintf("%d interface(s) active", totalInterfaces))
		if wgInterfaces > 0 && awgInterfaces > 0 {
			msg.WriteString(fmt.Sprintf(" (%d wg, %d awg)", wgInterfaces, awgInterfaces))
		} else if awgInterfaces > 0 {
			msg.WriteString(" (awg)")
		}
		return true, msg.String()
	}

	if len(errors) > 0 {
		return false, fmt.Sprintf("No active interfaces found: %s", strings.Join(errors, "; "))
	}
	return false, "No WireGuard or AmneziaWG interfaces found"
}

// checkDashboard checks dashboard HTTP/HTTPS status
func checkDashboard() HealthCheckResult {
	// Check HTTP
	httpURL := fmt.Sprintf("http://127.0.0.1:%d/", dashboardHTTPPort)
	if healthy, msg := checkHTTP(httpURL, httpTimeout); healthy {
		return HealthCheckResult{
			Service: "Dashboard (HTTP)",
			Status:  "healthy",
			Message: msg,
			Healthy: true,
		}
	}

	// Check HTTPS
	httpsURL := fmt.Sprintf("https://127.0.0.1:%d/", dashboardHTTPSPort)
	if healthy, msg := checkHTTP(httpsURL, httpTimeout); healthy {
		return HealthCheckResult{
			Service: "Dashboard (HTTPS)",
			Status:  "healthy",
			Message: msg,
			Healthy: true,
		}
	}

	// Check if ports are listening
	if checkPort("127.0.0.1", dashboardHTTPPort, socketTimeout) {
		return HealthCheckResult{
			Service: "Dashboard",
			Status:  "warning",
			Message: "Port listening but HTTP check failed",
			Healthy: false,
		}
	}

	if checkPort("127.0.0.1", dashboardHTTPSPort, socketTimeout) {
		return HealthCheckResult{
			Service: "Dashboard",
			Status:  "warning",
			Message: "Port listening but HTTPS check failed",
			Healthy: false,
		}
	}

	return HealthCheckResult{
		Service: "Dashboard",
		Status:  "unhealthy",
		Message: "Not responding on ports 80 or 443",
		Healthy: false,
	}
}

// checkTor checks Tor control ports
func checkTor() []HealthCheckResult {
	var results []HealthCheckResult
	password := os.Getenv("VANGUARD")

	// Check main Tor control port
	if healthy, msg := checkTorControl(torControlPort1, password); healthy {
		results = append(results, HealthCheckResult{
			Service: "Tor (Main)",
			Status:  "healthy",
			Message: msg,
			Healthy: true,
		})
	} else if checkPort("127.0.0.1", torControlPort1, socketTimeout) {
		results = append(results, HealthCheckResult{
			Service: "Tor (Main)",
			Status:  "warning",
			Message: "Port listening but control check failed",
			Healthy: false,
		})
	} else {
		results = append(results, HealthCheckResult{
			Service: "Tor (Main)",
			Status:  "unhealthy",
			Message: msg,
			Healthy: false,
		})
	}

	// Check DNS Tor control port
	if healthy, msg := checkTorControl(torControlPort2, password); healthy {
		results = append(results, HealthCheckResult{
			Service: "Tor (DNS)",
			Status:  "healthy",
			Message: msg,
			Healthy: true,
		})
	} else if checkPort("127.0.0.1", torControlPort2, socketTimeout) {
		results = append(results, HealthCheckResult{
			Service: "Tor (DNS)",
			Status:  "warning",
			Message: "Port listening but control check failed",
			Healthy: false,
		})
	} else {
		results = append(results, HealthCheckResult{
			Service: "Tor (DNS)",
			Status:  "unhealthy",
			Message: msg,
			Healthy: false,
		})
	}

	return results
}

// checkWireGuard checks WireGuard and AmneziaWG interfaces
func checkWireGuard() HealthCheckResult {
	if healthy, msg := checkWireGuardInterfaces(); healthy {
		return HealthCheckResult{
			Service: "WireGuard/AmneziaWG",
			Status:  "healthy",
			Message: msg,
			Healthy: true,
		}
	}

	return HealthCheckResult{
		Service: "WireGuard/AmneziaWG",
		Status:  "unhealthy",
		Message: "No active interfaces",
		Healthy: false,
	}
}

// runAllChecks runs all health checks
func runAllChecks() []HealthCheckResult {
	var results []HealthCheckResult

	// Check Dashboard
	results = append(results, checkDashboard())

	// Check Tor
	results = append(results, checkTor()...)

	// Check WireGuard
	results = append(results, checkWireGuard())

	return results
}

// printResults prints health check results
func printResults(results []HealthCheckResult, json bool) {
	if json {
		fmt.Print("{\"checks\":[")
		for i, result := range results {
			if i > 0 {
				fmt.Print(",")
			}
			fmt.Printf("{\"service\":\"%s\",\"status\":\"%s\",\"message\":\"%s\",\"healthy\":%t}",
				result.Service, result.Status, result.Message, result.Healthy)
		}
		fmt.Println("]}")
		return
	}

	// Text output
	allHealthy := true
	for _, result := range results {
		statusIcon := "✓"
		if !result.Healthy {
			statusIcon = "✗"
			allHealthy = false
		} else if result.Status == "warning" {
			statusIcon = "⚠"
		}

		fmt.Printf("[%s] %s: %s - %s\n", statusIcon, result.Service, result.Status, result.Message)
	}

	if allHealthy {
		fmt.Println("\nAll health checks passed")
		os.Exit(0)
	} else {
		fmt.Println("\nSome health checks failed")
		os.Exit(1)
	}
}

func main() {
	jsonOutput := flag.Bool("json", false, "Output results in JSON format")
	checkDashboardOnly := flag.Bool("dashboard", false, "Check dashboard only")
	checkTorOnly := flag.Bool("tor", false, "Check Tor only")
	checkWireGuardOnly := flag.Bool("wireguard", false, "Check WireGuard only")
	flag.Parse()

	var results []HealthCheckResult

	if *checkDashboardOnly {
		results = append(results, checkDashboard())
	} else if *checkTorOnly {
		results = append(results, checkTor()...)
	} else if *checkWireGuardOnly {
		results = append(results, checkWireGuard())
	} else {
		results = runAllChecks()
	}

	printResults(results, *jsonOutput)
}
