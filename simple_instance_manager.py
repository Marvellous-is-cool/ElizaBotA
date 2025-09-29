"""
Simple Instance Manager - Lightweight version for production
Prevents multiple bot instances without external dependencies
"""

import os
import time
import fcntl
import atexit
import signal
from pathlib import Path

class SimpleInstanceManager:
    def __init__(self, bot_name="ElizaBot"):
        self.bot_name = bot_name
        self.lock_file = f"/tmp/{bot_name}.lock"
        self.pid_file = f"/tmp/{bot_name}.pid"
        self.lock_fd = None
        
    def acquire_lock(self):
        """Acquire exclusive lock to prevent multiple instances"""
        try:
            # Create lock file
            self.lock_fd = open(self.lock_file, 'w')
            
            # Try to acquire exclusive lock (non-blocking)
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Write our PID
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            
            # Also create a separate PID file
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
            # Register cleanup on exit
            atexit.register(self.release_lock)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            print(f"✅ Instance lock acquired for PID {os.getpid()}")
            return True
            
        except (IOError, OSError) as e:
            print(f"❌ Could not acquire lock: {e}")
            if self.lock_fd:
                self.lock_fd.close()
                self.lock_fd = None
            return False
    
    def release_lock(self):
        """Release the instance lock"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
                self.lock_fd = None
                
                # Clean up files
                if os.path.exists(self.lock_file):
                    os.unlink(self.lock_file)
                if os.path.exists(self.pid_file):
                    os.unlink(self.pid_file)
                    
                print(f"✅ Instance lock released for PID {os.getpid()}")
            except Exception as e:
                print(f"⚠️ Error releasing lock: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"📡 Received signal {signum}, releasing lock...")
        self.release_lock()
        exit(0)
    
    def check_existing_instance(self):
        """Check if another instance is already running (simplified)"""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                # Simple check if process exists
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    return pid
                except OSError:
                    # Process doesn't exist, clean up stale PID file
                    os.unlink(self.pid_file)
                    
            except (ValueError, IOError):
                pass
        
        return None
    
    def kill_existing_instances(self):
        """Kill any existing bot instances (simplified)"""
        killed_count = 0
        
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                try:
                    print(f"🔪 Killing existing instance PID {pid}")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(2)  # Give time for graceful shutdown
                    
                    # Check if still running, force kill if needed
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)
                    except OSError:
                        pass  # Process already dead
                    
                    killed_count = 1
                    
                except OSError:
                    pass  # Process already dead
                    
            except (ValueError, IOError):
                pass
        
        if killed_count > 0:
            print(f"💀 Killed {killed_count} existing instances")
            time.sleep(2)  # Give time for cleanup
        
        return killed_count

# Global instance manager
simple_instance_manager = SimpleInstanceManager()

def ensure_single_instance():
    """Ensure only one bot instance is running (simplified)"""
    print("🔍 Checking for existing instances...")
    
    existing_pid = simple_instance_manager.check_existing_instance()
    if existing_pid:
        print(f"⚠️ Found existing instance with PID {existing_pid}")
        simple_instance_manager.kill_existing_instances()
    
    # Try to acquire lock
    if not simple_instance_manager.acquire_lock():
        print("❌ Another instance is already running! Exiting...")
        exit(1)
    
    print("✅ Single instance ensured")
    return True

if __name__ == "__main__":
    # Test the simple instance manager
    ensure_single_instance()
    print("Simple instance manager test successful!")
    time.sleep(2)