# Command Testing Guide for Gunicorn Deployment

This guide helps you test that all bot commands work properly when deployed with Gunicorn.

## Commands to Test

### Room Chat Commands

**Owner Only:**
- `!set` - Set bot position (should work immediately)
- `!fixdata` - Fix registration data  
- `!set event <date>` - Set event date
- `!addhost <username>` - Add host
- `!removehost <username>` - Remove host

**Host/Owner:**
- `!notify <message>` - Send notification to subscribers
- `!start` - Start match show
- `!stop` - Stop match show
- `!clear` - Clear registrations
- `!next` - Next contestant
- `!match` - Create match

**Anyone:**
- `!equip <item>` - Equip item
- `!remove <item>` - Remove item
- `!unsub` - Unsubscribe from notifications
- `!help` - Get help
- `!stats` - View statistics

### Whisper Commands

**Registration:**
- `POP` - Start POP registration
- `LOVE` - Start LOVE registration
- `!sub` - Subscribe to notifications
- `help` - Get help via whisper

## Testing Checklist

### 1. Basic Functionality Test
```
✅ Bot responds to commands in chat
✅ Bot responds to whispers  
✅ Commands execute without errors
✅ Database operations work (if MongoDB connected)
✅ Commands work for different user permission levels
```

### 2. Error Handling Test
```
✅ Invalid commands show appropriate errors
✅ Permission-restricted commands show access denied
✅ Database failures don't crash the bot
✅ Network issues don't break command processing
```

### 3. Performance Test  
```
✅ Multiple users can use commands simultaneously
✅ Commands don't block other bot functions
✅ Bot remains responsive during command processing
✅ Memory usage stays stable over time
```

### 4. Gunicorn-Specific Test
```
✅ Commands work immediately after deployment
✅ Bot state persists across requests
✅ Database connection is maintained
✅ No race conditions between commands
```

## Monitoring Endpoints

Use these endpoints to monitor bot health:

**Basic Health Check:**
```
GET /health
```

**Detailed Status:**
```
GET /bot-status
```

The `/bot-status` endpoint shows:
- Bot running status
- Database connection status  
- Environment variables status
- Command functionality prediction

## Troubleshooting Commands

If commands aren't working:

### 1. Check Bot Connection
- Look for "Starting bot in worker 0" in logs
- Verify bot appears online in Highrise room
- Check `/bot-status` endpoint

### 2. Check Database Connection  
- Look for MongoDB connection messages in logs
- Check `/bot-status` for database_connected: true
- Test with `python test_mongodb_connection.py`

### 3. Check Permissions
- Ensure bot is invited to the room
- Verify ROOM_ID matches the actual room
- Check BOT_TOKEN is valid and complete

### 4. Check Environment Variables
```bash
# In Render dashboard, verify:
ROOM_ID=your_room_id
BOT_TOKEN=your_bot_token  
MONGODB_URI=your_connection_string
```

## Expected Behavior

### !set Command
- **Working**: "Bot position updated! 📍"
- **Not Working**: "Error setting position: [error]"
- **Permission Issue**: "Only the room owner can set my position! 🔒"

### Database Commands (!addhost, !unsub, etc.)
- **With Database**: Commands save data permanently
- **Without Database**: Commands work but data not persisted
- **Database Error**: Command continues but shows warning

### Registration Commands (POP, LOVE)
- **Working**: User gets registration prompts
- **Not Working**: No response or error message
- **Database Issue**: Registration works but may not persist

## Performance Expectations

With Gunicorn deployment:
- ✅ Commands should respond within 1-2 seconds
- ✅ Multiple users can register simultaneously  
- ✅ Bot handles 10+ concurrent command requests
- ✅ Memory usage stays under 100MB per worker
- ✅ No noticeable delays or timeouts

## Common Issues and Fixes

**Commands not responding:**
- Check bot initialization in logs
- Restart the Render service
- Verify environment variables

**Database operations failing:**
- Check MongoDB Atlas IP allowlist
- Verify connection string format
- Test connection independently

**Permission errors:**
- Verify user IDs in bot logs
- Check owner_id initialization
- Ensure proper room permissions

**Slow responses:**
- Check Render region/MongoDB region proximity
- Monitor database connection latency  
- Consider connection pooling optimization