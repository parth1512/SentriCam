# Debugging Telegram Bot Not Responding

## Current Issue
Bot responds to `/register` but doesn't process the name input ("Parth").

## Diagnosis Steps

1. **Check if server is running:**
   ```bash
   ps aux | grep "python.*app.py"
   ```

2. **Check if bot is polling:**
   ```bash
   cd web
   python3 test_bot_connection.py
   ```
   - If "Pending updates: X" where X > 0 → Bot is NOT polling
   - If "Pending updates: 0" → Bot IS polling (updates are being processed)

3. **Check server logs:**
   Look for:
   - `✅ Telegram Bot: Started (Polling mode)`
   - `🔄 Telegram Bot: Starting polling...`
   - Any error messages

4. **Test bot manually:**
   - Send `/start` → Should get welcome message
   - Send `/register` → Should ask for name
   - Send your name → Should ask for phone
   - If it stops at name, the conversation handler isn't working

## Common Issues

### Issue 1: Bot Thread Not Running
**Symptom:** Bot responds initially then stops

**Fix:** Restart server and check logs for bot thread status

### Issue 2: Conversation State Lost
**Symptom:** Bot asks for name but doesn't respond when name is sent

**Possible Causes:**
- Handler not registered correctly
- ConversationHandler state not maintained
- Handler exception that's being silently caught

**Fix:** Check server logs for errors when name is sent

### Issue 3: Bot Not Polling
**Symptom:** Messages accumulate in Telegram queue

**Fix:** 
- Restart server
- Check if bot thread is alive
- Verify bot token is correct

## Quick Fix

1. **Restart the server:**
   ```bash
   # Stop existing server
   pkill -f "python.*app.py"
   
   # Start server
   cd web
   source ../.venv/bin/activate
   python app.py
   ```

2. **Watch for bot startup messages:**
   - Should see: `✅ Telegram Bot: Started (Polling mode)`
   - Should see: `🔄 Telegram Bot: Starting polling...`

3. **Test in Telegram:**
   - Send `/start`
   - Send `/register`
   - Send your name
   - Check if bot responds

## If Still Not Working

Run the standalone bot to test:
```bash
cd web
source ../.venv/bin/activate
python run_telegram_bot_standalone.py
```

This will show if the issue is with the bot itself or with the server integration.




