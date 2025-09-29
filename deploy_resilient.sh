#!/bin/bash
# Enhanced deployment script with TaskGroup error prevention
# Uses the resilient connection manager

echo "🚀 Enhanced 24/7 Bot Deployment with TaskGroup Protection"
echo "========================================================"

# Check environment variables
if [ -z "$ROOM_ID" ] || [ -z "$BOT_TOKEN" ]; then
    echo "❌ Missing ROOM_ID or BOT_TOKEN environment variables"
    exit 1
fi

echo "✅ Environment variables configured"
echo "🎯 Target room: $ROOM_ID"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt > /dev/null 2>&1

# Check if we should use Gunicorn (production) or safe_bot (development)
if [ "$DEPLOYMENT_MODE" = "production" ]; then
    echo "🏭 Starting production deployment with Gunicorn..."
    echo "   • 4 workers with resilient connection managers"
    echo "   • TaskGroup error protection enabled"
    echo "   • Health monitoring and auto-recovery"
    exec gunicorn --config gunicorn_config.py webserver:app
else
    echo "🧪 Starting development deployment with safe_bot..."
    echo "   • Single resilient connection manager"
    echo "   • Direct TaskGroup error handling"
    echo "   • Enhanced logging and monitoring"
    exec python3 safe_bot.py
fi