from bot.bot import HighriseBot as Bot

# Import necessary modules to maintain backward compatibility
from highrise import BaseBot, __main__, CurrencyItem, Item, Position, AnchorPosition, SessionMetadata, User
from highrise.__main__ import BotDefinition
from asyncio import run as arun
import asyncio
import os
from highrise.models import *
from highrise.webapi import *
from getItems import getclothes, getCommands
from functions.play import play, end, soon, is_game_active
# from webserver import keep_alive
from aiohttp.client_exceptions import ClientConnectionError, ClientConnectorError, ClientConnectionResetError
import importlib.util
from json import load, dump


emotesava = [
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
    "idle-dance-tiktok4"
]

vip_users = [
  "User_taken2"
]

commds = [
    'allemo',
    'emo',
    'emote',
    'equip',
    'funfact',
    'remove',
    'userinfo',
    'loop',
    'teleport',
    'stop',
    'kick',
    'move',
    'commands',
    'bot commands',
    '!allemo',
    'everyemo',
    'categories',
]


class Bot(BaseBot):

  def __init__(self):
    super().__init__()
    self.bot_id = None
    self.owner_id = None
    self.bot_status = False
    self.tip_data = {}
    self.load_tip_data()
    self.bot_position = None
    self.dice_interval = 3  # default
    self.dice_task = None


  async def on_chat(self, user: User, message: str) -> None:
    try:
        response = await self.command_handler(user.id, message)
        if response:
            await self.highrise.chat("Room users fetched successfully.")
        lowerMsg = message.lower()
        
        # Add error handling around this API call
        try:
            response = await self.highrise.get_room_users()
            if hasattr(response, 'content'):
                if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
                    roomUsers = response.content
                else:
                    await self.highrise.chat("Failed to fetch room users.")
                    return
            else:
                await self.highrise.chat("Failed to fetch room users.")
                return
        except (ClientConnectionResetError, ClientConnectorError, ClientConnectionError) as e:
            print(f"Connection error in get_room_users: {e}")
            # Could attempt to reconnect here, but for now just inform the user
            await self.highrise.chat("Connection error while fetching room users. Please try again.")
            return
        except Exception as e:
            print(f"Unexpected error in get_room_users: {e}")
            await self.highrise.chat("An error occurred while fetching room users.")
            return

        # Proceed with the rest of your command handling
        # ...existing code...
    except (ClientConnectionResetError, ClientConnectorError, ClientConnectionError) as e:
        print(f"Connection error in on_chat: {e}")
        # Connection issues - could implement a reconnection strategy here
    except Exception as e:
        print(f"Unexpected error in on_chat: {e}")
        # Log the error but don't crash

    if lowerMsg.startswith("!door"):
      await self.highrise.teleport(user_id=user.id,
                                   dest=Position(float(0), float(0), float(0)))

    if lowerMsg.startswith("!vips"):
      vipsinstr = ''

      for vip in vip_users:
        vipsinstr += f"{vip} \n"

      await self.highrise.chat(f"Here are the vips: \n {vipsinstr} ")

    if lowerMsg.startswith("!addvip"):
      if user.username != "coolbuoy":
        await self.highrise.chat("You do not have permission to do this")
        return
      #separete message into parts
      parts = message.split()
      #check if message is valid "kick @username"
      if len(parts) != 2:
        await self.highrise.chat(
            "Invalid add vip command format. use !addvip <username>")
        return
      #checks if there's a @ in the message
      if "@" not in parts[1]:
        username = parts[1]
      else:
        username = parts[1][1:]
      #add user to vip
      try:
        vip_users.append(username)
        await self.highrise.chat(
            f"{username} has been added to one of the vips")
      except Exception as e:
        await self.highrise.chat(f"{e}")
        return
        #send message to chat
        await self.highrise.chat(
            f"{username} has been added to one of the vips")

    # --- Improved VIP teleport logic ---
    if lowerMsg.startswith("!teleport"):
      is_vip = user.id == self.owner_id or user.username == "coolbuoy" or user.username in vip_users
      if not is_vip:
        await self.highrise.chat(
            f"You are not a VIP. Only VIPs are authorized to use the teleporter."
        )
        return
      try:
        command, username, coordinate = lowerMsg.split(" ")
      except:
        await self.highrise.chat(
            "Incorrect format, please use !teleport <username> <x,y,z>")
        return
      response = await self.highrise.get_room_users()
      if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
        room_users = response.content
      else:
        await self.highrise.chat("Failed to fetch room users.")
        return
      user_id = None
      for room_user, pos in room_users:
        if room_user.username.lower() == username.lower():
          user_id = room_user.id
          break
      if user_id is None:
        await self.highrise.chat(
            "User not found, please specify a valid user and coordinate")
        return
      try:
        x, y, z = coordinate.split(",")
      except:
        await self.highrise.chat(
            "Coordinate not found or incorrect format, use x,y,z")
        return
      await self.highrise.teleport(user_id=user_id,
                                   dest=Position(float(x), float(y),
                                                 float(z)))
   
    # --- Improved VIP teleport logic for host platform ---
    if lowerMsg.startswith("!tele host"):
        is_vip = user.id == self.owner_id or user.username == "coolbuoy" or user.username in vip_users
        if not is_vip:
            await self.highrise.chat(
                f"You are not a VIP. Only VIPs are authorized to use the teleporter."
            )
            return
        try:
            # Teleport the command caller directly to host platform
            await self.highrise.teleport(
                user_id=user.id,
                dest=Position(float(2), float(9.5), float(0))
            )
        except Exception as e:
            await self.highrise.chat(f"Teleport error: {e}")
    
    # --- Improved VIP teleport logic ---
    if lowerMsg.startswith("!pos"):
      is_vip = user.id == self.owner_id or user.username == "coolbuoy" or user.username in vip_users
      if not is_vip:
        await self.highrise.chat(
            f"You are not a VIP. Only VIPs are authorized to use the teleporter."
        )
        return
      try:
        command, username = lowerMsg.split(" ")
      except:
        await self.highrise.chat(
            "Incorrect format, please use !pos <username>")
        return
      response = await self.highrise.get_room_users()
      if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
        room_users = response.content
      else:
        await self.highrise.chat("Failed to fetch room users.")
        return
      user_id = None
      for room_user, pos in room_users:
        if room_user.username.lower() == username.lower():
          user_id = room_user.id
          break
      if user_id is None:
        await self.highrise.chat(
            "User not found, please specify a valid user and coordinate")
        return
      await self.highrise.teleport(user_id=user_id,
                                   dest=Position(float(11), float(0),
                                                 float(29)))

    if message.startswith("kick"):
      if user.username != "coolbuoy":
        await self.highrise.chat("You do not have permission to do this")
        return
      #separete message into parts
      parts = message.split()
      #check if message is valid "kick @username"
      if len(parts) != 2:
        await self.highrise.chat("Invalid kick command format.")
        return
      #checks if there's a @ in the message
      if "@" not in parts[1]:
        username = parts[1]
      else:
        username = parts[1][1:]
      #check if user is in room
      response = await self.highrise.get_room_users()
      if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
          room_users = response.content
      else:
          await self.highrise.chat("Failed to fetch room users.")
          return
      user_id = None
      for room_user, pos in room_users:
        if room_user.username.lower() == username.lower():
          user_id = room_user.id
          break
      if user_id is None:
        await self.highrise.chat(
            "User not found, please specify a valid user and coordinate")
        return
      #kick user
      try:
        await self.highrise.moderate_room(user_id, "kick")
      except Exception as e:
        await self.highrise.chat(f"{e}")
        #send message to chat
        return
      await self.highrise.chat(f"{username} has been kicked out of the room.")

    # --- Loop emote for another user: !loop <emote> <username> ---
    if lowerMsg.startswith("!loop"):
        try:
            parts = message.split()
            if len(parts) == 2:
                # !loop <emote> (self loop)
                emote_name = parts[1]
                await send_specific_emote_periodically(self, user, emote_name)
            elif len(parts) == 3:
                # !loop <emote> <username>
                emote_name = parts[1]
                target_username = parts[2].lstrip("@")
                # Prevent looping on owner or VIPs
                if target_username.lower() == self.owner_id or target_username.lower() == "coolbuoy" or target_username.lower() in [vip.lower() for vip in vip_users]:
                    await self.highrise.chat("You cannot loop emotes on the owner or VIPs.")
                    return
                # Find target user in room
                room_users_resp = await self.highrise.get_room_users()
                target_user = None
                if hasattr(room_users_resp, "content"):
                    for room_user, _ in room_users_resp.content:
                        if room_user.username.lower() == target_username.lower():
                            target_user = room_user
                            break
                if not target_user:
                    await self.highrise.chat(f"User '{target_username}' not found in the room.")
                    return
                await send_specific_emote_periodically(self, user, emote_name, target_user=target_user)
            else:
                await self.highrise.chat("Usage: !loop <emote> [username]")
        except Exception as e:
            await self.highrise.chat(f"Error: {str(e)}")
        return

    # --- Stop emote for another user: !stop <username> ---
    if lowerMsg.startswith("!stop"):
        try:
            parts = message.split()
            if len(parts) == 1:
                # !stop (self stop)
                await stop_emote_task(self, user)
            elif len(parts) == 2:
                # !stop <username>
                target_username = parts[1].lstrip("@")
                # Prevent stopping owner or VIPs
                if target_username.lower() == self.owner_id or target_username.lower() == "coolbuoy" or target_username.lower() in [vip.lower() for vip in vip_users]:
                    await self.highrise.chat("You cannot stop emotes for the owner or VIPs.")
                    return
                await stop_emote_task_by_username(self, target_username)
            else:
                await self.highrise.chat("Usage: !stop [username]")
        except Exception as e:
            await self.highrise.chat(f"Error: {str(e)}")
        return

    if lowerMsg.startswith("stop"):
      await stop_emote_task(self, user)

    if message.lstrip().startswith(("!fight", "!hug", "!flirt")):
      response = await self.highrise.get_room_users()
      if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
          users = [content[0] for content in response.content]
      else:
          await self.highrise.chat("Failed to fetch room users.")
          return
      usernames = [user.username.lower() for user in users]
      parts = message[1:].split()
      args = parts[1:]

      if len(args) < 1:
        await self.highrise.send_whisper(user.id,
                                         f"Usage: !{parts[0]} <@username>")
        return
      elif args[0][0] != "@":
        await self.highrise.send_whisper(
            user.id, f"Invalid user format. Please use '@username'.")
        return
      elif args[0][1:].lower() not in usernames:
        await self.highrise.send_whisper(user.id,
                                         f"{args[0][1:]} is not in the room.")
        return

      user_id = next(
          (u.id for u in users if u.username.lower() == args[0][1:].lower()),
          None)
      if not user_id:
        await self.highrise.send_whisper(user.id,
                                         f"User {args[0][1:]} not found")
        return

      try:
        if message.startswith("!fight"):
          await self.highrise.chat(
              f"\n🥷 @{user.username} And @{args[0][1:]} Fighting Each Other, let's see who breaks a tooth"
          )
          await self.highrise.send_emote("emote-swordfight", user.id)
          await self.highrise.send_emote("emote-swordfight", user_id)
        elif message.startswith("!hug"):
          await self.highrise.chat(
              f"\n🫂 @{user.username} And @{args[0][1:]} Hugging Each Other❤️")
          await self.highrise.send_emote("emote-hug", user.id)
          await self.highrise.send_emote("emote-hug", user_id)
        elif message.startswith("!flirt"):
          await self.highrise.chat(
              f"\n Hey @{user.username} And @{args[0][1:]} Flirting Each Other 😏❤️"
          )
          await self.highrise.send_emote("emote-lust", user.id)
          await self.highrise.send_emote("emote-lust", user_id)
      except Exception as e:
        await self.highrise.chat(
            f"An exception occurred[Due To {parts[0][1:]}]: {e}")

    for emotename in emotesava:
      try:
        if lowerMsg.startswith(f"{emotename.rsplit('-', 1)[-1]}"):
          await self.highrise.send_emote(emotename, user.id)
        if lowerMsg.startswith(f"{emotename.rsplit('-', 1)[-1]} all"):
          for roomUser, _ in roomUsers:
            await self.highrise.send_emote(emotename, roomUser.id)
      except Exception as e:
        await self.highrise.chat(f"An Error Occured: {e}")

    # Add play/end/soon command handling for owner
    if lowerMsg.startswith("!play") and user.id == self.owner_id:
        await play(self, user, message)
        return
    if lowerMsg.startswith("!end") and user.id == self.owner_id:
        await end(self, user, message)
        return
    if lowerMsg.startswith("!soon") and user.id == self.owner_id:
        await soon(self, user, message)
        return

  async def on_emote(self, user: User, emote_id: str,
                     receiver: User | None) -> None:
    pass

  async def on_whisper(self, user: User, message: str) -> None:
    response = await self.command_handler(user.id, message)
    if response:
      try:
        await self.highrise.send_whisper(user.id, response)
      except Exception as e:
        await self.highrise.chat(f"Whisper Error: {e}")

  async def on_message(self, user_id: str, conversation_id: str,
                       is_new_conversation: bool) -> None:
    response = await self.highrise.get_messages(conversation_id)
    message = ""  # Initialize message with a default value
    if isinstance(response, GetMessagesRequest.GetMessagesResponse):
      message = response.messages[0].content
    user = None
    try:
      # Fetch user object for permission checks
      room_users_resp = await self.highrise.get_room_users()
      if isinstance(room_users_resp, GetRoomUsersRequest.GetRoomUsersResponse):
        user_tuple = next((u for u in room_users_resp.content if u[0].id == user_id), None)
        if user_tuple:
          user = user_tuple[0]
      if message.lower() == "!equip help" or message.lower() == "equip":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id, f"Equip Help 🆘: {getclothes('help')}")
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry, you don't have access to this command")

      elif message.lower() == "eq h":
        response = await self.highrise.get_room_users()
        if isinstance(response, GetRoomUsersRequest.GetRoomUsersResponse):
            user_tuple = next((u for u in response.content if u[0].id == user_id), None)
            if user_tuple:
              user = user_tuple[0]
            else:
              user = None
        else:
            await self.highrise.chat("Failed to fetch room users.")
            user = None
        if not user:
          await self.highrise.send_message(
              conversation_id,
              "User information could not be retrieved.")
          return
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Hairs 👱‍♂️: {getclothes('hair')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <hairname> in the room to equip / !remove <hairname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq t":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Shirts 🎽: {getclothes('top')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <topname> in the room to equip / !remove <topname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq p":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Pants 👖: {getclothes('pant')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <pantname> in the room to equip / !remove <pantname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq s":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Skirts 🩳: {getclothes('skirt')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <skirtname> in the room to equip / !remove <skirtname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq sh":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Shoes 👟: {getclothes('shoe')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <shoename> in the room to equip / !remove <shoename> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq b":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Back hair 👱‍♂️:'Short Short Fro', 'Box Braids', 'Long Undercut Dreads', 'Undercut Dreads', 'Side Swept Fro', 'Long Buzzed Fro', 'Short Buzzed Fro', 'Curly Undercut', 'Tight Curls', 'Loose Curls', 'Shaggy Curls', 'Short Curls', 'Medium Wavy Cut', 'Short Wavy Cut', 'Wavy Undercut', 'Wavy Side Part', 'Shaggy Side Part', 'Combed Back Waves', 'Blown Back Waves', 'Short Straight', 'Side Combed Straight', 'Straight Slicked Back', 'Buzz Cut', 'Shaggy Crew Cut', 'Faux Hawk', 'Shaggy Straight', 'Straight Side Part', 'Combed Back Undercut', 'Upward Swoosh', 'Side Swept Undercut', 'Side Swept', 'Crew Cut', 'Over Shoulder Wavy Short', 'Over Shoulder Wavy Long', 'Over Shoulder Straight Short', 'Over Shoulder Straight Bangs', 'Over Shoulder Straight Long', 'Over Shoulder Pony', 'Over Shoulder Curly', 'Over Shoulder Coily', 'Over Shoulder Braid'"
          )
          await self.highrise.send_message(
              conversation_id,
              f"\n'Wavy Long Bob', 'Sweet Curl Waves', 'Poofy Bob', 'Short Beach Waves', 'Long Beach Waves', 'Long Glamour Waves', 'Chunky Waves', 'Wavy Short', 'Wavy Medium', 'Wavy Low Pony', 'Wavy High Pony', 'Wavy Pixie', 'Wavy Long', 'Top Knot Back', 'Straight Short Low Pigtails', 'Straight Short High Pigtails', 'Straight Short', 'Straight Medium', 'Straight Low Pony', 'Straight Long Low Pigtails', 'Straight Long', 'Straight High Pony', 'Straight Pixie', 'Sleek Straight Pony', 'Sleek Straight Medium', 'Sleek Straight Long', 'Sleek Straight Short', 'Bettie Waves', 'Marilyn Curls', 'Loose Coily Short', 'Loose Coily Medium', 'Loose Coily Long', 'Long Wavy Half Bun', 'Half Pony', 'Dreads Medium', 'Dreads Low Pony', 'Dreads Long', 'Dreads High Pony', 'Dreads Extra Short', 'Dreads Short', 'Double Top Knots Back', 'Low Double Buns', 'Curly Short Low Pigtails', 'Curly Short High Pigtails', 'Curly No Bangs Back', 'Curly Medium', 'Curly Low Pony', 'Curly Long High Pigtails', 'Curly Long', 'Curly High Pony', 'Curly Pixie', 'Coily Short', 'Coily Pinapple Hair', 'Coily Medium', 'Coily Low Pony', 'Coily Long', 'Coily High Pony', 'Bald', 'Low Bun', 'High Bun', 'Afro Short', 'Afro Pom Poms Back', 'Afro Medium', 'Afro Long', 'Afro High Pony'"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq so":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Sock 🧦: {getclothes('sock')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <sockname> in the room to equip / !remove <sockname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq a":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Accesories 🧣: {getclothes('assec')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <assessoriesname> in the room to equip / !remove <assessoriesname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")
        # new ones
      elif message.lower() == "eq fh":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Face hairs 👱‍♀️: {getclothes('face')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <facehairname> in the room to equip / !remove <facehairname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq eb":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Eyebrows 👁‍🗨: {getclothes('eyebrow')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <eyebrowname> in the room to equip / !remove <eyebrowname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq e":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Eyes 👁: {getclothes('eye')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <eyename> in the room to equip / !remove <eyename> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq n":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Noses 👃: {getclothes('nose')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <nosename> in the room to equip / !remove <nosename> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq m":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Mouth 👄: {getclothes('mouth')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <mouthname> in the room to equip / !remove <mouthname> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "eq fr":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"Here are the list of Freckles ☺: {getclothes('freckle')}")
          await self.highrise.send_message(
              conversation_id,
              f"\n\nUsage ⌨: Type !equip <frecklename> in the room to equip / !remove <frecklename> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id,
              f"Sorry {user.username}, you don't have access to this command")

      elif message.lower() == "evemo":
        if user_id == self.owner_id:
          await self.highrise.send_message(
              conversation_id,
              f"All emotes 👯‍♂️ : 'sit-idle-cute'  'idle_zombie'  'idle_layingdown2'  'idle_layingdown'  'idle-sleep'  'idle-sad'  'idle-posh'  'idle-loop-tired'  'idle-loop-tapdance'  'idle-loop-sitfloor'  'idle-loop-shy'  'idle-loop-sad'  'idle-loop-happy'  'idle-loop-annoyed'  'idle-loop-aerobics'  'idle-lookup'  'idle-hero'  'idle-floorsleeping2'  'idle-floorsleeping'  'idle-enthusiastic'  'idle-dance-swinging'  'idle-dance-headbobbing'  'idle-angry'  'emote-yes'  'emote-wings'  'emote-wave'  'emote-tired'  'emote-think'  'emote-theatrical'  'emote-tapdance'  'emote-superrun'  'emote-superpunch 'emote-sumo'  'emote-suckthumb'  'emote-splitsdrop'  'emote-snowball'  'emote-snowangel'  'emote-shy'  'emote-secrethandshake'  'emote-sad'  'emote-ropepull'  'emote-roll'  'emote-rofl'  'emote-robot'  'emote-rainbow'  'emote-proposing'  'emote-peekaboo'  'emote-peace'  'emote-panic'  'emote-no'  'emote-ninjarun'  'emote-nightfever'  'emote-monster_fail'  'emote-model'  'emote-lust'  'emote-levelup'  'emote-laughing2'  'emote-laughing'  'emote-kiss'  'emote-kicking'  'emote-jumpb'  'emote-judochop'  'emote-jetpack'  'emote-hugyourself"
          )
          await self.highrise.send_message(
              conversation_id,
              f"'emote-hot'  'emote-hero'  'emote-hello'  'emote-headball'  'emote-harlemshake'  'emote-happy'  'emote-handstand'  'emote-greedy'  'emote-graceful'  'emote-gordonshuffle' 'emote-ghost-idle'  'emote-gangnam'  'emote-frollicking'  'emote-fainting'  'emote-fail2'  'emote-fail1'  'emote-exasperatedb'  'emote-exasperated'  'emote-elbowbump'  'emote-disco'  'emote-disappear'  'emote-deathdrop'  'emote-death2'  'emote-death'  'emote-dab'  'emote-curtsy'  'emote-confused'  'emote-cold'  'emote-charging'  'emote-bunnyhop'  'emote-bow'  'emote-boo'  'emote-baseball'  'emote-apart'  'emoji-thumbsup'  'emoji-there'  'emoji-sneeze'  'emoji-smirking'  'emoji-sick'  'emoji-scared'  'emoji-punch'  'emoji-pray'  'emoji-poop'  'emoji-naughty'  'emoji-mind-blown'  'emoji-lying'  'emoji-halo'  'emoji-hadoken'  'emoji-give-up'  'emoji-gagging'  'emoji-flex'  'emoji-dizzy'  'emoji-cursing'  'emoji-crying'  'emoji-clapping'  'emoji-celebrate'  'emoji-arrogance'  'emoji-angry'  'dance-voguehands'  'dance-tiktok8'  'dance-tiktok2'  'dance-spiritual'  'dance-smoothwalk'  'dance-singleladies'  'dance-shoppingcart'  'dance-russian'  'dance-robotic'  'dance-pennywise'  'dance-orangejustice'  'dance-metal'  'dance-martial-artist'  'dance-macarena'  'dance-handsup'  'dance-floss'  'dance-duckwalk'  'dance-breakdance'  'dance-blackpink'  'dance-aerobics'"
          )
          await self.highrise.send_message(
              conversation_id,
              f"\n\nHere are the lists of all emotes in the normal emote name, useful for when you want to buy emotes for your bot that users can use [use !buy <itemname> in room to buy any of the unavailable ones].. To see emotes available for use instead, enter !allemo "
          )
          await self.highrise.send_message(
              conversation_id,
              f"\n\nEnter the last word of any of these emote in the room to check if they are free/available e.g to use the 'emoji-flex', type flex in the room \n\n To buy unavailale ones !equip <emotename> in the room to equip / !remove <emotename> in the room to remove \n Note that the names are case sensitive"
          )
        else:
          await self.highrise.send_message(
              conversation_id, f"Sorry, you don't have access to this command")

      elif message.lower().startswith("help"):
        await self.highrise.send_message(
            conversation_id,
            f"Good day ☺, what can i help you with? : {getCommands('help')}")

      elif message.lower() in commds:
        await self.highrise.send_message(
            conversation_id, f"{getCommands(f'{message.lower()}')}")

      elif message.lower().startswith("hi"):
        await self.highrise.send_message(
            conversation_id,
            "Hey, How's your day? ☺ \nTo show you list of available options, type help"
        )

      else:
        await self.highrise.send_message(
            conversation_id,
            f"I can't understand your message, type help for further assistance.."
        )

    except Exception as e:
      await self.highrise.send_message(
          conversation_id,
          f"Sorry, i can't fetch the response for you.. \n Kindly contact @coolbuoy with error code: msg281 if error persists \n\n 📛Error Message {e}"
      )

  # Handle commands from any source (chat/whisper/message)
  async def command_handler(self, user_id, message: str):
    command = message.lower().strip()
    
    if command.startswith("!set"):
        if user_id != self.owner_id:
            await self.highrise.chat("❌ Only the room owner can use this command.")
            return None
        try:
            result = await self.set_bot_position(user_id)
            if result:
                await self.highrise.chat(f"✅ {result}")
            else:
                await self.highrise.chat("❌ Failed to set bot position.")
        except Exception as e:
            await self.highrise.chat(f"❌ Set Error: {e}")
            print(f"Set command error: {e}")
        return None
        
    elif command.startswith("!top"):
      if user_id != self.owner_id:  # Only listen to host's commands
        return  # Build a 10 top tippers leaderboard
      top_tippers = self.get_top_tippers()
      formatted_tippers = []
      for i, (user_id, user_data) in enumerate(top_tippers):
        username = user_data['username']
        total_tips = user_data['total_tips']
        formatted_tippers.append(f"{i + 1}. {username} ({total_tips}g)")

      tipper_message = '\n'.join(formatted_tippers)
      return f"Top Tippers:\n{tipper_message}"
    elif command.startswith("!get "):
      if user_id != self.owner_id:  # Only listen to host's commands
        return  # Query a specific user's tips
      username = command.split(" ", 1)[1].replace("@", "")
      tip_amount = self.get_user_tip_amount(username)
      if tip_amount is not None:
        return f"{username} se ha inclinado {tip_amount}g"
      else:
        return f"{username} no se ha volcado."
    elif command.startswith("!wallet"):
      if user_id != self.owner_id:  # Only listen to host's commands
        return  # Get Bot wallet gold
      wallet = await self.highrise.get_wallet()
      for currency in wallet.content:
        if currency.type == 'gold':
          gold = currency.amount
          return f"Tengo {gold}g en mi billetera."
      return "No hay oro en la billetera."

    parts = message.split(" ")
    command = parts[0][1:]
    functions_folder = "functions"
    # Check if the function exists in the module
    for file_name in os.listdir(functions_folder):
      if file_name.endswith(".py"):
        module_path = None
        module_name = file_name[:-3]  # Remove the '.py' extension

        if os.path.isfile(os.path.join(functions_folder, file_name)):
          module_path = os.path.join(functions_folder, file_name)
        

        if module_path:
          try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check if the function exists in the module
            if hasattr(module, command) and callable(getattr(module, command)):
              function = getattr(module, command)
              await function(self, user_id, message)
              return  # Exit the loop if a matching function is found
          except Exception as e:
            await self.highrise.chat(
                f"Error loading module {module_name}: {str(e)}")

    # If no matching function is found
    return

  async def on_tip(self, sender: User, receiver: User,
                   tip: CurrencyItem | Item) -> None:
    if isinstance(tip, CurrencyItem):
      await self.highrise.chat(
          f"{sender.username} tipped {tip.amount}g -> {receiver.username}")
      if receiver.id == self.bot_id:
        if sender.id not in self.tip_data:
          self.tip_data[sender.id] = {
              "username": sender.username,
              "total_tips": 0
          }

        self.tip_data[sender.id]['total_tips'] += tip.amount
        self.write_tip_data(sender, tip.amount)

        if tip.amount >= 100:
          await self.highrise.chat(
              f"{sender.username} Tipped  {tip.amount} for VIP. Teleporting now..."
          )
          #teleports the user to the specified coordinate
          await self.highrise.teleport(user_id=sender.id,
                                       dest=Position(float(15), float(9.1),
                                                     float(12)))

  async def on_user_join(self, user: User,
                         position: Position | AnchorPosition) -> None:
    if user.username == "coolbuoy":
      await self.highrise.react("wave", user.id)
      await self.highrise.chat(
        f"Welcome boss! The coolestkid reporting here..... I am your special bot made by you. We have gathered here today to play what? BINGO!!!!!!!!!!!!!")
      
    # Else - regular welcome
    else:
       await self.highrise.react("wave", user.id)
       
       # Change welcome message based on game state
       await self.highrise.chat(
            f"Welcome {user.username}, to the COOLIANS WELCOME PARTY!!! We are the coolest crew you can ever meet. Enjoy your stay and have fun! 🎉"
           )

  async def on_user_leave(self, user: User) -> None:
    await self.highrise.chat(
        f"{user.username} left, we hope {user.username} had a good time btw..."
    )

  async def on_start(self, session_metadata: SessionMetadata) -> None:
    self.bot_id = session_metadata.user_id
    self.owner_id = session_metadata.room_info.owner_id
    self.bot_status = True  # Set status first
    
    # Then place the bot
    await self.place_bot()
    
    await self.highrise.chat("What a good day be ACTIVE! haha 🤣")
    # print("started...")

  # Return the top 10 tippers
  def get_top_tippers(self):
    if not self.tip_data:
        return []
    sorted_tippers = sorted(self.tip_data.items(),
                            key=lambda x: x[1]['total_tips'],
                            reverse=True)
    return sorted_tippers[:10]

  # Return the amount a particular username has tipped
  def get_user_tip_amount(self, username):
    for _, user_data in self.tip_data.items():
      if user_data['username'].lower() == username.lower():
        return user_data['total_tips']
    return None

  # Place bot on start
  async def place_bot(self):
    # Wait for bot to be ready, but with a timeout
    timeout_counter = 0
    while self.bot_status is False and timeout_counter < 20:  # 10 second timeout
        await asyncio.sleep(0.5)
        timeout_counter += 1
    
    if not self.bot_status:
        print("Bot status not ready, skipping position placement")
        return
    
    try:
        self.bot_position = self.get_bot_position()
        # Check if position is not the default (0, 0, 0)
        if (self.bot_position.x != 0 or self.bot_position.y != 0 or self.bot_position.z != 0):
            await self.highrise.teleport(self.bot_id, self.bot_position)
            print(f"Bot placed at saved position: {self.bot_position}")
        else:
            print("Bot using default position")
    except Exception as e:
        print(f"Error placing bot at startup: {e}")
        await self.highrise.chat(f"Error with starting position: {e}")

  # Write tip event to file
  def write_tip_data(self, user: User, tip: int) -> None:
    with open("./data.json", "r+") as file:
      data = load(file)
      user_data = data["users"].get(user.id, {
          "total_tips": 0,
          "username": user.username
      })
      user_data["total_tips"] += tip
      user_data["username"] = user.username
      data["users"][user.id] = user_data
      file.seek(0)
      dump(data, file)
      file.truncate()

  # Set the bot position at player's location permanently
  async def set_bot_position(self, user_id) -> str:
    try:
        # Get room users
        room_users_response = await self.highrise.get_room_users()
        if not isinstance(room_users_response, GetRoomUsersRequest.GetRoomUsersResponse):
            return "Failed to get room users."
        
        # Find the user's position
        user_position = None
        for room_user, pos in room_users_response.content:
            if user_id == room_user.id:
                if isinstance(pos, Position):
                    user_position = pos
                    break
        
        if user_position is None:
            return "Could not find your position in the room."
        
        # Save position to file
        try:
            with open("./data.json", "r+") as file:
                data = load(file)
                data["bot_position"] = {
                    "x": user_position.x,
                    "y": user_position.y,
                    "z": user_position.z,
                    "facing": user_position.facing
                }
                file.seek(0)
                dump(data, file)
                file.truncate()
        except Exception as e:
            return f"Failed to save position to file: {e}"
        
        # Teleport bot to the position
        try:
            # Create a slightly offset position to avoid collision
            set_position = Position(
                user_position.x, 
                user_position.y + 0.0000001,
                user_position.z,
                facing=user_position.facing
            )
            
            # Teleport to offset position first
            await self.highrise.teleport(self.bot_id, set_position)
            # Then to exact position
            await self.highrise.teleport(self.bot_id, user_position)
            
            # Update bot's stored position
            self.bot_position = user_position
            
            return f"Bot position updated to ({user_position.x:.1f}, {user_position.y:.1f}, {user_position.z:.1f})"
            
        except Exception as e:
            return f"Failed to teleport bot: {e}"
            
    except Exception as e:
        print(f"Error in set_bot_position: {e}")
        return f"Error setting bot position: {e}"
      
  # Load tip data on start
  def load_tip_data(self) -> None:
    with open("./data.json", "r") as file:
      data = load(file)
      self.tip_data = data["users"]

  # Load bot position from file
  def get_bot_position(self) -> Position:
    with open("./data.json", "r") as file:
      data = load(file)
      pos_data = data["bot_position"]
      return Position(pos_data["x"], pos_data["y"], pos_data["z"],
                      pos_data["facing"])

  async def run_bot(self, room_id, api_key) -> None:
    asyncio.create_task(self.place_bot())
    definitions = [BotDefinition(self, room_id, api_key)]
    await __main__.main(definitions)


# Automatically create json file if not exists
def data_file(filename: str, default_data: str = "{}") -> None:
  if not os.path.exists(filename):
    with open(filename, 'w') as file:
      file.write(default_data)


DEFAULT_DATA = '{"users": {}, "bot_position": {"x": 0, "y": 0, "z": 0, "facing": "FrontRight"}}'
data_file("./data.json", DEFAULT_DATA)

# To run the bot directly (without Flask keep-alive), use:
#   python main.py
# This is recommended for local development and debugging.

# Uncomment below to enable direct execution:
if __name__ == "__main__":
  import os
  from dotenv import load_dotenv
  load_dotenv()
  ROOM_ID = os.getenv("ROOM_ID")
  API_KEY = os.getenv("BOT_TOKEN")
  arun(Bot().run_bot(ROOM_ID, API_KEY))
