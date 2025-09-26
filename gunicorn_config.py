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
    if worker.nr == 0:  # Only start bot in the first worker
        print(f"Starting bot in worker {worker.nr}")
        
        # Import and start the bot function from webserver
        from webserver import start_bot
        from threading import Thread
        
        # Start the bot in a background thread
        bot_thread = Thread(target=start_bot, daemon=True)
        bot_thread.start()
        
        print(f"Bot thread started in worker {worker.nr}")
