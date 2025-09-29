#!/usr/bin/env python3
"""
Test script for TaskGroup error prevention
Uses the resilient connection manager only
"""
import os
import sys
import asyncio
import logging
from connection_resilience import ResilientBotManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Test resilient connection manager"""
    try:
        print("🧪 Testing Resilient Connection Manager")
        print("=" * 50)
        
        # Check environment
        room_id = os.getenv("ROOM_ID")
        bot_token = os.getenv("BOT_TOKEN")
        
        if not room_id or not bot_token:
            print("❌ Missing ROOM_ID or BOT_TOKEN environment variables")
            return 1
        
        print(f"🎯 Target room: {room_id.strip().rstrip('%')}")
        print("🔄 Starting resilient connection manager...")
        
        # Create and run resilient manager
        manager = ResilientBotManager()
        asyncio.run(manager.run_with_resilience())
        
        return 0
        
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())