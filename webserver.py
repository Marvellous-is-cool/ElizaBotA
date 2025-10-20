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
def restart_bot_endpoint():
    """Endpoint to restart the bot (for debugging)"""
    try:
        # This is a simple restart signal - actual restart handled by BotManager
        bot_logs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "Manual restart requested via /restart endpoint",
            "module": "webserver"
        })
        
        return jsonify({
            "status": "restart_requested", 
            "message": "Bot restart has been requested. Check /bot-status for updates.",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/force-restart', methods=['POST'])
def force_restart_bot():
    """Force restart the entire service (emergency use)"""
    try:
        bot_logs.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": "WARNING",
            "message": "FORCE RESTART requested - shutting down service",
            "module": "webserver"
        })
        
        # Log the restart request
        import os
        import signal
        
        def shutdown_server():
            import time
            time.sleep(1)  # Give time for response
            os.kill(os.getpid(), signal.SIGTERM)
        
        from threading import Thread
        Thread(target=shutdown_server, daemon=True).start()
        
        return jsonify({
            "status": "force_restarting",
            "message": "Service will restart in 1 second. Render will automatically restart it.",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e)
        }), 500

@app.route('/bot-metrics')
def bot_metrics():
    """Get detailed bot metrics"""
    try:
        return jsonify({
            "bot_running": bot_running,
            "uptime_seconds": round(time.time() - bot_start_time) if bot_start_time else None,
            "total_logs": len(bot_logs),
            "error_logs": len([log for log in bot_logs if log.get('level') == 'ERROR']),
            "warning_logs": len([log for log in bot_logs if log.get('level') == 'WARNING']),
            "memory_usage": "N/A",  # Can be enhanced with psutil
            "worker_info": {
                "process_id": os.getpid(),
                "environment": os.getenv("ENVIRONMENT", "production")
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

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

class BotManager:
    """Robust bot manager with automatic restart capabilities - DISABLED BY DEFAULT to prevent multilogin"""
    
    def __init__(self, worker_id=0, auto_start=False):
        self.worker_id = worker_id
        self.bot_running = False
        self.bot_start_time = None
        self.restart_count = 0
        self.max_restarts = 20  # Increased for TaskGroup errors
        self.restart_delay = 30  # seconds
        self.should_run = auto_start  # CRITICAL: Disabled by default!
        self.bot_task = None
        
        # Multilogin prevention: Only start bot in primary worker (worker_id=0) AND if auto_start=True
        self.is_primary_worker = (worker_id == 0)
        if not self.is_primary_worker:
            self.should_run = False  # Disable bot in secondary workers
            self.log(f"🚫 Worker {worker_id}: Bot DISABLED (secondary worker)")
        elif not auto_start:
            self.should_run = False
            self.log(f"🚫 Worker {worker_id}: Bot DISABLED (auto_start=False - preventing multilogin)")
        else:
            self.log(f"🎯 Worker {worker_id}: Primary worker - Bot ENABLED")
        
    def log(self, message):
        """Log with worker ID"""
        print(f"[Worker-{self.worker_id}] {message}")
        
    async def run_bot(self):
        """Run the bot with error handling"""
        try:
            self.log("🚀 Starting bot instance...")
            
            # Use safer bot launcher
            from safe_bot import safe_bot_main
            await safe_bot_main()
            
        except Exception as e:
            self.log(f"❌ Bot crashed: {e}")
            raise
            
    async def bot_supervisor(self):
        """Supervise the bot and restart if needed"""
        while self.should_run:
            try:
                self.bot_running = True
                self.bot_start_time = time.time()
                
                # Run the bot
                await self.run_bot()
                
            except Exception as e:
                self.log(f"Bot error: {e}")
                self.bot_running = False
                
                # Special handling for specific errors
                error_msg = str(e)
                if "TaskGroup" in error_msg or "ExceptionGroup" in error_msg:
                    self.log("TaskGroup error detected - likely connection issue")
                elif "Multilogin closing connection" in error_msg:
                    self.log("🚫 Multilogin conflict detected - another bot instance running!")
                
                # Check restart limits
                if self.restart_count >= self.max_restarts:
                    self.log(f"Max restarts ({self.max_restarts}) reached. Stopping.")
                    break
                
                # Increment restart count and wait
                self.restart_count += 1
                
                # Exponential backoff for TaskGroup errors
                delay = self.restart_delay
                if "TaskGroup" in str(e):
                    delay = min(self.restart_delay * (2 ** min(self.restart_count - 1, 4)), 300)
                
                self.log(f"Restarting bot in {delay}s (attempt {self.restart_count}/{self.max_restarts})")
                
                await asyncio.sleep(delay)
                
            finally:
                self.bot_running = False
                
        self.log("Bot supervisor stopped")
        
    def start(self):
        """Start the bot manager"""
        global bot_running, bot_start_time
        
        try:
            self.log("Starting bot manager...")
            
            # Only run bot in worker 0 to avoid conflicts
            if self.worker_id == 0:
                self.log("Primary worker - starting bot")
                
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Update global status
                bot_running = True
                bot_start_time = time.time()
                
                # Run supervisor
                loop.run_until_complete(self.bot_supervisor())
                
                # Cleanup
                bot_running = False
                loop.close()
                
            else:
                self.log("Secondary worker - standing by")
                # Secondary workers can monitor and take over if needed
                while self.should_run:
                    time.sleep(60)  # Check every minute
                    
        except Exception as e:
            self.log(f"Bot manager error: {e}")
            bot_running = False
            
    def stop(self):
        """Stop the bot manager"""
        self.should_run = False
        self.log("Bot manager stop requested")

def start_bot():
    """Legacy function for compatibility"""
    bot_manager = BotManager(worker_id=0)
    bot_manager.start()

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