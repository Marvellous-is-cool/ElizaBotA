#!/usr/bin/env python3

"""
Debug script for running the bot directly with verbose error reporting
"""

import os
import asyncio
import traceback
from dotenv import load_dotenv
from main import main

# Load environment variables
load_dotenv()

async def run_with_error_handling():
    try:
        # Run the main function
        await main()
    except Exception as e:
        print(f"ERROR: Bot connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        
        # For TaskGroup errors, try to extract the inner exception
        if "TaskGroup" in str(e):
            print("\nAttempting to extract inner TaskGroup exception...")
            try:
                if hasattr(e, "__context__") and e.__context__:
                    print(f"Inner exception: {e.__context__}")
                    print(f"Inner exception type: {type(e.__context__).__name__}")
                    if hasattr(e.__context__, "exceptions") and e.__context__.exceptions:
                        for i, ex in enumerate(e.__context__.exceptions):
                            print(f"Exception {i+1}: {ex}")
                            print(f"Exception {i+1} type: {type(ex).__name__}")
                if hasattr(e, "__cause__") and e.__cause__:
                    print(f"Cause: {e.__cause__}")
            except Exception as extract_error:
                print(f"Failed to extract inner exception: {extract_error}")

if __name__ == "__main__":
    # Print environment variables for debugging
    print(f"ROOM_ID: {'Set' if os.getenv('ROOM_ID') else 'Not set'}")
    print(f"BOT_TOKEN: {'Set' if os.getenv('BOT_TOKEN') else 'Not set'}")
    
    # Run the bot
    print("Starting bot...")
    asyncio.run(run_with_error_handling())