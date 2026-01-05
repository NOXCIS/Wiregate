#!/usr/bin/env python3
# Simple UDP Echo Server for Testing
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

import socket
import struct
import sys
import re

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 51820
QUIET = sys.argv[2] == '--quiet' if len(sys.argv) > 2 else False

# Packet format from stress-udp-client.py: sequence (4 bytes) + timestamp (8 bytes)
HEADER_FORMAT = "!Id"  # Network byte order: unsigned int + double
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', PORT))

if not QUIET:
    print(f"UDP Echo Server listening on 0.0.0.0:{PORT}")
    print("Press Ctrl+C to stop")
    print("")

packet_count = 0
try:
    while True:
        data, addr = sock.recvfrom(4096)
        packet_count += 1
        
        # Try to extract sequence number from binary packet header
        seq_num = None
        is_binary = False
        text = None
        
        if len(data) >= HEADER_SIZE:
            try:
                seq_num, timestamp = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
                is_binary = True
            except struct.error:
                pass
        
        # If no binary header, try to decode as text and extract number from text
        if seq_num is None:
            try:
                text = data.decode('utf-8')
                # Try to extract packet number from text like "Test packet #123" or "Test packet #123 at ..."
                match = re.search(r'#(\d+)', text)
                if match:
                    seq_num = int(match.group(1))
            except UnicodeDecodeError:
                is_binary = True
                text = f"<binary {len(data)} bytes>"
        
        # Logging: show actual packet number even when only logging every 100th packet
        if not QUIET:
            if seq_num is not None:
                # For packets with sequence numbers, log every 100th but show actual seq_num
                if packet_count % 100 == 0:
                    print(f"Received from {addr}: packet #{seq_num} (total received: {packet_count}, size: {len(data)} bytes)")
            else:
                # For packets without sequence numbers, show the text or binary info
                if text:
                    print(f"Received from {addr}: {text}")
                else:
                    print(f"Received from {addr}: <binary {len(data)} bytes>")
        
        # Echo back
        sock.sendto(data, addr)
        
        if not QUIET and not is_binary and seq_num is None:
            print(f"Echoed back to {addr}")
except KeyboardInterrupt:
    if not QUIET:
        print(f"\nShutting down... (processed {packet_count} packets)")
finally:
    sock.close()

