from flask import Flask, jsonify
import os
from threading import Thread
from dotenv import load_dotenv
import asyncio
import time
import signal
import sys

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Global variables to track bot status
bot_running = False
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
        "bot_running": bot_running,
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
    global bot_running, bot_start_time
    
    # Import here to avoid circular imports
    from main import main, Bot
    from highrise import __main__
    from highrise.__main__ import BotDefinition
    
    # Record start time for uptime tracking
    bot_start_time = time.time()
    bot_running = True
    
    # Get environment variables
    room_id = os.getenv("ROOM_ID")
    bot_token = os.getenv("BOT_TOKEN")
    
    if not room_id or not bot_token:
        print("❌ Error: Missing ROOM_ID or BOT_TOKEN environment variables!")
        bot_running = False
        return
    
    # Clean the credentials
    room_id = room_id.strip().rstrip('%') if room_id else None
    bot_token = bot_token.strip().rstrip('%') if bot_token else None
    
    print(f"Starting bot for room: {room_id}")
    
    # Run the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Create bot instance and definition
        bot_instance = Bot()
        definitions = [BotDefinition(bot_instance, room_id, bot_token)]
        
        # Run the main function from Highrise SDK
        loop.run_until_complete(__main__.main(definitions))
    except Exception as e:
        print(f"Bot crashed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        bot_running = False

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