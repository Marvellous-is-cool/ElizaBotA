from flask import Flask, jsonify, request
import os
from threading import Thread
from dotenv import load_dotenv
import asyncio
import time
import signal
import sys
from collections import deque
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Global variables to track bot status
bot_running = False
bot_start_time = None
bot_thread = None

# Global log storage (thread-safe deque with max size)
bot_logs = deque(maxlen=1000)  # Keep last 1000 log entries
log_lock = asyncio.Lock()

class BotLogHandler(logging.Handler):
    """Custom log handler to capture bot logs"""
    
    def emit(self, record):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = {
                "timestamp": timestamp,
                "level": record.levelname,
                "message": self.format(record),
                "module": record.name
            }
            bot_logs.append(log_entry)
        except Exception:
            # Avoid infinite recursion if logging fails
            pass

# Set up logging to capture bot activities
def setup_logging():
    """Set up logging to capture bot activities"""
    # Create our custom handler
    bot_handler = BotLogHandler()
    bot_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    bot_handler.setFormatter(formatter)
    
    # Add handler to root logger to catch all logs
    root_logger = logging.getLogger()
    root_logger.addHandler(bot_handler)
    root_logger.setLevel(logging.INFO)
    
    # Also add handler specifically to highrise and bot modules
    highrise_logger = logging.getLogger('highrise')
    highrise_logger.addHandler(bot_handler)
    
    bot_logger = logging.getLogger('main')
    bot_logger.addHandler(bot_handler)

# Initialize logging
setup_logging()

@app.route('/')
def home():
    return "💘 Matchmaking Bot is alive! 💕"

@app.route('/health')
def health():
    uptime = None
    if bot_start_time:
        uptime = round(time.time() - bot_start_time)
    
    return jsonify({
        "status": "healthy", 
        "bot": "matchmaking-bot",
        "bot_running": bot_running,
        "uptime_seconds": uptime
    })

@app.route('/bot-status')
def bot_status():
    """Detailed bot status for debugging"""
    # Import here to avoid circular imports
    try:
        from db.init_db import initialize_db
        import asyncio
        
        # Check database connection
        async def check_db():
            try:
                client = await initialize_db()
                if client:
                    await client.disconnect()
                    return True
                return False
            except:
                return False
        
        # Run the async check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db_connected = loop.run_until_complete(check_db())
        loop.close()
        
    except Exception as e:
        db_connected = False
    
    return jsonify({
        "bot_running": bot_running,
        "database_connected": db_connected,
        "uptime_seconds": round(time.time() - bot_start_time) if bot_start_time else None,
        "environment_vars": {
            "ROOM_ID": "Set" if os.getenv("ROOM_ID") else "Missing",
            "BOT_TOKEN": "Set" if os.getenv("BOT_TOKEN") else "Missing", 
            "MONGODB_URI": "Set" if os.getenv("MONGODB_URI") else "Missing"
        },
        "commands_should_work": bot_running and (db_connected or "fallback_available"),
        "total_logs": len(bot_logs)
    })

@app.route('/logs')
@app.route('/debug')
def get_logs():
    """Get bot logs for debugging"""
    try:
        # Get query parameters
        from flask import request
        limit = request.args.get('limit', 100, type=int)
        level_filter = request.args.get('level', None)
        
        # Limit the number of logs returned
        limit = min(limit, 1000)  # Max 1000 logs at once
        
        # Convert deque to list and get recent logs
        logs_list = list(bot_logs)
        
        # Filter by log level if specified
        if level_filter:
            level_filter = level_filter.upper()
            logs_list = [log for log in logs_list if log['level'] == level_filter]
        
        # Get the most recent logs (last N entries)
        recent_logs = logs_list[-limit:] if limit > 0 else logs_list
        
        return jsonify({
            "status": "success",
            "total_logs_available": len(bot_logs),
            "logs_returned": len(recent_logs),
            "filters": {
                "limit": limit,
                "level": level_filter
            },
            "logs": recent_logs
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "logs": []
        }), 500

@app.route('/logs/clear')
def clear_logs():
    """Clear all stored logs (use with caution)"""
    try:
        bot_logs.clear()
        return jsonify({
            "status": "success",
            "message": "All logs cleared",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/logs/live')
def live_logs():
    """Get the most recent log entries (last 10)"""
    try:
        recent_logs = list(bot_logs)[-10:] if len(bot_logs) > 0 else []
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "recent_logs": recent_logs,
            "bot_running": bot_running,
            "uptime": round(time.time() - bot_start_time) if bot_start_time else None
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "recent_logs": []
        }), 500

@app.route('/dashboard')
def dashboard():
    """Simple HTML dashboard for viewing logs and status"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Matchmaking Bot Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .status-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status-card h3 { margin-top: 0; color: #333; }
            .status-good { border-left: 4px solid #4CAF50; }
            .status-warning { border-left: 4px solid #FF9800; }
            .status-error { border-left: 4px solid #F44336; }
            .logs-section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .log-entry { padding: 10px; margin: 5px 0; border-radius: 5px; font-family: 'Courier New', monospace; font-size: 14px; }
            .log-info { background: #e3f2fd; }
            .log-warning { background: #fff3e0; }
            .log-error { background: #ffebee; }
            .log-debug { background: #f3e5f5; }
            .controls { margin: 20px 0; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; color: white; }
            .btn-primary { background: #2196F3; }
            .btn-success { background: #4CAF50; }
            .btn-warning { background: #FF9800; }
            .refresh-info { margin: 10px 0; color: #666; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💘 Matchmaking Bot Dashboard</h1>
                <p>Real-time monitoring and debugging interface</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card status-good" id="bot-status">
                    <h3>🤖 Bot Status</h3>
                    <p id="bot-running">Loading...</p>
                    <p id="bot-uptime">Loading...</p>
                </div>
                <div class="status-card status-good" id="db-status">
                    <h3>🗄️ Database</h3>
                    <p id="db-connection">Loading...</p>
                </div>
                <div class="status-card status-good" id="env-status">
                    <h3>⚙️ Environment</h3>
                    <p id="env-vars">Loading...</p>
                </div>
                <div class="status-card status-good" id="log-status">
                    <h3>📋 Logs</h3>
                    <p id="log-count">Loading...</p>
                </div>
            </div>
            
            <div class="logs-section">
                <h2>📜 Recent Logs</h2>
                <div class="controls">
                    <button class="btn btn-primary" onclick="refreshLogs()">🔄 Refresh</button>
                    <button class="btn btn-success" onclick="startAutoRefresh()">▶️ Auto Refresh</button>
                    <button class="btn btn-warning" onclick="stopAutoRefresh()">⏸️ Stop Auto</button>
                    <select id="logLevel" onchange="refreshLogs()">
                        <option value="">All Levels</option>
                        <option value="ERROR">Errors Only</option>
                        <option value="WARNING">Warnings</option>
                        <option value="INFO">Info</option>
                    </select>
                </div>
                <div class="refresh-info" id="refresh-info">Click refresh to load logs</div>
                <div id="logs-container">Loading logs...</div>
            </div>
        </div>

        <script>
            let autoRefreshInterval = null;
            
            async function fetchStatus() {
                try {
                    const response = await fetch('/bot-status');
                    const data = await response.json();
                    
                    document.getElementById('bot-running').textContent = data.bot_running ? '✅ Running' : '❌ Stopped';
                    document.getElementById('bot-uptime').textContent = data.uptime_seconds ? `⏱️ Uptime: ${Math.floor(data.uptime_seconds / 60)}m ${data.uptime_seconds % 60}s` : '⏱️ No uptime data';
                    document.getElementById('db-connection').textContent = data.database_connected ? '✅ Connected' : '❌ Disconnected';
                    
                    const envVars = data.environment_vars;
                    const envStatus = Object.values(envVars).every(v => v === 'Set') ? '✅ All Set' : '⚠️ Some Missing';
                    document.getElementById('env-vars').textContent = envStatus;
                    
                    document.getElementById('log-count').textContent = `📊 ${data.total_logs || 0} logs stored`;
                    
                    // Update card colors based on status
                    document.getElementById('bot-status').className = `status-card ${data.bot_running ? 'status-good' : 'status-error'}`;
                    document.getElementById('db-status').className = `status-card ${data.database_connected ? 'status-good' : 'status-warning'}`;
                } catch (error) {
                    console.error('Failed to fetch status:', error);
                }
            }
            
            async function refreshLogs() {
                try {
                    const level = document.getElementById('logLevel').value;
                    const url = level ? `/logs?level=${level}&limit=50` : '/logs?limit=50';
                    const response = await fetch(url);
                    const data = await response.json();
                    
                    const container = document.getElementById('logs-container');
                    container.innerHTML = '';
                    
                    if (data.logs && data.logs.length > 0) {
                        data.logs.forEach(log => {
                            const entry = document.createElement('div');
                            entry.className = `log-entry log-${log.level.toLowerCase()}`;
                            entry.innerHTML = `<strong>${log.timestamp}</strong> [${log.level}] ${log.message}`;
                            container.appendChild(entry);
                        });
                        document.getElementById('refresh-info').textContent = `Last updated: ${new Date().toLocaleTimeString()} | Showing ${data.logs.length} logs`;
                    } else {
                        container.innerHTML = '<p>No logs available</p>';
                    }
                } catch (error) {
                    document.getElementById('logs-container').innerHTML = `<p>Error loading logs: ${error.message}</p>`;
                }
            }
            
            function startAutoRefresh() {
                if (autoRefreshInterval) clearInterval(autoRefreshInterval);
                autoRefreshInterval = setInterval(() => {
                    refreshLogs();
                    fetchStatus();
                }, 5000);
                document.getElementById('refresh-info').textContent = 'Auto-refresh enabled (every 5 seconds)';
            }
            
            function stopAutoRefresh() {
                if (autoRefreshInterval) {
                    clearInterval(autoRefreshInterval);
                    autoRefreshInterval = null;
                }
                document.getElementById('refresh-info').textContent = 'Auto-refresh stopped';
            }
            
            // Initial load
            fetchStatus();
            refreshLogs();
        </script>
    </body>
    </html>
    """
    return html

@app.route('/restart', methods=['POST'])
def restart_bot():
    """Endpoint to restart the bot (protected in production)"""
    # In production, this should have authentication
    restart_bot_process()
    return jsonify({"status": "restarting"})

def run_flask():
    """Run the Flask app for development purposes"""
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8081)),
        debug=True,
        use_reloader=False  # Disable reloader when running with the bot
    )

def keep_alive():
    """Legacy method to keep the web server alive in development"""
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

def start_bot():
    """Start the Highrise bot in a separate thread"""
    global bot_running, bot_start_time
    
    # Set up logging for this function
    logger = logging.getLogger('webserver.bot')
    
    # Import here to avoid circular imports
    from main import main, Bot
    from highrise import __main__
    from highrise.__main__ import BotDefinition
    
    # Record start time for uptime tracking
    bot_start_time = time.time()
    bot_running = True
    
    logger.info("🚀 Starting Highrise bot initialization...")
    
    # Get environment variables
    room_id = os.getenv("ROOM_ID")
    bot_token = os.getenv("BOT_TOKEN")
    mongodb_uri = os.getenv("MONGODB_URI")
    
    logger.info(f"Environment check - ROOM_ID: {'✅' if room_id else '❌'}, BOT_TOKEN: {'✅' if bot_token else '❌'}, MONGODB_URI: {'✅' if mongodb_uri else '❌'}")
    
    if not room_id or not bot_token:
        logger.error("❌ Missing required environment variables!")
        bot_running = False
        return
    
    # Clean the credentials
    room_id = room_id.strip().rstrip('%') if room_id else None
    bot_token = bot_token.strip().rstrip('%') if bot_token else None
    
    logger.info(f"🎯 Starting bot for room: {room_id[:8]}...")
    
    # Run the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("🔧 Creating bot instance and definition...")
        
        # Create bot instance and definition
        bot_instance = Bot()
        definitions = [BotDefinition(bot_instance, room_id, bot_token)]
        
        logger.info("🌐 Connecting to Highrise...")
        
        # Run the main function from Highrise SDK
        loop.run_until_complete(__main__.main(definitions))
    except Exception as e:
        logger.error(f"💥 Bot crashed with error: {e}")
        logger.error(f"📋 Error details: {type(e).__name__}")
        import traceback
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
    finally:
        bot_running = False
        logger.info("🛑 Bot stopped")

def restart_bot_process():
    """Restart the bot process"""
    global bot_thread
    
    # Stop existing bot if running
    if bot_thread and bot_thread.is_alive():
        # Signal bot to stop (this depends on how your bot handles signals)
        # This is a simple implementation and might need more robust handling
        bot_thread.join(timeout=5)
    
    # Start bot in a new thread
    bot_thread = Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()

def handle_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    print("Received shutdown signal, closing...")
    # Clean up resources here if needed
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# For production with Gunicorn, the bot will be started differently
# See the if __name__ == "__main__" block in run.py

if __name__ == "__main__":
    # Start the bot in a separate thread
    restart_bot_process()
    
    # Start the Flask app in the main thread
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8081)),
        debug=False
    )