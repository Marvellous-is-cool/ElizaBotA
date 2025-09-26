#!/usr/bin/env python3

"""
WSGI module for Gunicorn deployment
This module provides the WSGI application object that Gunicorn needs
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import the Flask app from webserver
from webserver import app

# This is the WSGI application object that Gunicorn will use
application = app

# For debugging - print some info when this module is loaded
print("WSGI module loaded successfully")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path includes: {current_dir}")

if __name__ == "__main__":
    # This is for local testing only
    port = int(os.getenv('PORT', 8080))
    print(f"Running Flask app directly on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)