# Highrise Matchmaking Bot

A matchmaking bot for Highrise that helps users find their perfect match in the virtual world. Built with Python, MongoDB Atlas, and the Highrise Bot SDK.

## Features

- **User Profile Management**: Users can create and update their matchmaking profiles
- **Matchmaking**: Find compatible matches based on profile information
- **Clothing Commands**: Equip and remove clothing items
- **Position Control**: Set the bot's position in the room
- **Persistent Storage**: All data stored in MongoDB Atlas

## Requirements

- Python 3.8+
- MongoDB Atlas account (or local MongoDB)
- Highrise Bot account

## Environment Setup

Create a `.env` file with the following variables:

```
PORT=6000
ROOM_ID=your_room_id
BOT_TOKEN=your_bot_token

# MongoDB Atlas connection string
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<dbname>?retryWrites=true&w=majority
MONGODB_DB_NAME=MatchBot
```

## Installation

1. Clone the repository
2. Install dependencies:

```
pip install -r requirements.txt
```

3. Set up your `.env` file with your credentials
4. Run the bot:

```
python run.py
```

## MongoDB Atlas Setup

1. Create a [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) account
2. Create a new cluster
3. Create a database user with read/write permissions
4. Get your connection string from the "Connect" button
5. Replace `<username>`, `<password>`, `<cluster>`, and `<dbname>` in the connection string
6. Add the connection string to your `.env` file

## Bot Commands

- `!match` - Find a potential match
- `!match profile` - Create/update your profile
- `!match view` - View your profile
- `!match history` - See your match history
- `!match help` - See all matchmaking commands
- `!equip <item_name>` - Equip a clothing item
- `!remove <category>` - Remove a clothing category
- `!set` - Set the bot's position (owner only)
- `!interval <minutes>` - Change match prompt frequency (owner only)

## Deployment Options

### Deploying to Render

1. Sign up for a [Render](https://render.com/) account
2. Create a new Web Service
3. Connect your GitHub repository
4. Set the build command to `pip install -r requirements.txt`
5. Set the start command to `python run.py`
6. Add your environment variables under "Environment"
7. Deploy the service

### Deploying to Vercel

> **Note**: Vercel is best for API or serverless functions, not long-running processes like bots.

For Vercel, we provide an API mode that allows health checks and webhook interactions:

1. Sign up for a [Vercel](https://vercel.com/) account
2. Install Vercel CLI: `npm install -g vercel`
3. Run `vercel` in the project directory
4. Add your environment variables in the Vercel dashboard
5. Deploy with `vercel --prod`

The Vercel deployment provides these endpoints:

- `/` - Health check
- `/api/status` - Bot status information
- `/api/webhook` - Webhook endpoint for external triggers (POST)

## Important Note about Vercel Deployment

Vercel is designed for serverless functions and does not support long-running processes like bots. The Vercel deployment provided in this repository offers API endpoints that can be used to check the bot's status and potentially trigger actions via webhooks.

**For running the actual bot process, we recommend using Render or another service that supports long-running processes.**

## License

MIT License
