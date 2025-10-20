"""
Gunicorn configuration file for the Matchmaking Bot
"""
import os
from threading import Thread

# Get the PORT environment variable and convert it to an integer
# Render sets this automatically, and we need to respect it
port = int(os.getenv('PORT', '6000'))
bind = f"0.0.0.0:{port}"
workers = 1  # CRITICAL: Single worker prevents multilogin conflicts!
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
    """Start ONLY ONE bot manager after forking a worker - CRITICAL FOR MULTILOGIN PREVENTION"""
    print(f"🔒 Initializing worker {worker.nr} with multilogin prevention")
    
    # CRITICAL: Only start bot in the PRIMARY worker to prevent multilogin
    if worker.nr != 0:
        print(f"⚠️ Secondary worker {worker.nr} - Bot DISABLED to prevent multilogin")
        return  # Exit early for non-primary workers
    
    print(f"🎯 Primary worker {worker.nr} - Starting bot here ONLY")
    
    # Import managers with error handling
    import threading
    import asyncio
    
    # CRITICAL: Only use connection_resilience, NOT both managers!
    # Using both BotManager AND ResilientBotManager causes multilogin!
    try:
        from connection_resilience import ResilientBotManager
        resilient_manager_available = True
        print("✅ Using ResilientBotManager (SINGLE INSTANCE)")
    except ImportError as e:
        print(f"❌ ResilientBotManager import failed: {e}")
        resilient_manager_available = False
    
    # Start ONLY the resilient manager
    if resilient_manager_available:
        def run_resilient_bot():
            try:
                print("🚀 Starting SINGLE bot instance via ResilientBotManager")
                resilient_manager = ResilientBotManager()
                asyncio.run(resilient_manager.run_with_resilience())
            except KeyboardInterrupt:
                print(f"[Worker-{worker.nr}] 👋 Bot shutdown requested")
            except Exception as e:
                print(f"[Worker-{worker.nr}] ❌ Bot error: {e}")
        
        resilient_thread = threading.Thread(target=run_resilient_bot, daemon=True)
        resilient_thread.start()
        print(f"✅ PRIMARY WORKER {worker.nr}: SINGLE bot instance started")
    else:
        print(f"❌ Worker {worker.nr}: No bot manager available!")

def worker_int(worker):
    """Handle worker interruption"""
    print(f"Worker {worker.pid} interrupted, cleaning up bot...")

def when_ready(server):
    """Called when Gunicorn is ready to accept connections"""
    print(f"Gunicorn server ready with {server.cfg.workers} workers")
