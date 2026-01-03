#!/usr/bin/env python3
"""
Test script for Telegram notification feature
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import app, db, Vehicle
from services.telegram_service import get_telegram_service

def test_telegram_service():
    """Test Telegram service functionality"""
    print("=" * 60)
    print("🧪 TESTING TELEGRAM SERVICE")
    print("=" * 60)
    
    # Check if Telegram is enabled
    telegram_service = get_telegram_service()
    print(f"\n1. Telegram Service Status:")
    print(f"   Enabled: {telegram_service.enabled}")
    print(f"   Bot Token: {'Set' if telegram_service.bot_token else 'Not set'}")
    
    if not telegram_service.enabled:
        print("\n⚠️  Telegram service is disabled.")
        print("   Set TELEGRAM_ENABLED=true and TELEGRAM_BOT_TOKEN to enable.")
        return False
    
    # Test bot info
    print(f"\n2. Testing Bot Connection:")
    bot_info = telegram_service.get_bot_info()
    if bot_info:
        print(f"   ✅ Bot connected: @{bot_info.get('username')}")
        print(f"   Bot Name: {bot_info.get('first_name')}")
        print(f"   Bot ID: {bot_info.get('id')}")
    else:
        print(f"   ❌ Failed to get bot info. Check your bot token.")
        return False
    
    # Check vehicles with Telegram chat ID
    print(f"\n3. Checking Registered Vehicles:")
    with app.app_context():
        vehicles = Vehicle.query.filter(Vehicle.telegram_chat_id.isnot(None)).all()
        print(f"   Vehicles with Telegram: {len(vehicles)}")
        
        if len(vehicles) == 0:
            print(f"   ⚠️  No vehicles have Telegram chat ID linked.")
            print(f"   Use the API to link: POST /api/vehicles/<vehicle_number>/telegram")
            return False
        
        for vehicle in vehicles:
            print(f"   - {vehicle.vehicle_number} ({vehicle.name}): {vehicle.telegram_chat_id}")
    
    # Test notification (optional)
    if len(vehicles) > 0:
        vehicle = vehicles[0]
        print(f"\n4. Test Notification (optional):")
        response = input(f"   Send test notification to {vehicle.name}? (y/n): ")
        if response.lower() == 'y':
            print(f"   Sending test notification...")
            result = telegram_service.send_vehicle_alert(
                chat_id=vehicle.telegram_chat_id,
                user_name=vehicle.name,
                vehicle_number=vehicle.vehicle_number,
                camera_location_name="Test Camera",
                latitude=12.968194,
                longitude=79.155917,
                send_location=True
            )
            
            if result.get('message', {}).get('success'):
                print(f"   ✅ Test notification sent successfully!")
            else:
                error = result.get('message', {}).get('error', 'Unknown error')
                print(f"   ❌ Failed to send notification: {error}")
    
    print("\n" + "=" * 60)
    print("✅ Telegram service test completed!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    test_telegram_service()




