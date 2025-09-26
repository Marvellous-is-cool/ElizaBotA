"""
Initialize MongoDB collections and indexes.
"""

import asyncio
import logging
from db.mongo_client import MongoDBClient

logger = logging.getLogger(__name__)
logger.disabled = True  # Disable this logger completely

async def initialize_db():
    """Initialize MongoDB connection and collections"""
    # Create MongoDB client
    mongo_client = MongoDBClient()
    
    # Try to connect
    connected = await mongo_client.connect()
    
    if not connected:
        logger.error("Failed to connect to MongoDB. Using local file storage as fallback.")
        return None
    
    logger.info("Successfully connected to MongoDB")
    return mongo_client

if __name__ == "__main__":
    # For manual testing
    async def test_connection():
        client = await initialize_db()
        if client:
            print("Connection successful!")
            await client.disconnect()
        else:
            print("Connection failed!")
    
    asyncio.run(test_connection())