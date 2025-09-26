#!/usr/bin/env python3
"""
Simple test script to verify the WSGI setup works correctly
"""

import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_wsgi_import():
    """Test if the WSGI application can be imported"""
    try:
        from wsgi import application
        print("✅ WSGI application imported successfully")
        print(f"Application type: {type(application)}")
        return True
    except Exception as e:
        print(f"❌ Failed to import WSGI application: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_webserver_import():
    """Test if the webserver module can be imported"""
    try:
        from webserver import app, start_bot
        print("✅ Webserver module imported successfully")
        print(f"Flask app: {type(app)}")
        print(f"Start bot function: {type(start_bot)}")
        return True
    except Exception as e:
        print(f"❌ Failed to import webserver: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """Test environment variables"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['ROOM_ID', 'BOT_TOKEN']
    optional_vars = ['MONGODB_URI', 'MONGODB_DB_NAME', 'PORT']
    
    print("\nEnvironment Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Found (length: {len(value)})")
        else:
            print(f"❌ {var}: Missing")
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"ℹ️  {var}: Found (length: {len(value)})")
        else:
            print(f"ℹ️  {var}: Not set")

if __name__ == "__main__":
    print("Testing WSGI setup for production deployment...")
    print("=" * 50)
    
    # Test imports
    wsgi_ok = test_wsgi_import()
    webserver_ok = test_webserver_import()
    
    # Test environment
    test_environment()
    
    print("\n" + "=" * 50)
    if wsgi_ok and webserver_ok:
        print("✅ All tests passed! Ready for deployment.")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)