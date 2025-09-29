#!/usr/bin/env python3
"""
Connection Pool Reset - Completely clear all connection states
"""

import asyncio
import os
import time
from connection_pool import ConnectionPoolManager

async def complete_reset():
    """Completely reset connection pool and clear all states"""
    print("🧹 Performing complete connection pool reset...")
    
    # Create a fresh connection pool instance
    pool = ConnectionPoolManager()
    
    # Force cleanup all existing connections
    await pool.force_cleanup_all()
    
    # Clear the global connection pool completely
    pool.connections.clear()
    pool.cleanup_tasks.clear()
    
    print("✅ Connection pool completely reset")
    print("📊 Pool state:", {
        'connections': len(pool.connections),
        'cleanup_tasks': len(pool.cleanup_tasks)
    })
    
    return True

if __name__ == "__main__":
    result = asyncio.run(complete_reset())
    print("🚀 Ready for fresh bot connection!")