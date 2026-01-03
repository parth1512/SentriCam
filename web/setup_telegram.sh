#!/bin/bash
# Quick setup script for Telegram notifications

echo "=========================================="
echo "🚀 Telegram Notifications Setup"
echo "=========================================="
echo ""

# Check if .env file exists
if [ -f .env ]; then
    echo "📄 Found .env file"
    source .env
else
    echo "📄 No .env file found"
    echo ""
    read -p "Enter your Telegram Bot Token: " BOT_TOKEN
    read -p "Enter your Telegram Chat ID: " CHAT_ID
    read -p "Enter your Vehicle Number: " VEHICLE_NUMBER
    
    echo ""
    echo "Setting environment variables..."
    export TELEGRAM_ENABLED=true
    export TELEGRAM_BOT_TOKEN=$BOT_TOKEN
    
    echo ""
    echo "Linking Telegram to vehicle..."
    curl -X POST http://localhost:5002/api/vehicles/$VEHICLE_NUMBER/telegram \
      -H "Content-Type: application/json" \
      -d "{\"telegram_chat_id\": \"$CHAT_ID\"}" | python3 -m json.tool
    
    echo ""
    echo "Testing notification..."
    curl -X POST http://localhost:5002/api/telegram/test/$VEHICLE_NUMBER | python3 -m json.tool
    
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "To make this permanent, create a .env file with:"
    echo "TELEGRAM_ENABLED=true"
    echo "TELEGRAM_BOT_TOKEN=$BOT_TOKEN"
fi
