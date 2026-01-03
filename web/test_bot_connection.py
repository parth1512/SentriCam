#!/usr/bin/env python3
"""
Quick test script to check if Telegram bot is responding
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env
load_dotenv(Path(__file__).parent / '.env')

token = os.getenv('TELEGRAM_BOT_TOKEN', '')

if not token:
    print("❌ TELEGRAM_BOT_TOKEN not found")
    sys.exit(1)

print("=" * 60)
print("🔍 TESTING TELEGRAM BOT CONNECTION")
print("=" * 60)

# Test 1: Check bot info
print("\n1. Testing bot API connection...")
try:
    response = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
    if response.status_code == 200:
        bot_info = response.json()
        if bot_info.get('ok'):
            bot = bot_info.get('result', {})
            print(f"   ✅ Bot is accessible")
            print(f"   Bot: @{bot.get('username')}")
            print(f"   Name: {bot.get('first_name')}")
        else:
            print(f"   ❌ Bot API error: {bot_info.get('description')}")
    else:
        print(f"   ❌ HTTP Error: {response.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Check for pending updates
print("\n2. Checking for pending updates...")
try:
    response = requests.get(f'https://api.telegram.org/bot{token}/getUpdates', timeout=10)
    if response.status_code == 200:
        updates_data = response.json()
        if updates_data.get('ok'):
            updates = updates_data.get('result', [])
            print(f"   Pending updates: {len(updates)}")
            if len(updates) > 0:
                print(f"   ⚠️  Bot is NOT polling - {len(updates)} updates queued!")
                print(f"   Latest update: {updates[-1].get('update_id')}")
            else:
                print(f"   ✅ No pending updates (bot may be polling)")
        else:
            print(f"   ❌ Error: {updates_data.get('description')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Send a test message to yourself (if chat_id is known)
print("\n3. Bot status:")
print("   If updates are queued, the bot thread may not be running.")
print("   Check server logs for bot initialization messages.")
print("=" * 60)




