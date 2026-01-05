#!/usr/bin/env python3
# Enhanced UDP Stress Test Server
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

"""
UDP Stress Test Server with statistics collection.

Features:
- Echo with sequence number validation
- Statistics collection
- Packet loss detection
- Throughput measurement
- Real-time metrics reporting
"""

import argparse
import json
import signal
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class Statistics:
    """Statistics for the stress test server."""
    packets_received: int = 0
    packets_echoed: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    unique_sequences: Set[int] = field(default_factory=set)
    duplicate_sequences: int = 0
    gaps_detected: int = 0
    start_time: float = 0.0
    last_activity: float = 0.0
    errors: int = 0
    clients: Dict[str, int] = field(default_factory=dict)  # client addr -> packet count
    
    @property
    def duration(self) -> float:
        return time.time() - self.start_time if self.start_time else 0
    
    @property
    def packets_per_second(self) -> float:
        return self.packets_received / self.duration if self.duration > 0 else 0
    
    @property
    def throughput_mbps(self) -> float:
        return (self.bytes_received * 8 / 1_000_000) / self.duration if self.duration > 0 else 0
    
    @property
    def unique_clients(self) -> int:
        return len(self.clients)
    
    def to_dict(self) -> dict:
        return {
            "packets_received": self.packets_received,
            "packets_echoed": self.packets_echoed,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "unique_sequences": len(self.unique_sequences),
            "duplicate_sequences": self.duplicate_sequences,
            "gaps_detected": self.gaps_detected,
            "duration_seconds": round(self.duration, 2),
            "packets_per_second": round(self.packets_per_second, 2),
            "throughput_mbps": round(self.throughput_mbps, 4),
            "unique_clients": self.unique_clients,
            "errors": self.errors,
        }
    
    def __str__(self) -> str:
        return f"""
=== Server Statistics ===
Duration:           {self.duration:.2f}s
Packets Received:   {self.packets_received}
Packets Echoed:     {self.packets_echoed}
Unique Sequences:   {len(self.unique_sequences)}
Duplicate Packets:  {self.duplicate_sequences}
Sequence Gaps:      {self.gaps_detected}
Throughput:         {self.packets_per_second:.2f} pps / {self.throughput_mbps:.4f} Mbps
Unique Clients:     {self.unique_clients}
Errors:             {self.errors}
=========================
"""


class StressTestServer:
    """UDP stress test server with echo and statistics."""
    
    # Packet format: sequence (4 bytes) + timestamp (8 bytes) + payload
    HEADER_FORMAT = "!Id"  # Network byte order: unsigned int + double
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    def __init__(
        self,
        host: str,
        port: int,
        verbose: bool = False,
        stats_interval: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.stats_interval = stats_interval
        
        self.stats = Statistics()
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.lock = threading.Lock()
        self.last_seq_by_client: Dict[str, int] = {}
    
    def parse_packet(self, data: bytes) -> tuple:
        """Parse a packet and return (seq, timestamp, payload)."""
        if len(data) < self.HEADER_SIZE:
            return None, None, None
        seq, timestamp = struct.unpack(self.HEADER_FORMAT, data[:self.HEADER_SIZE])
        payload = data[self.HEADER_SIZE:]
        return seq, timestamp, payload
    
    def stats_reporter_thread(self):
        """Thread that periodically reports statistics."""
        while self.running:
            time.sleep(self.stats_interval)
            if self.running:
                with self.lock:
                    print(f"\n[{time.strftime('%H:%M:%S')}] Stats: "
                          f"{self.stats.packets_received} pkts, "
                          f"{self.stats.packets_per_second:.1f} pps, "
                          f"{self.stats.unique_clients} clients")
    
    def run(self):
        """Run the stress test server."""
        print(f"Starting stress test server on {self.host}:{self.port}")
        print(f"Stats interval: {self.stats_interval}s")
        print("Press Ctrl+C to stop\n")
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        
        self.running = True
        self.stats.start_time = time.time()
        
        # Start stats reporter thread
        reporter = threading.Thread(target=self.stats_reporter_thread, daemon=True)
        reporter.start()
        
        try:
            while self.running:
                try:
                    self.sock.settimeout(1.0)
                    data, addr = self.sock.recvfrom(65535)
                    recv_time = time.time()
                    
                    client_key = f"{addr[0]}:{addr[1]}"
                    
                    seq, timestamp, payload = self.parse_packet(data)
                    
                    with self.lock:
                        self.stats.packets_received += 1
                        self.stats.bytes_received += len(data)
                        self.stats.last_activity = recv_time
                        
                        # Track client
                        if client_key not in self.stats.clients:
                            self.stats.clients[client_key] = 0
                        self.stats.clients[client_key] += 1
                        
                        # Track sequences
                        if seq is not None:
                            if seq in self.stats.unique_sequences:
                                self.stats.duplicate_sequences += 1
                            else:
                                self.stats.unique_sequences.add(seq)
                            
                            # Check for gaps
                            if client_key in self.last_seq_by_client:
                                expected = self.last_seq_by_client[client_key] + 1
                                if seq != expected and seq > expected:
                                    self.stats.gaps_detected += seq - expected
                            self.last_seq_by_client[client_key] = seq
                    
                    if self.verbose and seq is not None and seq % 100 == 0:
                        print(f"Received packet #{seq} from {client_key}")
                    
                    # Echo back
                    try:
                        self.sock.sendto(data, addr)
                        with self.lock:
                            self.stats.packets_echoed += 1
                            self.stats.bytes_sent += len(data)
                    except Exception as e:
                        with self.lock:
                            self.stats.errors += 1
                        if self.verbose:
                            print(f"Echo error to {client_key}: {e}")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        with self.lock:
                            self.stats.errors += 1
                        if self.verbose:
                            print(f"Receive error: {e}")
                            
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False
            self.sock.close()
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="UDP Stress Test Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 0.0.0.0 51820
  %(prog)s 0.0.0.0 51820 --stats-interval 10
  %(prog)s 0.0.0.0 51820 --verbose
        """,
    )
    parser.add_argument("host", nargs="?", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("port", type=int, nargs="?", default=51820, help="Bind port (default: 51820)")
    parser.add_argument("-i", "--stats-interval", type=float, default=5.0, help="Stats reporting interval (default: 5.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-j", "--json", type=str, help="Output final results to JSON file")
    
    args = parser.parse_args()
    
    server = StressTestServer(
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        stats_interval=args.stats_interval,
    )
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted, stopping...")
        server.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    stats = server.run()
    print(stats)
    
    # Output to JSON if requested
    if args.json:
        with open(args.json, "w") as f:
            json.dump(stats.to_dict(), f, indent=2)
        print(f"Results saved to {args.json}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

