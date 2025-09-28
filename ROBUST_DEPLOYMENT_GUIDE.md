# 🚀 Robust Bot Deployment Guide

## Overview
This deployment provides a highly durable, 24/7 matchmaking bot with automatic restart capabilities and comprehensive monitoring.

## Key Improvements

### 🔄 Multi-Worker Architecture
- **4 Gunicorn workers** for redundancy
- **Primary worker (0)** runs the bot
- **Secondary workers (1-3)** provide failover capability
- **Automatic worker recycling** after 2000 requests

### 💊 Health Monitoring System
- **Database connectivity checks** every 5 minutes
- **Automatic reconnection** on database failures
- **Bot process supervision** with restart capabilities
- **Comprehensive logging** with web interface

### 🛡️ Error Recovery
- **Exponential backoff** on connection failures
- **3-retry system** for database initialization
- **Graceful degradation** when services fail
- **Crash recovery** with restart limits

## Monitoring Endpoints

### Health Check
```bash
curl https://your-app.onrender.com/health
```
Response:
```json
{
  "status": "healthy",
  "bot": "matchmaking-bot", 
  "bot_running": true,
  "uptime_seconds": 3600
}
```

### Detailed Status
```bash
curl https://your-app.onrender.com/bot-status
```

### Live Logs
```bash
curl https://your-app.onrender.com/logs?limit=20&level=ERROR
```

### Interactive Dashboard
Visit: `https://your-app.onrender.com/dashboard`

## Testing the Deployment

### 1. Local Testing
```bash
# Test database connection
python test_mongodb_connection.py

# Test bot startup
python debug_run.py

# Test web server
python webserver.py
```

### 2. Production Testing
```bash
# Check if bot is running
curl https://your-app.onrender.com/health

# View recent logs
curl https://your-app.onrender.com/logs/live

# Check bot metrics
curl https://your-app.onrender.com/bot-metrics
```

### 3. Bot Commands Testing
In Highrise room:
- `!help` - Should show all available commands
- `!match` - Should register for matchmaking
- `!status` - Should show registration status

## Deployment Configuration

### Gunicorn Settings
- **Workers**: 4 (for robustness)
- **Timeout**: 300 seconds (for long-running operations)
- **Max Requests**: 2000 (worker recycling)
- **Graceful Timeout**: 60 seconds
- **Memory Limit**: 200MB per worker

### Environment Variables
Required:
- `BOT_TOKEN` - Highrise bot token
- `ROOM_ID` - Target room ID
- `MONGODB_URI` - MongoDB connection string

Optional:
- `PORT` - Server port (auto-set by Render)
- `MONGODB_DB_NAME` - Database name (default: "MatchBot")

## Troubleshooting

### Bot Not Connecting
1. Check `/health` endpoint
2. View logs: `/logs?level=ERROR`
3. Verify environment variables in Render dashboard
4. Check MongoDB connection with `/bot-status`

### Database Issues
1. Verify `MONGODB_URI` format includes SSL parameters
2. Check database connectivity: `/bot-status`
3. Review connection logs: `/logs?limit=50`
4. MongoDB will auto-retry with exponential backoff

### Memory/Performance Issues
1. Monitor metrics: `/bot-metrics`
2. Check worker memory usage in Render logs
3. Review error rates: `/logs?level=ERROR`
4. Workers auto-restart after 2000 requests

## Best Practices

### 🔍 Regular Monitoring
- Check `/health` endpoint daily
- Monitor `/bot-metrics` for performance
- Review error logs weekly: `/logs?level=ERROR`

### 🚨 Emergency Procedures
- **Bot crash**: Check `/logs` for errors
- **Database issues**: Logs show auto-retry attempts
- **Memory leaks**: Workers auto-restart periodically
- **Total failure**: Render auto-restarts the service

### 📊 Performance Optimization
- Monitor response times via `/bot-metrics`
- Check database query performance in logs
- Review memory usage patterns
- Adjust worker count if needed

## Files Structure
```
BotA/
├── deploy_robust.sh         # Main deployment script
├── gunicorn_config.py      # Multi-worker configuration
├── webserver.py            # Flask app with monitoring
├── main.py                 # Bot with health monitoring
├── render.yaml             # Render deployment config
├── wsgi.py                 # WSGI entry point
└── requirements.txt        # Dependencies
```

## Success Indicators
✅ **Health endpoint returns 200**
✅ **Bot responds to commands in room**
✅ **Database queries work (matchmaking)**
✅ **Logs show periodic health checks**
✅ **Dashboard shows uptime > 24 hours**

This robust deployment ensures your bot stays active 24/7 with automatic recovery from any failures!