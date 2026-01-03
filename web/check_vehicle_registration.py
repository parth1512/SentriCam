#!/usr/bin/env python3
"""Check vehicle registration in database"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import app
from models import Vehicle, db

with app.app_context():
    vehicles = Vehicle.query.all()
    print(f"\n{'='*60}")
    print(f"📋 REGISTERED VEHICLES")
    print(f"{'='*60}")
    
    if not vehicles:
        print("❌ No vehicles registered in database")
        print("\n💡 To register a vehicle:")
        print("   1. Start the Telegram bot")
        print("   2. Send /register to your bot")
        print("   3. Follow the registration steps")
    else:
        for v in vehicles:
            print(f"\n✅ Vehicle: {v.vehicle_number}")
            print(f"   Name: {v.name}")
            print(f"   Phone: {v.phone_number}")
            print(f"   Telegram Chat ID: {v.telegram_chat_id or '❌ NOT LINKED'}")
            print(f"   Created: {v.created_at}")
            
            if not v.telegram_chat_id:
                print(f"   ⚠️  WARNING: No Telegram chat ID - notifications will NOT be sent!")
    
    print(f"\n{'='*60}\n")




