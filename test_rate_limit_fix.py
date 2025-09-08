#!/usr/bin/env python3
"""
Test script for rate limit fix
"""

import os
import sys

# Add the Src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Src'))

def test_redis_cursor_dict_access():
    """Test that Redis cursor results can be accessed as dictionaries"""
    print("Testing Redis cursor dictionary access...")
    
    try:
        from wiregate.modules.DataBase.DataBaseManager import sqlSelect
        
        # Test a simple query
        cursor = sqlSelect("SELECT 'test_value' as test_field")
        result = cursor.fetchone()
        
        if result:
            print(f"✓ Query executed successfully")
            print(f"  Result type: {type(result)}")
            print(f"  Result attributes: {dir(result)}")
            
            # Test dictionary-style access
            try:
                value = result['test_field']
                print(f"✓ Dictionary access works: {value}")
            except Exception as e:
                print(f"✗ Dictionary access failed: {e}")
                return False
            
            # Test attribute access
            try:
                value = result.test_field
                print(f"✓ Attribute access works: {value}")
            except Exception as e:
                print(f"✗ Attribute access failed: {e}")
                return False
            
            # Test get method
            try:
                value = result.get('test_field', 'default')
                print(f"✓ Get method works: {value}")
            except Exception as e:
                print(f"✗ Get method failed: {e}")
                return False
            
            return True
        else:
            print("✗ No result returned from query")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_rate_limit_query():
    """Test the specific rate limit query that was failing"""
    print("\nTesting rate limit query...")
    
    try:
        from wiregate.modules.DataBase.DataBaseManager import sqlSelect
        
        # Test the query that was failing
        cursor = sqlSelect("SELECT upload_rate_limit, download_rate_limit, scheduler_type FROM 'ADMINS' WHERE id = 'test_peer'")
        results = cursor.fetchall()
        
        print(f"✓ Rate limit query executed successfully")
        print(f"  Found {len(results)} results")
        
        if results:
            result = results[0]
            print(f"  Result type: {type(result)}")
            
            # Test the specific access pattern that was failing
            try:
                upload_rate = result['upload_rate_limit']
                download_rate = result['download_rate_limit']
                scheduler_type = result['scheduler_type']
                print(f"✓ Dictionary access works: upload={upload_rate}, download={download_rate}, scheduler={scheduler_type}")
            except Exception as e:
                print(f"✗ Dictionary access failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Rate limit query test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Rate Limit Fix Test")
    print("=" * 60)
    
    tests = [
        ("Redis Cursor Dictionary Access", test_redis_cursor_dict_access),
        ("Rate Limit Query", test_rate_limit_query)
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
        print("🎉 All tests passed! Rate limit fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
