"""
Safe bot launcher that handles TaskGroup errors properly
"""
import asyncio
import os
from highrise import BaseBot, __main__
from highrise.__main__ import BotDefinition
from main import Bot
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_bot_main():
    """Safe bot main with proper TaskGroup error handling"""
    try:
        # Get credentials
        room_id = os.getenv("ROOM_ID")
        bot_token = os.getenv("BOT_TOKEN")
        
        if not room_id or not bot_token:
            logger.error("Missing ROOM_ID or BOT_TOKEN environment variables")
            return
            
        # Clean credentials
        room_id = room_id.strip().rstrip('%')
        bot_token = bot_token.strip().rstrip('%')
        
        logger.info(f"🚀 Starting safe bot launcher for room: {room_id}")
        
        # Create bot definition
        bot_instance = Bot()
        definitions = [BotDefinition(bot_instance, room_id, bot_token)]
        
        # Use asyncio.run directly to avoid TaskGroup issues
        try:
            await __main__.main(definitions)
        except* Exception as eg:
            # Handle ExceptionGroup properly in Python 3.11+
            logger.error(f"Bot ExceptionGroup: {eg}")
            for exc in eg.exceptions:
                logger.error(f"  - {type(exc).__name__}: {exc}")
            raise
            
    except Exception as e:
        logger.error(f"Safe bot launcher error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(safe_bot_main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal bot error: {e}")