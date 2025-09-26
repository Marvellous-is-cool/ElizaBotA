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
    from main import main
    import asyncio
    
    print("Starting Matchmaking Bot...")
    
    # Create a new event loop for the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Call main without arguments - it will get environment variables itself
        loop.run_until_complete(main())
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