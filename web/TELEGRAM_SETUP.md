# Telegram Notification Setup Guide

This guide explains how to set up Telegram notifications for vehicle tracking alerts.

## Overview

When a vehicle's 30-second timer expires (no detection for 30 seconds), the system automatically sends a Telegram notification to the registered vehicle owner with:
- Vehicle last seen location
- Google Maps link
- Location pin on map

## Prerequisites

1. A Telegram account
2. A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
3. Your Telegram Chat ID

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Step 2: Get Your Telegram Chat ID

### Method 1: Using @userinfobot
1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Start a conversation with it
3. It will reply with your chat ID (a number like `123456789`)

### Method 2: Using @getidsbot
1. Search for [@getidsbot](https://t.me/getidsbot) on Telegram
2. Start a conversation
3. It will show your chat ID

### Method 3: Programmatically
1. Start a chat with your bot
2. Send any message to your bot
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":123456789}` in the response

## Step 3: Configure Environment Variables

Create a `.env` file in the `web/` directory or set environment variables:

```bash
# Enable Telegram notifications
TELEGRAM_ENABLED=true

# Your Telegram Bot Token (from BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

Or export them before running the server:

```bash
export TELEGRAM_ENABLED=true
export TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## Step 4: Run Database Migration

If the database already exists, run the migration script to add the `telegram_chat_id` column:

```bash
cd web
python3 migrate_add_telegram.py
```

If the database doesn't exist, it will be created automatically with the new schema when you start the server.

## Step 5: Link Telegram to Your Vehicle

### Option 1: Using API (Recommended)

```bash
# Link Telegram chat ID to a vehicle
curl -X POST http://localhost:5002/api/vehicles/MH20GA2345/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "telegram_chat_id": "123456789"
  }'
```

Replace:
- `MH20GA2345` with your vehicle number
- `123456789` with your Telegram chat ID

### Option 2: Using the Web Interface

The frontend will have a form to link Telegram chat ID (coming soon).

### Option 3: Direct Database Update

```bash
sqlite3 web/vehicles.db
UPDATE vehicles SET telegram_chat_id = '123456789' WHERE vehicle_number = 'MH20GA2345';
```

## Step 6: Test the Setup

### Test Bot Connection

```bash
curl http://localhost:5002/api/telegram/bot-info
```

This should return bot information if the token is valid.

### Test Notification

```bash
curl -X POST http://localhost:5002/api/telegram/test/MH20GA2345
```

Replace `MH20GA2345` with your vehicle number. This will send a test notification to your Telegram.

## Step 7: Verify Notifications Work

1. Make sure your vehicle is registered in the database
2. Ensure Telegram chat ID is linked to your vehicle
3. Start the camera detection system
4. When your vehicle is detected and then the 30-second timer expires, you should receive a Telegram notification

## Notification Message Format

You will receive a message like this:

```
🚗 Vehicle Update Alert

Hello John Doe,

Your car (MH20GA2345) was last seen near Camera 1.

Tap below to view on map:
📍 View on Google Maps

Last updated: 2025-11-09 19:30:45
```

Along with a location pin on the map showing the exact coordinates.

## API Endpoints

### Link Telegram Chat ID
```
POST /api/vehicles/<vehicle_number>/telegram
Body: {"telegram_chat_id": "123456789"}
```

### Unlink Telegram Chat ID
```
DELETE /api/vehicles/<vehicle_number>/telegram
```

### Get Bot Info
```
GET /api/telegram/bot-info
```

### Test Notification
```
POST /api/telegram/test/<vehicle_number>
```

## Troubleshooting

### Bot token not working
- Verify the token is correct (no extra spaces)
- Check that the bot is not deleted or revoked
- Test the token using: `https://api.telegram.org/bot<TOKEN>/getMe`

### Not receiving notifications
- Verify `TELEGRAM_ENABLED=true` is set
- Check that your vehicle has a `telegram_chat_id` in the database
- Check server logs for error messages
- Test using the `/api/telegram/test/<vehicle_number>` endpoint

### Invalid chat ID
- Make sure you've started a conversation with your bot
- Verify the chat ID is correct (it's a number, not a username)
- Try getting your chat ID again using @userinfobot

### Database migration issues
- Make sure the database file exists
- Check file permissions
- Run the migration script manually: `python3 migrate_add_telegram.py`

## Security Notes

- Never commit your bot token to version control
- Use environment variables for sensitive data
- Keep your bot token secure
- Regularly rotate your bot token if compromised

## Disabling Telegram Notifications

To disable Telegram notifications:

```bash
export TELEGRAM_ENABLED=false
```

Or remove the `TELEGRAM_BOT_TOKEN` environment variable.

The system will continue to work normally without Telegram notifications.




