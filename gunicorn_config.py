"""
Gunicorn configuration file for the Matchmaking Bot
"""
import os
import multiprocessing

# Import the when_ready function to start the bot
from wsgi import when_ready

# Server hooks
on_starting = None
on_reload = None
on_ready = when_ready  # Call our function when the server is ready

# Bind to 0.0.0.0 on the port specified by the PORT environment variable (default to 8000)
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

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