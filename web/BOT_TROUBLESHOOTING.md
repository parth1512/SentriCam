# Telegram Bot Troubleshooting Guide

## Issue: Bot Not Responding to Commands

### Quick Check
1. **Is the server running?**
   ```bash
   ps aux | grep "python.*app.py"
   ```

2. **Check if bot is polling:**
   ```bash
   cd web
   python3 test_bot_connection.py
   ```
   - If you see "Pending updates: X" where X > 0, the bot is NOT polling
   - If you see "Pending updates: 0", the bot is likely polling

### Common Issues

#### 1. Bot Thread Not Starting
**Symptoms:** Bot doesn't respond, pending updates accumulate

**Solution:**
- Restart the server
- Check server logs for bot initialization messages
- Look for: `✅ Telegram Bot: Started (Polling mode)`

#### 2. Environment Variables Not Loaded
**Symptoms:** Bot not starting, "Token not found" error

**Solution:**
- Ensure `.env` file exists in `web/` directory
- Check `.env` contains:
  ```
  TELEGRAM_ENABLED=true
  TELEGRAM_BOT_TOKEN=your_token_here
  ```

#### 3. Bot Thread Crashed
**Symptoms:** Bot started but stopped responding

**Solution:**
- Check server logs for errors
- Restart the server
- The bot thread may have crashed silently

### Testing the Bot

1. **Test bot connection:**
   ```bash
   cd web
   python3 test_bot_connection.py
   ```

2. **Send a test command:**
   - Open Telegram
   - Send `/start` to your bot
   - If no response, the bot is not polling

3. **Check server logs:**
   - Look for bot initialization messages
   - Check for any error messages

### Manual Bot Start (Standalone)

If the bot doesn't start with the server, you can run it standalone:

```bash
cd web
source ../.venv/bin/activate
python run_telegram_bot_standalone.py
```

This will run ONLY the bot (for registration), not the full server.

### Verification Steps

1. ✅ Server is running
2. ✅ `.env` file exists and has correct token
3. ✅ Server logs show "Telegram Bot: Started"
4. ✅ `test_bot_connection.py` shows 0 pending updates
5. ✅ Bot responds to `/start` command




