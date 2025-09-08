#!/bin/bash

echo "=========================================="
echo "WireGate Redis KEYS Command Fix"
echo "=========================================="

echo "Stopping Redis container..."
docker-compose stop redis

echo "Starting Redis container with updated configuration..."
docker-compose up -d redis

echo "Waiting for Redis to start..."
sleep 5

echo "Testing Redis connection..."
python3 test_redis_connection.py

echo "=========================================="
echo "Fix complete! Redis should now work properly."
echo "You can now restart WireGate:"
echo "docker-compose up -d wiregate"
echo "=========================================="
