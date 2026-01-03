#!/usr/bin/env python3
"""
Standalone Telegram Bot Runner
This script allows the Telegram bot to run independently of the Flask server.
Useful for running the bot as a separate service.

Usage:
    python run_telegram_bot_standalone.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import Flask app and bot
from flask import Flask
from models import db
from services.telegram_bot import TelegramBot

def create_minimal_app():
    """Create a minimal Flask app for database access"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'telegram_bot_secret'
    
    # Database configuration
    db_path = Path(__file__).resolve().parent / 'vehicles.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.as_posix()}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print("✅ Database initialized")
    
    return app

def main():
    """Main function to run the Telegram bot standalone"""
    print("=" * 60)
    print("🤖 Starting Telegram Bot (Standalone Mode)")
    print("=" * 60)
    
    # Check for bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
    
    if not telegram_enabled:
        print("⚠️  Telegram is disabled. Set TELEGRAM_ENABLED=true in .env")
        sys.exit(1)
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        sys.exit(1)
    
    # Create minimal Flask app for database access
    print("📦 Creating Flask app for database access...")
    app = create_minimal_app()
    
    # Create and initialize bot directly (not in thread, since we'll run polling in main thread)
    print("🚀 Initializing Telegram bot...")
    bot = TelegramBot(bot_token, app)
    if not bot.initialize():
        print("❌ Failed to initialize Telegram bot")
        sys.exit(1)
    
    print("✅ Telegram bot initialized!")
    print("📱 Users can now register via Telegram")
    print("⚠️  Note: This bot only handles registration.")
    print("    Vehicle detection and notifications require the main server.")
    print("\n" + "=" * 60)
    print("Starting bot polling... (Press Ctrl+C to stop)")
    print("=" * 60 + "\n")
    
    try:
        # Run polling in main thread (blocking call)
        bot.start_polling()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping Telegram bot...")
        bot.stop()
        print("✅ Bot stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

