# Deploying the Matchmaking Bot with Gunicorn

This guide explains how to deploy the Matchmaking Bot using Gunicorn for production environments.

## How It Works

The bot uses a WSGI setup for production deployment:

- `wsgi.py`: WSGI application entry point for Gunicorn
- `webserver.py`: Flask web server that also manages the bot
- `gunicorn_config.py`: Gunicorn configuration with bot startup hooks
- `render.yaml`: Render platform configuration

## Local Testing

Before deploying to Render, test the setup:

```bash
# Install dependencies
pip install -r requirements.txt

# Test WSGI setup
python test_wsgi_setup.py

# Test with Gunicorn locally
gunicorn --config gunicorn_config.py wsgi:application

# Alternative: Test with run.py for comparison
python run.py
```

## Deployment on Render

### 1. Environment Variables

Set these in your Render dashboard:

**Required:**
- `ROOM_ID`: Your Highrise room ID
- `BOT_TOKEN`: Your Highrise bot token

**Optional:**
- `MONGODB_URI`: Your MongoDB connection string
- `MONGODB_DB_NAME`: Your database name (defaults to "MatchShowBot")

**Automatic:**
- `PORT`: Set automatically by Render

### 2. Deploy with render.yaml

The current `render.yaml` configuration:

```yaml
services:
  - type: web
    name: matchmaking-bot
    runtime: python
    buildCommand: pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
    startCommand: gunicorn --config gunicorn_config.py wsgi:application
```

This will:
1. Install dependencies during build
2. Start Gunicorn with the proper WSGI application
3. Automatically start the bot in a background thread
4. Serve the Flask web interface for health checks

### 3. Manual Render Configuration

If not using `render.yaml`:

1. Create a new "Web Service"
2. Connect your Git repository
3. Set build command: `pip install --upgrade pip setuptools wheel && pip install -r requirements.txt`
4. Set start command: `gunicorn --config gunicorn_config.py wsgi:application`
5. Add environment variables
6. Deploy

## Monitoring

### Health Check Endpoints

- `GET /`: Basic alive check
- `GET /health`: Detailed status with bot uptime

### Logs

Check Render logs for:
- "Starting bot in worker 0" - Bot initialization
- MongoDB connection status
- Highrise connection status
- Bot command responses

## Troubleshooting

### Bot Not Responding to Commands

1. **Check Logs**: Look for bot initialization errors
2. **Verify Environment**: Ensure `ROOM_ID` and `BOT_TOKEN` are correct
3. **Test Locally**: Compare with `python run.py` behavior
4. **Check Bot Permissions**: Ensure bot is invited to the room

### "No application module specified" Error

This error is fixed in the current configuration. If you see it:
1. Verify `wsgi.py` exports `application`
2. Check `render.yaml` uses `wsgi:application` not `wsgi:app`

### MongoDB Connection Issues

1. **SSL Errors**: Check IP allowlisting in MongoDB Atlas
2. **Connection String**: Verify `MONGODB_URI` format
3. **Test Connection**: Use `python test_mongodb_connection.py`

### Import Errors

1. **Run Tests**: `python test_wsgi_setup.py`
2. **Check Dependencies**: Verify `requirements.txt` is complete
3. **Path Issues**: Ensure all modules are in the correct directory

## Development vs Production

**Development (`run.py`):**
- Direct bot execution
- Flask runs in main thread
- Good for testing and debugging

**Production (Gunicorn):**
- WSGI-compliant web server
- Bot runs in background thread
- Proper process management
- Better resource handling

## Maintenance

**Updates:**
1. Push to Git repository
2. Render auto-deploys from main branch

**Monitoring:**
- Set up Render alerts for failures
- Monitor `/health` endpoint
- Check logs regularly for errors

**Scaling:**
- Current setup uses 1 worker (recommended for this bot)
- Bot state is maintained in MongoDB
- Can handle multiple concurrent web requests

## Files Reference

- `wsgi.py`: WSGI application entry point
- `webserver.py`: Flask app + bot management  
- `gunicorn_config.py`: Gunicorn configuration
- `render.yaml`: Render deployment config
- `test_wsgi_setup.py`: Setup verification script
