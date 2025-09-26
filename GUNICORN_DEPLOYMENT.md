# Deploying the Matchmaking Bot with Gunicorn

This guide explains how to deploy the Matchmaking Bot using Gunicorn for production environments.

## Local Testing

Before deploying to Render, test locally:

```bash
# Make sure all dependencies are installed
pip install -r requirements.txt

# Make the start script executable
chmod +x start.sh

# Run the bot with Gunicorn
./start.sh
```

## Deployment on Render

### 1. Set Up Environment Variables

Make sure to set these environment variables in your Render dashboard:

- `ROOM_ID`: Your Highrise room ID
- `BOT_TOKEN`: Your Highrise bot token
- `MONGODB_URI`: Your MongoDB connection string
- `MONGODB_DB_NAME`: Your MongoDB database name (optional)
- `PORT`: Will be set automatically by Render

### 2. Configure the Render Service

#### Option 1: Using render.yaml

If deploying with the existing render.yaml file, ensure it has:

```yaml
services:
  - type: web
    name: matchmaking-bot
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: ./start.sh
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

#### Option 2: Manual Dashboard Configuration

If creating a new service in Render dashboard:

1. Choose "Web Service"
2. Link to your Git repository
3. Set a name (e.g., "matchmaking-bot")
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `./start.sh`
6. Add the environment variables listed above
7. Deploy the service

## Troubleshooting

If the bot runs but doesn't respond to commands:

1. Check the Render logs for any error messages
2. Verify MongoDB connection is successful
3. Make sure the bot is properly connected to Highrise
4. Try running locally with `python run.py` to compare behavior

If you see SSL errors with MongoDB:

1. Make sure your IP is allowlisted in MongoDB Atlas
2. Check that the MongoDB URI is correctly formatted
3. Try running `python test_mongodb_connection.py` to test the connection

## Maintaining the Bot

To update the bot:

1. Push changes to your Git repository
2. Render will automatically rebuild and deploy

To monitor the bot:

1. Use the Render dashboard to view logs
2. Set up alerts for service failures
3. Periodically check for MongoDB connection issues

## Additional Resources

- Gunicorn documentation: https://docs.gunicorn.org/
- Render documentation: https://render.com/docs
- MongoDB Atlas documentation: https://docs.atlas.mongodb.com/
