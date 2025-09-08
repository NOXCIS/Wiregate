#!/usr/bin/env python3
"""
Test Redis connection and KEYS command
"""

import os
import sys
import redis

def test_redis_connection():
    """Test basic Redis connection"""
    print("Testing Redis connection...")
    
    try:
        # Connect to Redis
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD', 'wiregate_redis_password'),
            decode_responses=True
        )
        
        # Test basic connection
        redis_client.ping()
        print("✓ Redis connection successful")
        
        # Test KEYS command
        print("Testing KEYS command...")
        try:
            keys = redis_client.keys("wiregate:*")
            print(f"✓ KEYS command works, found {len(keys)} keys")
        except redis.exceptions.ResponseError as e:
            if "unknown command 'KEYS'" in str(e):
                print("✗ KEYS command is disabled")
                print("Testing SCAN command as fallback...")
                try:
                    cursor = 0
                    count = 0
                    while True:
                        cursor, partial_keys = redis_client.scan(cursor, match="wiregate:*", count=100)
                        count += len(partial_keys)
                        if cursor == 0:
                            break
                    print(f"✓ SCAN command works, found {count} keys")
                except Exception as scan_error:
                    print(f"✗ SCAN command failed: {scan_error}")
            else:
                print(f"✗ KEYS command failed: {e}")
        
        # Test basic operations
        print("Testing basic Redis operations...")
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        if value == "test_value":
            print("✓ Basic SET/GET operations work")
        else:
            print("✗ Basic SET/GET operations failed")
        
        # Clean up
        redis_client.delete("test_key")
        print("✓ Cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Redis Connection Test")
    print("=" * 50)
    
    if test_redis_connection():
        print("\n🎉 Redis is working correctly!")
        return 0
    else:
        print("\n❌ Redis connection failed!")
        return 1

if __name__ == "__main__":
    exit(main())
