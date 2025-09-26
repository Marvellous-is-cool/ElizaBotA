"""
Gunicorn configuration file for the Matchmaking Bot
"""
import os
from threading import Thread

# Get the PORT environment variable and convert it to an integer
# Render sets this automatically, and we need to respect it
port = int(os.getenv('PORT', '10000'))
bind = f"0.0.0.0:{port}"
workers = 1
worker_class = 'sync'
timeout = 120
loglevel = 'info'
proc_name = 'matchmaking-bot'
preload_app = True
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30
keepalive = 5
accesslog = '-'
errorlog = '-'

def post_fork(server, worker):
    """Start the bot after forking a worker"""
    def start_bot_thread():
        try:
            # Import main directly, just like in run.py
            from main import main, Bot
            from highrise import __main__
            from highrise.__main__ import BotDefinition
            import asyncio
            import sys
            import os

            print("Starting Matchmaking Bot in worker...")
            
            # Check environment variables
            room_id = os.getenv("ROOM_ID")
            bot_token = os.getenv("BOT_TOKEN")
            mongodb_uri = os.getenv("MONGODB_URI")
            mongodb_db_name = os.getenv("MONGODB_DB_NAME")
            
            print(f"ROOM_ID found: {'Yes' if room_id else 'No'}")
            print(f"BOT_TOKEN found: {'Yes' if bot_token else 'No'}")
            print(f"MONGODB_URI found: {'Yes' if mongodb_uri else 'No'}")
            print(f"MONGODB_DB_NAME found: {'Yes' if mongodb_db_name else 'No'}")
            
            if not room_id or not bot_token:
                print("❌ Error: Missing required environment variables!")
                return
                
            # Clean the credentials (remove any trailing % or whitespace)
            room_id = room_id.strip().rstrip('%') if room_id else None
            bot_token = bot_token.strip().rstrip('%') if bot_token else None
            
            print(f"Starting bot for room: {room_id}")

            # Create a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Create bot definition directly, just like in main.py
                bot_instance = Bot()  
                definitions = [BotDefinition(bot_instance, room_id, bot_token)]
                
                # Run the main function from the Highrise SDK
                print("Starting bot with highrise.__main__.main()")
                loop.run_until_complete(__main__.main(definitions))
                
            except Exception as e:
                print(f"Bot initialization error: {e}")
                print(f"Error type: {type(e).__name__}")
                # Print the full traceback for debugging
                import traceback
                traceback.print_exc()
                
                # For TaskGroup errors, try to extract the inner exception
                if "TaskGroup" in str(e):
                    print("Attempting to extract inner TaskGroup exception...")
                    try:
                        # This is a common pattern for extracting inner exceptions from TaskGroup
                        if hasattr(e, "__context__") and e.__context__:
                            print(f"Inner exception: {e.__context__}")
                        if hasattr(e, "__cause__") and e.__cause__:
                            print(f"Cause: {e.__cause__}")
                    except Exception as extract_error:
                        print(f"Failed to extract inner exception: {extract_error}")
                        
                # Special handling for common errors
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
                elif "MongoDB" in str(e) or "mongo" in str(e).lower():
                    print("\n💡 MongoDB connection troubleshooting:")
                    print("   • Check that your MONGODB_URI environment variable is set correctly")
                    print("   • Verify network connectivity to your MongoDB server")
                    print("   • Ensure IP allowlisting is configured in MongoDB Atlas")
                    print("   • Run test_mongodb_connection.py script for detailed diagnostics")
        except Exception as e:
            print(f"Bot thread error: {e}")
            import traceback
            traceback.print_exc()

    if worker.nr == 0:
        bot_thread = Thread(target=start_bot_thread, daemon=True)
        bot_thread.start()
        print(f"Bot thread started in worker {worker.nr}")
