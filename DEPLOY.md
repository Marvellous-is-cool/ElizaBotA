# 🚀 Render Deployment Guide

This guide will help you deploy your Birthday Bot to Render for 24/7 operation.

## 📋 Prerequisites

1. GitHub account
2. Render account (free tier available)
3. Your bot credentials (BOT_TOKEN and ROOM_ID)

## 🛠️ Step 1: Prepare Your Repository

1. **Push to GitHub:**

   ```bash
   git init
   git add .
   git commit -m "Initial birthday bot setup"
   git branch -M main
   git remote add origin https://github.com/yourusername/your-repo.git
   git push -u origin main
   ```

2. **Make sure these files are in your repo:**
   - ✅ `Procfile` - Tells Render how to run the bot
   - ✅ `requirements.txt` - Python dependencies
   - ✅ `runtime.txt` - Python version
   - ✅ `render.yaml` - Render configuration
   - ✅ `.gitignore` - Protects sensitive files

## 🔧 Step 2: Deploy to Render

### Option A: Using Render Dashboard (Recommended)

1. **Go to [render.com](https://render.com) and sign up/login**

2. **Create a New Web Service:**

   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your birthday bot repository

3. **Configure the Service:**

   ```
   Name: birthday-bot
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python run_simplified.py
   ```

4. **Set Environment Variables:**

   - Go to "Environment" section
   - Add `BOT_TOKEN` = your_bot_token_here
   - Add `ROOM_ID` = your_room_id_here

5. **Deploy:**
   - Click "Deploy Web Service"
   - Wait for deployment to complete

### Option B: Using Blueprint (Advanced)

1. **Fork this repository to your GitHub**
2. **Update render.yaml with your repo URL**
3. **Deploy via Blueprint:**
   - In Render dashboard, click "New +" → "Blueprint"
   - Paste your repository URL
   - Follow the prompts

## 📊 Step 3: Monitor Your Bot

1. **Check Logs:**

   - In Render dashboard → Your service → "Logs"
   - Look for "Birthday Bot activated! 🎉"

2. **Verify Bot is Online:**

   - Go to your Highrise room
   - The bot should join and send welcome message

3. **Test Commands:**
   - Try `!help` in the room
   - Test `!birthday` for romantic messages

## ⚙️ Step 4: Configuration

### Environment Variables in Render:

- `BOT_TOKEN` - Your Highrise bot token
- `ROOM_ID` - Your Highrise room ID

### Bot Settings (config.py):

- `BIRTHDAY_GIRL_USERNAME` - Birthday girl's username
- `PICKUP_LINE_INTERVAL_MINUTES` - How often to send messages
- `CUSTOM_PICKUP_LINES` - Add your own romantic messages

## 🔄 Auto-Deploy Setup

Render automatically redeploys when you push to your main branch:

```bash
# Make changes to your bot
git add .
git commit -m "Update pickup lines"
git push origin main
# Render will automatically redeploy!
```

## 💰 Render Pricing

- **Free Tier:** Perfect for bots (750 hours/month)
- **Paid Tier:** $7/month for always-on service
- **Recommendation:** Start with free tier

## 🛠️ Troubleshooting

### Bot Won't Start:

1. Check Render logs for errors
2. Verify environment variables are set correctly
3. Make sure BOT_TOKEN and ROOM_ID are correct

### Bot Goes Offline:

1. Free tier "sleeps" after 15 minutes of inactivity
2. Upgrade to paid tier for 24/7 operation
3. Or implement a keep-alive ping service

### Connection Issues:

1. Check if bot is invited to the room
2. Verify room ID is correct
3. Check bot token hasn't expired

## 🎉 Success!

Your birthday bot should now be running 24/7 on Render, sending romantic pickup lines every 2 minutes to Elizaabetta! 💕

## 📞 Support

If you encounter issues:

1. Check Render's documentation
2. Review the bot logs
3. Test locally first with `python run_simplified.py`
