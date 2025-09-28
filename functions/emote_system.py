"""
Emote Functions for Highrise Bot
Supports single emotes, targeted emotes, couple emotes, and group emotes
"""

from highrise import BaseBot, User
from highrise.models import *
from highrise.webapi import *
import re

# Available emotes list
AVAILABLE_EMOTES = [
    "emote-kiss", "emote-no", "emote-sad", "emote-yes", "emote-laughing",
    "emote-hello", "emote-wave", "emote-shy", "emote-tired", "emoji-angry",
    "idle-loop-sitfloor", "emoji-thumbsup", "emote-lust", "emoji-cursing",
    "emote-greedy", "emoji-flex", "emoji-gagging", "emoji-celebrate",
    "dance-macarena", "dance-tiktok8", "dance-blackpink", "emote-model",
    "dance-tiktok2", "dance-pennywise", "emote-bow", "dance-russian",
    "emote-curtsy", "emote-snowball", "emote-hot", "emote-snowangel",
    "emote-charging", "dance-shoppingcart", "emote-confused",
    "idle-enthusiastic", "emote-telekinesis", "emote-float",
    "emote-teleporting", "emote-swordfight", "emote-maniac",
    "emote-energyball", "emote-snake", "idle_singing", "emote-frog",
    "emote-superpose", "emote-cute", "dance-tiktok9", "dance-weird",
    "dance-tiktok10", "emote-pose7", "emote-pose8", "idle-dance-casual",
    "emote-pose1", "emote-pose3", "emote-pose5", "emote-cutey",
    "emote-punkguitar", "emote-zombierun", "emote-fashionista",
    "emote-gravity", "dance-icecream", "dance-wrong", "idle-uwu",
    "idle-dance-tiktok4", "emote-hug"
]

# Emote categories for better organization
EMOTE_CATEGORIES = {
    "emotions": ["kiss", "sad", "yes", "no", "laughing", "hello", "wave", "shy", "tired", "angry", "lust", "cute", "bow", "curtsy"],
    "dances": ["macarena", "tiktok8", "blackpink", "tiktok2", "pennywise", "russian", "shoppingcart", "tiktok9", "weird", "tiktok10", "icecream", "wrong", "tiktok4"],
    "poses": ["model", "pose1", "pose3", "pose5", "pose7", "pose8", "superpose", "cutey"],
    "actions": ["telekinesis", "float", "teleporting", "swordfight", "energyball", "snake", "frog", "charging", "maniac", "zombierun", "fashionista", "gravity"],
    "idle": ["sitfloor", "enthusiastic", "singing", "casual", "uwu"],
    "emojis": ["thumbsup", "cursing", "greedy", "flex", "gagging", "celebrate"]
}

async def find_user_by_username(bot: BaseBot, username: str) -> str | None:
    """Find a user ID by username in the room"""
    try:
        # Remove @ if present
        clean_username = username.replace("@", "").strip()
        
        # Get room users
        room_users = await bot.highrise.get_room_users()
        
        for room_user, _ in room_users.content:
            if room_user.username.lower() == clean_username.lower():
                return room_user.id
        return None
    except Exception as e:
        print(f"Error finding user {username}: {e}")
        return None

async def get_emote_id_from_name(emote_name: str) -> str | None:
    """Convert emote name to full emote ID"""
    emote_name = emote_name.lower().strip()
    
    for emote_id in AVAILABLE_EMOTES:
        # Check if the emote name matches the end of the emote ID
        if emote_id.endswith(f"-{emote_name}") or emote_id.endswith(f"_{emote_name}"):
            return emote_id
        # Also check if it's an exact match for emoji types
        if emote_id == f"emoji-{emote_name}" or emote_id == f"emote-{emote_name}":
            return emote_id
        # Check dance types
        if emote_id == f"dance-{emote_name}":
            return emote_id
        # Check idle types
        if emote_id == f"idle-{emote_name}" or emote_id == f"idle_{emote_name}":
            return emote_id
    return None

async def single_emote(bot: BaseBot, user: User, message: str) -> bool:
    """Handle single emote commands (user types 'kiss' and does emote-kiss)"""
    try:
        message_lower = message.lower().strip()
        
        # Check for "emote_name all" pattern for group emotes
        if " all" in message_lower:
            emote_name = message_lower.replace(" all", "").strip()
            emote_id = await get_emote_id_from_name(emote_name)
            
            if emote_id:
                # Get all room users and send emote to everyone
                room_users = await bot.highrise.get_room_users()
                emote_count = 0
                
                for room_user, _ in room_users.content:
                    try:
                        await bot.highrise.send_emote(emote_id, room_user.id)
                        emote_count += 1
                    except:
                        continue  # Skip users that can't receive emotes
                
                if emote_count > 0:
                    await bot.highrise.chat(f"🎭 {user.username} made everyone {emote_name}! ({emote_count} users)")
                return True
        
        # Check for single emote
        else:
            emote_id = await get_emote_id_from_name(message_lower)
            if emote_id:
                await bot.highrise.send_emote(emote_id, user.id)
                return True
        
        return False
    except Exception as e:
        print(f"Error in single_emote: {e}")
        return False

async def emote(bot: BaseBot, user: User, message: str) -> None:
    """
    Main emote command: !emote @username emotename
    Usage: !emote @john kiss
    """
    try:
        parts = message.split()
        
        if len(parts) < 3:
            await bot.highrise.chat("💡 Usage: !emote @username emotename\nExample: !emote @john kiss")
            return
        
        target_username = parts[1]
        emote_name = parts[2].lower()
        
        # Find target user
        target_user_id = await find_user_by_username(bot, target_username)
        if not target_user_id:
            await bot.highrise.chat(f"❌ User {target_username} not found in room")
            return
        
        # Get emote ID
        emote_id = await get_emote_id_from_name(emote_name)
        if not emote_id:
            await bot.highrise.chat(f"❌ Emote '{emote_name}' not found. Use !emotes to see available emotes.")
            return
        
        # Send emote to target user
        await bot.highrise.send_emote(emote_id, target_user_id)
        
        # Get clean username for display
        clean_username = target_username.replace("@", "")
        await bot.highrise.chat(f"🎭 {user.username} made {clean_username} do {emote_name}!")
        
    except Exception as e:
        await bot.highrise.chat(f"❌ Error with emote command: {e}")

async def fight(bot: BaseBot, user: User, message: str) -> None:
    """
    Fight command: !fight @username
    Both users will do sword fight emote
    """
    try:
        parts = message.split()
        
        if len(parts) < 2:
            await bot.highrise.chat("💡 Usage: !fight @username")
            return
        
        target_username = parts[1]
        target_user_id = await find_user_by_username(bot, target_username)
        
        if not target_user_id:
            await bot.highrise.chat(f"❌ User {target_username} not found in room")
            return
        
        # Send fight emote to both users
        await bot.highrise.send_emote("emote-swordfight", user.id)
        await bot.highrise.send_emote("emote-swordfight", target_user_id)
        
        clean_username = target_username.replace("@", "")
        await bot.highrise.chat(f"⚔️ {user.username} and {clean_username} are fighting! Let's see who wins! 🥷")
        
    except Exception as e:
        await bot.highrise.chat(f"❌ Error with fight command: {e}")

async def hug(bot: BaseBot, user: User, message: str) -> None:
    """
    Hug command: !hug @username
    Both users will do hug emote
    """
    try:
        parts = message.split()
        
        if len(parts) < 2:
            await bot.highrise.chat("💡 Usage: !hug @username")
            return
        
        target_username = parts[1]
        target_user_id = await find_user_by_username(bot, target_username)
        
        if not target_user_id:
            await bot.highrise.chat(f"❌ User {target_username} not found in room")
            return
        
        # Send hug emote to both users
        await bot.highrise.send_emote("emote-hug", user.id)
        await bot.highrise.send_emote("emote-hug", target_user_id)
        
        clean_username = target_username.replace("@", "")
        await bot.highrise.chat(f"🫂 {user.username} and {clean_username} are hugging! So sweet! ❤️")
        
    except Exception as e:
        await bot.highrise.chat(f"❌ Error with hug command: {e}")

async def flirt(bot: BaseBot, user: User, message: str) -> None:
    """
    Flirt command: !flirt @username
    Both users will do lust emote
    """
    try:
        parts = message.split()
        
        if len(parts) < 2:
            await bot.highrise.chat("💡 Usage: !flirt @username")
            return
        
        target_username = parts[1]
        target_user_id = await find_user_by_username(bot, target_username)
        
        if not target_user_id:
            await bot.highrise.chat(f"❌ User {target_username} not found in room")
            return
        
        # Send flirt emote to both users
        await bot.highrise.send_emote("emote-lust", user.id)
        await bot.highrise.send_emote("emote-lust", target_user_id)
        
        clean_username = target_username.replace("@", "")
        await bot.highrise.chat(f"😏 {user.username} and {clean_username} are flirting! How romantic! 💕")
        
    except Exception as e:
        await bot.highrise.chat(f"❌ Error with flirt command: {e}")

async def emotes(bot: BaseBot, user: User, message: str) -> None:
    """
    Show available emotes organized by category
    """
    try:
        await bot.highrise.chat("🎭 **Available Emotes** 🎭")
        await bot.highrise.chat("💡 Type emote name to use it, or 'emotename all' for everyone!")
        
        # Show each category
        for category, emote_list in EMOTE_CATEGORIES.items():
            emote_names = ", ".join(emote_list[:8])  # Show first 8 to avoid message length limits
            if len(emote_list) > 8:
                emote_names += f"... ({len(emote_list)} total)"
            await bot.highrise.chat(f"**{category.title()}:** {emote_names}")
        
        await bot.highrise.chat("💡 Commands: !emote @user emotename, !fight @user, !hug @user, !flirt @user")
        
    except Exception as e:
        await bot.highrise.chat(f"❌ Error showing emotes: {e}")

async def allemo(bot: BaseBot, user: User, message: str) -> None:
    """Alias for emotes command"""
    await emotes(bot, user, message)

async def emo(bot: BaseBot, user: User, message: str) -> None:
    """Show a random emote suggestion"""
    try:
        import random
        random_emotes = random.sample(AVAILABLE_EMOTES, min(5, len(AVAILABLE_EMOTES)))
        emote_names = [emote.split('-')[-1] for emote in random_emotes]
        
        await bot.highrise.chat(f"🎭 Try these emotes: {', '.join(emote_names)}")
        await bot.highrise.chat("💡 Type the emote name or use !emote @user emotename")
        
    except Exception as e:
        await bot.highrise.chat(f"❌ Error showing random emotes: {e}")