#!/usr/bin/env python3
"""
Test MongoDB connection for debugging deployment issues
This script attempts to connect to MongoDB using the configured credentials
and reports success or failure details.
"""

import os
import asyncio
import traceback
from dotenv import load_dotenv
from db.mongo_client import MongoDBClient

# Load environment variables
load_dotenv()

async def test_mongodb_connection():
    """Test MongoDB connection with detailed error reporting"""
    print("MongoDB Connection Test")
    print("-" * 50)
    
    # Get MongoDB URI from environment
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME")
    
    print(f"MONGODB_URI found in env: {'Yes' if mongodb_uri else 'No'}")
    print(f"MONGODB_DB_NAME found in env: {'Yes' if mongodb_db_name else 'No'}")
    
    # Create MongoDB client
    mongo_client = MongoDBClient()
    
    # Get URI and DB name from client (which may use config.py defaults)
    used_uri = mongo_client.uri
    used_db_name = mongo_client.db_name
    
    # Mask the password in the URI for secure logging
    if used_uri and "mongodb" in used_uri:
        parts = used_uri.split("@")
        if len(parts) > 1:
            auth_part = parts[0].split("://")[1].split(":")
            if len(auth_part) > 1:
                masked_uri = f"{parts[0].split('://')[0]}://{auth_part[0]}:****@{parts[1]}"
            else:
                masked_uri = used_uri
        else:
            masked_uri = used_uri
    else:
        masked_uri = "[Not configured]"
    
    print(f"Using URI: {masked_uri}")
    print(f"Using database name: {used_db_name}")
    
    print("\nAttempting connection...")
    try:
        # Try to connect
        connected = await mongo_client.connect()
        
        if connected:
            print("\n✅ Successfully connected to MongoDB!")
            print(f"Database name: {mongo_client.db_name}")
            
            # List collections
            print("\nCollections:")
            collections = await mongo_client.db.list_collection_names()
            if collections:
                for collection in collections:
                    print(f"- {collection}")
            else:
                print("No collections found (database may be empty)")
            
            # Test a simple query
            print("\nTesting simple query...")
            bot_data = await mongo_client.db.bot_data.find_one({})
            if bot_data:
                print("✓ Query successful - bot_data found")
            else:
                print("✓ Query executed - no bot_data found (database may be empty)")
                
            # Close connection
            await mongo_client.disconnect()
            print("\nConnection closed.")
            return True
        else:
            print("\n❌ Failed to connect to MongoDB!")
            print("The MongoDB client reported a connection failure.")
            return False
            
    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        print("\nFull error details:")
        traceback.print_exc()
        
        # Provide troubleshooting suggestions
        print("\n💡 Troubleshooting suggestions:")
        
        if "Invalid scheme" in str(e) or "URL must be of type string" in str(e):
            print("- Check that your MONGODB_URI is correctly formatted")
            print("- A valid MongoDB URI starts with mongodb:// or mongodb+srv://")
            
        elif "timed out" in str(e) or "ServerSelectionTimeoutError" in str(e):
            print("- Make sure your MongoDB server is running")
            print("- Check for network connectivity issues")
            print("- Verify IP address allowlisting in MongoDB Atlas settings")
            print("- Ensure your Render service has network access to MongoDB")
            
        elif "Authentication failed" in str(e):
            print("- Check your MongoDB username and password")
            print("- Ensure the user has proper permissions")
            
        else:
            print("- Verify your MONGODB_URI environment variable")
            print("- Check network connectivity to your MongoDB server")
            print("- Ensure MongoDB is running and accessible from Render")
        
        return False

if __name__ == "__main__":
    asyncio.run(test_mongodb_connection())