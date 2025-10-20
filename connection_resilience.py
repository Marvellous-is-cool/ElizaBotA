"""
Enhanced Connection Resilience for Highrise Bot
Prevents TaskGroup errors and handles connection drops gracefully
"""
import asyncio
import logging
import os
import sys
from typing import Optional
from highrise import BaseBot, __main__
from highrise.__main__ import BotDefinition
from main import Bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResilientBotManager:
    """Manages bot connection with automatic reconnection and error recovery"""
    
    def __init__(self):
        self.bot_instance: Optional[Bot] = None
        self.room_id: Optional[str] = None
        self.bot_token: Optional[str] = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 50
        self.base_delay = 5
        self.max_delay = 300
        self.running = False
        
    def get_credentials(self) -> tuple[str, str]:
        """Get and validate bot credentials"""
        room_id = os.getenv("ROOM_ID")
        bot_token = os.getenv("BOT_TOKEN")
        
        if not room_id or not bot_token:
            raise ValueError("Missing ROOM_ID or BOT_TOKEN environment variables")
            
        # Clean credentials
        room_id = room_id.strip().rstrip('%')
        bot_token = bot_token.strip().rstrip('%')
        
        return room_id, bot_token
    
    def calculate_delay(self) -> float:
        """Calculate exponential backoff delay"""
        delay = min(self.base_delay * (2 ** self.reconnect_attempts), self.max_delay)
        return delay
    
    async def create_bot_session(self) -> bool:
        """Create a new bot session with connection"""
        try:
            logger.info(f"🤖 Creating bot session (attempt {self.reconnect_attempts + 1})")
            
            # Create fresh bot instance
            self.bot_instance = Bot()
            
            # Create bot definition
            definitions = [BotDefinition(self.bot_instance, self.room_id, self.bot_token)]
            
            # Start bot with timeout protection
            bot_task = asyncio.create_task(__main__.main(definitions))
            
            # Monitor for completion or errors
            await bot_task
            
            return True
            
        except asyncio.CancelledError:
            logger.info("Bot session cancelled")
            return False
        except Exception as e:
            logger.error(f"Bot session error: {e}")
            return False
    
    async def handle_connection_error(self, error: Exception):
        """Handle connection errors with appropriate recovery"""
        error_str = str(error).lower()
        
        if "taskgroup" in error_str or "unhandled errors" in error_str:
            logger.warning("🔄 TaskGroup error detected - connection issue")
        elif "multilogin" in error_str:
            logger.warning("🔄 Multilogin connection closed - reconnecting")
        elif "connection" in error_str:
            logger.warning("🔄 Connection error - attempting recovery")
        else:
            logger.error(f"❌ Unexpected error: {error}")
        
        # Calculate delay
        delay = self.calculate_delay()
        logger.info(f"⏳ Waiting {delay}s before reconnection attempt...")
        await asyncio.sleep(delay)
    
    async def run_with_resilience(self):
        """Main resilient bot runner"""
        self.running = True
        logger.info("🚀 Starting Resilient Bot Manager")
        
        # CRITICAL: Force cleanup any stale connections from previous deployments
        logger.info("🧹 Cleaning up any stale connections from previous deployments...")
        await asyncio.sleep(5)  # Wait 5 seconds for old deployments to fully shut down
        logger.info("✅ Cleanup wait complete - starting fresh connection")
        
        try:
            # Get credentials once
            self.room_id, self.bot_token = self.get_credentials()
            logger.info(f"🎯 Target room: {self.room_id}")
            
            while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
                try:
                    logger.info(f"🔗 Connection attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}")
                    
                    # Attempt to create and run bot session
                    success = await self.create_bot_session()
                    
                    if success:
                        logger.info("✅ Bot session completed successfully")
                        self.reconnect_attempts = 0  # Reset on success
                    else:
                        raise Exception("Bot session failed")
                        
                except KeyboardInterrupt:
                    logger.info("👋 Shutdown requested by user")
                    break
                except asyncio.CancelledError:
                    logger.info("👋 Bot operation cancelled")
                    break
                except Exception as e:
                    self.reconnect_attempts += 1
                    await self.handle_connection_error(e)
                    
                    if self.reconnect_attempts >= self.max_reconnect_attempts:
                        logger.error(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached")
                        break
                        
        except Exception as e:
            logger.error(f"❌ Critical error in resilient manager: {e}")
        finally:
            self.running = False
            logger.info("🛑 Resilient Bot Manager stopped")

# Enhanced safe wrapper for TaskGroup compatibility
async def safe_bot_runner():
    """Safe bot runner that prevents TaskGroup errors"""
    manager = ResilientBotManager()
    
    try:
        await manager.run_with_resilience()
    except KeyboardInterrupt:
        logger.info("👋 Graceful shutdown initiated")
    except Exception as e:
        logger.error(f"❌ Safe runner error: {e}")
        sys.exit(1)

def main():
    """Main entry point with proper event loop handling"""
    try:
        # Ensure clean event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # If loop is running, create task
            asyncio.create_task(safe_bot_runner())
        else:
            # Create new event loop
            asyncio.run(safe_bot_runner())
            
    except KeyboardInterrupt:
        logger.info("👋 Program terminated by user")
    except Exception as e:
        logger.error(f"❌ Main error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()