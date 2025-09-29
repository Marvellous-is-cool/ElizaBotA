"""
Safe bot launcher that handles TaskGroup errors properly
Now uses the resilient connection manager
"""
import asyncio
import os
import sys
from connection_resilience import ResilientBotManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_bot_main():
    """Safe bot main using resilient connection manager"""
    try:
        logger.info("🚀 Starting safe bot with resilient connection manager")
        
        # Create resilient manager
        manager = ResilientBotManager()
        
        # Run with built-in TaskGroup protection
        await manager.run_with_resilience()
        
    except KeyboardInterrupt:
        logger.info("👋 Safe bot shutdown requested")
    except Exception as e:
        logger.error(f"Safe bot launcher error: {e}")
        raise

def main():
    """Main entry point with proper event loop handling"""
    try:
        asyncio.run(safe_bot_main())
    except KeyboardInterrupt:
        logger.info("👋 Program terminated by user")
    except Exception as e:
        logger.error(f"Main error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()