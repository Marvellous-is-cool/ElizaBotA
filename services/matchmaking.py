"""
Matchmaking service for Match Show Bot.
Handles all matchmaking logic, profiles, and user interactions.
"""

import logging
import random
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import re
from db.mongo_client import MongoDBClient
from config import MATCH_PROMPT_INTERVAL, MIN_AGE

# Define compatibility factors for matching
COMPATIBILITY_FACTORS = ["age", "country", "continent"]
MATCH_COOLDOWN_MINUTES = 30  # Default cooldown time

logger = logging.getLogger(__name__)
logger.disabled = True  # Disable this logger completely

class MatchmakingService:
    def __init__(self, db_client: MongoDBClient):
        self.db = db_client
        self.active_profiles = {}  # Cache of active profiles
        self.active_matches = {}  # Currently active matchmaking sessions
    
    async def handle_match_command(self, user_id: str, username: str, message: str) -> str:
        """Handle the !match command and its variations"""
        # Record user interaction
        await self.db.save_user(user_id, username)
        
        # Check command variations
        if re.search(r'^!match\s+profile', message, re.I):
            return await self.handle_profile_setup(user_id, username, message)
            
        if re.search(r'^!match\s+view', message, re.I):
            return await self.view_profile(user_id)
            
        if re.search(r'^!match\s+help', message, re.I):
            return self.get_match_help()
            
        if re.search(r'^!match\s+history', message, re.I):
            return await self.get_match_history(user_id)
            
        # Default match command - find matches
        return await self.find_match(user_id, username)
    
    async def handle_profile_setup(self, user_id: str, username: str, message: str) -> str:
        """Handle profile setup or updates"""
        # Extract profile info using regex
        profile_data = {}
        
        age_match = re.search(r'age[:\s]+(\d+)', message, re.I)
        if age_match:
            profile_data["age"] = int(age_match.group(1))
            
        gender_match = re.search(r'gender[:\s]+(\w+)', message, re.I)
        if gender_match:
            profile_data["gender"] = gender_match.group(1).lower()
            
        looking_match = re.search(r'looking\s+for[:\s]+(\w+)', message, re.I)
        if looking_match:
            profile_data["looking_for"] = looking_match.group(1).lower()
            
        interests_match = re.search(r'interests[:\s]+([\w\s,]+)', message, re.I)
        if interests_match:
            interests = [i.strip() for i in interests_match.group(1).split(",")]
            profile_data["interests"] = interests
            
        bio_match = re.search(r'bio[:\s]+([\w\s,.!?]+)(?:\s|$)', message, re.I)
        if bio_match:
            profile_data["bio"] = bio_match.group(1).strip()
        
        # If we got some valid profile data
        if profile_data:
            profile_data["username"] = username
            profile_data["user_id"] = user_id
            profile_data["last_active"] = datetime.now()
            
            success = await self.db.save_user_profile(user_id, profile_data)
            
            if success:
                return (
                    f"✅ Profile updated successfully!\n\n"
                    f"Use '!match view' to see your profile or '!match' to find someone!"
                )
            else:
                return "❌ Error updating profile. Please try again later."
        else:
            # Not enough data provided, show profile format
            return (
                "📝 **Profile Setup**\n\n"
                "Please use this format to set up your profile:\n\n"
                "!match profile age: [your age] gender: [your gender] "
                "looking for: [gender preference] interests: [your interests] "
                "bio: [brief description]\n\n"
                "Example:\n!match profile age: 25 gender: male looking for: female "
                "interests: music, hiking, gaming bio: Friendly and outgoing person looking for connections!"
            )
    
    async def view_profile(self, user_id: str) -> str:
        """View a user's profile"""
        profile = await self.db.get_user_profile(user_id)
        
        if not profile:
            return (
                "⚠️ You don't have a profile yet!\n\n"
                "Create one with: !match profile age: [age] gender: [gender] ..."
            )
        
        # Format profile for display
        profile_text = "👤 **Your Matchmaking Profile**\n\n"
        
        if "username" in profile:
            profile_text += f"Name: {profile['username']}\n"
        
        if "age" in profile:
            profile_text += f"Age: {profile['age']}\n"
            
        if "gender" in profile:
            profile_text += f"Gender: {profile['gender'].capitalize()}\n"
            
        if "looking_for" in profile:
            profile_text += f"Looking for: {profile['looking_for'].capitalize()}\n"
            
        if "interests" in profile and profile["interests"]:
            interests = ", ".join(profile["interests"])
            profile_text += f"Interests: {interests}\n"
            
        if "bio" in profile:
            profile_text += f"\nBio: {profile['bio']}\n"
            
        if "match_count" in profile:
            profile_text += f"\nMatches made: {profile['match_count']}"
        
        return profile_text
    
    def get_match_help(self) -> str:
        """Get help for matchmaking commands"""
        return (
            "❤️ **Matchmaking Commands** ❤️\n\n"
            "• !match - Find a potential match\n"
            "• !match profile ... - Create/update your profile\n"
            "• !match view - View your current profile\n"
            "• !match history - See your recent matches\n"
            "• !match help - Show this help message\n\n"
            f"Note: You can request a new match every {MATCH_COOLDOWN_MINUTES} minutes."
        )
    
    async def get_match_history(self, user_id: str) -> str:
        """Get a user's match history"""
        matches = await self.db.get_recent_matches(user_id)
        
        if not matches:
            return "You haven't matched with anyone yet! Try '!match' to find someone!"
        
        history_text = "❤️ **Your Recent Matches** ❤️\n\n"
        
        for i, match in enumerate(matches, 1):
            # Determine which user ID is the match (not the current user)
            match_id = match["user1_id"] if match["user2_id"] == user_id else match["user2_id"]
            
            # Get the match's profile
            match_profile = await self.db.get_user_profile(match_id)
            match_name = match_profile.get("username", "Unknown User") if match_profile else "Unknown User"
            
            # Format match info
            match_time = match["last_matched"].strftime("%Y-%m-%d")
            compatibility = int(match["compatibility_score"] * 100)
            
            history_text += f"{i}. {match_name} - {compatibility}% compatible (matched on {match_time})\n"
        
        return history_text
    
    async def find_match(self, user_id: str, username: str) -> str:
        """Find a match for a user"""
        # Check if user has a profile
        profile = await self.db.get_user_profile(user_id)
        
        if not profile:
            return (
                "⚠️ You need to create a profile before matching!\n\n"
                "Create one with: !match profile age: [age] gender: [gender] ..."
            )
        
        # Check if user is on cooldown
        can_match = await self.db.can_request_match(user_id, MATCH_COOLDOWN_MINUTES)
        
        if not can_match:
            return (
                f"⏳ Please wait! You can request a new match every {MATCH_COOLDOWN_MINUTES} minutes.\n"
                "Try again soon or use '!match history' to see your previous matches!"
            )
        
        # Find potential matches
        potential_matches = await self.db.find_potential_matches(user_id)
        
        if not potential_matches:
            return (
                "😔 No matching profiles found right now.\n"
                "Try again later or invite more friends to join the matchmaking!"
            )
        
        # Select a random match from the potentials
        match = random.choice(potential_matches)
        match_username = match.get("username", "Someone special")
        
        # Calculate compatibility score (simplified example)
        compatibility = random.uniform(0.5, 0.99)  # 50-99% compatibility
        compatibility_pct = int(compatibility * 100)
        
        # Record the match
        await self.db.record_match_attempt(
            user_id, match["user_id"], compatibility, True
        )
        
        # Create the match response
        match_text = (
            f"💘 **Match Found!** 💘\n\n"
            f"You and {match_username} are {compatibility_pct}% compatible!\n\n"
        )
        
        # Add some match details
        if "interests" in match and match["interests"]:
            interests = ", ".join(match["interests"][:3])  # First 3 interests
            match_text += f"Shared interests: {interests}\n"
            
        if "age" in match:
            match_text += f"Age: {match['age']}\n"
            
        if "bio" in match:
            # Truncate bio if too long
            bio = match["bio"]
            if len(bio) > 100:
                bio = bio[:97] + "..."
            match_text += f"\n{match_username}'s bio: \"{bio}\"\n"
        
        match_text += "\nWhy not say hello and get to know each other? 😊"
        
        return match_text
        
    async def get_random_match_prompt(self) -> str:
        """Get a random prompt to encourage matchmaking"""
        from config import MATCH_PROMPTS
        return random.choice(MATCH_PROMPTS)