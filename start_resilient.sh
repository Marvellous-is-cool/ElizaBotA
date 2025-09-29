#!/bin/bash

echo "🚀 Starting ElizaBot with resilient multilogin-resistant deployment..."

# Kill any existing Python processes that might be running our bot
echo "🔪 Cleaning up any existing bot processes..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "python.*safe_main.py" 2>/dev/null || true
pkill -f "python.*resilient_launcher.py" 2>/dev/null || true
pkill -f "gunicorn.*wsgi:app" 2>/dev/null || true

# Clean up lock files
echo "🧹 Cleaning up lock files..."
rm -f /tmp/ElizaBot.lock /tmp/ElizaBot.pid 2>/dev/null || true

# Wait for cleanup
sleep 5

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found!"
    exit 1
fi

# Check if required files exist
if [ ! -f "resilient_launcher.py" ]; then
    echo "❌ Error: resilient_launcher.py not found!"
    exit 1
fi

if [ ! -f "instance_manager.py" ]; then
    echo "❌ Error: instance_manager.py not found!"
    exit 1
fi

if [ ! -f "connection_pool.py" ]; then
    echo "❌ Error: connection_pool.py not found!"
    exit 1
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo "📁 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start with resilient launcher
echo "🚀 Starting bot with Resilient Launcher (multilogin prevention)..."
echo "🔒 Features: Instance management, connection pooling, TaskGroup error handling"

# Use nohup to run in background if needed
if [ "$1" = "daemon" ]; then
    echo "🌙 Running in daemon mode..."
    nohup python3 resilient_launcher.py > bot_output.log 2>&1 &
    echo $! > bot.pid
    echo "✅ Bot started in background (PID: $(cat bot.pid))"
    echo "📁 Logs: tail -f bot_output.log"
else
    echo "🖥️ Running in foreground mode..."
    exec python3 resilient_launcher.py
fi