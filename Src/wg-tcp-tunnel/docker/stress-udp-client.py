#!/usr/bin/env python3
# Enhanced UDP Stress Test Client
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

"""
UDP Stress Test Client with packet sequencing, latency tracking, and metrics.

Features:
- Configurable packet rate
- Packet sequence numbers for loss detection
- Timestamp tracking for latency measurement
- Statistics reporting
- Support for both raw TCP and WebSocket transport modes
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
from typing import Dict, Optional


@dataclass
class Statistics:
    """Statistics for the stress test."""
    packets_sent: int = 0
    packets_received: int = 0
    packets_lost: int = 0
    packets_out_of_order: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    latencies: list = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    errors: int = 0
    
    def add_latency(self, latency_ms: float):
        self.latencies.append(latency_ms)
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else time.time() - self.start_time
    
    @property
    def packets_per_second(self) -> float:
        return self.packets_sent / self.duration if self.duration > 0 else 0
    
    @property
    def throughput_mbps(self) -> float:
        return (self.bytes_sent * 8 / 1_000_000) / self.duration if self.duration > 0 else 0
    
    @property
    def loss_rate(self) -> float:
        return (self.packets_lost / self.packets_sent * 100) if self.packets_sent > 0 else 0
    
    @property
    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0
    
    @property
    def min_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0
    
    @property
    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0
    
    @property
    def p50_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.5)
        return sorted_latencies[idx]
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    def to_dict(self) -> dict:
        return {
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packets_lost": self.packets_lost,
            "packets_out_of_order": self.packets_out_of_order,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "duration_seconds": round(self.duration, 2),
            "packets_per_second": round(self.packets_per_second, 2),
            "throughput_mbps": round(self.throughput_mbps, 4),
            "loss_rate_percent": round(self.loss_rate, 2),
            "latency_ms": {
                "avg": round(self.avg_latency, 2),
                "min": round(self.min_latency, 2),
                "max": round(self.max_latency, 2),
                "p50": round(self.p50_latency, 2),
                "p95": round(self.p95_latency, 2),
                "p99": round(self.p99_latency, 2),
            },
            "errors": self.errors,
        }
    
    def __str__(self) -> str:
        return f"""
=== Stress Test Results ===
Duration:           {self.duration:.2f}s
Packets Sent:       {self.packets_sent}
Packets Received:   {self.packets_received}
Packets Lost:       {self.packets_lost} ({self.loss_rate:.2f}%)
Out of Order:       {self.packets_out_of_order}
Throughput:         {self.packets_per_second:.2f} pps / {self.throughput_mbps:.4f} Mbps
Latency (ms):       avg={self.avg_latency:.2f} min={self.min_latency:.2f} max={self.max_latency:.2f}
                    p50={self.p50_latency:.2f} p95={self.p95_latency:.2f} p99={self.p99_latency:.2f}
Errors:             {self.errors}
===========================
"""


class StressTestClient:
    """UDP stress test client."""
    
    # Packet format: sequence (4 bytes) + timestamp (8 bytes) + payload
    HEADER_FORMAT = "!Id"  # Network byte order: unsigned int + double
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    
    def __init__(
        self,
        host: str,
        port: int,
        rate: float = 100.0,
        duration: float = 10.0,
        packet_size: int = 256,
        timeout: float = 1.0,
        verbose: bool = False,
    ):
        self.host = host
        self.port = port
        self.rate = rate
        self.duration = duration
        self.packet_size = max(packet_size, self.HEADER_SIZE + 1)
        self.timeout = timeout
        self.verbose = verbose
        
        self.stats = Statistics()
        self.running = False
        self.sock: Optional[socket.socket] = None
        self.pending_packets: Dict[int, float] = {}  # seq -> send_time
        self.last_seq_received = -1
        self.lock = threading.Lock()
    
    def create_packet(self, seq: int) -> bytes:
        """Create a packet with sequence number and timestamp."""
        timestamp = time.time()
        header = struct.pack(self.HEADER_FORMAT, seq, timestamp)
        payload_size = self.packet_size - self.HEADER_SIZE
        payload = bytes([seq % 256] * payload_size)
        return header + payload
    
    def parse_packet(self, data: bytes) -> tuple:
        """Parse a packet and return (seq, send_timestamp, payload)."""
        if len(data) < self.HEADER_SIZE:
            return None, None, None
        seq, timestamp = struct.unpack(self.HEADER_FORMAT, data[:self.HEADER_SIZE])
        payload = data[self.HEADER_SIZE:]
        return seq, timestamp, payload
    
    def sender_thread(self):
        """Thread that sends packets at the specified rate."""
        interval = 1.0 / self.rate if self.rate > 0 else 0
        seq = 0
        next_send = time.time()
        
        while self.running and (time.time() - self.stats.start_time) < self.duration:
            try:
                packet = self.create_packet(seq)
                send_time = time.time()
                
                self.sock.sendto(packet, (self.host, self.port))
                
                with self.lock:
                    self.pending_packets[seq] = send_time
                    self.stats.packets_sent += 1
                    self.stats.bytes_sent += len(packet)
                
                if self.verbose and seq % 1000 == 0:
                    print(f"Sent packet #{seq} ({self.stats.packets_sent} total)")
                
                seq += 1
                
                # Rate limiting
                if interval > 0:
                    next_send += interval
                    sleep_time = next_send - time.time()
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    elif sleep_time < -0.1:
                        # Falling behind, reset
                        next_send = time.time()
                        
            except Exception as e:
                with self.lock:
                    self.stats.errors += 1
                if self.verbose:
                    print(f"Send error: {e}")
    
    def receiver_thread(self):
        """Thread that receives packets and calculates latency."""
        while self.running:
            try:
                self.sock.settimeout(0.1)
                data, addr = self.sock.recvfrom(65535)
                recv_time = time.time()
                
                seq, send_timestamp, payload = self.parse_packet(data)
                if seq is None:
                    continue
                
                with self.lock:
                    # Only count as received if this is a packet we actually sent
                    # (i.e., it's in pending_packets)
                    if seq in self.pending_packets:
                        self.stats.packets_received += 1
                        self.stats.bytes_received += len(data)
                        latency_ms = (recv_time - self.pending_packets[seq]) * 1000
                        self.stats.add_latency(latency_ms)
                        del self.pending_packets[seq]
                    else:
                        # Duplicate or unexpected packet - don't count as received
                        # but still count bytes for throughput measurement
                        self.stats.bytes_received += len(data)
                        latency_ms = 0
                    
                    # Check for out-of-order
                    if seq < self.last_seq_received:
                        self.stats.packets_out_of_order += 1
                    self.last_seq_received = max(self.last_seq_received, seq)
                
                if self.verbose and seq % 1000 == 0:
                    if latency_ms > 0:
                        print(f"Received packet #{seq}, latency: {latency_ms:.2f}ms ({self.stats.packets_received} total)")
                    else:
                        print(f"Received duplicate/unexpected packet #{seq} ({self.stats.packets_received} unique received)")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    with self.lock:
                        self.stats.errors += 1
                    if self.verbose:
                        print(f"Receive error: {e}")
    
    def run(self) -> Statistics:
        """Run the stress test and return statistics."""
        print(f"Starting stress test to {self.host}:{self.port}")
        print(f"Rate: {self.rate} pps, Duration: {self.duration}s, Packet size: {self.packet_size} bytes")
        print()
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.running = True
        self.stats.start_time = time.time()
        
        # Start threads
        sender = threading.Thread(target=self.sender_thread, daemon=True)
        receiver = threading.Thread(target=self.receiver_thread, daemon=True)
        
        sender.start()
        receiver.start()
        
        # Show progress during test
        if self.verbose:
            progress_interval = max(1.0, self.duration / 10)  # Show progress ~10 times
            last_progress = time.time()
            while sender.is_alive():
                time.sleep(0.5)
                elapsed = time.time() - self.stats.start_time
                if elapsed - last_progress >= progress_interval:
                    with self.lock:
                        sent = self.stats.packets_sent
                        received = self.stats.packets_received
                    if elapsed > 0:
                        print(f"[{elapsed:.1f}s] Progress: {sent} sent, {received} received ({sent/elapsed:.1f} pps)")
                    last_progress = elapsed
        
        # Wait for sender to complete
        sender.join()
        
        # Wait a bit for remaining responses
        if self.verbose:
            print("Waiting for remaining responses...")
        time.sleep(self.timeout)
        
        self.running = False
        self.stats.end_time = time.time()
        
        # Calculate lost packets
        with self.lock:
            self.stats.packets_lost = len(self.pending_packets)
        
        receiver.join(timeout=1.0)
        self.sock.close()
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(
        description="UDP Stress Test Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s localhost 51822 --rate 100 --duration 10
  %(prog)s localhost 51822 --rate 1000 --duration 60 --size 1024
  %(prog)s localhost 51822 --rate 500 --duration 30 --json results.json
        """,
    )
    parser.add_argument("host", help="Target host")
    parser.add_argument("port", type=int, help="Target port")
    parser.add_argument("-r", "--rate", type=float, default=100, help="Packets per second (default: 100)")
    parser.add_argument("-d", "--duration", type=float, default=10, help="Test duration in seconds (default: 10)")
    parser.add_argument("-s", "--size", type=int, default=256, help="Packet size in bytes (default: 256)")
    parser.add_argument("-t", "--timeout", type=float, default=2.0, help="Response timeout in seconds (default: 2.0)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-j", "--json", type=str, help="Output results to JSON file")
    
    args = parser.parse_args()
    
    client = StressTestClient(
        host=args.host,
        port=args.port,
        rate=args.rate,
        duration=args.duration,
        packet_size=args.size,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted, stopping...")
        client.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    
    stats = client.run()
    print(stats)
    
    # Output to JSON if requested
    if args.json:
        with open(args.json, "w") as f:
            json.dump(stats.to_dict(), f, indent=2)
        print(f"Results saved to {args.json}")
    
    # Exit with error if significant packet loss
    if stats.loss_rate > 5:
        print("WARNING: High packet loss detected!")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()

