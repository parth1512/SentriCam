# 🚀 Quick Start: Telegram Notifications Setup

Follow these steps to enable Telegram notifications for your vehicle tracking system.

## Step 1: Create a Telegram Bot (5 minutes)

1. Open Telegram app on your phone or computer
2. Search for **@BotFather** and start a chat
3. Send the command: `/newbot`
4. Follow the prompts:
   - Choose a name for your bot (e.g., "My Vehicle Tracker")
   - Choose a username (must end with 'bot', e.g., "my_vehicle_tracker_bot")
5. **Copy the bot token** that BotFather gives you (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
   - ⚠️ **SAVE THIS TOKEN** - you'll need it in Step 3

## Step 2: Get Your Telegram Chat ID (2 minutes)

1. Search for **@userinfobot** on Telegram
2. Start a conversation with it
3. It will reply with your chat ID (a number like `123456789`)
   - ⚠️ **SAVE THIS CHAT ID** - you'll need it in Step 4

**Alternative method:**
- Start a chat with your bot (search for the bot username you created)
- Send any message to your bot
- Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
- Look for `"chat":{"id":123456789}` in the response

## Step 3: Configure Environment Variables

### Option A: Export in Terminal (Temporary - until you close terminal)

```bash
export TELEGRAM_ENABLED=true
export TELEGRAM_BOT_TOKEN=your_bot_token_here
```

Replace `your_bot_token_here` with the token from Step 1.

### Option B: Create .env File (Permanent - Recommended)

1. Create a file named `.env` in the `web/` directory:

```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web"
nano .env
```

2. Add these lines:

```
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

3. Save and exit (Ctrl+X, then Y, then Enter)

**Note:** If you use `.env` file, you may need to install `python-dotenv`:
```bash
pip install python-dotenv
```

And add this to `app.py` at the top:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Step 4: Restart Your Server

Stop the current server (Ctrl+C) and restart it:

```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project"
source venv/bin/activate
cd web
python app.py
```

You should see:
```
✅ Telegram service: Enabled (Bot: @your_bot_username)
```

If you see a warning, check your bot token.

## Step 5: Link Telegram to Your Vehicle

### Check your vehicle number first:

```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web"
python3 check_db.py
```

### Link Telegram using API:

```bash
curl -X POST http://localhost:5002/api/vehicles/MH20GA2345/telegram \
  -H "Content-Type: application/json" \
  -d '{"telegram_chat_id": "123456789"}'
```

Replace:
- `MH20GA2345` with your actual vehicle number
- `123456789` with your Telegram chat ID from Step 2

### Verify it's linked:

```bash
python3 check_db.py
```

You should see your Telegram chat ID in the "Telegram" column.

## Step 6: Test the Notification

Send a test notification:

```bash
curl -X POST http://localhost:5002/api/telegram/test/MH20GA2345
```

Replace `MH20GA2345` with your vehicle number.

**You should receive a Telegram message with:**
- Vehicle alert message
- Google Maps link
- Location pin on map

## Step 7: Test Real Detection

1. Make sure your vehicle is registered in the database
2. Make sure Telegram chat ID is linked
3. Start the camera detection system
4. When your vehicle is detected:
   - System starts a 30-second timer
   - If no further detections occur for 30 seconds
   - You'll automatically receive a Telegram notification!

## Troubleshooting

### Bot token not working?
```bash
# Test your bot token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

Should return bot information if token is valid.

### Not receiving notifications?
1. Check server logs for errors
2. Verify Telegram is enabled:
   ```bash
   curl http://localhost:5002/api/telegram/bot-info
   ```
3. Check vehicle has Telegram chat ID:
   ```bash
   python3 check_db.py
   ```
4. Test notification manually:
   ```bash
   curl -X POST http://localhost:5002/api/telegram/test/MH20GA2345
   ```

### Environment variables not working?
- Make sure you exported them in the same terminal where you run the server
- Or use `.env` file method (more reliable)

## What Happens Next?

Once set up, the system will automatically:
1. ✅ Detect your vehicle at cameras
2. ✅ Start a 30-second timer
3. ✅ If no further detections → Send Telegram notification
4. ✅ Include Google Maps link and location pin

You don't need to do anything else - it's fully automatic! 🎉

## Quick Reference Commands

```bash
# Check database
python3 check_db.py

# Test Telegram service
python3 test_telegram.py

# Link Telegram to vehicle
curl -X POST http://localhost:5002/api/vehicles/<VEHICLE_NUMBER>/telegram \
  -H "Content-Type: application/json" \
  -d '{"telegram_chat_id": "<YOUR_CHAT_ID>"}'

# Test notification
curl -X POST http://localhost:5002/api/telegram/test/<VEHICLE_NUMBER>

# Check bot info
curl http://localhost:5002/api/telegram/bot-info
```

## Need Help?

1. Check `web/TELEGRAM_SETUP.md` for detailed documentation
2. Check server logs for error messages
3. Run `python3 test_telegram.py` to diagnose issues




