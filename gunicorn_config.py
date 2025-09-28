"""
Gunicorn configuration file for the Matchmaking Bot
"""
import os
from threading import Thread

# Get the PORT environment variable and convert it to an integer
# Render sets this automatically, and we need to respect it
port = int(os.getenv('PORT', '6000'))
bind = f"0.0.0.0:{port}"
workers = 4  # Multiple workers for robustness
worker_class = 'sync'
timeout = 300  # Longer timeout for bot operations
loglevel = 'info'
proc_name = 'matchmaking-bot'
preload_app = True
max_requests = 2000
max_requests_jitter = 100
graceful_timeout = 60
keepalive = 10
accesslog = '-'
errorlog = '-'
worker_connections = 1000
max_worker_memory = 200  # MB

def post_fork(server, worker):
    """Start the bot manager after forking a worker"""
    # Start bot manager in all workers for redundancy
    print(f"Initializing worker {worker.nr} with bot manager")
    
    # Import and start the bot manager from webserver
    from webserver import BotManager
    import threading
    
    # Create and start bot manager in this worker
    bot_manager = BotManager(worker_id=worker.nr)
    manager_thread = threading.Thread(target=bot_manager.start, daemon=True)
    manager_thread.start()
    
    print(f"Bot manager started in worker {worker.nr}")

def worker_int(worker):
    """Handle worker interruption"""
    print(f"Worker {worker.pid} interrupted, cleaning up bot...")

def when_ready(server):
    """Called when Gunicorn is ready to accept connections"""
    print(f"Gunicorn server ready with {server.cfg.workers} workers")
