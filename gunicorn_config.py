"""
Gunicorn configuration file for the Matchmaking Bot
"""
import os
import sys
from threading import Thread

# Bind to 0.0.0.0 on the port specified by the PORT environment variable (default to 8000)
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Number of worker processes
workers = 1  # For a bot, a single worker is typically enough

# Worker class
worker_class = 'sync'  # Use sync workers for Flask

# Timeout for worker processes in seconds
timeout = 120  # Longer timeout since the bot might have longer-running operations

# Log level
loglevel = 'info'

# Process name
proc_name = 'matchmaking-bot'

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50  # Add jitter to max_requests to avoid all workers restarting at the same time

# Graceful timeout (seconds) - Wait for workers to finish serving requests before gracefully restarting
graceful_timeout = 30

# Keep the process alive, even if no requests are coming in
keepalive = 5  # Seconds

# Access log format
accesslog = '-'  # Log to stdout
errorlog = '-'  # Log to stderr

# Define a function to start the bot when Gunicorn is ready
def post_fork(server, worker):
    """Start the bot after forking a worker"""
    def start_bot_thread():
        # Import here to avoid circular imports
        try:
            from main import main, Bot
            from highrise.__main__ import BotDefinition
            import asyncio
            
            print("Starting Matchmaking Bot in worker...")
            
            # Define bot configuration
            bot_definition = BotDefinition(
                bot=Bot,
                room_id=os.getenv("ROOM_ID"),
                token=os.getenv("BOT_TOKEN"),
            )
            
            # Create a new event loop for the bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            main(bot_definition)
        except Exception as e:
            print(f"Bot thread error: {e}")
    
    # Only start the bot in the first worker
    if worker.nr == 0:
        bot_thread = Thread(target=start_bot_thread)
        bot_thread.daemon = True
        bot_thread.start()
        print(f"Bot thread started in worker {worker.nr}")

# Number of worker processes
workers = 4  # For a bot, a single worker is typically enough

# Worker class
worker_class = 'sync'  # Use sync workers for Flask

# Timeout for worker processes in seconds
timeout = 120  # Longer timeout since the bot might have longer-running operations

# Log level
loglevel = 'info'

# Process name
proc_name = 'matchmaking-bot'

# Preload the application
preload_app = True

# Maximum number of requests a worker will process before restarting
max_requests = 1000
max_requests_jitter = 50  # Add jitter to max_requests to avoid all workers restarting at the same time

# Graceful timeout (seconds) - Wait for workers to finish serving requests before gracefully restarting
graceful_timeout = 30

# Keep the process alive, even if no requests are coming in
keepalive = 5  # Seconds

# Access log format
accesslog = '-'  # Log to stdout
errorlog = '-'  # Log to stderr