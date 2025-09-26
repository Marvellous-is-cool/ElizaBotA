#!/usr/bin/env python3

"""
Production run script for the Match Show Bot with web server for Render
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from threading import Thread
from flask import Flask
import time

# Configure logging (disabled)
logging.basicConfig(
    level=logging.CRITICAL,  # Only critical errors will be logged
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.disabled = True  # Disable this logger completely

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from main import main

# Create Flask app for health checks (required for Render web service)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "💘 Match Show Bot is running! 💕"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "match-show-bot"}

def run_web_server():
    """Run Flask web server on the PORT specified by Render"""
    port = int(os.getenv('PORT', 6000))
    logger.info(f"Starting web server on port {port}")
    print(f"🌐 Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

def run_bot():
    """Run the Match Show bot"""
    logger.info("Starting Match Show Bot...")
    print("💘 Starting Match Show Bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Match Show Bot stopped by user")
        print("\n👋 Match Show Bot stopped!")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Start web server in background thread
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Small delay to let web server start
    time.sleep(2)
    
    # Run the bot in main thread
    run_bot()
