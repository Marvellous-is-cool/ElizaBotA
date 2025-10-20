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
    Usage: tip @username amount OR !tip @username amount
    Example: tip @john 50 OR !tip @john 50
    """
    # Check if user is owner
    if user.id != bot.owner_id:
        return "❌ Owner only"
    
    # Parse command: tip @username amount (with or without !)
    pattern = r'^!?tip\s+@(\w+)\s+(\d+)$'
    match = re.match(pattern, message.lower().strip())
    
    if not match:
        return "❌ Usage: tip @user 50"
    
    target_username = match.group(1)
    amount = int(match.group(2))
    
    if amount <= 0:
        return "❌ Amount must be > 0"
    
    if amount > 10000:
        return "❌ Max 10,000g per tip"
    
    try:
        # Get room users to find the target
        room_users = (await bot.highrise.get_room_users()).content
        target_user = None
        
        for room_user, _ in room_users:
            if room_user.username.lower() == target_username.lower():
                target_user = room_user
                break
        
        if not target_user:
            return f"❌ @{target_username} not found"
        
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
            return f"❌ Not enough gold"
        
        # Map amount to correct tip type (Highrise uses specific tip types)
        # tip_user(user_id, tip_type) - tip_type contains the amount
        tip_type_map = {
            1: "gold_bar_1",
            5: "gold_bar_5", 
            10: "gold_bar_10",
            50: "gold_bar_50",
            100: "gold_bar_100",
            500: "gold_bar_500",
            1000: "gold_bar_1k",
            5000: "gold_bar_5k",
            10000: "gold_bar_10k"
        }
        
        if amount not in tip_type_map:
            return f"❌ Amount must be: 1, 5, 10, 50, 100, 500, 1k, 5k, or 10k"
        
        tip_type = tip_type_map[amount]
        
        # Send the tip (only 2 args: user_id and tip_type)
        await bot.highrise.tip_user(target_user.id, tip_type)
        
        # Send short confirmation to owner (whisper)
        return f"✅ Tipped @{target_user.username} {amount}g"
        
    except Exception as e:
        # Log the actual error for debugging
        print(f"❌ tip_user error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Return a short error with hint
        error_msg = str(e)
        if "gold_bar" in error_msg.lower():
            return "❌ Invalid gold type"
        elif "balance" in error_msg.lower() or "insufficient" in error_msg.lower():
            return "❌ Not enough gold"
        else:
            return f"❌ Error: {str(e)[:50]}"


async def tip_all_users(bot: BaseBot, user: User, message: str) -> Optional[str]:
    """
    Tip all users in the room
    Usage: tipall amount OR !tipall amount
    Example: tipall 10 OR !tipall 10
    """
    # Check if user is owner
    if user.id != bot.owner_id:
        return "❌ Owner only"
    
    # Parse command: tipall amount (with or without !)
    pattern = r'^!?tipall\s+(\d+)$'
    match = re.match(pattern, message.lower().strip())
    
    if not match:
        return "❌ Usage: tipall 10"
    
    amount_per_user = int(match.group(1))
    
    if amount_per_user <= 0:
        return "❌ Amount must be > 0"
    
    if amount_per_user > 1000:
        return "❌ Max 1000g per user"
    
    try:
        # Get all room users
        room_users = (await bot.highrise.get_room_users()).content
        
        # Filter out the bot itself
        users_to_tip = [room_user for room_user, _ in room_users if room_user.id != bot.bot_id]
        
        if not users_to_tip:
            return "❌ No users in room"
        
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
            return f"❌ Not enough gold"
        
        # Map amount to correct tip type
        tip_type_map = {
            1: "gold_bar_1",
            5: "gold_bar_5", 
            10: "gold_bar_10",
            50: "gold_bar_50",
            100: "gold_bar_100",
            500: "gold_bar_500",
            1000: "gold_bar_1k",
            5000: "gold_bar_5k",
            10000: "gold_bar_10k"
        }
        
        if amount_per_user not in tip_type_map:
            return f"❌ Amount must be: 1, 5, 10, 50, 100, 500, 1k, 5k, or 10k"
        
        tip_type = tip_type_map[amount_per_user]
        
        # Tip all users (limit response to avoid "message too long")
        success_count = 0
        failed_count = 0
        
        for room_user in users_to_tip:
            try:
                await bot.highrise.tip_user(room_user.id, tip_type)
                success_count += 1
            except Exception as e:
                print(f"Failed to tip {room_user.username}: {e}")
                failed_count += 1
        
        # Ultra-short response to avoid "message too long" error
        if failed_count > 0:
            return f"✅ {success_count} tipped | ⚠️ {failed_count} failed"
        else:
            return f"✅ Tipped {success_count} users {amount_per_user}g"
        
    except Exception as e:
        # Log the actual error for debugging
        print(f"❌ tip_all_users error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return f"❌ Error: {str(e)[:50]}"


async def tip_participants(bot: BaseBot, user: User, message: str) -> Optional[str]:
    """
    Tip all registered participants (POP or LOVE)
    Usage: tipparticipants amount OR !tipparticipants amount
    Example: tipparticipants 50 OR !tipparticipants 50
    """
    # Check if user is owner
    if user.id != bot.owner_id:
        return "❌ Owner only"
    
    # Parse command: tipparticipants amount (with or without !)
    pattern = r'^!?tipparticipants\s+(\d+)$'
    match = re.match(pattern, message.lower().strip())
    
    if not match:
        return "❌ Usage: tipparticipants 50"
    
    amount_per_user = int(match.group(1))
    
    if amount_per_user <= 0:
        return "❌ Amount must be > 0"
    
    if amount_per_user > 5000:
        return "❌ Max 5000g per user"
    
    try:
        # Check if database is available
        if not bot.db_client or not bot.db_client.is_connected:
            return "❌ DB not available"
        
        # Get all participants from database
        participants_collection = bot.db_client.db.participants
        participants = await participants_collection.find().to_list(length=None)
        
        if not participants:
            return "❌ No participants"
        
        # Get current room users
        room_users = (await bot.highrise.get_room_users()).content
        room_user_ids = {room_user.id for room_user, _ in room_users}
        
        # Filter participants who are currently in the room
        participants_in_room = [p for p in participants if p['user_id'] in room_user_ids]
        
        if not participants_in_room:
            return "❌ No participants in room"
        
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
            return f"❌ Not enough gold"
        
        # Map amount to correct tip type
        tip_type_map = {
            1: "gold_bar_1",
            5: "gold_bar_5", 
            10: "gold_bar_10",
            50: "gold_bar_50",
            100: "gold_bar_100",
            500: "gold_bar_500",
            1000: "gold_bar_1k",
            5000: "gold_bar_5k",
            10000: "gold_bar_10k"
        }
        
        if amount_per_user not in tip_type_map:
            return f"❌ Amount must be: 1, 5, 10, 50, 100, 500, 1k, 5k, or 10k"
        
        tip_type = tip_type_map[amount_per_user]
        
        # Tip all participants (avoid long messages)
        success_count = 0
        failed_count = 0
        
        for participant in participants_in_room:
            try:
                await bot.highrise.tip_user(participant['user_id'], tip_type)
                success_count += 1
            except Exception as e:
                print(f"Failed to tip participant {participant.get('username', 'unknown')}: {e}")
                failed_count += 1
        
        # Ultra-short response
        if failed_count > 0:
            return f"✅ {success_count} tipped | ⚠️ {failed_count} failed"
        else:
            return f"✅ Tipped {success_count} participants {amount_per_user}g"
        
    except Exception as e:
        # Log the actual error for debugging
        print(f"❌ tip_participants error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return f"❌ Error: {str(e)[:50]}"


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
