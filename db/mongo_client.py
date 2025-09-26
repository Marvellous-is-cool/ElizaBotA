"""
MongoDB client for the Match Show bot.
Handles all database operations and connection management.
"""

import os
import asyncio
import copy
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from config import MONGODB_URI, MONGODB_DB_NAME

logger = logging.getLogger(__name__)
logger.disabled = True  # Disable this logger completely

class MongoDBClient:
    def __init__(self):
        """Initialize the MongoDB client with URI from environment or config"""
        # Get MongoDB URI from environment or config
        self.uri = os.getenv("MONGODB_URI", MONGODB_URI)
        self.db_name = os.getenv("MONGODB_DB_NAME", MONGODB_DB_NAME)
        self.client = None
        self.db = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Connect to MongoDB and initialize collections"""
        try:
            # Print status information without exposing credentials
            masked_uri = self.uri
            if "://" in masked_uri and "@" in masked_uri:
                parts = masked_uri.split("@")
                auth_part = parts[0].split("://")[1].split(":")
                if len(auth_part) > 1:
                    masked_uri = f"{parts[0].split('://')[0]}://{auth_part[0]}:****@{parts[1]}"
            
            print(f"Connecting to MongoDB at: {masked_uri}")
            print(f"Database name: {self.db_name}")
            
            # Create motor client
            self.client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=10000)
            
            # Check connection
            print("Testing MongoDB server connection...")
            await self.client.server_info()
            
            # Get database
            self.db = self.client[self.db_name]
            self.is_connected = True
            print(f"Connected to MongoDB database: {self.db_name}")
            logger.info(f"Connected to MongoDB database: {self.db_name}")
            
            # Initialize collections
            print("Initializing collections...")
            self.users = self.db.users
            self.matches = self.db.matches
            self.profiles = self.db.profiles
            self.interactions = self.db.interactions
            self.bot_data = self.db.bot_data
            self.registrations = self.db.registrations
            self.subscribers = self.db.subscribers
            
            # Create indexes
            print("Creating database indexes...")
            await self.users.create_index("user_id", unique=True)
            await self.profiles.create_index("user_id", unique=True)
            await self.matches.create_index([("user1_id", 1), ("user2_id", 1)], unique=True)
            await self.registrations.create_index("user_id", unique=True)
            
            print("MongoDB setup complete")
            return True
        
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.is_connected = False
            print(f"Failed to connect to MongoDB: {str(e)}")
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            
            # Add troubleshooting info
            if "timed out" in str(e) or "ServerSelectionTimeoutError" in str(e):
                print("MongoDB connection timed out. Possible causes:")
                print("- Network connectivity issues")
                print("- MongoDB server not running or accessible")
                print("- IP address not whitelisted in MongoDB Atlas")
                print("- Incorrect connection string")
            
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False
            logger.info("Disconnected from MongoDB")
    
    async def save_user(self, user_id: str, username: str) -> bool:
        """Save or update a user in the database"""
        try:
            await self.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "username": username,
                        "last_seen": datetime.now()
                    },
                    "$setOnInsert": {
                        "joined_date": datetime.now(),
                        "match_count": 0
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving user {user_id}: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get a user's matchmaking profile"""
        try:
            return await self.profiles.find_one({"user_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user profile {user_id}: {str(e)}")
            return None
    
    async def save_user_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Save or update a user's matchmaking profile"""
        try:
            profile_data["updated_at"] = datetime.now()
            await self.profiles.update_one(
                {"user_id": user_id},
                {
                    "$set": profile_data,
                    "$setOnInsert": {
                        "created_at": datetime.now()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving profile for {user_id}: {str(e)}")
            return False
    
    async def record_match_attempt(self, user1_id: str, user2_id: str, 
                                  compatibility_score: float, matched: bool) -> bool:
        """Record a match attempt between two users"""
        try:
            # Sort IDs to ensure consistency in document keys
            users = sorted([user1_id, user2_id])
            
            await self.matches.update_one(
                {"user1_id": users[0], "user2_id": users[1]},
                {
                    "$set": {
                        "last_matched": datetime.now(),
                        "compatibility_score": compatibility_score,
                        "matched": matched
                    },
                    "$inc": {"match_attempts": 1},
                    "$setOnInsert": {
                        "first_matched": datetime.now()
                    }
                },
                upsert=True
            )
            
            # Update match counts for both users
            await self.users.update_one(
                {"user_id": user1_id},
                {"$inc": {"match_count": 1}}
            )
            await self.users.update_one(
                {"user_id": user2_id},
                {"$inc": {"match_count": 1}}
            )
            
            return True
        except Exception as e:
            logger.error(f"Error recording match: {str(e)}")
            return False
    
    async def get_recent_matches(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get a user's recent matches"""
        try:
            # Find matches where user is either user1 or user2
            matches = []
            cursor = self.matches.find({
                "$or": [
                    {"user1_id": user_id},
                    {"user2_id": user_id}
                ],
                "matched": True
            }).sort("last_matched", -1).limit(limit)
            
            async for match in cursor:
                matches.append(match)
            
            return matches
        except Exception as e:
            logger.error(f"Error getting matches for {user_id}: {str(e)}")
            return []
    
    async def can_request_match(self, user_id: str, cooldown_minutes: int) -> bool:
        """Check if user can request a new match (based on cooldown)"""
        try:
            # Find most recent match attempt
            last_match = await self.matches.find_one(
                {"$or": [{"user1_id": user_id}, {"user2_id": user_id}]},
                sort=[("last_matched", -1)]
            )
            
            if not last_match:
                return True  # No previous matches found
            
            # Calculate time since last match
            last_time = last_match.get("last_matched")
            if not last_time:
                return True
                
            time_diff = (datetime.now() - last_time).total_seconds() / 60
            return time_diff >= cooldown_minutes
            
        except Exception as e:
            logger.error(f"Error checking match cooldown for {user_id}: {str(e)}")
            return True  # Default to allowing match if there's an error
    
    async def save_bot_position(self, position_data: Dict) -> bool:
        """Save bot position data to MongoDB"""
        try:
            await self.bot_data.update_one(
                {"data_type": "bot_position"},
                {
                    "$set": {
                        "position": position_data,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving bot position: {str(e)}")
            return False
    
    async def get_bot_position(self) -> Optional[Dict]:
        """Get bot position from MongoDB"""
        try:
            data = await self.bot_data.find_one({"data_type": "bot_position"})
            return data.get("position") if data else None
        except Exception as e:
            logger.error(f"Error retrieving bot position: {str(e)}")
            return None
    
    async def find_potential_matches(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Find potential matches for a user based on compatibility"""
        try:
            # Get user profile
            user_profile = await self.profiles.find_one({"user_id": user_id})
            if not user_profile:
                return []
                
            # Find users with compatible profiles
            matches = []
            pipeline = [
                # Exclude the user themselves
                {"$match": {"user_id": {"$ne": user_id}}},
                # Match compatibility criteria
                {"$match": {
                    # Match criteria would go here - simplified for now
                    "looking_for": {"$in": [user_profile.get("gender", "any"), "any"]}
                }},
                # Sort by most compatible (this logic can be expanded)
                {"$sort": {"last_active": -1}},
                {"$limit": limit}
            ]
            
            cursor = self.profiles.aggregate(pipeline)
            async for doc in cursor:
                matches.append(doc)
                
            return matches
        except Exception as e:
            logger.error(f"Error finding matches for {user_id}: {str(e)}")
            return []
            
    async def save_registration(self, user_id: str = None, username: str = None, reg_type: str = None, registration_data: Dict = None) -> bool:
        """Save a user's registration for the Match Show"""
        try:
            # Handle different parameter types
            if isinstance(user_id, dict):
                # The first parameter is actually the registration data
                data = copy.deepcopy(user_id)
            else:
                # Handle both new and old calling styles
                data = registration_data if registration_data else {}
                
                # Make sure we're working with a copy to avoid modifying the original
                data = copy.deepcopy(data)
                
                # Add user_id and type if passed as parameters
                if user_id:
                    data["user_id"] = user_id
                if username:
                    data["username"] = username
                
            # Ensure type and registration_type are consistent
            if reg_type:
                data["type"] = reg_type
                data["registration_type"] = reg_type
                
            # If the data contains a registration type, make sure it's available at both levels
            if "data" in data and "registration_type" in data["data"]:
                data["type"] = data["data"]["registration_type"]
                data["registration_type"] = data["data"]["registration_type"]
            elif "type" in data:
                data["registration_type"] = data["type"]
            elif "registration_type" in data:
                data["type"] = data["registration_type"]
                
            # Make sure username is available at the root level
            if "username" not in data and "data" in data and "username" in data["data"]:
                data["username"] = data["data"]["username"]
                
            # Add timestamp if not present
            if "registration_time" not in data:
                data["registration_time"] = datetime.now()
                
            # Ensure completed flag is set
            if "completed" not in data:
                data["completed"] = True
                
            # Make sure all important fields are at the root level if they're nested in data
            important_fields = ["user_id", "username", "name", "age", "gender", "country", "continent", "occupation"]
            for field in important_fields:
                if field not in data and "data" in data and field in data["data"]:
                    data[field] = data["data"][field]
            
            # Ensure user_id is available in data
            if "user_id" not in data:
                logger.error("Cannot save registration without user_id")
                return False
                
            # Create a flattened version of the data to save
            flat_data = {}
            
            # Check for username in all possible locations with detailed logging
            username = data.get("username", None)
            logger.info(f"Initial username check at root level: {username}")
            
            if not username and "data" in data:
                username = data["data"].get("username", None)
                logger.info(f"Secondary username check in data object: {username}")
            
            # Try one more place - directly in the session object
            if not username:
                username = data.get("username", None)  # Try root again just in case
                logger.info(f"Final username check attempt: {username}")
                
            # Log username search results
            if username:
                logger.info(f"✅ Successfully found username '{username}' in registration data")
            else:
                logger.warning(f"❌ Username not found in any location in registration data")
                logger.warning(f"Full data object for debugging: {data}")
                
            # Start with all fields at the root level
            for key, value in data.items():
                if key != "data":  # Skip the nested data object for now
                    flat_data[key] = value
            
            # If there's a nested data object, extract its fields
            if "data" in data and isinstance(data["data"], dict):
                for key, value in data["data"].items():
                    # For username, always use the one we found earlier
                    if key == "username" and username:
                        flat_data["username"] = username
                    # Don't overwrite root fields with nested ones for other fields
                    elif key not in flat_data:
                        flat_data[key] = value
                        
            # Finally, ensure username is set if we found it
            if username:
                flat_data["username"] = username
            
            # Log the flattened data for debugging
            logger.info(f"Flattened registration data: {flat_data}")
            
            # Save to registrations collection
            result = await self.registrations.update_one(
                {"user_id": flat_data["user_id"]},
                {"$set": flat_data},
                upsert=True
            )
            
            # Verify the document was actually inserted/updated
            if result.matched_count == 0 and result.upserted_id is None:
                logger.error(f"Failed to save registration for {flat_data.get('username', 'unknown')}: No document matched or inserted")
                return False
            
            # Log with the correct user information from the flattened data
            username = flat_data.get('username', 'unknown')
            reg_type = flat_data.get('type', 'unknown')
            user_id = flat_data.get('user_id', 'unknown')
            logger.info(f"Successfully saved registration for {username} (ID: {user_id}), type: {reg_type}")
            
            # Log essential registration data fields for debugging
            logger.info(f"Registration saved with fields: user_id={user_id}, username={username}, type={reg_type}, completed={flat_data.get('completed', False)}")
            return True
        except Exception as e:
            logger.error(f"Error saving registration for {data.get('user_id', 'unknown')}: {str(e)}")
            # Log more detailed debug information
            logger.error(f"Registration data that failed: {data}")
            return False
    
    async def get_registrations(self, filter_type: Optional[str] = None, 
                             filter_location: Optional[str] = None) -> List[Dict]:
        """Get registrations with optional filters"""
        try:
            # Build query
            query = {"completed": True}
            if filter_type:
                query["registration_type"] = filter_type
            if filter_location:
                query["$or"] = [
                    {"country": {"$regex": filter_location, "$options": "i"}},
                    {"continent": {"$regex": filter_location, "$options": "i"}}
                ]
            
            # Get registrations
            registrations = []
            cursor = self.registrations.find(query).sort("registration_time", -1)
            async for doc in cursor:
                registrations.append(doc)
            
            return registrations
        except Exception as e:
            logger.error(f"Error getting registrations: {str(e)}")
            return []
    
    async def count_registrations(self, filter_type: Optional[str] = None, 
                               filter_location: Optional[str] = None) -> int:
        """Count registrations with optional filters"""
        try:
            # Build query
            query = {"completed": True}
            if filter_type:
                query["registration_type"] = filter_type
            if filter_location:
                query["$or"] = [
                    {"country": {"$regex": filter_location, "$options": "i"}},
                    {"continent": {"$regex": filter_location, "$options": "i"}}
                ]
            
            # Count registrations
            return await self.registrations.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting registrations: {str(e)}")
            return 0
            
    async def save_hosts(self, host_ids: List[str]) -> bool:
        """Save list of hosts to database"""
        try:
            await self.bot_data.update_one(
                {"data_type": "hosts"},
                {"$set": {"user_ids": host_ids, "updated_at": datetime.now()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving hosts: {str(e)}")
            return False
    
    async def get_hosts(self) -> List[str]:
        """Get list of hosts from database"""
        try:
            result = await self.bot_data.find_one({"data_type": "hosts"})
            if result and "user_ids" in result:
                return result["user_ids"]
            return []
        except Exception as e:
            logger.error(f"Error retrieving hosts: {str(e)}")
            return []
    
    async def save_event_date(self, event_date: str) -> bool:
        """Save event date to database"""
        try:
            await self.bot_data.update_one(
                {"data_type": "event"},
                {"$set": {"date": event_date, "updated_at": datetime.now()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving event date: {str(e)}")
            return False
            
    async def get_event_date(self) -> str:
        """Get event date from database"""
        try:
            result = await self.bot_data.find_one({"data_type": "event"})
            if result and "date" in result:
                return result["date"]
            return ""
        except Exception as e:
            logger.error(f"Error retrieving event date: {str(e)}")
            return ""
    
    async def save_subscribers(self, subscriber_ids: List[str]) -> bool:
        """Save list of subscribers to database"""
        try:
            await self.bot_data.update_one(
                {"data_type": "subscribers"},
                {"$set": {"user_ids": subscriber_ids, "updated_at": datetime.now()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error saving subscribers: {str(e)}")
            return False
            
    async def get_subscribers(self) -> List[str]:
        """Get list of subscribers from database"""
        try:
            result = await self.bot_data.find_one({"data_type": "subscribers"})
            if result and "user_ids" in result:
                return result["user_ids"]
            return []
        except Exception as e:
            logger.error(f"Error retrieving subscribers: {str(e)}")
            return []
            
    async def save_subscriber(self, user_id: str, username: str) -> bool:
        """Save a single subscriber"""
        try:
            # Get current subscribers
            subscribers_doc = await self.bot_data.find_one({"data_type": "subscribers"})
            subscriber_ids = subscribers_doc.get("user_ids", []) if subscribers_doc else []
            
            # Add new subscriber if not already present
            if user_id not in subscriber_ids:
                subscriber_ids.append(user_id)
                
            # Update subscribers document
            await self.bot_data.update_one(
                {"data_type": "subscribers"},
                {
                    "$set": {
                        "user_ids": subscriber_ids,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True
            )
            
            # Also save in subscribers collection for additional metadata
            await self.subscribers.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "username": username,
                        "updated_at": datetime.now()
                    },
                    "$setOnInsert": {
                        "subscribed_at": datetime.now()
                    }
                },
                upsert=True
            )
            
            return True
        except Exception as e:
            logger.error(f"Error saving subscriber {user_id}: {str(e)}")
            return False