#!/usr/bin/env python3
"""
Resilient Bot Launcher - Prevents multilogin conflicts and handles TaskGroup errors
"""

import os
import sys
import asyncio
import signal
import time
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# Import instance management with fallback
try:
    from instance_manager import ensure_single_instance, instance_manager
except ImportError:
    from simple_instance_manager import ensure_single_instance, simple_instance_manager as instance_manager

from connection_pool import connection_pool
from main import main as bot_main


class ResilientBotLauncher:
    def __init__(self):
        self.running = False
        self.restart_count = 0
        self.max_restarts = 10
        self.restart_delay = 30  # seconds
        
    async def launch_bot(self):
        """Launch bot with resilience and multilogin prevention"""
        print("🚀 Starting Resilient Bot Launcher")
        
        # Ensure single instance
        try:
            ensure_single_instance()
        except SystemExit:
            print("❌ Another instance is already running!")
            return False
        
        self.running = True
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        while self.running and self.restart_count < self.max_restarts:
            try:
                print(f"🔄 Starting bot (attempt {self.restart_count + 1}/{self.max_restarts})")
                
                # Clean up any stale connections
                await connection_pool.force_cleanup_all()
                
                # Launch the bot
                success = await bot_main()
                
                if success:
                    print("✅ Bot completed successfully")
                    break
                else:
                    print("❌ Bot failed to start")
                    
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped by user")
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"🚨 Bot crashed: {error_msg}")
                
                # Handle specific error types
                if "Multilogin closing connection" in error_msg:
                    print("🔧 Multilogin conflict detected - killing existing instances")
                    instance_manager.kill_existing_instances()
                    self.restart_delay = 60  # Longer delay for multilogin
                    
                elif "TaskGroup" in error_msg or "ExceptionGroup" in error_msg:
                    print("🔧 TaskGroup error detected - implementing connection resilience")
                    self.restart_delay = 45
                    
                else:
                    print(f"🔧 General error - using standard restart delay")
                    self.restart_delay = 30
            
            # Check if we should restart
            if self.running and self.restart_count < self.max_restarts - 1:
                self.restart_count += 1
                print(f"⏳ Restarting in {self.restart_delay} seconds...")
                await asyncio.sleep(self.restart_delay)
                
                # Exponential backoff (max 5 minutes)
                self.restart_delay = min(self.restart_delay * 1.2, 300)
            else:
                break
        
        print("🔚 Bot launcher shutting down")
        await self.cleanup()
        
        if self.restart_count >= self.max_restarts:
            print(f"❌ Max restarts ({self.max_restarts}) reached!")
            return False
            
        return True
    
    def signal_handler(self, signum, frame):
        """Handle termination signals gracefully"""
        print(f"\n📡 Received signal {signum}")
        self.running = False
    
    async def cleanup(self):
        """Clean up resources"""
        print("🧹 Performing final cleanup...")
        
        # Cleanup connections
        await connection_pool.force_cleanup_all()
        
        # Release instance lock
        instance_manager.release_lock()
        
        print("✅ Cleanup completed")


async def main():
    """Main entry point"""
    launcher = ResilientBotLauncher()
    return await launcher.launch_bot()


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Launcher stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"🚨 Fatal launcher error: {e}")
        sys.exit(1)