"""
Tipping System for Match Show Bot
Allows bot owner to tip users privately via whispers
"""

from highrise import BaseBot, User
from highrise.models import *
from typing import Optional, List
import re


async def tip_user(bot: BaseBot, user: User, message: str) -> Optional[str]:
    """
    Tip a specific user
    Usage: tip @username amount
    Example: tip @john 50
    """
    # Check if user is owner
    if user.id != bot.owner_id:
        return "❌ Only the room owner can use tip commands."
    
    # Parse command: tip @username amount
    pattern = r'^tip\s+@(\w+)\s+(\d+)$'
    match = re.match(pattern, message.lower().strip())
    
    if not match:
        return "❌ Usage: tip @username amount\nExample: tip @john 50"
    
    target_username = match.group(1)
    amount = int(match.group(2))
    
    if amount <= 0:
        return "❌ Tip amount must be greater than 0."
    
    if amount > 10000:
        return "❌ Maximum tip amount is 10,000 gold per transaction."
    
    try:
        # Get room users to find the target
        room_users = (await bot.highrise.get_room_users()).content
        target_user = None
        
        for room_user, _ in room_users:
            if room_user.username.lower() == target_username.lower():
                target_user = room_user
                break
        
        if not target_user:
            return f"❌ User @{target_username} not found in the room."
        
        # Check bot's wallet balance
        wallet_response = await bot.highrise.get_wallet()
        wallet = wallet_response.content
        
        # Wallet is a list of CurrencyItem objects
        bot_balance = 0
        if isinstance(wallet, list):
            for item in wallet:
                if hasattr(item, 'amount'):
                    bot_balance += item.amount
        else:
            # Fallback if wallet is a single object
            bot_balance = wallet.amount if hasattr(wallet, 'amount') else 0
        
        if bot_balance < amount:
            return f"❌ Insufficient balance. Bot has {bot_balance}g, need {amount}g."
        
        # Send the tip
        await bot.highrise.tip_user(target_user.id, "gold_bar_1", amount)
        
        # Send confirmation to owner (whisper)
        return f"✅ Tipped @{target_user.username} {amount}g!\n💰 Remaining: {bot_balance - amount}g"
        
    except Exception as e:
        return f"❌ Failed to tip user: {str(e)}"


async def tip_all_users(bot: BaseBot, user: User, message: str) -> Optional[str]:
    """
    Tip all users in the room
    Usage: tipall amount
    Example: tipall 10
    """
    # Check if user is owner
    if user.id != bot.owner_id:
        return "❌ Only the room owner can use tip commands."
    
    # Parse command: tipall amount
    pattern = r'^tipall\s+(\d+)$'
    match = re.match(pattern, message.lower().strip())
    
    if not match:
        return "❌ Usage: tipall amount\nExample: tipall 10"
    
    amount_per_user = int(match.group(1))
    
    if amount_per_user <= 0:
        return "❌ Tip amount must be greater than 0."
    
    if amount_per_user > 1000:
        return "❌ Maximum tip amount per user is 1,000 gold for tipall."
    
    try:
        # Get all room users
        room_users = (await bot.highrise.get_room_users()).content
        
        # Filter out the bot itself
        users_to_tip = [room_user for room_user, _ in room_users if room_user.id != bot.bot_id]
        
        if not users_to_tip:
            return "❌ No users to tip in the room."
        
        total_amount = amount_per_user * len(users_to_tip)
        
        # Check bot's wallet balance
        wallet_response = await bot.highrise.get_wallet()
        wallet = wallet_response.content
        
        # Wallet is a list of CurrencyItem objects
        bot_balance = 0
        if isinstance(wallet, list):
            for item in wallet:
                if hasattr(item, 'amount'):
                    bot_balance += item.amount
        else:
            bot_balance = wallet.amount if hasattr(wallet, 'amount') else 0
        
        if bot_balance < total_amount:
            max_users = bot_balance // amount_per_user if amount_per_user > 0 else 0
            return f"❌ Insufficient balance.\n💰 Bot: {bot_balance}g\n📊 Need: {total_amount}g\n💡 Can tip {max_users} users"
        
        # Tip all users (limit response to avoid "message too long")
        success_count = 0
        failed_count = 0
        
        for room_user in users_to_tip:
            try:
                await bot.highrise.tip_user(room_user.id, "gold_bar_1", amount_per_user)
                success_count += 1
            except Exception:
                failed_count += 1
        
        # Build short response to avoid "message too long" error
        response = f"✅ Tipped {success_count} users {amount_per_user}g each\n"
        response += f"💰 Spent: {success_count * amount_per_user}g"
        
        if failed_count > 0:
            response += f"\n⚠️ {failed_count} failed"
        
        return response
        
    except Exception as e:
        return f"❌ Failed to tip all users: {str(e)}"


async def tip_participants(bot: BaseBot, user: User, message: str) -> Optional[str]:
    """
    Tip all registered participants (POP or LOVE)
    Usage: tipparticipants amount
    Example: tipparticipants 50
    """
    # Check if user is owner
    if user.id != bot.owner_id:
        return "❌ Only the room owner can use tip commands."
    
    # Parse command: tipparticipants amount
    pattern = r'^tipparticipants\s+(\d+)$'
    match = re.match(pattern, message.lower().strip())
    
    if not match:
        return "❌ Usage: tipparticipants amount\nExample: tipparticipants 50"
    
    amount_per_user = int(match.group(1))
    
    if amount_per_user <= 0:
        return "❌ Tip amount must be greater than 0."
    
    if amount_per_user > 5000:
        return "❌ Maximum tip amount per participant is 5,000 gold."
    
    try:
        # Check if database is available
        if not bot.db_client or not bot.db_client.is_connected:
            return "❌ Database not available."
        
        # Get all participants from database
        participants_collection = bot.db_client.db.participants
        participants = await participants_collection.find().to_list(length=None)
        
        if not participants:
            return "❌ No participants registered yet."
        
        # Get current room users
        room_users = (await bot.highrise.get_room_users()).content
        room_user_ids = {room_user.id for room_user, _ in room_users}
        
        # Filter participants who are currently in the room
        participants_in_room = [p for p in participants if p['user_id'] in room_user_ids]
        
        if not participants_in_room:
            return "❌ No registered participants currently in the room."
        
        total_amount = amount_per_user * len(participants_in_room)
        
        # Check bot's wallet balance
        wallet_response = await bot.highrise.get_wallet()
        wallet = wallet_response.content
        
        # Wallet is a list of CurrencyItem objects
        bot_balance = 0
        if isinstance(wallet, list):
            for item in wallet:
                if hasattr(item, 'amount'):
                    bot_balance += item.amount
        else:
            bot_balance = wallet.amount if hasattr(wallet, 'amount') else 0
        
        if bot_balance < total_amount:
            max_users = bot_balance // amount_per_user if amount_per_user > 0 else 0
            return f"❌ Insufficient balance.\n💰 Bot: {bot_balance}g\n📊 Need: {total_amount}g"
        
        # Tip all participants (avoid long messages)
        success_count = 0
        failed_count = 0
        
        for participant in participants_in_room:
            try:
                await bot.highrise.tip_user(participant['user_id'], "gold_bar_1", amount_per_user)
                success_count += 1
            except Exception:
                failed_count += 1
        
        # Build short response
        response = f"✅ Tipped {success_count} participants {amount_per_user}g each\n"
        response += f"💰 Spent: {success_count * amount_per_user}g"
        
        if failed_count > 0:
            response += f"\n⚠️ {failed_count} failed"
        
        return response
        
    except Exception as e:
        return f"❌ Failed to tip participants: {str(e)}"


async def check_wallet(bot: BaseBot, user: User) -> Optional[str]:
    """
    Check bot's wallet balance
    Usage: wallet
    """
    # Check if user is owner or VIP
    if user.id != bot.owner_id and user.id not in bot.vips:
        return "❌ Only the owner and VIPs can check the wallet."
    
    try:
        wallet_response = await bot.highrise.get_wallet()
        wallet = wallet_response.content
        
        # Wallet is a list of CurrencyItem objects
        bot_balance = 0
        if isinstance(wallet, list):
            for item in wallet:
                if hasattr(item, 'amount'):
                    bot_balance += item.amount
        else:
            bot_balance = wallet.amount if hasattr(wallet, 'amount') else 0
        
        return f"💰 Bot Wallet Balance: {bot_balance}g"
        
    except Exception as e:
        return f"❌ Failed to check wallet: {str(e)}"


async def tip_help(bot: BaseBot, user: User) -> Optional[str]:
    """Show tipping system help"""
    if user.id != bot.owner_id:
        return None
    
    return (
        "💰 **Tipping System Commands** (Owner Only - Whisper)\n\n"
        "**Tip Individual User:**\n"
        "• tip @username amount - Tip a specific user\n"
        "  Example: tip @john 50\n\n"
        "**Tip Multiple Users:**\n"
        "• tipall amount - Tip everyone in the room\n"
        "  Example: tipall 10\n\n"
        "• tipparticipants amount - Tip all registered participants\n"
        "  Example: tipparticipants 50\n\n"
        "**Check Balance:**\n"
        "• wallet - Check bot's gold balance\n\n"
        "**Limits:**\n"
        "• Single tip: Max 10,000g\n"
        "• Tipall: Max 1,000g per user\n"
        "• Participants: Max 5,000g per user\n\n"
        "💡 All commands are private via whisper!"
    )
