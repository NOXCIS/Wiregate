#!/bin/bash
# Test script for wg-tcp-tunnel Docker setup
# SPDX-FileCopyrightText: 2023-2025 Arkadiusz Bokowy and contributors
# SPDX-License-Identifier: MIT

set -e

echo "=== wg-tcp-tunnel Docker Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker or docker-compose not found${NC}"
    exit 1
fi

# Use docker compose if available (newer), otherwise docker-compose
COMPOSE_CMD="docker-compose"
if command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
fi

echo "Using: ${COMPOSE_CMD}"
echo ""

# Build and start containers
echo -e "${YELLOW}Building containers...${NC}"
${COMPOSE_CMD} build

echo -e "${YELLOW}Starting containers...${NC}"
${COMPOSE_CMD} up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Check if containers are running
echo -e "${YELLOW}Checking container status...${NC}"
${COMPOSE_CMD} ps

# Test connectivity
echo ""
echo -e "${YELLOW}Testing connectivity...${NC}"

# Test server TCP port
if nc -z localhost 51820 2>/dev/null; then
    echo -e "${GREEN}✓ Server TCP port 51820 is open${NC}"
else
    echo -e "${RED}✗ Server TCP port 51820 is not accessible${NC}"
fi

# Test client UDP port
if nc -zu localhost 51822 2>/dev/null; then
    echo -e "${GREEN}✓ Client UDP port 51822 is open${NC}"
else
    echo -e "${YELLOW}⚠ Client UDP port 51822 check (UDP checks may be unreliable)${NC}"
fi

# Send a test packet
echo ""
echo -e "${YELLOW}Sending test packet...${NC}"
TEST_MESSAGE="Hello from test script at $(date +%H:%M:%S)"
echo "${TEST_MESSAGE}" | nc -u -w 1 localhost 51822 2>/dev/null && \
    echo -e "${GREEN}✓ Test packet sent${NC}" || \
    echo -e "${YELLOW}⚠ Test packet send (may have succeeded)${NC}"

# Show logs
echo ""
echo -e "${YELLOW}Recent logs:${NC}"
echo "--- Server logs ---"
${COMPOSE_CMD} logs --tail=10 server
echo ""
echo "--- Client logs ---"
${COMPOSE_CMD} logs --tail=10 client

echo ""
echo -e "${GREEN}=== Test Complete ==="
echo "View full logs with: ${COMPOSE_CMD} logs -f"
echo "Stop containers with: ${COMPOSE_CMD} down${NC}"

