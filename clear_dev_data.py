#!/usr/bin/env python3
"""
Script to clear development data in Redis.
Run this when you want to start fresh during development.
"""

import sys
import os

# Add the Src directory to the path so we can import wiregate modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

from wiregate.modules.DataBase.DataBaseManager import get_redis_manager

def main():
    print("Clearing development data from Redis...")
    
    try:
        # Get Redis manager
        redis_manager = get_redis_manager()
        
        # Test connection
        redis_manager.redis_client.ping()
        print("✓ Connected to Redis")
        
        # Clear all WireGate data
        all_keys = redis_manager.get_all_keys()
        if all_keys:
            deleted_count = redis_manager.delete_keys(all_keys)
            print(f"✓ Deleted {deleted_count} keys from Redis")
        else:
            print("ℹ No data found to clear")
            
        print("\n✓ Development data cleared!")
        print("You can now restart WireGate and it will start fresh.")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure Redis is running and accessible.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
