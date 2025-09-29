#!/usr/bin/env python3
"""
Quick test to verify multilogin prevention is working
"""

import os
import asyncio
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_connection():
    """Test bot connection without multiple instances"""
    print("🧪 Testing multilogin prevention...")
    
    # Check if we have required environment variables
    room_id = os.getenv("ROOM_ID")
    bot_token = os.getenv("BOT_TOKEN")
    
    if not room_id or not bot_token:
        print("❌ Missing ROOM_ID or BOT_TOKEN")
        return False
    
    try:
        # Import main bot function
        from main import main as bot_main
        
        print(f"🔗 Attempting connection to room: {room_id}")
        print("⚠️ This should succeed without multilogin errors")
        
        # Run the bot
        success = await bot_main()
        
        if success:
            print("✅ Connection test passed!")
            return True
        else:
            print("❌ Connection test failed")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"🚨 Test failed with error: {error_msg}")
        
        if "Multilogin closing connection" in error_msg:
            print("🚫 MULTILOGIN ERROR DETECTED!")
            print("💡 This means another bot instance is running")
            print("🔧 Fix: Use single worker in gunicorn_config.py")
            return False
        elif "TaskGroup" in error_msg:
            print("⚠️ TaskGroup error - connection issue")
            return False
        else:
            print(f"❓ Unknown error: {error_msg}")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)