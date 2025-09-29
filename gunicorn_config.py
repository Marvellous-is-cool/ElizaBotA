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
    """Start the resilient bot manager after forking a worker - MULTILOGIN PREVENTION"""
    print(f"🔒 Initializing worker {worker.nr} with multilogin prevention")
    
    # CRITICAL: Only start bot in the PRIMARY worker to prevent multilogin
    if worker.nr == 0:
        print(f"🎯 Primary worker {worker.nr} - Bot will start here")
    else:
        print(f"⚠️ Secondary worker {worker.nr} - Bot DISABLED to prevent multilogin")
    
    # Import managers with error handling
    import threading
    import asyncio
    
    try:
        from webserver import BotManager
        bot_manager_available = True
    except ImportError as e:
        print(f"⚠️ BotManager import failed: {e}")
        bot_manager_available = False
    
    try:
        from connection_resilience import ResilientBotManager
        resilient_manager_available = True
    except ImportError as e:
        print(f"⚠️ ResilientBotManager import failed: {e}")
        resilient_manager_available = False
    
    # Create web-based bot manager for dashboard (if available)
    if bot_manager_available:
        try:
            bot_manager = BotManager(worker_id=worker.nr)
            manager_thread = threading.Thread(target=bot_manager.start, daemon=True)
            manager_thread.start()
            print(f"✅ Web manager started for worker {worker.nr}")
        except Exception as e:
            print(f"⚠️ Web manager failed to start: {e}")
    
    # Create resilient connection manager for TaskGroup protection (if available)
    if resilient_manager_available:
        def run_resilient_bot():
            try:
                resilient_manager = ResilientBotManager()
                asyncio.run(resilient_manager.run_with_resilience())
            except KeyboardInterrupt:
                print(f"[Worker-{worker.nr}] 👋 Resilient bot shutdown requested")
            except Exception as e:
                print(f"[Worker-{worker.nr}] ❌ Resilient bot error: {e}")
                # Let it restart automatically via cron
        
        resilient_thread = threading.Thread(target=run_resilient_bot, daemon=True)
        resilient_thread.start()
        print(f"✅ Resilient connection manager started for worker {worker.nr}")
    
    # Fallback: If no managers available, at least log it
    if not bot_manager_available and not resilient_manager_available:
        print(f"⚠️ Worker {worker.nr}: No bot managers available - running minimal configuration")

def worker_int(worker):
    """Handle worker interruption"""
    print(f"Worker {worker.pid} interrupted, cleaning up bot...")

def when_ready(server):
    """Called when Gunicorn is ready to accept connections"""
    print(f"Gunicorn server ready with {server.cfg.workers} workers")
