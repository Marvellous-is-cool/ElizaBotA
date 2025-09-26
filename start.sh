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

# Start gunicorn with the specified config and explicit port binding
echo "Executing: gunicorn -c gunicorn_config.py --bind 0.0.0.0:${PORT:-10000} wsgi:app"
exec gunicorn -c gunicorn_config.py --bind 0.0.0.0:${PORT:-10000} wsgi:app