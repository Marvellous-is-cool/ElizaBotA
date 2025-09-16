#!/usr/bin/env python3

"""
Production run script for the Birthday Bot with web server for Render
"""

import asyncio
import sys
import os
from pathlib import Path
from threading import Thread
from flask import Flask
import time

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from main import main

# Create Flask app for health checks (required for Render web service)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🎂 Birthday Bot is running! 💕"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "birthday-bot"}

def run_web_server():
    """Run Flask web server on the PORT specified by Render"""
    port = int(os.getenv('PORT', 6000))
    print(f"🌐 Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

def run_bot():
    """Run the birthday bot"""
    print("🎉 Starting Birthday Bot... 🎂")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Birthday Bot stopped!")
    except Exception as e:
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
