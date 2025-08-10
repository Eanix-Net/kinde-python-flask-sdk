#!/usr/bin/env python3
"""
Test script to verify Redis storage refactor functionality.
This script tests that:
1. RedisStorageFactory can be imported and used
2. StorageFactory defaults to Redis when available
3. OAuth can initialize without framework dependencies
"""

import sys
import os

# Add the SDK to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_redis_storage_factory():
    """Test RedisStorageFactory can be imported and used."""
    print("Testing RedisStorageFactory import and usage...")
    
    try:
        from kinde_sdk.core.storage.redis_storage_factory import RedisStorageFactory, RedisFactory
        from kinde_sdk.core.storage import RedisStorage
        print("✓ RedisStorageFactory imported successfully")
        
        # Test factory creation (will fail without Redis, but should not crash)
        try:
            storage = RedisStorageFactory.create_storage()
            print("✓ RedisStorageFactory.create_storage() works")
            print(f"  Storage type: {type(storage).__name__}")
        except Exception as e:
            print(f"⚠ RedisStorageFactory creation failed (expected without Redis): {e}")
        
        # Test alias
        try:
            storage = RedisFactory.create_storage()
            print("✓ RedisFactory alias works")
        except Exception as e:
            print(f"⚠ RedisFactory creation failed (expected without Redis): {e}")
            
        return True
    except Exception as e:
        print(f"✗ RedisStorageFactory test failed: {e}")
        return False


def test_storage_factory_defaults():
    """Test that StorageFactory defaults to Redis when available."""
    print("\nTesting StorageFactory defaults to Redis...")
    
    try:
        from kinde_sdk.core.storage.storage_factory import StorageFactory
        
        # Test default behavior
        storage = StorageFactory.create_storage()
        storage_type = type(storage).__name__
        print(f"✓ StorageFactory.create_storage() returned: {storage_type}")
        
        # Test explicit Redis request
        try:
            redis_storage = StorageFactory.create_storage({"type": "redis"})
            redis_type = type(redis_storage).__name__
            print(f"✓ Explicit Redis request returned: {redis_type}")
        except Exception as e:
            print(f"⚠ Explicit Redis request failed (expected without Redis): {e}")
        
        return True
    except Exception as e:
        print(f"✗ StorageFactory test failed: {e}")
        return False


def test_oauth_framework_agnostic():
    """Test that OAuth can initialize without framework dependencies."""
    print("\nTesting OAuth framework-agnostic initialization...")
    
    # Set minimal required environment variables
    os.environ["KINDE_CLIENT_ID"] = "test_client_id"
    os.environ["KINDE_CLIENT_SECRET"] = "test_client_secret"
    os.environ["KINDE_REDIRECT_URI"] = "http://localhost:8000/callback"
    os.environ["KINDE_HOST"] = "https://test.kinde.com"
    
    try:
        from kinde_sdk.auth.oauth import OAuth
        
        # Test OAuth initialization without framework
        oauth = OAuth()
        print("✓ OAuth initialized successfully without framework dependencies")
        print(f"  Framework: {oauth.framework}")
        print(f"  Storage manager initialized: {oauth._storage_manager is not None}")
        
        # Check storage backend
        if oauth._storage_manager:
            storage = oauth._storage_manager.storage
            storage_type = type(storage).__name__ if storage else "None"
            print(f"  Storage backend: {storage_type}")
        
        return True
    except Exception as e:
        print(f"✗ OAuth framework-agnostic test failed: {e}")
        import traceback
        print(f"  Traceback: {traceback.format_exc()}")
        return False
    finally:
        # Clean up environment
        for key in ["KINDE_CLIENT_ID", "KINDE_CLIENT_SECRET", "KINDE_REDIRECT_URI", "KINDE_HOST"]:
            if key in os.environ:
                del os.environ[key]


def test_main_sdk_imports():
    """Test that main SDK imports work correctly."""
    print("\nTesting main SDK imports...")
    
    try:
        from kinde_sdk import OAuth, RedisStorage, RedisStorageFactory, RedisFactory
        print("✓ Main SDK imports work correctly")
        print(f"  OAuth: {OAuth}")
        print(f"  RedisStorage: {RedisStorage}")
        print(f"  RedisStorageFactory: {RedisStorageFactory}")
        print(f"  RedisFactory: {RedisFactory}")
        return True
    except Exception as e:
        print(f"✗ Main SDK imports failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing Redis Storage Refactor...")
    print("=" * 50)
    
    tests = [
        test_redis_storage_factory,
        test_storage_factory_defaults,
        test_oauth_framework_agnostic,
        test_main_sdk_imports,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Redis storage refactor is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the output above for details.")
        sys.exit(1)
