#!/bin/bash
# start.sh - Production startup script for the Matchmaking Bot

echo "Starting Matchmaking Bot with Gunicorn..."
exec gunicorn -c gunicorn_config.py wsgi:app