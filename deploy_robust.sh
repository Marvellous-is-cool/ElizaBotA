#!/bin/bash

# Robust Bot Deployment Script
echo "🚀 Starting robust matchmaking bot deployment..."

# Check environment variables
if [ -z "$ROOM_ID" ]; then
    echo "❌ ROOM_ID environment variable not set"
    exit 1
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN environment variable not set"
    exit 1
fi

if [ -z "$MONGODB_URI" ]; then
    echo "❌ MONGODB_URI environment variable not set"
    exit 1
fi

echo "✅ Environment variables validated"

# Install dependencies
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"

# Test database connection
echo "🔍 Testing database connection..."
python -c "
import asyncio
import os
from db.init_db import initialize_db

async def test_db():
    try:
        client = await initialize_db()
        if client:
            print('✅ Database connection successful')
            await client.disconnect()
            return True
        else:
            print('❌ Database connection failed')
            return False
    except Exception as e:
        print(f'❌ Database error: {e}')
        return False

result = asyncio.run(test_db())
exit(0 if result else 1)
"

if [ $? -ne 0 ]; then
    echo "❌ Database connection test failed"
    exit 1
fi

# Start the application with Gunicorn
echo "🔥 Starting Gunicorn with robust bot management..."
echo "Workers: 4"
echo "Port: ${PORT:-10000}"
echo "Timeout: 300 seconds"

exec gunicorn --config gunicorn_config.py wsgi:application