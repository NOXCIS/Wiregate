#!/usr/bin/env python3
"""
Test script for Redis database migration
This script tests the new Redis-based database functionality
"""

import os
import sys
import json
from datetime import datetime

# Add the Src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

def test_redis_connection():
    """Test Redis connection"""
    print("Testing Redis connection...")
    try:
        from wiregate.modules.DataBase.DataBaseManager import get_redis_manager
        manager = get_redis_manager()
        
        # Test KEYS command specifically
        try:
            keys = manager.redis_client.keys("wiregate:*")
            print(f"✓ Redis connection successful (KEYS command works, found {len(keys)} keys)")
        except Exception as keys_error:
            if "unknown command 'KEYS'" in str(keys_error):
                print("✓ Redis connection successful (KEYS disabled, using SCAN fallback)")
            else:
                print(f"✗ Redis KEYS command failed: {keys_error}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\nTesting database operations...")
    try:
        from wiregate.modules.DataBase.DataBaseManager import ConfigurationDatabase
        
        # Create a test configuration database
        test_config = "test_config"
        db = ConfigurationDatabase(test_config)
        
        # Test table creation
        print("  Creating test tables...")
        db.create_database()
        print("  ✓ Tables created successfully")
        
        # Test peer insertion
        print("  Testing peer insertion...")
        test_peer = {
            "id": "test_peer_1",
            "name": "Test Peer",
            "private_key": "test_private_key",
            "DNS": "1.1.1.1",
            "endpoint_allowed_ip": "0.0.0.0/0",
            "total_receive": 0.0,
            "total_sent": 0.0,
            "total_data": 0.0,
            "endpoint": "N/A",
            "status": "stopped",
            "latest_handshake": "N/A",
            "allowed_ip": "10.0.0.2/32",
            "cumu_receive": 0.0,
            "cumu_sent": 0.0,
            "cumu_data": 0.0,
            "mtu": 1420,
            "keepalive": 21,
            "remote_endpoint": "N/A",
            "preshared_key": "",
            "address_v4": "10.0.0.2/32",
            "address_v6": "",
            "upload_rate_limit": 0,
            "download_rate_limit": 0,
            "scheduler_type": "htb"
        }
        
        result = db.insert_peer(test_peer)
        if result:
            print("  ✓ Peer inserted successfully")
        else:
            print("  ✗ Peer insertion failed")
            return False
        
        # Test peer retrieval
        print("  Testing peer retrieval...")
        retrieved_peer = db.search_peer("test_peer_1")
        if retrieved_peer and retrieved_peer.get("name") == "Test Peer":
            print("  ✓ Peer retrieved successfully")
        else:
            print("  ✗ Peer retrieval failed")
            return False
        
        # Test peer update
        print("  Testing peer update...")
        update_data = {"status": "running", "total_receive": 1024.0}
        result = db.update_peer("test_peer_1", update_data)
        if result:
            print("  ✓ Peer updated successfully")
        else:
            print("  ✗ Peer update failed")
            return False
        
        # Test peer deletion
        print("  Testing peer deletion...")
        result = db.delete_peer("test_peer_1")
        if result:
            print("  ✓ Peer deleted successfully")
        else:
            print("  ✗ Peer deletion failed")
            return False
        
        # Clean up test data
        db.drop_database()
        print("  ✓ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"✗ Database operations failed: {e}")
        return False

def test_compatibility_functions():
    """Test SQL compatibility functions"""
    print("\nTesting SQL compatibility functions...")
    try:
        from wiregate.modules.DataBase.DataBaseManager import sqlSelect, sqlUpdate
        
        # Test SQL UPDATE (CREATE TABLE)
        print("  Testing CREATE TABLE...")
        result = sqlUpdate("CREATE TABLE test_table (id VARCHAR, name VARCHAR)")
        if result:
            print("  ✓ CREATE TABLE successful")
        else:
            print("  ✗ CREATE TABLE failed")
            return False
        
        # Test SQL INSERT
        print("  Testing INSERT...")
        result = sqlUpdate("INSERT INTO test_table VALUES ('test1', 'Test Name')")
        if result:
            print("  ✓ INSERT successful")
        else:
            print("  ✗ INSERT failed")
            return False
        
        # Test SQL SELECT
        print("  Testing SELECT...")
        cursor = sqlSelect("SELECT * FROM test_table WHERE id = 'test1'")
        result = cursor.fetchone()
        if result and result.name == 'Test Name':
            print("  ✓ SELECT successful")
        else:
            print("  ✗ SELECT failed")
            return False
        
        # Test SQL UPDATE
        print("  Testing UPDATE...")
        result = sqlUpdate("UPDATE test_table SET name = 'Updated Name' WHERE id = 'test1'")
        if result:
            print("  ✓ UPDATE successful")
        else:
            print("  ✗ UPDATE failed")
            return False
        
        # Test SQL DELETE
        print("  Testing DELETE...")
        result = sqlUpdate("DELETE FROM test_table WHERE id = 'test1'")
        if result:
            print("  ✓ DELETE successful")
        else:
            print("  ✗ DELETE failed")
            return False
        
        # Clean up
        sqlUpdate("DROP TABLE test_table")
        print("  ✓ Test table cleaned up")
        
        return True
        
    except Exception as e:
        print(f"✗ Compatibility functions failed: {e}")
        return False

def test_configuration_database():
    """Test Configuration class with Redis database"""
    print("\nTesting Configuration class with Redis...")
    try:
        from wiregate.modules.Core import Configuration
        
        # Create a test configuration
        print("  Creating test configuration...")
        config = Configuration("test_config_redis")
        
        if hasattr(config, 'db') and config.db is not None:
            print("  ✓ Configuration database initialized")
        else:
            print("  ✗ Configuration database not initialized")
            return False
        
        # Test database methods
        print("  Testing database methods...")
        
        # Test create database
        config.db.create_database()
        print("  ✓ Database created")
        
        # Test migrate database
        config.db.migrate_database()
        print("  ✓ Database migrated")
        
        # Test dump database
        dump_data = list(config.db.dump_database())
        print(f"  ✓ Database dumped ({len(dump_data)} statements)")
        
        # Clean up
        config.db.drop_database()
        print("  ✓ Test configuration cleaned up")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration class test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("WireGate Redis Database Migration Test")
    print("=" * 60)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Database Operations", test_database_operations),
        ("SQL Compatibility", test_compatibility_functions),
        ("Configuration Class", test_configuration_database)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! Redis migration is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
