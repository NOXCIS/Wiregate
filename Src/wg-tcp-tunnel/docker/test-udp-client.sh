#!/bin/bash
# Simple UDP Test Client
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

HOST=${1:-127.0.0.1}
PORT=${2:-51822}
INTERVAL=${3:-2}

echo "UDP Test Client sending to ${HOST}:${PORT} every ${INTERVAL} seconds"
echo "Press Ctrl+C to stop"
echo ""

COUNTER=1
while true; do
    MESSAGE="Test packet #${COUNTER} at $(date +%H:%M:%S)"
    echo "Sending: ${MESSAGE}"
    echo "${MESSAGE}" | nc -u -w 1 "${HOST}" "${PORT}" 2>/dev/null || {
        echo "Failed to send packet"
    }
    sleep "${INTERVAL}"
    COUNTER=$((COUNTER + 1))
done

