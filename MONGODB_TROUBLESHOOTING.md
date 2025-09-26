# MongoDB Connection Troubleshooting

This document explains how to troubleshoot MongoDB connection issues when deploying your Highrise bot.

## Testing MongoDB Connection Locally

1. Make sure your `.env` file contains the correct MongoDB connection string:

```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority
MONGODB_DB_NAME=YourDatabaseName
```

2. Run the MongoDB connection test script:

```bash
python test_mongodb_connection.py
```

This script will:
- Verify your MongoDB connection string is valid
- Attempt to connect to the database
- List available collections
- Run a simple query

## Checking MongoDB Connection in Production

When deployed on Render, you can check the MongoDB connection by:

1. Making sure the environment variables are correctly set in your Render dashboard:
   - Go to the Render Dashboard → Your Service → Environment
   - Verify `MONGODB_URI` and `MONGODB_DB_NAME` are set correctly

2. Check the logs in the Render dashboard for MongoDB connection information:
   - The improved code now logs MongoDB connection status
   - Look for "Connected to MongoDB database" or error messages

## Common MongoDB Connection Issues

### Connection Timeout

If you see errors like:
```
ServerSelectionTimeoutError: No servers found yet
```

This usually means:
- The MongoDB server is not accessible from your environment
- Network connectivity issues
- MongoDB Atlas IP allowlist is not configured properly

**Solution:** In MongoDB Atlas:
1. Go to Network Access
2. Add your current IP address
3. For Render deployment, add 0.0.0.0/0 (or better, Render's IP ranges)

### Authentication Failed

If you see errors related to authentication:

**Solution:**
1. Check the username and password in your connection string
2. Ensure the user has the appropriate permissions
3. Recreate the user in MongoDB Atlas if necessary

### Database Not Found

If the connection succeeds but you can't access your data:

**Solution:**
1. Make sure you're using the correct database name
2. Check if the collections exist
3. Initialize the database with test data if needed

## Ensuring MongoDB Works with Gunicorn

The code has been updated to properly initialize MongoDB when running with Gunicorn:

1. `safe_main.py` now explicitly initializes the MongoDB connection
2. `wsgi.py` and `gunicorn_config.py` have improved error handling
3. `start.sh` tests the MongoDB connection before starting Gunicorn

If you're still having issues, try running:

```bash
./start.sh
```

This script will test the MongoDB connection before starting Gunicorn.

## Testing MongoDB Independently

You can test your MongoDB connection independently using:

```bash
python -c "
import asyncio, os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
async def test():
    uri = os.getenv('MONGODB_URI')
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    await client.server_info()
    print('Connection successful!')

asyncio.run(test())
"
```

If this fails while `test_mongodb_connection.py` succeeds, there might be an issue with how the credentials are loaded in your application.