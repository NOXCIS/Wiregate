#!/bin/bash
# Simple UDP Echo Server for Testing
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

PORT=${1:-51820}

echo "UDP Echo Server listening on 0.0.0.0:${PORT}"
echo "Press Ctrl+C to stop"
echo ""

# Use netcat to create a UDP echo server
# OpenBSD netcat syntax: nc -u -l -p PORT
# GNU netcat syntax: nc -u -l PORT
while true; do
    # Try OpenBSD netcat syntax first
    if nc -u -l -p "${PORT}" 2>/dev/null; then
        continue
    fi
    # Try GNU netcat syntax
    if nc -u -l "${PORT}" 2>/dev/null; then
        continue
    fi
    # If both fail, wait and retry
    echo "Warning: netcat failed, retrying..."
    sleep 1
done

