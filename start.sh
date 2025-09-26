#!/bin/bash
# start.sh - Production startup script for the Matchmaking Bot

echo "Starting Matchmaking Bot with Gunicorn..."

# Make sure gunicorn is installed
if ! command -v gunicorn &> /dev/null; then
    echo "Error: gunicorn not found. Installing..."
    pip install gunicorn
fi

# Make sure the app module is importable
if [ ! -f "wsgi.py" ]; then
    echo "Error: wsgi.py not found!"
    exit 1
fi

# Make sure the config file exists
if [ ! -f "gunicorn_config.py" ]; then
    echo "Error: gunicorn_config.py not found!"
    exit 1
fi

# Set environment variables if needed
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# Print environment info for debugging
echo "Environment: PORT=${PORT}"
echo "Current directory: $(pwd)"
echo "Python path: ${PYTHONPATH}"

# Check required environment variables
if [ -z "$ROOM_ID" ]; then
    echo "❌ Error: ROOM_ID not set in environment!"
    echo "Please set ROOM_ID in your .env file or environment variables"
    exit 1
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Error: BOT_TOKEN not set in environment!"
    echo "Please set BOT_TOKEN in your .env file or environment variables"
    exit 1
fi

echo "ROOM_ID: Found ✅"
echo "BOT_TOKEN: Found ✅"

# Check if MongoDB environment variables are set
if [ -z "$MONGODB_URI" ]; then
    echo "⚠️  Warning: MONGODB_URI not set in environment!"
    echo "    The bot will try to use default configuration from config.py"
    echo "    This may cause connection issues in production."
else
    # Mask the password for display
    MASKED_URI=$(echo $MONGODB_URI | sed -E 's/\/\/([^:]+):([^@]+)@/\/\/\1:****@/')
    echo "MongoDB URI: $MASKED_URI"
fi

if [ -z "$MONGODB_DB_NAME" ]; then
    echo "ℹ️  MONGODB_DB_NAME not set, will use default"
else
    echo "MongoDB Database: $MONGODB_DB_NAME"
fi

# Test the bot connection (similar to how run.py works)
echo "Verifying environment for bot..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

room_id = os.getenv('ROOM_ID')
bot_token = os.getenv('BOT_TOKEN')
mongodb_uri = os.getenv('MONGODB_URI')

print(f'ROOM_ID: {room_id[:5]}... (length: {len(room_id)})')
print(f'BOT_TOKEN: {bot_token[:5]}... (length: {len(bot_token)})')
if mongodb_uri:
    print(f'MONGODB_URI configured: Yes (length: {len(mongodb_uri)})')
else:
    print('MONGODB_URI configured: No')
" || echo "⚠️ Environment verification failed, but continuing startup"

# Test MongoDB connection before starting Gunicorn
echo "Testing MongoDB connection..."
python -c "
import asyncio
from db.init_db import initialize_db

async def test_connection():
    print('Initializing DB connection...')
    client = await initialize_db()
    if client:
        print('✅ MongoDB connection successful!')
        await client.disconnect()
        return True
    else:
        print('❌ MongoDB connection failed!')
        print('Bot will continue with limited functionality')
        return False

asyncio.run(test_connection())
" || echo "⚠️  MongoDB connection test failed, but continuing startup"

# Set log level for more verbose output
export GUNICORN_LOG_LEVEL=${GUNICORN_LOG_LEVEL:-"debug"}

# Start gunicorn with the specified config and explicit port binding
echo "Executing: gunicorn --config gunicorn_config.py --bind 0.0.0.0:${PORT:-10000} wsgi:application"
exec gunicorn --config gunicorn_config.py --bind 0.0.0.0:${PORT:-10000} wsgi:application