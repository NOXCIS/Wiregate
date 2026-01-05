#!/usr/bin/env python3
# Rapid Connection Test for UDP Tunnel
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

"""
Test rapid UDP packet sending and receiving through the tunnel.

This test sends UDP packets rapidly and verifies that responses are received.
It properly handles UDP's connectionless nature and accounts for tunnel overhead.
"""

import argparse
import socket
import sys
import time
import threading
from typing import Dict, Optional


class RapidConnectionTester:
    """Test rapid UDP connections through the tunnel."""
    
    def __init__(
        self,
        host: str,
        port: int,
        num_attempts: int = 100,
        timeout: float = 3.0,
        packet_size: int = 64,
    ):
        self.host = host
        self.port = port
        self.num_attempts = num_attempts
        self.timeout = timeout
        self.packet_size = packet_size
        
        self.success = 0
        self.failure = 0
        self.responses: Dict[int, bytes] = {}
        self.lock = threading.Lock()
    
    def send_and_receive(self, seq: int) -> bool:
        """Send a packet and wait for response."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        
        try:
            # Create packet with sequence number
            packet = f"rapid-{seq}".encode('utf-8')
            if len(packet) < self.packet_size:
                packet = packet + b'x' * (self.packet_size - len(packet))
            
            # Send packet
            send_time = time.time()
            sock.sendto(packet, (self.host, self.port))
            
            # Wait for response
            try:
                data, addr = sock.recvfrom(4096)
                recv_time = time.time()
                latency = (recv_time - send_time) * 1000  # ms
                
                # Verify response matches (echo server should send back same data)
                if data == packet:
                    with self.lock:
                        self.responses[seq] = data
                        self.success += 1
                    return True
                else:
                    # Response doesn't match
                    with self.lock:
                        self.failure += 1
                    return False
            except socket.timeout:
                # No response received
                with self.lock:
                    self.failure += 1
                return False
        except Exception as e:
            # Send or other error
            with self.lock:
                self.failure += 1
            return False
        finally:
            sock.close()
    
    def run(self, json_output: bool = False):
        """Run the rapid connection test."""
        if not json_output:
            print(f"Testing rapid UDP connections to {self.host}:{self.port}")
            print(f"Attempts: {self.num_attempts}, Timeout: {self.timeout}s, Packet size: {self.packet_size} bytes")
            print()
        
        start_time = time.time()
        
        # Send all packets rapidly
        threads = []
        for i in range(1, self.num_attempts + 1):
            thread = threading.Thread(target=self.send_and_receive, args=(i,))
            thread.start()
            threads.append(thread)
            
            # Small delay to avoid overwhelming the system
            if i % 10 == 0:
                time.sleep(0.01)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        elapsed = time.time() - start_time
        
        # Report results (only if not JSON output)
        if not json_output:
            print(f"Results: {self.success} success, {self.failure} failed")
            print(f"Success rate: {self.success / self.num_attempts * 100:.1f}%")
            print(f"Total time: {elapsed:.2f}s")
            print(f"Rate: {self.num_attempts / elapsed:.1f} attempts/second")
        
        return {
            'attempts': self.num_attempts,
            'success': self.success,
            'failure': self.failure,
            'success_rate_percent': self.success / self.num_attempts * 100 if self.num_attempts > 0 else 0,
            'duration_seconds': elapsed,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Test rapid UDP connections through tunnel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("host", help="Target host")
    parser.add_argument("port", type=int, help="Target port")
    parser.add_argument("-n", "--num-attempts", type=int, default=100,
                       help="Number of connection attempts (default: 100)")
    parser.add_argument("-t", "--timeout", type=float, default=3.0,
                       help="Timeout per attempt in seconds (default: 3.0)")
    parser.add_argument("-s", "--size", type=int, default=64,
                       help="Packet size in bytes (default: 64)")
    parser.add_argument("-j", "--json", action="store_true",
                       help="Output results as JSON")
    
    args = parser.parse_args()
    
    tester = RapidConnectionTester(
        host=args.host,
        port=args.port,
        num_attempts=args.num_attempts,
        timeout=args.timeout,
        packet_size=args.size,
    )
    
    results = tester.run(json_output=args.json)
    
    if args.json:
        import json
        # Output only JSON when --json is used
        print(json.dumps(results))
    else:
        # Exit with error if success rate is too low
        if results['success_rate_percent'] < 50:
            print("ERROR: Success rate below 50%")
            sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

