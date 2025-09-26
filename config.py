# Match Show Bot Configuration
# Edit these values to customize your bot

# Match Show settings
MATCH_PROMPT_INTERVAL = 30  # Minutes between public match prompts in room
BOT_NAME = "Match Show"  # Bot's display name

# Registration settings
MIN_AGE = 18  # Minimum age for registration
DEFAULT_HOSTS = ["coolbuoy"]  # Default host usernames

# MongoDB settings (can be overridden by environment variables)
# For MongoDB Atlas, set MONGODB_URI in your .env file to your connection string
# Example: mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority
MONGODB_URI = "mongodb://localhost:27017"  # Default local MongoDB URI (will be overridden by env variable)
MONGODB_DB_NAME = "MatchShowBot"  # Database name



# Bot responses and prompts
MATCH_PROMPTS = [
    "Looking for your perfect match? Send 'POP' or 'LOVE' to register for our Match Show! ❤️",
    "The Match Show is coming soon! Send 'POP' to register as a participant! 💞",
    "Looking for love? Send 'LOVE' to join our upcoming Match Show! 💘",
    "Don't miss out on finding your match! Register for the Match Show by sending 'POP' or 'LOVE'! �"
]

# Event settings
DEFAULT_EVENT_DATE = "Coming soon"  # Default event date message
REGISTRATION_FIELDS = ["name", "age", "occupation", "country", "type", "continent"]
REQUIRED_FIELDS = ["name", "age", "country", "continent"]

# Note: ROOM_ID and BOT_TOKEN are now read from environment variables (.env file)