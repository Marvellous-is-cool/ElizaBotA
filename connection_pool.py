"""
Connection Pool Manager - Prevents multilogin connection conflicts
Manages Highrise connection lifecycle with proper cleanup
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager

@dataclass
class ConnectionState:
    """Track connection state and metadata"""
    connected: bool = False
    last_connect_time: float = 0
    connect_attempts: int = 0
    connection_id: Optional[str] = None
    error_count: int = 0

class ConnectionPoolManager:
    def __init__(self):
        self.connections: Dict[str, ConnectionState] = {}
        self.connection_lock = asyncio.Lock()
        self.cleanup_tasks = set()
        
    async def get_connection_state(self, bot_id: str) -> ConnectionState:
        """Get or create connection state for bot"""
        async with self.connection_lock:
            if bot_id not in self.connections:
                self.connections[bot_id] = ConnectionState()
            return self.connections[bot_id]
    
    async def can_connect(self, bot_id: str) -> bool:
        """Check if bot can safely connect without conflicts"""
        state = await self.get_connection_state(bot_id)
        
        # Prevent rapid reconnection attempts
        time_since_last = time.time() - state.last_connect_time
        if time_since_last < 10:  # 10 second cooldown (reduced from 30)
            print(f"⏳ Connection cooldown active for {bot_id} ({10-time_since_last:.1f}s remaining)")
            return False
        
        # Limit connection attempts
        if state.connect_attempts > 3:
            if time_since_last < 120:  # 2 minute penalty (reduced from 5)
                print(f"🚫 Connection penalty active for {bot_id} (too many attempts)")
                return False
            else:
                # Reset attempts after penalty period
                state.connect_attempts = 0
        
        return True
    
    async def register_connection_attempt(self, bot_id: str):
        """Register a connection attempt"""
        state = await self.get_connection_state(bot_id)
        state.last_connect_time = time.time()
        state.connect_attempts += 1
        
    async def register_connection_success(self, bot_id: str, connection_id: str):
        """Register successful connection"""
        state = await self.get_connection_state(bot_id)
        state.connected = True
        state.connection_id = connection_id
        state.connect_attempts = 0  # Reset on success
        state.error_count = 0
        print(f"✅ Connection registered for {bot_id}: {connection_id}")
    
    async def register_connection_failure(self, bot_id: str, error: str):
        """Register connection failure"""
        state = await self.get_connection_state(bot_id)
        state.connected = False
        state.connection_id = None
        state.error_count += 1
        print(f"❌ Connection failed for {bot_id}: {error}")
    
    async def cleanup_connection(self, bot_id: str):
        """Clean up connection state"""
        async with self.connection_lock:
            if bot_id in self.connections:
                state = self.connections[bot_id]
                state.connected = False
                state.connection_id = None
                print(f"🧹 Cleaned up connection for {bot_id}")
    
    @asynccontextmanager
    async def managed_connection(self, bot_id: str):
        """Context manager for safe connection handling"""
        if not await self.can_connect(bot_id):
            raise ConnectionError(f"Cannot connect {bot_id} - cooldown or penalty active")
        
        await self.register_connection_attempt(bot_id)
        
        try:
            yield
            # Connection successful if we reach here without exception
            print(f"🔗 Connection context completed successfully for {bot_id}")
            
        except Exception as e:
            await self.register_connection_failure(bot_id, str(e))
            raise
        
        finally:
            # Schedule cleanup after a delay
            cleanup_task = asyncio.create_task(self._delayed_cleanup(bot_id))
            self.cleanup_tasks.add(cleanup_task)
            cleanup_task.add_done_callback(self.cleanup_tasks.discard)
    
    async def _delayed_cleanup(self, bot_id: str):
        """Delayed connection cleanup"""
        await asyncio.sleep(5)  # Wait before cleanup
        await self.cleanup_connection(bot_id)
    
    async def force_cleanup_all(self):
        """Force cleanup all connections"""
        async with self.connection_lock:
            for bot_id in list(self.connections.keys()):
                await self.cleanup_connection(bot_id)
            
            # Cancel all cleanup tasks
            for task in list(self.cleanup_tasks):
                task.cancel()
            self.cleanup_tasks.clear()
            
            print("🧹 Force cleaned all connections")
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        stats = {
            'total_connections': len(self.connections),
            'active_connections': sum(1 for state in self.connections.values() if state.connected),
            'failed_connections': sum(1 for state in self.connections.values() if state.error_count > 0),
            'connections': {}
        }
        
        for bot_id, state in self.connections.items():
            stats['connections'][bot_id] = {
                'connected': state.connected,
                'attempts': state.connect_attempts,
                'errors': state.error_count,
                'last_connect': state.last_connect_time,
                'connection_id': state.connection_id
            }
        
        return stats

# Global connection pool manager
connection_pool = ConnectionPoolManager()

async def safe_highrise_connection(bot_id: str):
    """Safe wrapper for Highrise connections"""
    async with connection_pool.managed_connection(bot_id):
        # Connection setup code goes here
        return True

if __name__ == "__main__":
    # Test the connection pool
    async def test():
        print("Testing connection pool...")
        
        # Test normal flow
        async with connection_pool.managed_connection("test_bot_1"):
            await connection_pool.register_connection_success("test_bot_1", "conn_123")
        
        # Test rapid reconnection prevention
        try:
            async with connection_pool.managed_connection("test_bot_1"):
                pass
        except ConnectionError as e:
            print(f"Expected error: {e}")
        
        print("Connection pool test completed!")
        print("Stats:", connection_pool.get_connection_stats())
    
    asyncio.run(test())