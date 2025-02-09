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
	"bufio"
	"bytes"
	"flag"
	"fmt"
	"net"
	"os"
	"strings"
	"time"
)

const (
	logDir          = "./log"
	logFile         = logDir + "/tor_circuit_refresh_log.txt"
	bufferSize      = 8192
	torControlPort1 = 9051
	torControlPort2 = 9054
	socketTimeout   = 5 * time.Second
)

// logMessage logs messages to a file and optionally prints to the console.
func logMessage(message string, addNewlines, toConsole bool) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	logMsg := fmt.Sprintf("[%s] %s", timestamp, message)

	if toConsole {
		fmt.Println(logMsg)
	}

	// Ensure log directory exists
	if err := os.MkdirAll(logDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] Could not create log directory: %v\n", err)
		return
	}

	// Open or create log file
	f, err := os.OpenFile(logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		fmt.Fprintf(os.Stderr, "[ERROR] Could not open log file: %v\n", err)
		return
	}
	defer f.Close()

	writer := bufio.NewWriter(f)
	writer.WriteString(logMsg + "\n")
	if addNewlines {
		writer.WriteString(strings.Repeat("\n", 5))
	}
	writer.Flush()
}

// sendSignal sends a NEWNYM signal to the Tor control port and retrieves circuit status.
func sendSignal(port int, password string, statusBuffer *bytes.Buffer) bool {
	address := fmt.Sprintf("127.0.0.1:%d", port)
	conn, err := net.DialTimeout("tcp", address, socketTimeout)
	if err != nil {
		logMessage("[TOR-FLUX] [ERROR] Connection to Tor control port failed", false, false)
		return false
	}
	defer conn.Close()

	conn.SetDeadline(time.Now().Add(socketTimeout))

	reader := bufio.NewReader(conn)

	// Authenticate
	if password != "" {
		authCmd := fmt.Sprintf("AUTHENTICATE \"%s\"\r\n", password)
		fmt.Fprint(conn, authCmd)

		resp, _ := reader.ReadString('\n')
		if !strings.Contains(resp, "250") {
			logMessage("[TOR-FLUX] [ERROR] Tor authentication failed", false, false)
			return false
		}
	}

	// Send NEWNYM signal
	fmt.Fprint(conn, "SIGNAL NEWNYM\r\n")
	resp, _ := reader.ReadString('\n')
	if !strings.Contains(resp, "250") {
		logMessage("[TOR-FLUX] [ERROR] Failed to send NEWNYM signal", false, false)
		return false
	}

	// Get circuit status
	fmt.Fprint(conn, "GETINFO circuit-status\r\n")
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			break
		}
		statusBuffer.WriteString(line)
	}

	logMessage("[TOR-FLUX] Current Circuit Status:", false, false)
	logMessage(statusBuffer.String(), false, false)
	logMessage("[TOR-FLUX] New Tor Circuits Requested Successfully.", false, false)

	return true
}

// sendHUP sends a HUP signal to the specified Tor control port
func sendHUP(port int, password string) bool {
	address := fmt.Sprintf("127.0.0.1:%d", port)
	conn, err := net.DialTimeout("tcp", address, socketTimeout)
	if err != nil {
		logMessage("[TOR-FLUX] [ERROR] Connection to Tor control port failed", false, false)
		return false
	}
	defer conn.Close()

	conn.SetDeadline(time.Now().Add(socketTimeout))
	reader := bufio.NewReader(conn)

	// Authenticate
	if password != "" {
		authCmd := fmt.Sprintf("AUTHENTICATE \"%s\"\r\n", password)
		fmt.Fprint(conn, authCmd)

		resp, _ := reader.ReadString('\n')
		if !strings.Contains(resp, "250") {
			logMessage("[TOR-FLUX] [ERROR] Tor authentication failed", false, false)
			return false
		}
	}

	// Send SIGNAL HUP
	fmt.Fprint(conn, "SIGNAL HUP\r\n")
	resp, _ := reader.ReadString('\n')
	if !strings.Contains(resp, "250") {
		logMessage("[TOR-FLUX] [ERROR] Failed to send HUP signal", false, false)
		return false
	}

	logMessage("[TOR-FLUX] HUP signal sent successfully", false, true)
	return true
}

func main() {
	// Define command line flags
	configType := flag.String("config", "", "Configuration type (main/dns) for HUP signal")
	flag.Parse()

	password := os.Getenv("VANGUARD")
	if password == "" {
		logMessage("[TOR-FLUX] [ERROR] Tor control port password (VANGUARD) is not set or empty.", false, true)
		os.Exit(1)
	}

	// If config type is specified, send HUP signal
	if *configType != "" {
		var port int
		switch strings.ToLower(*configType) {
		case "main":
			port = torControlPort1
		case "dns":
			port = torControlPort2
		default:
			logMessage("[TOR-FLUX] [ERROR] Invalid config type. Use 'main' or 'dns'.", false, true)
			os.Exit(1)
		}

		if !sendHUP(port, password) {
			os.Exit(1)
		}
		return
	}

	// Original NEWNYM functionality
	logMessage("[TOR-FLUX] Starting Tor circuit refresh...", false, true)
	statusBuffer1 := &bytes.Buffer{}
	statusBuffer2 := &bytes.Buffer{}
	sendSignal(torControlPort1, password, statusBuffer1)
	sendSignal(torControlPort2, password, statusBuffer2)
	logMessage("[TOR-FLUX] Tor circuit refresh completed.", true, true)
}
