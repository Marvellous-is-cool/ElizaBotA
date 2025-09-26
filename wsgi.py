#!/usr/bin/env python3

"""
Production startup script for Gunicorn with Highrise bot
This file is used as a pre-loading script before Gunicorn starts
"""

import os
import threading
import time
from threading import Thread
import signal
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define a variable to track whether we're running under Gunicorn
running_under_gunicorn = 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '')

def start_bot_thread():
    """Start the Highrise bot in a separate thread"""
    # Import here to avoid circular imports
    from safe_main import run_bot
    import asyncio
    from db.mongo_client import MongoDBClient
    
    print("Starting Matchmaking Bot...")
    
    # Check MongoDB environment variables
    import os
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME")
    print(f"MONGODB_URI found: {'Yes' if mongodb_uri else 'No'}")
    print(f"MONGODB_DB_NAME found: {'Yes' if mongodb_db_name else 'No'}")
    
    # Create a new event loop for the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Call run_bot without arguments - it will initialize MongoDB and get environment variables itself
        loop.run_until_complete(run_bot())
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
        
        # Special handling for MongoDB connection errors
        if "MongoDB" in str(e) or "mongo" in str(e).lower():
            print("\n💡 MongoDB connection troubleshooting:")
            print("   • Check that your MONGODB_URI environment variable is set correctly")
            print("   • Verify network connectivity to your MongoDB server")
            print("   • Ensure IP allowlisting is configured in MongoDB Atlas")
            print("   • Run test_mongodb_connection.py script for detailed diagnostics")
    except Exception as e:
        print(f"Bot crashed with error: {e}")
    finally:
        print("Bot has stopped.")

# When the app is loaded by Gunicorn, start the bot in a background thread
def when_ready(server):
    """This function is called when Gunicorn is ready to accept connections"""
    bot_thread = Thread(target=start_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    print("Gunicorn server is ready, bot thread started")

# Import the Flask app
from webserver import app

# For testing purposes when running directly
if __name__ == "__main__":
    
    # Start the bot thread
    bot_thread = Thread(target=start_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Wait for a few seconds for the bot to initialize
    time.sleep(3)
    
    # Run the Flask app
    port = int(os.getenv('PORT', 8081))
    app.run(host='0.0.0.0', port=port, debug=False)