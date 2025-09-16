#!/usr/bin/env python3

"""
Simplified run script for the Birthday Bot
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(str(Path(__file__).parent))

from main import main

if __name__ == "__main__":
    print("🎉 Starting Birthday Bot... 🎂")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Birthday Bot stopped!")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)
