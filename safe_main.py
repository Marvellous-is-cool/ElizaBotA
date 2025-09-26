"""
Alternative main.py entry point with improved TaskGroup error handling
for use with Gunicorn
"""

import os
import asyncio
import traceback
from dotenv import load_dotenv
from highrise import __main__
from highrise.__main__ import BotDefinition
from main import Bot
from db.init_db import initialize_db

# Load environment variables
load_dotenv()

async def run_bot():
    """Modified version of main() from main.py with better error handling"""
    # Get credentials from environment variables
    room_id = os.getenv("ROOM_ID")
    bot_token = os.getenv("BOT_TOKEN")
    mongodb_uri = os.getenv("MONGODB_URI")
    
    print(f"Starting matchmaking bot")
    print(f"ROOM_ID found: {'Yes' if room_id else 'No'}")
    print(f"BOT_TOKEN found: {'Yes' if bot_token else 'No'}")
    print(f"MONGODB_URI found: {'Yes' if mongodb_uri else 'No'}")
    
    if not room_id:
        print("❌ Error: ROOM_ID not found in environment variables!")
        print("Please set ROOM_ID in your .env file")
        return
    
    if not bot_token:
        print("❌ Error: BOT_TOKEN not found in environment variables!")
        print("Please set BOT_TOKEN in your .env file")
        return
    
    if not mongodb_uri:
        print("⚠️ Warning: MONGODB_URI not found in environment variables!")
        print("Using default configuration from config.py")
    
    # Clean the credentials (remove any trailing % or whitespace)
    room_id = room_id.strip().rstrip('%') if room_id else None
    bot_token = bot_token.strip().rstrip('%') if bot_token else None
    
    print(f"Starting bot for room: {room_id}")
    
    # Initialize database connection first
    print("Initializing MongoDB connection...")
    db_client = await initialize_db()
    
    if not db_client:
        print("⚠️ Warning: Failed to connect to MongoDB!")
        print("Bot will run with limited functionality - user data will not persist")
        print("Check your MONGODB_URI environment variable and network settings")
    else:
        print("✅ Successfully connected to MongoDB")
    
    try:
        bot_instance = Bot()
        # Make sure the bot instance has the db_client
        bot_instance.db_client = db_client
        
        definition = BotDefinition(bot_instance, room_id, bot_token)
        definitions = [definition]
        await __main__.main(definitions)
    except Exception as e:
        print(f"❌ Bot connection failed: {e}")
        traceback.print_exc()
        if "Invalid room id" in str(e):
            print("💡 Room ID troubleshooting:")
            print("   • Make sure the ROOM_ID in your .env file is correct")
            print("   • The bot must be invited to the room as a bot")
            print("   • Check that the room exists and is accessible")
        elif "API token not found" in str(e) or "Invalid token" in str(e):
            print("💡 Bot token troubleshooting:")
            print("   • Make sure your BOT_TOKEN in .env is correct and complete")
            print("   • Verify the token is from your Highrise developer account")
            print("   • Check for any extra characters or spaces")
        
        # Try to disconnect database if connected
        if db_client:
            try:
                await db_client.disconnect()
                print("Database connection closed")
            except:
                pass
            
        raise  # Re-raise for proper error reporting