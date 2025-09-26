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
            from main import main, Bot
            from highrise.__main__ import BotDefinition
            import asyncio

            print("Starting Matchmaking Bot in worker...")

            # Create a Bot instance first
            bot_instance = Bot()
            
            # Use positional arguments as shown in main.py
            bot_definition = BotDefinition(
                bot_instance,
                os.getenv("ROOM_ID"),
                os.getenv("BOT_TOKEN")
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            main(bot_definition)
        except Exception as e:
            print(f"Bot thread error: {e}")

    if worker.nr == 0:
        bot_thread = Thread(target=start_bot_thread, daemon=True)
        bot_thread.start()
        print(f"Bot thread started in worker {worker.nr}")
