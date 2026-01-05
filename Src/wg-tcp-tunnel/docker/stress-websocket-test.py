#!/usr/bin/env python3
# WebSocket Testing Utilities
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

"""
WebSocket testing utilities for wg-tcp-tunnel.

Features:
- WebSocket handshake testing
- Frame validation
- Reconnection testing
- Binary frame transmission
- Ping/pong keep-alive testing
"""

import argparse
import base64
import hashlib
import json
import os
import signal
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class WebSocketTestResults:
    """Results from WebSocket tests."""
    handshake_success: int = 0
    handshake_failure: int = 0
    frames_sent: int = 0
    frames_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    reconnections: int = 0
    ping_pong_success: int = 0
    ping_pong_failure: int = 0
    errors: List[str] = field(default_factory=list)
    latencies: List[float] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time
    
    @property
    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0
    
    @property
    def success_rate(self) -> float:
        total = self.handshake_success + self.handshake_failure
        return (self.handshake_success / total * 100) if total > 0 else 0
    
    def to_dict(self) -> dict:
        return {
            "handshake_success": self.handshake_success,
            "handshake_failure": self.handshake_failure,
            "handshake_success_rate": round(self.success_rate, 2),
            "frames_sent": self.frames_sent,
            "frames_received": self.frames_received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "reconnections": self.reconnections,
            "ping_pong_success": self.ping_pong_success,
            "ping_pong_failure": self.ping_pong_failure,
            "avg_latency_ms": round(self.avg_latency, 2),
            "duration_seconds": round(self.duration, 2),
            "errors": self.errors[:10],  # Limit errors in output
        }
    
    def __str__(self) -> str:
        return f"""
=== WebSocket Test Results ===
Duration:           {self.duration:.2f}s
Handshakes:         {self.handshake_success} success, {self.handshake_failure} failed ({self.success_rate:.1f}%)
Frames:             {self.frames_sent} sent, {self.frames_received} received
Bytes:              {self.bytes_sent} sent, {self.bytes_received} received
Reconnections:      {self.reconnections}
Ping/Pong:          {self.ping_pong_success} success, {self.ping_pong_failure} failed
Avg Latency:        {self.avg_latency:.2f}ms
Errors:             {len(self.errors)}
==============================
"""


class WebSocketClient:
    """Simple WebSocket client for testing."""
    
    WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    
    # WebSocket opcodes
    OPCODE_CONTINUATION = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xA
    
    def __init__(self, host: str, port: int, path: str = "/", timeout: float = 5.0):
        self.host = host
        self.port = port
        self.path = path
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self) -> Tuple[bool, str]:
        """Perform WebSocket handshake."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.host, self.port))
            
            # Generate WebSocket key
            ws_key = base64.b64encode(os.urandom(16)).decode('utf-8')
            
            # Send HTTP upgrade request
            request = (
                f"GET {self.path} HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )
            self.sock.send(request.encode())
            
            # Read response
            response = b""
            while b"\r\n\r\n" not in response:
                chunk = self.sock.recv(1024)
                if not chunk:
                    return False, "Connection closed during handshake"
                response += chunk
            
            response_str = response.decode('utf-8', errors='ignore')
            
            # Verify response
            if "101" not in response_str:
                return False, f"Expected 101 response, got: {response_str[:100]}"
            
            # Verify accept key
            expected_accept = base64.b64encode(
                hashlib.sha1((ws_key + self.WS_MAGIC).encode()).digest()
            ).decode('utf-8')
            
            if expected_accept not in response_str:
                return False, "Invalid Sec-WebSocket-Accept"
            
            self.connected = True
            return True, "Handshake successful"
            
        except Exception as e:
            return False, str(e)
    
    def send_frame(self, data: bytes, opcode: int = OPCODE_BINARY) -> bool:
        """Send a WebSocket frame."""
        if not self.connected:
            return False
        
        try:
            # Build frame header
            frame = bytearray()
            
            # First byte: FIN + opcode
            frame.append(0x80 | opcode)
            
            # Second byte: MASK + length
            length = len(data)
            if length <= 125:
                frame.append(0x80 | length)
            elif length <= 65535:
                frame.append(0x80 | 126)
                frame.extend(struct.pack("!H", length))
            else:
                frame.append(0x80 | 127)
                frame.extend(struct.pack("!Q", length))
            
            # Masking key
            mask = os.urandom(4)
            frame.extend(mask)
            
            # Masked payload
            masked_data = bytearray(len(data))
            for i, byte in enumerate(data):
                masked_data[i] = byte ^ mask[i % 4]
            frame.extend(masked_data)
            
            self.sock.send(bytes(frame))
            return True
            
        except Exception:
            return False
    
    def receive_frame(self) -> Tuple[Optional[int], Optional[bytes]]:
        """Receive a WebSocket frame."""
        if not self.connected:
            return None, None
        
        try:
            # Read first two bytes
            header = self.sock.recv(2)
            if len(header) < 2:
                return None, None
            
            opcode = header[0] & 0x0F
            masked = (header[1] & 0x80) != 0
            length = header[1] & 0x7F
            
            # Extended length
            if length == 126:
                ext = self.sock.recv(2)
                length = struct.unpack("!H", ext)[0]
            elif length == 127:
                ext = self.sock.recv(8)
                length = struct.unpack("!Q", ext)[0]
            
            # Masking key (if present)
            mask = None
            if masked:
                mask = self.sock.recv(4)
            
            # Payload
            payload = b""
            while len(payload) < length:
                chunk = self.sock.recv(min(4096, length - len(payload)))
                if not chunk:
                    break
                payload += chunk
            
            # Unmask if needed
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            
            return opcode, payload
            
        except Exception:
            return None, None
    
    def send_ping(self, data: bytes = b"ping") -> bool:
        """Send a ping frame."""
        return self.send_frame(data, self.OPCODE_PING)
    
    def close(self):
        """Close the WebSocket connection."""
        if self.sock:
            try:
                self.send_frame(b"", self.OPCODE_CLOSE)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
        self.connected = False


class WebSocketTester:
    """WebSocket testing suite."""
    
    def __init__(
        self,
        host: str,
        port: int,
        verbose: bool = False,
    ):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.results = WebSocketTestResults()
        self.running = True
    
    def test_handshake(self, count: int = 10) -> bool:
        """Test WebSocket handshake reliability."""
        print(f"Testing WebSocket handshake ({count} attempts)...")
        sys.stdout.flush()
        
        for i in range(count):
            if not self.running:
                break
                
            client = WebSocketClient(self.host, self.port)
            start = time.time()
            success, message = client.connect()
            latency = (time.time() - start) * 1000
            
            if success:
                self.results.handshake_success += 1
                self.results.latencies.append(latency)
                if self.verbose:
                    print(f"  Handshake {i+1}/{count}: OK ({latency:.1f}ms)")
                    sys.stdout.flush()
                elif (i + 1) % 5 == 0 or (i + 1) == count:
                    # Show progress every 5 handshakes or on the last one
                    print(f"  Progress: {i+1}/{count} handshakes completed ({self.results.handshake_success} success, {self.results.handshake_failure} failed)")
                    sys.stdout.flush()
            else:
                self.results.handshake_failure += 1
                self.results.errors.append(f"Handshake {i+1}: {message}")
                print(f"  Handshake {i+1}/{count}: FAILED - {message}")
                sys.stdout.flush()
            
            client.close()
            time.sleep(0.1)  # Small delay between attempts
        
        print(f"Handshake test completed: {self.results.handshake_success} success, {self.results.handshake_failure} failed")
        sys.stdout.flush()
        return self.results.handshake_failure == 0
    
    def test_binary_frames(self, frame_count: int = 100, frame_size: int = 1024) -> bool:
        """Test binary frame transmission."""
        print(f"Testing binary frames ({frame_count} frames, {frame_size} bytes each)...")
        
        client = WebSocketClient(self.host, self.port)
        success, message = client.connect()
        
        if not success:
            self.results.errors.append(f"Connect failed: {message}")
            return False
        
        self.results.handshake_success += 1
        
        for i in range(frame_count):
            if not self.running:
                break
                
            # Send binary frame
            data = os.urandom(frame_size)
            if client.send_frame(data):
                self.results.frames_sent += 1
                self.results.bytes_sent += frame_size
            else:
                self.results.errors.append(f"Failed to send frame {i+1}")
                continue
            
            # Receive echo
            try:
                client.sock.settimeout(2.0)
                opcode, received = client.receive_frame()
                if received:
                    self.results.frames_received += 1
                    self.results.bytes_received += len(received)
                    
                    if received == data:
                        if self.verbose and (i + 1) % 10 == 0:
                            print(f"  Frame {i+1}: OK")
                    else:
                        self.results.errors.append(f"Frame {i+1}: data mismatch")
                else:
                    self.results.errors.append(f"Frame {i+1}: no response")
            except Exception as e:
                self.results.errors.append(f"Frame {i+1}: {e}")
        
        client.close()
        return len(self.results.errors) == 0
    
    def test_ping_pong(self, count: int = 10) -> bool:
        """Test WebSocket ping/pong."""
        print(f"Testing ping/pong ({count} pings)...")
        
        client = WebSocketClient(self.host, self.port)
        success, message = client.connect()
        
        if not success:
            self.results.errors.append(f"Connect failed: {message}")
            return False
        
        self.results.handshake_success += 1
        
        for i in range(count):
            if not self.running:
                break
                
            ping_data = f"ping-{i}".encode()
            start = time.time()
            
            if client.send_ping(ping_data):
                try:
                    client.sock.settimeout(2.0)
                    opcode, pong_data = client.receive_frame()
                    latency = (time.time() - start) * 1000
                    
                    if opcode == WebSocketClient.OPCODE_PONG:
                        self.results.ping_pong_success += 1
                        self.results.latencies.append(latency)
                        if self.verbose:
                            print(f"  Ping {i+1}: PONG ({latency:.1f}ms)")
                    else:
                        self.results.ping_pong_failure += 1
                        if self.verbose:
                            print(f"  Ping {i+1}: unexpected opcode {opcode}")
                except Exception as e:
                    self.results.ping_pong_failure += 1
                    self.results.errors.append(f"Ping {i+1}: {e}")
            else:
                self.results.ping_pong_failure += 1
                self.results.errors.append(f"Ping {i+1}: send failed")
            
            time.sleep(0.5)
        
        client.close()
        return self.results.ping_pong_failure == 0
    
    def test_reconnection(self, count: int = 5, delay: float = 1.0) -> bool:
        """Test reconnection after disconnection."""
        print(f"Testing reconnection ({count} cycles)...")
        
        for i in range(count):
            if not self.running:
                break
                
            client = WebSocketClient(self.host, self.port)
            success, message = client.connect()
            
            if success:
                self.results.handshake_success += 1
                self.results.reconnections += 1
                
                # Send a test frame
                test_data = f"reconnect-test-{i}".encode()
                if client.send_frame(test_data, WebSocketClient.OPCODE_TEXT):
                    self.results.frames_sent += 1
                
                if self.verbose:
                    print(f"  Reconnection {i+1}: OK")
            else:
                self.results.handshake_failure += 1
                self.results.errors.append(f"Reconnection {i+1}: {message}")
                if self.verbose:
                    print(f"  Reconnection {i+1}: FAILED - {message}")
            
            client.close()
            time.sleep(delay)
        
        return self.results.handshake_failure == 0
    
    def run_all_tests(self) -> WebSocketTestResults:
        """Run all WebSocket tests."""
        self.results.start_time = time.time()
        
        print(f"\n=== WebSocket Tests for {self.host}:{self.port} ===\n")
        
        self.test_handshake(count=10)
        print()
        
        self.test_binary_frames(frame_count=50, frame_size=512)
        print()
        
        self.test_ping_pong(count=5)
        print()
        
        self.test_reconnection(count=5)
        print()
        
        self.results.end_time = time.time()
        return self.results


def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Testing Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s localhost 51820 --all
  %(prog)s localhost 51820 --handshake 20
  %(prog)s localhost 51820 --frames 100 --frame-size 2048
  %(prog)s localhost 51820 --ping 10
  %(prog)s localhost 51820 --reconnect 10
        """,
    )
    parser.add_argument("host", help="Target host")
    parser.add_argument("port", type=int, help="Target port")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--handshake", type=int, metavar="N", help="Test N handshakes")
    parser.add_argument("--frames", type=int, metavar="N", help="Test N binary frames")
    parser.add_argument("--frame-size", type=int, default=1024, help="Frame size in bytes")
    parser.add_argument("--ping", type=int, metavar="N", help="Test N ping/pong")
    parser.add_argument("--reconnect", type=int, metavar="N", help="Test N reconnections")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-j", "--json", type=str, help="Output results to JSON file")
    
    args = parser.parse_args()
    
    tester = WebSocketTester(
        host=args.host,
        port=args.port,
        verbose=args.verbose,
    )
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nInterrupted, stopping...")
        tester.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    tester.results.start_time = time.time()
    
    if args.all:
        tester.run_all_tests()
    else:
        if args.handshake:
            tester.test_handshake(args.handshake)
        if args.frames:
            tester.test_binary_frames(args.frames, args.frame_size)
        if args.ping:
            tester.test_ping_pong(args.ping)
        if args.reconnect:
            tester.test_reconnection(args.reconnect)
    
    tester.results.end_time = time.time()
    
    print(tester.results)
    
    if args.json:
        with open(args.json, "w") as f:
            json.dump(tester.results.to_dict(), f, indent=2)
        print(f"Results saved to {args.json}")
    
    # Exit with error if failures
    if tester.results.handshake_failure > 0 or tester.results.ping_pong_failure > 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

