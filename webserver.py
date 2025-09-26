from flask import Flask, jsonify
import os
from threading import Thread
from dotenv import load_dotenv
import asyncio
import time
import signal
import sys

# Import bot-related modules
from main import main, Bot
from highrise.__main__ import BotDefinition

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Global variables to track bot status
bot_instance = None
bot_start_time = None
bot_thread = None

@app.route('/')
def home():
    return "💘 Matchmaking Bot is alive! 💕"

@app.route('/health')
def health():
    uptime = None
    if bot_start_time:
        uptime = round(time.time() - bot_start_time)
    
    return jsonify({
        "status": "healthy", 
        "bot": "matchmaking-bot",
        "bot_running": bot_instance is not None,
        "uptime_seconds": uptime
    })

@app.route('/restart', methods=['POST'])
def restart_bot():
    """Endpoint to restart the bot (protected in production)"""
    # In production, this should have authentication
    restart_bot_process()
    return jsonify({"status": "restarting"})

def run_flask():
    """Run the Flask app for development purposes"""
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8081)),
        debug=True,
        use_reloader=False  # Disable reloader when running with the bot
    )

def keep_alive():
    """Legacy method to keep the web server alive in development"""
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

def start_bot():
    """Start the Highrise bot in a separate thread"""
    global bot_instance, bot_start_time
    
    # Record start time for uptime tracking
    bot_start_time = time.time()
    
    # Define bot configuration
    bot_definition = BotDefinition(
        bot=Bot,
        room_id=os.getenv("ROOM_ID"),
        token=os.getenv("BOT_TOKEN"),
    )
    
    # Run the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        main(bot_definition)
    except Exception as e:
        print(f"Bot crashed with error: {e}")
    finally:
        bot_instance = None

def restart_bot_process():
    """Restart the bot process"""
    global bot_thread
    
    # Stop existing bot if running
    if bot_thread and bot_thread.is_alive():
        # Signal bot to stop (this depends on how your bot handles signals)
        # This is a simple implementation and might need more robust handling
        bot_thread.join(timeout=5)
    
    # Start bot in a new thread
    bot_thread = Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    print("Received shutdown signal, closing...")
    # Clean up resources here if needed
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# For production with Gunicorn, the bot will be started differently
# See the if __name__ == "__main__" block in run.py

if __name__ == "__main__":
    # Start the bot in a separate thread
    restart_bot_process()
    
    # Start the Flask app in the main thread
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8081)),
        debug=False
    )