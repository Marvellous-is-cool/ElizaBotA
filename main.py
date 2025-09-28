from highrise import BaseBot, __main__, CurrencyItem, Item, Position, AnchorPosition, SessionMetadata, User
from highrise.__main__ import BotDefinition
from asyncio import run as arun
import asyncio
import random
import os
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from highrise.models import *
from highrise.webapi import *
from functions.equip import equip
from functions.remove import remove
from functions.emote_system import (
    emote, fight, hug, flirt, emotes, allemo, emo, single_emote
)
from config import MATCH_PROMPT_INTERVAL, BOT_NAME, MATCH_PROMPTS
from dotenv import load_dotenv
from db.init_db import initialize_db
from services.matchmaking import MatchmakingService

# Configure logging (disabled)
logging.basicConfig(
    level=logging.CRITICAL,  # Only critical errors will be logged
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.disabled = True  # Disable this logger completely

# Load environment variables
load_dotenv()

class Bot(BaseBot):
    def __init__(self):
        super().__init__()
        self.bot_id = None
        self.owner_id = None
        self.bot_status = False
        self.match_prompt_interval = MATCH_PROMPT_INTERVAL * 60  # Convert to minutes to seconds
        self.match_prompt_task = None
        self.bot_position = None
        self.db_client = None
        self.matchmaking = None
        
        # Match Show registration data
        self.registration_sessions = {}  # Store ongoing registration sessions
        self.event_date = None  # Store the event date
        self.hosts = []  # List of host user IDs
        self.vips = []  # List of VIP user IDs
        self.subscribers = []  # List of users to remind when show starts
        
    async def initialize_services(self):
        """Initialize database and services with retry logic"""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"🔗 Initializing database connection (attempt {attempt + 1}/{max_retries})...")
                
                # Initialize database
                self.db_client = await initialize_db()
                
                if self.db_client and self.db_client.is_connected:
                    print("✅ Database connected successfully")
                    
                    # Initialize matchmaking service
                    self.matchmaking = MatchmakingService(self.db_client)
                    
                    # Load hosts, VIPs, event date and subscribers from MongoDB
                    await self.load_match_show_data()
                    
                    # Load bot position from MongoDB
                    await self.load_bot_data()
                    
                    return True
                    
            except Exception as e:
                print(f"❌ Database initialization error (attempt {attempt + 1}): {e}")
                
            if attempt < max_retries - 1:
                print(f"Retrying database connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        print("⚠️ Database connection failed after all retries, using fallback mode")
        
        try:
            # Set default position on error
            await self.load_bot_data()
        except:
            pass  # Fallback to hardcoded defaults
            
        return False
            
    async def load_match_show_data(self):
        """Load Match Show data from MongoDB"""
        try:
            if self.db_client and self.db_client.is_connected:
                # Load hosts
                hosts_data = await self.db_client.bot_data.find_one({"data_type": "hosts"})
                if hosts_data:
                    self.hosts = hosts_data.get("user_ids", [])
                    
                # Load VIPs
                vips_data = await self.db_client.bot_data.find_one({"data_type": "vips"})
                if vips_data:
                    self.vips = vips_data.get("user_ids", [])
                    
                # Load event date
                event_data = await self.db_client.bot_data.find_one({"data_type": "event"})
                if event_data:
                    self.event_date = event_data.get("date")
                    
                # Load subscribers
                subscribers_data = await self.db_client.bot_data.find_one({"data_type": "subscribers"})
                if subscribers_data:
                    self.subscribers = subscribers_data.get("user_ids", [])
                    
                if self.event_date:
                    pass
                    
        except Exception as e:
            pass
    
    async def load_bot_data(self):
        """Load bot position data from MongoDB only"""
        self.bot_position = Position(0, 0, 0, "FrontRight")  # Default position
        
        if self.db_client and self.db_client.is_connected:
            try:
                position_data = await self.db_client.get_bot_position()
                if position_data:
                    self.bot_position = Position(
                        position_data["x"], 
                        position_data["y"], 
                        position_data["z"], 
                        position_data["facing"]
                    )
                    logger.info(f"Loaded bot position from MongoDB: {position_data}")
                else:
                    logger.info("No bot position found in MongoDB, using default position")
            except Exception as e:
                logger.warning(f"Failed to load bot position from MongoDB: {str(e)}")
        else:
            logger.warning("MongoDB not connected, using default bot position")
    
    async def get_username_from_id(self, user_id: str) -> str:
        """Get a username from a user ID using multiple methods for reliability
        
        Args:
            user_id: The user ID to lookup
            
        Returns:
            str: The username if found, or "Unknown" if not found
        """
        # Try getting users in room first (this is the most reliable method)
        try:
            response = await self.highrise.get_room_users()
            # Check if response has content attribute (GetRoomUsersResponse)
            if hasattr(response, 'content'):
                room_users = response.content
                for room_user, _ in room_users:
                    if room_user.id == user_id:
                        return room_user.username
        except Exception as e:
            pass
        
        # Try getting from WebAPI if available (but this requires implementing WebAPI client)
        # This would be better to implement but requires more setup
        
        # Finally check database if available
        if self.db_client and self.db_client.is_connected:
            try:
                user_data = await self.db_client.users.find_one({"user_id": user_id})
                if user_data and "username" in user_data:
                    return user_data["username"]
            except Exception as e:
                pass
        
        return "Unknown"

    async def set_bot_position(self, user_id):
        """Set the bot position at player's location"""
        try:
            response = await self.highrise.get_room_users()
            if hasattr(response, 'content'):
                room_users = response.content
                position = None
                
                for room_user, pos in room_users:
                    if user_id == room_user.id and isinstance(pos, Position):
                        position = pos
                        break
                
                if position:
                    # Save position data
                    position_data = {
                        "x": position.x,
                        "y": position.y,
                        "z": position.z,
                        "facing": position.facing
                    }
                    
                    logger.info(f"💾 Saving bot position: x={position.x}, y={position.y}, z={position.z}")
                    
                    # Save to MongoDB 
                    position_saved = False
                    if self.db_client and self.db_client.is_connected:
                        try:
                            await self.db_client.save_bot_position(position_data)
                            position_saved = True
                            logger.info("✅ Bot position saved to MongoDB")
                        except Exception as db_error:
                            logger.error(f"❌ Failed to save position to MongoDB: {db_error}")
                    
                    # Update bot position in memory
                    self.bot_position = position
                    
                    # Move bot to the position
                    try:
                        set_position = Position(position.x, position.y + 0.0000001, position.z, facing=position.facing)
                        await self.highrise.teleport(self.bot_id, set_position)
                        await self.highrise.teleport(self.bot_id, position)
                        await self.highrise.walk_to(position)
                        logger.info("🚶 Bot moved to new position")
                    except Exception as move_error:
                        logger.error(f"❌ Failed to move bot: {move_error}")
                    
                    if position_saved:
                        return "Bot position updated and saved! 📍"
                    else:
                        return "Bot position updated (not saved - database unavailable) 📍"
                else:
                    return "Failed to get your position! 🤔"
        except Exception as e:
            return f"Error setting position: {e}"

    async def place_bot(self):
        """Place bot at saved position"""
        while not self.bot_status:
            await asyncio.sleep(0.5)
        
        try:
            if self.bot_position and self.bot_position != Position(0, 0, 0, 'FrontRight'):
                await self.highrise.teleport(self.bot_id, self.bot_position)
        except Exception as e:
            pass

    async def fix_registration_data(self, dump_all=False):
        """Inspect and fix registration data in the database"""
        if not self.db_client or not self.db_client.is_connected:
            logger.warning("Cannot fix registration data - database not connected")
            return
            
        try:
            # Get all registrations
            all_registrations = await self.db_client.registrations.find({}).to_list(length=100)
            
            if dump_all:
                # Dump all registrations for debugging
                pass
            
            for reg in all_registrations:
                # Check if the registration has type in the correct place
                needs_update = False
                update_data = {}
                
                # Make sure type is at the root level
                if "type" not in reg:
                    if "data" in reg and "registration_type" in reg["data"]:
                        update_data["type"] = reg["data"]["registration_type"]
                        needs_update = True
                    elif "registration_type" in reg:
                        update_data["type"] = reg["registration_type"]
                        needs_update = True
                
                # Make sure registration_type is at the root level
                if "registration_type" not in reg:
                    if "data" in reg and "registration_type" in reg["data"]:
                        update_data["registration_type"] = reg["data"]["registration_type"]
                        needs_update = True
                    elif "type" in reg:
                        update_data["registration_type"] = reg["type"]
                        needs_update = True
                
                # Ensure both type and registration_type have valid values (POP or LOVE)
                if "type" in reg and reg["type"] not in ["POP", "LOVE"]:
                    if "registration_type" in reg and reg["registration_type"] in ["POP", "LOVE"]:
                        update_data["type"] = reg["registration_type"]
                        needs_update = True
                
                if "registration_type" in reg and reg["registration_type"] not in ["POP", "LOVE"]:
                    if "type" in reg and reg["type"] in ["POP", "LOVE"]:
                        update_data["registration_type"] = reg["type"]
                        needs_update = True
                
                # Update the document if needed
                if needs_update and update_data:
                    await self.db_client.registrations.update_one(
                        {"_id": reg["_id"]},
                        {"$set": update_data}
                    )
            
            # After fixing, dump all registrations for verification
            if dump_all:
                fixed_registrations = await self.db_client.registrations.find({}).to_list(length=100)
            
            # Return the total count and counts by type for verification
            total = await self.db_client.registrations.count_documents({})
            pop_count = await self.db_client.registrations.count_documents({"type": "POP"})
            love_count = await self.db_client.registrations.count_documents({"type": "LOVE"})
            
            logger.info(f"Final counts - Total: {total}, POP: {pop_count}, LOVE: {love_count}")
            return total, pop_count, love_count
        except Exception as e:
            return None

    async def on_start(self, session_metadata: SessionMetadata) -> None:
        self.bot_id = session_metadata.user_id
        self.owner_id = session_metadata.room_info.owner_id
        self.bot_status = True
        
        logger.info(f"🎯 Bot connected to room! Bot ID: {self.bot_id}, Owner ID: {self.owner_id}")
        
        # Initialize services (MongoDB and Matchmaking)
        logger.info("🔧 Initializing services (MongoDB and Matchmaking)...")
        services_initialized = await self.initialize_services()
        
        if services_initialized:
            logger.info("✅ Services initialized successfully")
        else:
            logger.warning("⚠️ Services initialization failed - running with limited functionality")
        
        # Load bot position
        logger.info("📍 Loading bot position data...")
        await self.load_bot_data()
        
        # Place bot at saved position
        logger.info("🚶 Placing bot at saved position...")
        await self.place_bot()
        
        # Fix registration data structure if needed
        if services_initialized:
            logger.info("🔧 Fixing registration data structure...")
            await self.fix_registration_data()
        
        # Start the match prompt task
        logger.info("⏰ Starting match prompt task...")
        await self.start_match_prompt_task()
        
        # Welcome message
        logger.info("📢 Sending welcome message to room...")
        await self.highrise.chat(f"💘 {BOT_NAME} Matchmaking Bot activated! 💘 Find your perfect match here")
        
        logger.info("🎉 Bot startup sequence completed successfully!")

    async def start_match_prompt_task(self):
        """Start the periodic match prompt task"""
        if self.match_prompt_task:
            self.match_prompt_task.cancel()
        
        self.match_prompt_task = asyncio.create_task(self.send_match_prompts_periodically())
        
        # Also start health monitoring
        self.health_task = asyncio.create_task(self.health_monitor_loop())

    async def send_match_prompts_periodically(self):
        """Send matchmaking prompts periodically"""
        while True:
            try:
                await asyncio.sleep(self.match_prompt_interval)
                
                # Send a random matchmaking prompt
                if self.matchmaking:
                    prompt = await self.matchmaking.get_random_match_prompt()
                else:
                    prompt = random.choice(MATCH_PROMPTS)
                    
                await self.highrise.chat(prompt)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(self.match_prompt_interval)

    async def health_monitor_loop(self):
        """Monitor bot health and database connectivity"""
        check_interval = 300  # 5 minutes
        
        while True:
            try:
                await asyncio.sleep(check_interval)
                
                # Check database connection
                if self.db_client:
                    try:
                        # Simple ping to check if connection is alive
                        await self.db_client.admin.command('ping')
                        print(f"💊 Health check passed at {datetime.now()}")
                    except Exception as e:
                        print(f"⚠️ Database health check failed: {e}")
                        # Try to reconnect
                        print("🔄 Attempting to reconnect to database...")
                        services_ok = await self.initialize_services()
                        if services_ok:
                            print("✅ Database reconnected successfully")
                        else:
                            print("❌ Database reconnection failed")
                
            except asyncio.CancelledError:
                print("💊 Health monitor stopped")
                break
            except Exception as e:
                print(f"❌ Health monitor error: {e}")
                await asyncio.sleep(60)  # Short delay before retrying

    async def find_user_registration(self, search_term):
        """Find a user's registration by username or user_id
        
        Args:
            search_term (str): Username or user ID to search for
            
        Returns:
            dict: Registration data or None if not found
        """
        if not self.db_client or not self.db_client.is_connected:
            return None
            
        try:
            # Try to find by username or user_id
            registration = await self.db_client.registrations.find_one({
                "$or": [
                    {"username": {"$regex": f"^{search_term}$", "$options": "i"}},  # Exact match
                    {"data.username": {"$regex": f"^{search_term}$", "$options": "i"}},  # Exact match
                    {"user_id": search_term}
                ]
            })
            
            # If not found by exact match, try partial match on username
            if not registration:
                registration = await self.db_client.registrations.find_one({
                    "$or": [
                        {"username": {"$regex": search_term, "$options": "i"}},  # Partial match
                        {"data.username": {"$regex": search_term, "$options": "i"}}  # Partial match
                    ]
                })
                
            return registration
        except Exception as e:
            return None
    
    async def format_registration_details(self, registration):
        """Format registration details in a consistent way"""
        try:
            # Extract data from either root level or nested data object
            data = registration.get("data", {}) if registration.get("data") else registration
            
            # Get core fields with fallbacks
            username = registration.get("username", "Unknown")
            name = data.get("name", registration.get("name", "Unknown"))
            age = data.get("age", registration.get("age", "?"))
            gender = data.get("gender", registration.get("gender", "Not specified"))
            country = data.get("country", registration.get("country", "Unknown"))
            continent = data.get("continent", registration.get("continent", "Unknown"))
            occupation = data.get("occupation", registration.get("occupation", "Unknown"))
            type_pref = data.get("type_preference", registration.get("type_preference", "Not specified"))
            
            # Format the details nicely
            details = f"@{username} ({name}, {age}, {gender})\n"
            details += f"   📍 {country}, {continent}\n"
            details += f"   💼 {occupation}\n"
            details += f"   👀 Looking for: {type_pref}"
            
            return details
        except Exception as e:
            return "Error retrieving details"
    
    async def on_user_join(self, user: User, position: Position | AnchorPosition) -> None:
        """Welcome users when they join"""
        logger.info(f"👋 User joined: @{user.username} (ID: {user.id})")
        
        try:
            await self.highrise.react("wave", user.id)
            await self.highrise.chat(f"Welcome {user.username}! 👋 Sit and Relax, the Match Show is about to begin! ❤️")
            
            # Send shorter whisper to avoid message length limits
            welcome_msg = (
                "💘 Welcome to Match Show! Whisper me:\n"
                "• POP - Register to participate\n"
                "• LOVE - Looking for love\n"
                "• !SUB - Get notifications\n"
                "• help - More info"
            )
            
            await self.highrise.send_whisper(user.id, welcome_msg)
            logger.info(f"✅ Welcome message sent to @{user.username}")
            
        except Exception as e:
            logger.error(f"❌ Error welcoming @{user.username}: {e}")
            # Don't crash if welcome fails - just log it
        
        # Save user to database if connected
        try:
            if self.db_client and self.db_client.is_connected:
                await self.db_client.save_user(user.id, user.username)
                logger.info(f"💾 Saved user @{user.username} to database")
        except Exception as e:
            logger.error(f"❌ Database save failed for @{user.username}: {e}")

    async def on_user_leave(self, user: User) -> None:
        """Say goodbye when users leave"""
        await self.highrise.chat(f"Goodbye {user.username}! � Hope you find your perfect match next time! 💖")

    async def on_whisper(self, user: User, message: str) -> None:
        """Handle whisper messages from users"""
        logger.info(f"👥 Whisper received: '{message}' from @{user.username} (ID: {user.id})")
        
        try:
            response = await self.command_handler(user.id, message)
            if response:
                try:
                    await self.highrise.send_whisper(user.id, response)
                    logger.info(f"✅ Whisper response sent to @{user.username}")
                except Exception as e:
                    await self.highrise.chat(f"Whisper Error: {e}")
                    logger.error(f"❌ Failed to send whisper to @{user.username}: {e}")
            else:
                logger.info(f"ℹ️ No response generated for whisper from @{user.username}")
        except Exception as e:
            logger.error(f"❌ Error processing whisper from @{user.username}: {e}")
    
    async def on_message(self, user_id: str, conversation_id: str, is_new_conversation: bool) -> None:
        """Handle direct messages to the bot via conversations"""
        response = await self.highrise.get_messages(conversation_id)
        message = ""  # Initialize message with a default value
        if hasattr(response, 'messages'):
            message = response.messages[0].content
            
        # Get user for permission checks
        user = None
        try:
            room_users_resp = await self.highrise.get_room_users()
            if hasattr(room_users_resp, 'content'):
                user_tuple = next((u for u in room_users_resp.content if u[0].id == user_id), None)
                if user_tuple:
                    user = user_tuple[0]
                
            # Process the DM based on message content
            await self.process_direct_message(user, user_id, conversation_id, message)
                
        except Exception as e:
            await self.highrise.send_message(
                conversation_id,
                f"Sorry, I couldn't process your message. Error: {str(e)}"
            )
    
    async def command_handler(self, user_id: str, message: str) -> Optional[str]:
        """Process commands and registration via whispers"""
        try:
            # Get username from users in room
            # Get username using the utility method
            username = await self.get_username_from_id(user_id)
            
            if username == "Unknown":
                return "Sorry, I couldn't identify you. Please try again later."
            
            # Check if user is in registration process
            if user_id in self.registration_sessions:
                # Process registration step (no conversation_id in whispers)
                await self.process_registration_step(user_id, username, message)
                return None
        except Exception as e:
            logger.error(f"Error in command_handler: {e}")
            return f"Error processing command: {str(e)}"
            
        # Check for registration commands
        message_upper = message.upper().strip()
        
        if message_upper == "POP":
            # Start registration process for POP
            self.registration_sessions[user_id] = {
                "type": "POP",
                "step": "name",
                "data": {
                    "username": username,
                    "user_id": user_id,
                    "registration_time": datetime.now()
                }
            }
            # Log the username for debugging
            logger.info(f"Starting POP registration for user: {username} (ID: {user_id})")
            return "Thank you for your interest. To register you as a candidate at our MATCH SHOW kindly fill the following details:\n\n1) Name: "
            
        elif message_upper == "LOVE":
            # Start registration process for LOVE
            self.registration_sessions[user_id] = {
                "type": "LOVE",
                "step": "name",
                "data": {
                    "username": username,
                    "user_id": user_id,
                    "registration_time": datetime.now()
                }
            }
            # Log the username for debugging
            logger.info(f"Starting LOVE registration for user: {username} (ID: {user_id})")
            return "Oh, you are here to find a love! Sure! we will connect you! Kindly fill the following details to check you in!\n\n1) Name: "
        
        elif message_upper == "!SUB" or message_upper == "SUB":
            # Add user to subscribers list
            if user_id not in self.subscribers:
                self.subscribers.append(user_id)
                # Save to database
                if self.db_client and self.db_client.is_connected:
                    await self.db_client.bot_data.update_one(
                        {"data_type": "subscribers"},
                        {"$set": {"user_ids": self.subscribers}},
                        upsert=True
                    )
                return "You've been added to the notification list! You'll receive a reminder when the Match Show starts."
            else:
                return "You're already on the notification list!"
        
        elif message_upper == "!UNSUB" or message_upper == "UNSUB":
            # Remove user from subscribers list
            if user_id in self.subscribers:
                self.subscribers.remove(user_id)
                # Save to database
                if self.db_client and self.db_client.is_connected:
                    await self.db_client.bot_data.update_one(
                        {"data_type": "subscribers"},
                        {"$set": {"user_ids": self.subscribers}},
                        upsert=True
                    )
                return "You've been removed from the notification list. You will no longer receive Match Show reminders."
            else:
                return "You are not currently subscribed to notifications."
                
        elif message_upper == "!WHEN" or message_upper == "WHEN":
            # Check when the next Match Show is scheduled
            if self.event_date:
                try:
                    # Parse the date to calculate time remaining
                    event_datetime = datetime.strptime(self.event_date, "%Y-%m-%d %H:%M")
                    now = datetime.now()
                    
                    if event_datetime > now:
                        # Calculate time difference
                        time_diff = event_datetime - now
                        days = time_diff.days
                        hours, remainder = divmod(time_diff.seconds, 3600)
                        minutes = remainder // 60
                        
                        # Format the countdown message
                        countdown = f"{days} days, {hours} hours, and {minutes} minutes" if days > 0 else f"{hours} hours and {minutes} minutes"
                        
                        return f"📅 The next Match Show is scheduled for:\n{self.event_date}\n\n⏰ That's in {countdown}!"
                    else:
                        return f"📅 The Match Show was scheduled for {self.event_date}, which has already passed.\nCheck with the hosts for the next event!"
                except ValueError:
                    # Invalid date format stored
                    return f"📅 The next Match Show is scheduled for: {self.event_date}"
            else:
                return "No Match Show is currently scheduled. Check back later or subscribe with '!SUB' to be notified!"
                
        elif message_upper.startswith("!USER"):
            # Check if user is owner or host
            is_privileged = user_id == self.owner_id or user_id in self.hosts
            
            if is_privileged:
                parts = message.split(None, 1)
                if len(parts) < 2 or not parts[1].strip():
                    return "Usage: !user <username or user_id>\n\nProvide a username or user ID to look up their profile."
                
                search_term = parts[1].strip()
                
                if self.db_client and self.db_client.is_connected:
                    try:
                        # Use the utility method to find the registration
                        registration = await self.find_user_registration(search_term)
                        
                        if registration:
                            # Format the registration details
                            details = await self.format_registration_details(registration)
                            registration_type = registration.get("type", registration.get("registration_type", "Unknown"))
                            reg_user_id = registration.get("user_id", "Unknown")
                            
                            # Format the full profile information
                            profile_info = f"👤 **User Profile**\n\n{details}\n\n📊 Type: {registration_type}\n🆔 User ID: {reg_user_id}"
                            
                            # Add registration date if available
                            if "registration_time" in registration:
                                reg_time = registration["registration_time"]
                                profile_info += f"\n📅 Registered: {reg_time.strftime('%Y-%m-%d %H:%M')}"
                            
                            return profile_info
                        else:
                            return f"❌ No user profile found with username or ID matching '{search_term}'."
                    except Exception as e:
                        logger.error(f"Error looking up user profile: {e}")
                        return f"❌ Error retrieving user profile: {str(e)}"
                else:
                    return "❌ Database not connected. Cannot look up user profiles."
            else:
                return "❌ Only the room owner and hosts can look up user profiles."
        
        # If none of the above, send help message
        return ("Welcome to the Match Show! Here's how to interact with me:\n\n"
            "• Send 'POP' to register as a participant\n"
            "• Send 'LOVE' to register as someone looking for love\n"
            "• Send '!SUB' to get notified when the show starts\n"
            "• Send '!UNSUB' to stop receiving notifications\n"
            "• Send '!WHEN' to check when the next Match Show is scheduled")
    
    async def process_direct_message(self, user, user_id: str, conversation_id: str, message: str):
        """Process direct messages sent to the bot"""
        # Get a reliable username using the utility method
        username = await self.get_username_from_id(user_id)
        
        # If we have a user object and no username was found, use that as fallback
        if username == "Unknown" and user and hasattr(user, 'username'):
            username = user.username
            logger.info(f"Using passed user object username: {username}")
        
        # Check if user is in registration process first
        if user_id in self.registration_sessions:
            # Log the username being used
            logger.info(f"Processing registration step for DM user: {username} (ID: {user_id})")
            # Process registration step with conversation_id
            await self.process_registration_step(user_id, username, message, conversation_id)
            return
            
        message_lower = message.lower().strip()
        
        # Handle commands based on message content
        if message_lower == "!equip help" or message_lower == "equip":
            if user_id == self.owner_id:
                await self.highrise.send_message(
                    conversation_id, f"Equip Help 🆘: Use !equip [item name] to equip an item.")
            else:
                await self.highrise.send_message(
                    conversation_id, f"Sorry, you don't have access to this command")
        
        elif message_lower.startswith("help"):
            is_privileged = user_id == self.owner_id or user_id in self.hosts
            
            if is_privileged:
                # Create owner-only commands section if this is the owner
                owner_commands = ""
                if user_id == self.owner_id:
                    owner_commands = "\n\n💎 OWNER COMMANDS 💎\n" + \
                    "• '!eraze' - Delete ALL registration records (requires confirmation)\n"
                
                await self.highrise.send_message(
                    conversation_id,
                    "💘 Match Show Bot Commands (ADMIN) 💘\n\n" +
                    "• 'POP' - To register as a participant\n" +
                    "• 'LOVE' - To register as someone looking for love\n" +
                    "• '!SUB' - To get notified when the show starts\n" +
                    "• '!UNSUB' - To stop receiving notifications\n" +
                    "• '!list' or '!check' - Count all registrations\n" +
                    "• '!list POP' - Show detailed 'POP' registrations\n" +
                    "• '!list LOVE' - Show detailed 'LOVE' registrations\n" +
                    "• '!list POP nigeria' - Filter by type & location\n" +
                    "• '!user <username>' - Look up a specific user's profile\n" +
                    "• '!rem <username>' - Remove a participant\n" +
                    "• '!notify <message>' - Send message to subscribers\n" +
                    "• '!event YYYY-MM-DD HH:MM' - Set Match Show date" +
                    owner_commands + "\n\n" +
                    "To use these commands, send them to me in whispers or in the room chat."
                )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "Welcome to the Match Show Bot! Here are the available commands:\n\n" +
                    "• 'POP' - To register as a participant\n" +
                    "• 'LOVE' - To register as someone looking for love\n" +
                    "• '!SUB' - To get notified when the show starts\n" +
                    "• '!UNSUB' - To stop receiving notifications\n" +
                    "• '!WHEN' - Check when the next Match Show is scheduled\n\n" +
                    "To use these commands, send them to me in whispers or in the room chat."
                )
        
        elif message_lower == "pop":
            # Start registration process for POP
            # Username should be properly set by now from our improved process_direct_message method
            self.registration_sessions[user_id] = {
                "type": "POP",
                "step": "name",
                "data": {
                    "username": username,
                    "user_id": user_id,
                    "registration_time": datetime.now()
                },
                "username": username  # Store at root level too
            }
            
            # Log the username for debugging
            logger.info(f"Starting POP registration for user (DM): {username} (ID: {user_id})")
            # Log the username for debugging
            logger.info(f"Starting POP registration for user (DM): {username} (ID: {user_id})")
            await self.highrise.send_message(conversation_id, 
                "Thank you for your interest. To register you as a candidate at our MATCH SHOW kindly fill the following details:\n\n"
                "1) Name: ")
            return
        
        elif message_lower == "love":
            # Start registration process for LOVE
            # Username should be properly set by now from our improved process_direct_message method
            self.registration_sessions[user_id] = {
                "type": "LOVE",
                "step": "name",
                "data": {
                    "username": username,
                    "user_id": user_id,
                    "registration_time": datetime.now()
                },
                "username": username  # Store at root level too
            }
            # Log the username for debugging
            logger.info(f"Starting LOVE registration for user (DM): {username} (ID: {user_id})")
            await self.highrise.send_message(conversation_id, 
                "Oh, you are here to find a love! Sure! we will connect you! Kindly fill the following details to check you in!\n\n"
                "1) Name: ")
            return
        
        elif message_lower == "!sub" or message_lower == "sub":
            # Add user to subscribers list
            if user_id not in self.subscribers:
                self.subscribers.append(user_id)
                # Save to database
                if self.db_client and self.db_client.is_connected:
                    await self.db_client.save_subscriber(user_id, user.username if user else "Unknown")
                await self.highrise.send_message(
                    conversation_id, 
                    "You've been added to the notification list! You'll receive a reminder when the Match Show starts."
                )
            else:
                await self.highrise.send_message(
                    conversation_id, 
                    "You're already on the notification list!"
                )
                
        elif message_lower == "!unsub" or message_lower == "unsub":
            # Remove user from subscribers list
            if user_id in self.subscribers:
                self.subscribers.remove(user_id)
                # Save to database
                if self.db_client and self.db_client.is_connected:
                    await self.db_client.bot_data.update_one(
                        {"data_type": "subscribers"},
                        {"$set": {"user_ids": self.subscribers}},
                        upsert=True
                    )
                await self.highrise.send_message(
                    conversation_id, 
                    "You've been removed from the notification list. You will no longer receive Match Show reminders."
                )
            else:
                await self.highrise.send_message(
                    conversation_id, 
                    "You are not currently subscribed to notifications."
                )
        
        elif message_lower.startswith("hi"):
            await self.highrise.send_message(
                conversation_id,
                "Hey, welcome to the Match Show Bot! 👋\n" +
                "To see available commands, type 'help'."
            )
            
        elif message_lower == "!when" or message_lower == "when":
            # Check when the next Match Show is scheduled
            if self.event_date:
                try:
                    # Parse the date to calculate time remaining
                    event_datetime = datetime.strptime(self.event_date, "%Y-%m-%d %H:%M")
                    now = datetime.now()
                    
                    if event_datetime > now:
                        # Calculate time difference
                        time_diff = event_datetime - now
                        days = time_diff.days
                        hours, remainder = divmod(time_diff.seconds, 3600)
                        minutes = remainder // 60
                        
                        # Format the countdown message
                        countdown = f"{days} days, {hours} hours, and {minutes} minutes" if days > 0 else f"{hours} hours and {minutes} minutes"
                        
                        await self.highrise.send_message(
                            conversation_id,
                            f"📅 The next Match Show is scheduled for:\n{self.event_date}\n\n⏰ That's in {countdown}!"
                        )
                    else:
                        await self.highrise.send_message(
                            conversation_id,
                            f"📅 The Match Show was scheduled for {self.event_date}, which has already passed.\nCheck with the hosts for the next event!"
                        )
                except ValueError:
                    # Invalid date format stored
                    await self.highrise.send_message(
                        conversation_id,
                        f"📅 The next Match Show is scheduled for: {self.event_date}"
                    )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "No Match Show is currently scheduled. Check back later or subscribe with '!SUB' to be notified!"
                )
                
        
        # Notify subscribers (owner/host only)
        elif message_lower == "!eraze":
            # Only the owner can erase all records
            if user_id == self.owner_id:
                try:
                    if self.db_client and self.db_client.is_connected:
                        # Confirm the action
                        await self.highrise.send_message(
                            conversation_id,
                            "⚠️ WARNING: This will erase ALL registration records and cannot be undone! Are you sure?\n\nSend '!confirm-eraze' to proceed."
                        )
                    else:
                        await self.highrise.send_message(
                            conversation_id,
                            "❌ Database not connected. Cannot erase records."
                        )
                except Exception as e:
                    logger.error(f"Error in eraze command: {e}")
                    await self.highrise.send_message(
                        conversation_id,
                        f"❌ Error: {str(e)}"
                    )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "❌ Only the room owner can perform this action."
                )
                
        elif message_lower == "!confirm-eraze":
            # Confirmation to erase all records - owner only
            if user_id == self.owner_id:
                try:
                    if self.db_client and self.db_client.is_connected:
                        # Delete all registration records
                        delete_result = await self.db_client.registrations.delete_many({})
                        
                        # Log the deletion
                        deleted_count = delete_result.deleted_count
                        logger.info(f"Erased {deleted_count} registration records by owner command")
                        
                        await self.highrise.send_message(
                            conversation_id,
                            f"✅ Successfully erased {deleted_count} registration records from the database."
                        )
                    else:
                        await self.highrise.send_message(
                            conversation_id,
                            "❌ Database not connected. Cannot erase records."
                        )
                except Exception as e:
                    logger.error(f"Error in confirm-eraze command: {e}")
                    await self.highrise.send_message(
                        conversation_id,
                        f"❌ Error: {str(e)}"
                    )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "❌ Only the room owner can perform this action."
                )
        
        elif message_lower.startswith("!event"):
            # Set event date (owner/host only)
            is_privileged = user_id == self.owner_id or user_id in self.hosts
            
            if is_privileged:
                # Extract the date
                parts = message.split(" ", 1)
                if len(parts) < 2 or not parts[1].strip():
                    # If no date provided, show the current event date
                    if self.event_date:
                        await self.highrise.send_message(
                            conversation_id,
                            f"📅 Current Match Show date is set to: {self.event_date}\n\nUse '!event YYYY-MM-DD HH:MM' to set a new date."
                        )
                    else:
                        await self.highrise.send_message(
                            conversation_id,
                            "No event date is currently set.\n\nUse '!event YYYY-MM-DD HH:MM' to set a date."
                        )
                    return
                
                # Try to parse the date
                date_str = parts[1].strip()
                try:
                    # Parse the date string
                    event_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                    
                    # Save to database
                    if self.db_client and self.db_client.is_connected:
                        await self.db_client.bot_data.update_one(
                            {"data_type": "event"},
                            {"$set": {"date": date_str}},
                            upsert=True
                        )
                    
                    # Update in memory
                    self.event_date = date_str
                    
                    # Confirm to user
                    await self.highrise.send_message(
                        conversation_id,
                        f"✅ Match Show date has been set to: {date_str}"
                    )
                    
                    logger.info(f"Event date set to {date_str} by {username} (ID: {user_id})")
                except ValueError:
                    # Invalid date format
                    await self.highrise.send_message(
                        conversation_id,
                        "❌ Invalid date format. Please use: YYYY-MM-DD HH:MM\nFor example: 2025-10-15 20:00"
                    )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "❌ Only the room owner and hosts can set the event date."
                )
                
        elif message_lower.startswith("!notify"):
            is_privileged = user_id == self.owner_id or user_id in self.hosts
            
            if is_privileged:
                # Extract the message
                parts = message.split(" ", 1)
                if len(parts) < 2 or not parts[1].strip():
                    await self.highrise.send_message(
                        conversation_id,
                        "Usage: !notify <message>"
                    )
                    return
                    
                notification_msg = parts[1].strip()
                
                # Add attribution
                sender_name = user.username if user else "Admin"
                full_message = f"📢 MATCH SHOW ANNOUNCEMENT from @{sender_name}:\n{notification_msg}"
                
                # Track successful notifications
                sent_count = 0
                
                # Load subscribers from database if not in memory
                if not self.subscribers and self.db_client and self.db_client.is_connected:
                    subscribers_data = await self.db_client.bot_data.find_one({"data_type": "subscribers"})
                    if subscribers_data:
                        self.subscribers = subscribers_data.get("user_ids", [])
                
                # Send to all subscribers
                for subscriber_id in self.subscribers:
                    try:
                        await self.highrise.send_whisper(subscriber_id, full_message)
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send notification to {subscriber_id}: {e}")
                
                # Confirm notification was sent
                await self.highrise.send_message(
                    conversation_id,
                    f"✅ Notification sent to {sent_count} subscribers!"
                )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "Only the room owner and hosts can send notifications! 🔒"
                )
            
        # List registered users (owner/host only)
        elif message_lower.startswith("!user"):
            # Check if user is owner or host
            is_privileged = user_id == self.owner_id or user_id in self.hosts
            
            if is_privileged:
                parts = message.split(None, 1)
                if len(parts) < 2 or not parts[1].strip():
                    await self.highrise.send_message(
                        conversation_id,
                        "Usage: !user <username>\n\nProvide a username to look up their profile."
                    )
                    return
                
                search_term = parts[1].strip()
                
                if self.db_client and self.db_client.is_connected:
                    try:
                        # Use the utility method to find the registration
                        registration = await self.find_user_registration(search_term)
                        
                        if registration:
                            # Format the registration details
                            details = await self.format_registration_details(registration)
                            registration_type = registration.get("type", registration.get("registration_type", "Unknown"))
                            reg_user_id = registration.get("user_id", "Unknown")
                            
                            # Format the full profile information
                            profile_info = f"👤 **User Profile**\n\n{details}\n\n📊 Type: {registration_type}\n🆔 User ID: {reg_user_id}"
                            
                            # Add registration date if available
                            if "registration_time" in registration:
                                reg_time = registration["registration_time"]
                                profile_info += f"\n📅 Registered: {reg_time.strftime('%Y-%m-%d %H:%M')}"
                            
                            await self.highrise.send_message(conversation_id, profile_info)
                        else:
                            await self.highrise.send_message(
                                conversation_id, 
                                f"❌ No user profile found with username or ID matching '{search_term}'."
                            )
                    except Exception as e:
                        logger.error(f"Error looking up user profile: {e}")
                        await self.highrise.send_message(
                            conversation_id,
                            f"❌ Error retrieving user profile: {str(e)}"
                        )
                else:
                    await self.highrise.send_message(
                        conversation_id,
                        "❌ Database not connected. Cannot look up user profiles."
                    )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "❌ Only the room owner and hosts can look up user profiles."
                )
        
        elif message_lower.startswith("!list") or message_lower.startswith("!check"):
            # Check if user is owner or host
            is_privileged = user_id == self.owner_id or user_id in self.hosts
            
            if is_privileged:
                if self.db_client and self.db_client.is_connected:
                    try:
                        parts = message.split()
                        filter_type = None
                        filter_gender = None
                        filter_location = None
                        
                        # Parse filters
                        if len(parts) >= 2:
                            filter_type = parts[1].upper()
                            if filter_type not in ["POP", "LOVE"]:
                                # Check if it's a gender filter instead
                                if parts[1].lower() in ["male", "female", "m", "f"]:
                                    filter_gender = parts[1].lower()
                                    filter_type = None
                                    if filter_gender in ["m"]:
                                        filter_gender = "male"
                                    elif filter_gender in ["f"]:
                                        filter_gender = "female"
                                else:
                                    filter_type = None
                        
                        if len(parts) >= 3:
                            # If second param is gender and third is location
                            if filter_gender and parts[2].lower() not in ["male", "female", "m", "f"]:
                                filter_location = parts[2].lower()
                            # If first param is type and second might be gender or location
                            elif filter_type:
                                if parts[2].lower() in ["male", "female", "m", "f"]:
                                    filter_gender = parts[2].lower()
                                    if filter_gender in ["m"]:
                                        filter_gender = "male"
                                    elif filter_gender in ["f"]:
                                        filter_gender = "female"
                                else:
                                    filter_location = parts[2].lower()
                                
                        if len(parts) >= 4 and filter_type and filter_gender:
                            filter_location = parts[3].lower()
                        
                        # Build query
                        query = {}
                        if filter_type:
                            # Check in all possible fields for registration type
                            query["$or"] = [
                                {"data.registration_type": filter_type},
                                {"type": filter_type},
                                {"registration_type": filter_type}
                            ]
                            
                        # Add gender filter if specified
                        if filter_gender:
                            gender_value = filter_gender.capitalize()
                            gender_query = {
                                "$or": [
                                    {"data.gender": {"$regex": gender_value, "$options": "i"}},
                                    {"gender": {"$regex": gender_value, "$options": "i"}}
                                ]
                            }
                            
                            # Combine with existing query
                            if "$or" in query:
                                query = {"$and": [query, gender_query]}
                            else:
                                query.update(gender_query)
                                
                        if filter_location:
                            location_query = {
                                "$or": [
                                    {"data.country": {"$regex": filter_location, "$options": "i"}},
                                    {"data.continent": {"$regex": filter_location, "$options": "i"}},
                                    {"country": {"$regex": filter_location, "$options": "i"}},
                                    {"continent": {"$regex": filter_location, "$options": "i"}}
                                ]
                            }
                            # Combine with existing query
                            if "$or" in query:
                                query = {"$and": [query, location_query]}
                            else:
                                query.update(location_query)
                        
                        # Log the query for debugging
                        logger.info(f"Registration query: {query}")
                        
                        # Debug collection information
                        collection_names = await self.db_client.db.list_collection_names()
                        logger.info(f"Available collections: {collection_names}")
                        
                        # Define comprehensive queries for each type, only including completed registrations
                        pop_query = {
                            "$and": [
                                {"completed": True},
                                {"$or": [
                                    {"type": "POP"}, 
                                    {"data.registration_type": "POP"},
                                    {"registration_type": "POP"}
                                ]}
                            ]
                        }
                        
                        love_query = {
                            "$and": [
                                {"completed": True},
                                {"$or": [
                                    {"type": "LOVE"}, 
                                    {"data.registration_type": "LOVE"},
                                    {"registration_type": "LOVE"}
                                ]}
                            ]
                        }
                        
                        # Get accurate counts
                        pop_count = await self.db_client.registrations.count_documents(pop_query)
                        love_count = await self.db_client.registrations.count_documents(love_query)
                        total_count = pop_count + love_count
                        
                        # Add extra debug information
                        logger.info(f"All registrations query...")
                        all_registrations = await self.db_client.registrations.find({}).to_list(length=100)
                        logger.info(f"Found {len(all_registrations)} total documents in registrations collection")
                        
                        # Specifically check for the user_id that was in the sample registration
                        sample_user_id = "6859d10382a3738b87362f82"  # This is from the log you shared
                        user_reg = await self.db_client.registrations.find_one({"user_id": sample_user_id})
                        if user_reg:
                            logger.info(f"Found registration for sample user: {sample_user_id}")
                            # Check if this registration has the completed flag
                            logger.info(f"Completed flag: {user_reg.get('completed', 'NOT SET')}")
                            logger.info(f"Registration type: {user_reg.get('type', 'NOT SET')}")
                        else:
                            logger.info(f"Did NOT find registration for sample user: {sample_user_id}")
                        
                        # Log the count results
                        logger.info(f"Registration counts: Total={total_count}, POP={pop_count}, LOVE={love_count}")
                        
                        # Format response in a more user-friendly way
                        response = "📊 Registration Summary 📊\n\n"
                        
                        # Prepare a more detailed query for filtered results
                        detailed_query = {"completed": True}  # Only include completed registrations
                        if filter_type:
                            detailed_query["$or"] = [
                                {"type": filter_type}, 
                                {"data.registration_type": filter_type},
                                {"registration_type": filter_type}
                            ]
                        
                        # Apply gender filter
                        if filter_gender:
                            gender_value = filter_gender.capitalize()
                            gender_query = {
                                "$or": [
                                    {"gender": gender_value},
                                    {"data.gender": gender_value},
                                    {"gender": {"$regex": f"^{filter_gender}", "$options": "i"}},
                                    {"data.gender": {"$regex": f"^{filter_gender}", "$options": "i"}}
                                ]
                            }
                            
                            if "$and" in detailed_query:
                                detailed_query["$and"].append(gender_query)
                            else:
                                detailed_query = {"$and": [detailed_query, gender_query]}
                        
                        # Apply location filter with more flexible regex pattern
                        if filter_location:
                            # Make the location filter more flexible with case insensitivity and partial matching
                            location_pattern = f".*{filter_location}.*"
                            location_query = {
                                "$or": [
                                    {"data.country": {"$regex": location_pattern, "$options": "i"}},
                                    {"data.continent": {"$regex": location_pattern, "$options": "i"}},
                                    {"country": {"$regex": location_pattern, "$options": "i"}},
                                    {"continent": {"$regex": location_pattern, "$options": "i"}}
                                ]
                            }
                            
                            if "$and" in detailed_query:
                                detailed_query["$and"].append(location_query)
                            else:
                                detailed_query = {"$and": [detailed_query, location_query]}
                        
                        # Show summary counts
                        if filter_type == "POP":
                            response += f"🎭 Participants: {pop_count} registered\n"
                        elif filter_type == "LOVE":
                            response += f"❤️ Love Seekers: {love_count} registered\n"
                        else:
                            # Show the complete summary with accurate counts
                            response += f"Total Registrations: {total_count}\n"
                            response += f"🎭 Participants: {pop_count}\n"
                            response += f"❤️ Love Seekers: {love_count}\n"
                        
                        # Show filter information
                        filter_info = []
                        if filter_type:
                            filter_info.append(f"Type: {filter_type}")
                        if filter_gender:
                            filter_info.append(f"Gender: {filter_gender.title()}")
                        if filter_location:
                            filter_info.append(f"Location: {filter_location.title()}")
                        
                        if filter_info:
                            response += f"\nFiltered by: {', '.join(filter_info)}"
                        
                        # Show detailed participant information if filtering
                        if filter_type or filter_gender or filter_location:
                            # Log the final query for debugging
                            logger.info(f"Detailed query: {detailed_query}")
                            
                            # Get detailed information about the participants
                            detailed_results = await self.db_client.registrations.find(detailed_query).to_list(length=20)
                            logger.info(f"Found {len(detailed_results)} registrations matching the detailed query")
                        
                            if detailed_results:
                                response += "\n\n� Detailed Participant List 👥\n"
                                for i, reg in enumerate(detailed_results, 1):
                                    response += f"\n{i}. {await self.format_registration_details(reg)}"
                                
                                # If there are many results, add a note
                                if len(detailed_results) == 20:
                                    response += "\n(Showing first 20 results. There may be more.)"
                            else:
                                response += "\n\nNo participants found matching these filters."
                        
                        # Send response in DM (might need multiple messages if very long)
                        if len(response) > 2000:
                            # Split into multiple messages if too long
                            parts = [response[i:i+2000] for i in range(0, len(response), 2000)]
                            for part in parts:
                                await self.highrise.send_message(conversation_id, part)
                        else:
                            await self.highrise.send_message(conversation_id, response)
                        
                        # Debug info for owner only when specifically requested
                        if user_id == self.owner_id and "debug" in message.lower():
                            # Add more comprehensive debug information
                            debug_info = f"Query: {detailed_query}\n\n"
                            
                            # Get one registration document to show its structure
                            sample_reg = await self.db_client.registrations.find_one({})
                            if sample_reg:
                                # Format the document in a readable way, excluding _id which isn't serializable
                                sample_reg_copy = dict(sample_reg)
                                if "_id" in sample_reg_copy:
                                    sample_reg_copy["_id"] = str(sample_reg_copy["_id"])
                                debug_info += f"Sample registration structure:\n{sample_reg_copy}"
                            else:
                                debug_info += "No registrations found in database."
                            
                            await self.highrise.send_message(
                                conversation_id,
                                f"Debug Info:\n{debug_info}"
                            )
                                
                    except Exception as e:
                        logger.error(f"Error in !list/!check command via DM: {e}")
                        await self.highrise.send_message(
                            conversation_id,
                            f"⚠️ Error checking registrations: {str(e)}"
                        )
                else:
                    await self.highrise.send_message(
                        conversation_id,
                        "⚠️ Database connection is not available!"
                    )
            else:
                await self.highrise.send_message(
                    conversation_id,
                    "Only the room owner and hosts can view registrations! 🔒"
                )
        
        else:
            await self.highrise.send_message(
                conversation_id,
                "I don't understand that command. Type 'help' to see available options."
            )
    
    async def process_registration_step(self, user_id: str, username: str, message: str, conversation_id: str = None):
        """Process a step in the registration process"""
        session = self.registration_sessions.get(user_id)
        if not session:
            return
        
        # Always try to update the username with the latest one, even if provided one is valid
        if username != "Unknown":
            session["data"]["username"] = username
            session["username"] = username
        else:
            # If we got "Unknown", try to fetch a better username
            better_username = await self.get_username_from_id(user_id)
            if better_username != "Unknown":
                session["data"]["username"] = better_username
                session["username"] = better_username
                username = better_username
        
        # Log the username being used for this step
        logger.info(f"Processing registration step for user: {username} (ID: {user_id})")
        
        current_step = session["step"]
        data = session["data"]
        
        try:
            # Process based on current step
            if current_step == "name":
                data["name"] = message.strip()
                session["step"] = "age"
                if conversation_id:
                    await self.highrise.send_message(conversation_id, "2) Age: ")
                else:
                    await self.highrise.send_whisper(user_id, "2) Age: ")
                
            elif current_step == "age":
                # Validate age is a number
                try:
                    age = int(message.strip())
                    if age < 18:
                        if conversation_id:
                            await self.highrise.send_message(conversation_id, "Sorry, you must be 18 or older to participate in our Match Show. Thank you for your interest! ❤️")
                        else:
                            await self.highrise.send_whisper(user_id, "Sorry, you must be 18 or older to participate in our Match Show. Thank you for your interest! ❤️")
                        del self.registration_sessions[user_id]
                        return
                    data["age"] = age
                    session["step"] = "gender"
                    if conversation_id:
                        await self.highrise.send_message(conversation_id, "3) Gender (Male/Female/Other): ")
                    else:
                        await self.highrise.send_whisper(user_id, "3) Gender (Male/Female/Other): ")
                except ValueError:
                    if conversation_id:
                        await self.highrise.send_message(conversation_id, "Please enter a valid age (numbers only). Try again:\n2) Age: ")
                    else:
                        await self.highrise.send_whisper(user_id, "Please enter a valid age (numbers only). Try again:\n2) Age: ")
                    return
                    
            elif current_step == "gender":
                # Normalize gender input
                gender = message.strip().lower()
                if gender in ["male", "m"]:
                    data["gender"] = "Male"
                elif gender in ["female", "f"]:
                    data["gender"] = "Female"
                else:
                    data["gender"] = message.strip().capitalize() or "Other"
                
                session["step"] = "occupation"
                if conversation_id:
                    await self.highrise.send_message(conversation_id, "4) Occupation/Student: ")
                else:
                    await self.highrise.send_whisper(user_id, "4) Occupation/Student: ")
                
            elif current_step == "occupation":
                data["occupation"] = message.strip()
                session["step"] = "country"
                if conversation_id:
                    await self.highrise.send_message(conversation_id, "5) Country: ")
                else:
                    await self.highrise.send_whisper(user_id, "5) Country: ")
                
            elif current_step == "country":
                data["country"] = message.strip()
                session["step"] = "type"
                if conversation_id:
                    await self.highrise.send_message(conversation_id, "6) Describe the ideal partner you're looking for (optional): ")
                else:
                    await self.highrise.send_whisper(user_id, "6) Describe your ideal partner (optional): ")

            elif current_step == "type":
                data["type_preference"] = message.strip() if message.strip() else "Not specified"
                session["step"] = "continent"
                if conversation_id:
                    await self.highrise.send_message(conversation_id, "7) Continent: ")
                else:
                    await self.highrise.send_whisper(user_id, "7) Continent: ")
                
            elif current_step == "continent":
                data["continent"] = message.strip()
                
                # Complete registration
                # Save to MongoDB
                if self.db_client and self.db_client.is_connected:
                    # Add registration type and timestamp
                    data["registration_type"] = session["type"]  # POP or LOVE
                    data["type"] = session["type"]  # Add type at root level for consistent querying
                    data["completed"] = True
                    data["completion_time"] = datetime.now()
                    
                    # Log registration data for debugging
                    logger.info(f"Saving registration: {data}")
                    
                    # Make sure the data includes user_id and username
                    if "user_id" not in data or not data["user_id"]:
                        data["user_id"] = user_id
                    
                    # Always use the passed username parameter as it should be the most reliable at this point
                    # Double-check that it's not "Unknown" before using it
                    if username != "Unknown":
                        data["username"] = username
                        session["username"] = username
                        
                        # This is the critical point - log exactly what we're using
                        logger.info(f"Using verified username '{username}' for user_id {user_id}")
                    else:
                        # If we still have "Unknown", try one more lookup as a last resort
                        try:
                            response = await self.highrise.get_room_users()
                            if hasattr(response, 'content'):
                                user_tuple = next((u for u in response.content if u[0].id == user_id), None)
                                if user_tuple:
                                    verified_username = user_tuple[0].username
                                    data["username"] = verified_username
                                    session["username"] = verified_username
                                    logger.info(f"Last-resort username lookup successful: {verified_username} for user_id {user_id}")
                        except Exception as e:
                            logger.error(f"Last-resort username lookup failed: {e}")
                    
                    # Log this critical data for debugging
                    logger.info(f"Final registration data before saving - user_id: {data.get('user_id')}, username: {data.get('username', 'STILL UNKNOWN!')}")
                        
                    # Save to registrations collection using the helper method
                    success = await self.db_client.save_registration(data)
                    
                    if not success:
                        logger.error(f"Failed to save registration for user {user_id}")
                        if conversation_id:
                            await self.highrise.send_message(conversation_id, "There was an issue saving your registration. Please try again later.")
                        else:
                            await self.highrise.send_whisper(user_id, "There was an issue saving your registration. Please try again later.")
                        return
                    
                    # Remove from session
                    del self.registration_sessions[user_id]
                    
                    completion_msg = ("Thank you, you have been registered. Kindly follow the hosts @coolbuoy for more info. "
                        "Send !sub so I can remind you when the show starts. "
                        "(Make sure you have a pic of you in your profile on/before the event, this is strictly important)")
                    
                    # Send completion message
                    if conversation_id:
                        await self.highrise.send_message(conversation_id, completion_msg)
                    else:
                        await self.highrise.send_whisper(user_id, completion_msg)
                else:  # No database connection
                    error_msg = "Sorry, I couldn't save your registration due to a database error. Please try again later."
                    if conversation_id:
                        await self.highrise.send_message(conversation_id, error_msg)
                    else:
                        await self.highrise.send_whisper(user_id, error_msg)
                    del self.registration_sessions[user_id]
                    
        except Exception as e:
            logger.error(f"Error processing registration step: {e}")
            error_msg = "Sorry, there was an error processing your registration. Please try again later."
            if conversation_id:
                await self.highrise.send_message(conversation_id, error_msg)
            else:
                await self.highrise.send_whisper(user_id, error_msg)
            del self.registration_sessions[user_id]

    async def on_chat(self, user: User, message: str) -> None:
        """Handle chat commands"""
        lower_msg = message.lower().strip()
        
        # Log all chat commands for debugging
        if lower_msg.startswith("!") or lower_msg in ["pop", "love", "help", "equip", "remove"]:
            logger.info(f"💬 Command received: '{message}' from @{user.username} (ID: {user.id})")
        
        try:
            # Set bot position command (only owner can use this)
            if lower_msg == "!set":
                logger.info(f"🎯 !set command from @{user.username} (Owner: {user.id == self.owner_id})")
                if user.id == self.owner_id:
                    try:
                        result = await self.set_bot_position(user.id)
                        await self.highrise.chat(result)
                        logger.info(f"✅ !set command completed: {result}")
                    except Exception as e:
                        error_msg = f"Error setting position: {str(e)[:100]}"
                        await self.highrise.chat(error_msg)
                        logger.error(f"❌ !set command failed: {e}")
                else:
                    await self.highrise.chat("Only the room owner can set my position! 🔒")
                    logger.warning(f"⚠️ !set command denied for @{user.username} (not owner)")
                return
            
            # Equip command
            if lower_msg.startswith("!equip") or lower_msg.startswith("equip"):
                await equip(self, user, message)
                return
            
            # Remove command  
            if lower_msg.startswith("!remove") or lower_msg.startswith("remove"):
                await remove(self, user, message)
                return
            
            # Unsubscribe command
            if lower_msg == "!unsub" or lower_msg == "unsub":
                if user.id in self.subscribers:
                    self.subscribers.remove(user.id)
                    # Save to database with error handling
                    try:
                        if self.db_client and self.db_client.is_connected:
                            await self.db_client.bot_data.update_one(
                                {"data_type": "subscribers"},
                                {"$set": {"user_ids": self.subscribers}},
                                upsert=True
                            )
                    except Exception as db_error:
                        print(f"Database error in !unsub: {db_error}")
                        # Continue anyway - the user was removed from memory
                    
                    await self.highrise.chat(f"@{user.username} has been removed from the notification list!")
                else:
                    await self.highrise.chat(f"@{user.username}, you were not subscribed to notifications.")
                return
            
            # Owner/Host commands
            is_privileged = user.id == self.owner_id or user.id in self.hosts
            
            # Fix registration data (owner only)
            if lower_msg == "!fixdata":
                if user.id == self.owner_id:
                    await self.highrise.chat("Fixing registration data structure... Please wait.")
                    
                    # Fix all registration data with detailed logging
                    results = await self.fix_registration_data(dump_all=True)
                    
                    if results:
                        total, pop, love = results
                        await self.highrise.chat(f"Registration data fixed! Total: {total}, POP: {pop}, LOVE: {love}")
                    else:
                        await self.highrise.chat("Error fixing registration data. Check logs for details.")
                else:
                    await self.highrise.chat("Only the owner can use this command! 🔒")
                return
            
            # Set event date (owner only)
            if lower_msg.startswith("!set event"):
                if user.id == self.owner_id:
                    parts = message.split(" ", 2)
                    if len(parts) >= 3:
                        self.event_date = parts[2].strip()
                        
                        # Save to database
                        if self.db_client and self.db_client.is_connected:
                            await self.db_client.bot_data.update_one(
                                {"data_type": "event"},
                                {"$set": {"date": self.event_date}},
                                upsert=True
                            )
                        
                        await self.highrise.chat(f"Match Show event date set to: {self.event_date}")
                    else:
                        await self.highrise.chat("Usage: !set event <date and time>")
                else:
                    await self.highrise.chat("Only the room owner can set the event date! 🔒")
                return
            
            # Add host (owner only)
            if lower_msg.startswith("!addhost"):
                if user.id == self.owner_id:
                    parts = message.split()
                    if len(parts) >= 2:
                        host_username = parts[1].strip()
                        # Get user ID from username
                        response = await self.highrise.get_room_users()
                        if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
                            room_users = response.content
                            host_id = None
                            
                            for room_user, _ in room_users:
                                if room_user.username.lower() == host_username.lower():
                                    host_id = room_user.id
                                    break
                            
                            if host_id:
                                if host_id not in self.hosts:
                                    self.hosts.append(host_id)
                                    
                                    # Save to database
                                    if self.db_client and self.db_client.is_connected:
                                        await self.db_client.bot_data.update_one(
                                            {"data_type": "hosts"},
                                            {"$set": {"user_ids": self.hosts}},
                                            upsert=True
                                        )
                                    
                                    await self.highrise.chat(f"Added @{host_username} as a host!")
                                else:
                                    await self.highrise.chat(f"@{host_username} is already a host!")
                            else:
                                await self.highrise.chat(f"Could not find user @{host_username} in the room!")
                    else:
                        await self.highrise.chat("Usage: !addhost <username>")
                else:
                    await self.highrise.chat("Only the room owner can add hosts! 🔒")
                return
            
            # Remove host (owner only)
            if lower_msg.startswith("!removehost"):
                if user.id == self.owner_id:
                    parts = message.split()
                    if len(parts) >= 2:
                        host_username = parts[1].strip()
                        # Get user ID from username
                        response = await self.highrise.get_room_users()
                        if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
                            room_users = response.content
                            host_id = None
                            
                            for room_user, _ in room_users:
                                if room_user.username.lower() == host_username.lower():
                                    host_id = room_user.id
                                    break
                            
                            if host_id and host_id in self.hosts:
                                self.hosts.remove(host_id)
                                
                                # Save to database
                                if self.db_client and self.db_client.is_connected:
                                    await self.db_client.bot_data.update_one(
                                        {"data_type": "hosts"},
                                        {"$set": {"user_ids": self.hosts}},
                                        upsert=True
                                    )
                                
                                await self.highrise.chat(f"Removed @{host_username} from hosts!")
                            else:
                                await self.highrise.chat(f"@{host_username} is not a host!")
                    else:
                        await self.highrise.chat("Usage: !removehost <username>")
                else:
                    await self.highrise.chat("Only the room owner can remove hosts! 🔒")
                return
                
            # Notify subscribers (owner/host only)
            if lower_msg.startswith("!notify"):
                if is_privileged:
                    parts = message.split(" ", 1)
                    if len(parts) > 1:
                        notification_message = parts[1]
                        sent_count = 0
                        
                        if self.subscribers and len(self.subscribers) > 0:
                            # Get subscribers from database if needed
                            if not self.subscribers and self.db_client and self.db_client.is_connected:
                                subscribers_data = await self.db_client.bot_data.find_one({"data_type": "subscribers"})
                                if subscribers_data:
                                    self.subscribers = subscribers_data.get("user_ids", [])
                            
                            # Send notification to each subscriber
                            for sub_id in self.subscribers:
                                try:
                                    await self.highrise.send_whisper(sub_id, f"📢 MATCH SHOW NOTIFICATION: {notification_message}")
                                    sent_count += 1
                                except Exception as e:
                                    logger.error(f"Error sending notification to {sub_id}: {e}")
                            
                            await self.highrise.chat(f"✅ Notification sent to {sent_count} subscribers!")
                        else:
                            await self.highrise.chat("No subscribers found in the list!")
                    else:
                        await self.highrise.chat("Usage: !notify <message>")
                else:
                    await self.highrise.chat("Only the room owner and hosts can send notifications! 🔒")
                return
            
            # Remove participant (owner/host only)
            if lower_msg.startswith("!rem"):
                if is_privileged:
                    parts = message.split(None, 1)
                    if len(parts) < 2:
                        await self.highrise.chat("Usage: !rem <username>")
                        return
                    
                    target_username = parts[1].strip()
                    
                    # Get room users to verify username
                    try:
                        room_users_response = await self.highrise.get_room_users()
                        if not isinstance(room_users_response, GetRoomUsersRequest.GetRoomUsersResponse):
                            await self.highrise.chat("⚠️ Failed to get room users")
                            return
                        
                        # Find user ID for the given username
                        target_user_id = None
                        for room_user, _ in room_users_response.content:
                            if room_user.username.lower() == target_username.lower():
                                target_user_id = room_user.id
                                target_username = room_user.username  # Use correct case
                                break
                        
                        # If not found in room, try to find in database
                        if not target_user_id and self.db_client and self.db_client.is_connected:
                            registration = await self.db_client.registrations.find_one(
                                {"username": {"$regex": f"^{re.escape(target_username)}$", "$options": "i"}}
                            )
                            if registration:
                                target_user_id = registration.get("user_id")
                                target_username = registration.get("username")
                        
                        if not target_user_id:
                            await self.highrise.chat(f"⚠️ Could not find user '{target_username}'")
                            return
                        
                        # Remove from database
                        if self.db_client and self.db_client.is_connected:
                            result = await self.db_client.registrations.delete_one({"user_id": target_user_id})
                            if result.deleted_count > 0:
                                await self.highrise.chat(f"✅ Successfully removed {target_username} from registrations!")
                                
                                # Log for debugging
                                logger.info(f"Removed registration for {target_username} ({target_user_id})")
                            else:
                                await self.highrise.chat(f"⚠️ {target_username} is not registered")
                        else:
                            await self.highrise.chat("⚠️ Database connection is not available!")
                    except Exception as e:
                        logger.error(f"Error removing participant: {e}")
                        await self.highrise.chat(f"⚠️ Error: {str(e)}")
                else:
                    await self.highrise.chat("Only the room owner and hosts can remove registrations! 🔒")
                return
                
            # List registered users (owner/host only)
            if lower_msg.startswith("!list") or lower_msg.startswith("!check"):
                if is_privileged:
                    if self.db_client and self.db_client.is_connected:
                        try:
                            parts = message.split()
                            filter_type = None
                            filter_location = None
                            
                            # Parse filters
                            filter_gender = None
                            if len(parts) >= 2:
                                filter_type = parts[1].upper()
                                if filter_type not in ["POP", "LOVE"]:
                                    # Check if it's a gender filter instead
                                    if parts[1].lower() in ["male", "female", "m", "f"]:
                                        filter_gender = parts[1].lower()
                                        filter_type = None
                                        if filter_gender in ["m"]:
                                            filter_gender = "male"
                                        elif filter_gender in ["f"]:
                                            filter_gender = "female"
                                    else:
                                        filter_type = None
                            
                            if len(parts) >= 3:
                                # If second param is gender and third is location
                                if filter_gender and parts[2].lower() not in ["male", "female", "m", "f"]:
                                    filter_location = parts[2].lower()
                                # If first param is type and second might be gender or location
                                elif filter_type:
                                    if parts[2].lower() in ["male", "female", "m", "f"]:
                                        filter_gender = parts[2].lower()
                                        if filter_gender in ["m"]:
                                            filter_gender = "male"
                                        elif filter_gender in ["f"]:
                                            filter_gender = "female"
                                    else:
                                        filter_location = parts[2].lower()
                                
                            if len(parts) >= 4 and filter_type and filter_gender:
                                filter_location = parts[3].lower()
                            
                            # Build query - only include completed registrations
                            query = {"completed": True}
                            if filter_type:
                                # Check in all possible fields for registration type
                                type_query = {
                                    "$or": [
                                        {"data.registration_type": filter_type},
                                        {"type": filter_type},
                                        {"registration_type": filter_type}
                                    ]
                                }
                                query = {"$and": [query, type_query]}
                            # Add gender filter if specified
                            if filter_gender:
                                gender_value = filter_gender.capitalize()
                                gender_query = {
                                    "$or": [
                                        {"gender": gender_value},
                                        {"data.gender": gender_value},
                                        {"gender": {"$regex": f"^{filter_gender}", "$options": "i"}},
                                        {"data.gender": {"$regex": f"^{filter_gender}", "$options": "i"}}
                                    ]
                                }
                                
                                # Combine with existing query
                                if "$and" in query:
                                    query["$and"].append(gender_query)
                                else:
                                    query = {"$and": [query, gender_query]}
                            
                            if filter_location:
                                # More flexible location matching with partial match
                                location_pattern = f".*{filter_location}.*"
                                location_query = {
                                    "$or": [
                                        {"data.country": {"$regex": location_pattern, "$options": "i"}},
                                        {"data.continent": {"$regex": location_pattern, "$options": "i"}},
                                        {"country": {"$regex": location_pattern, "$options": "i"}},
                                        {"continent": {"$regex": location_pattern, "$options": "i"}}
                                    ]
                                }
                                # Combine with existing query
                                if "$and" in query:
                                    query["$and"].append(location_query)
                                else:
                                    query = {"$and": [query, location_query]}
                            
                            # Log the query for debugging
                            logger.info(f"Registration query (on_chat): {query}")
                            
                            # Debug collection information
                            collection_names = await self.db_client.db.list_collection_names()
                            logger.info(f"Available collections: {collection_names}")
                            
                            # Add extra debug information
                            logger.info(f"All registrations query...")
                            all_registrations = await self.db_client.registrations.find({}).to_list(length=100)
                            logger.info(f"Found {len(all_registrations)} total documents in registrations collection")
                            
                            # If any documents exist, log the structure of the first one
                            if all_registrations and len(all_registrations) > 0:
                                sample = all_registrations[0]
                                sample_copy = dict(sample)
                                if "_id" in sample_copy:
                                    sample_copy["_id"] = str(sample_copy["_id"])
                                logger.info(f"Sample document structure: {sample_copy}")
                            
                            # Define comprehensive queries for each type, only including completed registrations
                            pop_query = {
                                "$and": [
                                    {"completed": True},
                                    {"$or": [
                                        {"type": "POP"}, 
                                        {"data.registration_type": "POP"},
                                        {"registration_type": "POP"}
                                    ]}
                                ]
                            }
                            
                            love_query = {
                                "$and": [
                                    {"completed": True},
                                    {"$or": [
                                        {"type": "LOVE"}, 
                                        {"data.registration_type": "LOVE"},
                                        {"registration_type": "LOVE"}
                                    ]}
                                ]
                            }
                            
                            # Get accurate counts
                            pop_count = await self.db_client.registrations.count_documents(pop_query)
                            love_count = await self.db_client.registrations.count_documents(love_query)
                            total_count = pop_count + love_count
                        
                            # Log the count results
                            logger.info(f"Registration counts: Total={total_count}, POP={pop_count}, LOVE={love_count}")
                            
                            # Check if we have an issue with the completed flag
                            all_completed = await self.db_client.registrations.count_documents({"completed": True})
                            all_without_completed = await self.db_client.registrations.count_documents({"completed": {"$exists": False}})
                            all_not_completed = await self.db_client.registrations.count_documents({"completed": False})
                            
                            logger.info(f"Registration counts by completion status: completed={all_completed}, missing_flag={all_without_completed}, not_completed={all_not_completed}")
                            
                            # Debug: See if we can find the registrations without filters
                            pop_without_completed = await self.db_client.registrations.count_documents({
                                "$or": [
                                    {"type": "POP"}, 
                                    {"data.registration_type": "POP"},
                                    {"registration_type": "POP"}
                                ]
                            })
                            logger.info(f"POP registrations without completed filter: {pop_without_completed}")
                            
                            # Get sample POP registration to examine
                            try:
                                sample_pop = await self.db_client.registrations.find_one({
                                    "$or": [
                                        {"type": "POP"}, 
                                        {"data.registration_type": "POP"},
                                        {"registration_type": "POP"}
                                    ]
                                })
                                
                                if sample_pop:
                                    # Convert ObjectId to string for logging
                                    sample_pop_dict = dict(sample_pop)
                                    if "_id" in sample_pop_dict:
                                        sample_pop_dict["_id"] = str(sample_pop_dict["_id"])
                                    
                                    # Log key fields to diagnose issues
                                    logger.info(f"Sample POP registration fields: user_id={sample_pop_dict.get('user_id', 'NOT SET')}, " +
                                               f"username={sample_pop_dict.get('username', 'NOT SET')}, " +
                                               f"type={sample_pop_dict.get('type', 'NOT SET')}, " +
                                               f"completed={sample_pop_dict.get('completed', 'NOT SET')}, " +
                                               f"registration_type={sample_pop_dict.get('registration_type', 'NOT SET')}")
                                else:
                                    logger.info("No POP registrations found at all.")
                            except Exception as e:
                                logger.error(f"Error examining registration: {e}")
                                
                            # Format response in a more user-friendly way
                            response = "📊 Registration Summary 📊\n\n"
                            
                            if filter_type == "POP":
                                response += f"🎭 Participants: {pop_count} registered\n"
                            elif filter_type == "LOVE":
                                response += f"❤️ Love Seekers: {love_count} registered\n"
                            else:
                                # Show the complete summary with accurate counts
                                response += f"Total Registrations: {total_count}\n"
                                response += f"🎭 Participants: {pop_count}\n"
                                response += f"❤️ Love Seekers: {love_count}\n"
                                
                            # Show filter information
                            filter_info = []
                            if filter_type:
                                filter_info.append(f"Type: {filter_type}")
                            if filter_gender:
                                filter_info.append(f"Gender: {filter_gender.title()}")
                            if filter_location:
                                filter_info.append(f"Location: {filter_location.title()}")
                            
                            if filter_info:
                                response += f"\nFiltered by: {', '.join(filter_info)}"
                            
                            # Get detailed registrations when filtering
                            if filter_type or filter_gender or filter_location:
                                # Log the final query for debugging
                                logger.info(f"Detailed query (on_chat): {query}")
                                
                                # Get the detailed registrations
                                registrations = await self.db_client.registrations.find(query).to_list(length=20)
                                filtered_count = len(registrations)
                                
                                logger.info(f"Found {filtered_count} registrations matching the detailed query")
                                
                                # Add detailed participant information
                                if filtered_count > 0:
                                    response += "\n\n👥 Detailed Participant List 👥\n"
                                    for i, reg in enumerate(registrations, 1):
                                        response += f"\n{i}. {await self.format_registration_details(reg)}"
                                
                            await self.highrise.chat(response)
                            
                            # Debug info for owner only when specifically requested
                            if user.id == self.owner_id and "debug" in message.lower():
                                # Add more comprehensive debug information
                                debug_info = f"Query: {query}\n\n"
                                
                                # Get one registration document to show its structure
                                sample_reg = await self.db_client.registrations.find_one({})
                                if sample_reg:
                                    # Format the document in a readable way, excluding _id which isn't serializable
                                    sample_reg_copy = dict(sample_reg)
                                    if "_id" in sample_reg_copy:
                                        sample_reg_copy["_id"] = str(sample_reg_copy["_id"])
                                    debug_info += f"Sample registration structure:\n{sample_reg_copy}"
                                else:
                                    debug_info += "No registrations found in database."
                                
                                await self.highrise.whisper(user.id, f"Debug Info:\n{debug_info}")
                                
                        except Exception as e:
                            logger.error(f"Error in !list/!check command: {e}")
                            await self.highrise.chat(f"⚠️ Error checking registrations: {str(e)}")
                    else:
                        await self.highrise.chat("⚠️ Database connection is not available!")
                else:
                    await self.highrise.chat("Only the room owner and hosts can view registrations! 🔒")
                return
            
            # Send notification to all subscribers (owner/host only)
            if lower_msg.startswith("!notify"):
                if is_privileged:
                    # Extract the message
                    parts = message.split(" ", 1)
                    if len(parts) < 2 or not parts[1].strip():
                        await self.highrise.chat("Usage: !notify <message>")
                        return
                        
                    notification_msg = parts[1].strip()
                    
                    # Add attribution
                    full_message = f"📢 MATCH SHOW ANNOUNCEMENT from @{user.username}:\n{notification_msg}"
                    
                    # Track successful notifications
                    sent_count = 0
                    
                    # Send to all subscribers
                    for subscriber_id in self.subscribers:
                        try:
                            await self.highrise.send_whisper(subscriber_id, full_message)
                            sent_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send notification to {subscriber_id}: {e}")
                    
                    # Confirm notification was sent
                    await self.highrise.chat(f"✅ Notification sent to {sent_count} subscribers!")
                else:
                    await self.highrise.chat("Only the room owner and hosts can send notifications! 🔒")
                return
            
            # Emote Commands
            if lower_msg.startswith("!emote"):
                await emote(self, user, message)
                return
            
            if lower_msg.startswith("!fight"):
                await fight(self, user, message)
                return
            
            if lower_msg.startswith("!hug"):
                await hug(self, user, message)
                return
            
            if lower_msg.startswith("!flirt"):
                await flirt(self, user, message)
                return
            
            if lower_msg in ["!emotes", "emotes", "!allemo", "allemo"]:
                await emotes(self, user, message)
                return
            
            if lower_msg in ["!emo", "emo"]:
                await emo(self, user, message)
                return
            
            # Help command
            if lower_msg in ["!help", "help", "commands"]:
                help_text = (
                    f"💘 Match Show Bot Commands 💘\n\n"
                    "[For Users]\n"
                    "• Send 'POP' to register as a participant\n"
                    "• Send 'LOVE' to register as someone looking for love\n"
                    "• Send '!SUB' to get notified when the show starts\n"
                    "• !equip <item_name> - Equip clothing item\n"
                    "• !remove <category> - Remove clothing category\n\n"
                    "[Emotes & Fun]\n"
                    "• Type 'kiss', 'wave', 'dance' etc. to do emotes\n"
                    "• Add 'all' (e.g., 'kiss all') to make everyone do it\n"
                    "• !emote @username emotename - Make someone do an emote\n"
                    "• !fight @username - Sword fight with someone\n"
                    "• !hug @username - Hug someone\n"
                    "• !flirt @username - Flirt with someone\n"
                    "• !emotes - See all available emotes\n\n"
                )
                
                # Always show host commands to owner
                if is_privileged or user.id == self.owner_id:
                    help_text += (
                        "[For Hosts & Owner]\n"
                        "• !list/!check - Count all registrations\n"
                        "• !list POP - Show detailed 'POP' registrations\n"
                        "• !list LOVE - Show detailed 'LOVE' registrations\n"
                        "• !list male/female - Filter by gender\n"
                        "• !list POP female - Filter by type & gender\n"
                        "• !list POP nigeria - Filter by type & location\n"
                        "• !list male nigeria - Filter by gender & location\n"
                        "• !notify <message> - Send message to all subscribers\n\n"
                    )
                
                # Always show owner commands to owner
                if user.id == self.owner_id:
                    help_text += (
                        "[For Owner Only]\n"
                        "• !set - Set bot position\n"
                        "• !set event <date> - Set event date\n"
                        "• !addhost <username> - Add a host\n"
                        "• !removehost <username> - Remove a host\n\n"
                    )
                
                # Add event info if available
                if self.event_date:
                    help_text += f"📅 Next Match Show: {self.event_date}\n"
                
                await self.highrise.chat(help_text)
                return
            
            # Single emote detection (must be at the end to avoid conflicts with commands)
            # Check if user typed a single emote name or "emote all"
            emote_handled = await single_emote(self, user, message)
            if emote_handled:
                return
                
        except Exception as e:
            logger.error(f"Error in on_chat: {e}")
            await self.highrise.chat("Sorry, something went wrong! Please try again. 🤖")

async def main():
    # Get credentials from environment variables
    room_id = os.getenv("ROOM_ID")
    bot_token = os.getenv("BOT_TOKEN")
    
    # Debug information
    logger.info(f"Starting matchmaking bot")
    logger.info(f"ROOM_ID found: {'Yes' if room_id else 'No'}")
    logger.info(f"BOT_TOKEN found: {'Yes' if bot_token else 'No'}")
    
    if not room_id:
        logger.error("ROOM_ID not found in environment variables!")
        print("❌ Error: ROOM_ID not found in environment variables!")
        print("Please set ROOM_ID in your .env file")
        return
    
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables!")
        print("❌ Error: BOT_TOKEN not found in environment variables!")
        print("Please set BOT_TOKEN in your .env file")
        return
    
    # Clean the credentials (remove any trailing % or whitespace)
    room_id = room_id.strip().rstrip('%') if room_id else None
    bot_token = bot_token.strip().rstrip('%') if bot_token else None
    
    logger.info(f"Starting bot for room: {room_id}")
    
    try:
        definitions = [BotDefinition(Bot(), room_id, bot_token)]
        await __main__.main(definitions)
    except Exception as e:
        logger.error(f"Bot connection failed: {e}")
        print(f"❌ Bot connection failed: {e}")
        
        # Check for TaskGroup/ExceptionGroup error
        if "TaskGroup" in str(e) or "ExceptionGroup" in str(e):
            print("💡 TaskGroup error detected - this is often a connection issue")
            print("   • This will auto-retry with exponential backoff")
            print("   • Check bot token and room ID validity")
        elif "Invalid room id" in str(e):
            print("💡 Room ID troubleshooting:")
            print("   • Make sure the ROOM_ID in your .env file is correct")
            print("   • The bot must be invited to the room as a bot")
            print("   • Check that the room exists and is accessible")
        elif "API token not found" in str(e) or "Invalid token" in str(e):
            print("💡 Bot token troubleshooting:")
            print("   • Make sure your BOT_TOKEN in .env is correct and complete")
            print("   • Verify the token is from your Highrise developer account")
            print("   • Check for any extra characters or spaces")
        raise


if __name__ == "__main__":
    arun(main())
