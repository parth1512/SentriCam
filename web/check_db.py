#!/usr/bin/env python3
"""
Simple script to check the vehicles database
"""
import sqlite3
from pathlib import Path
import sys

# Get database path
db_path = Path(__file__).resolve().parent / 'vehicles.db'

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    sys.exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("🚗 VEHICLES DATABASE")
print("=" * 60)
print(f"Database: {db_path}\n")

# Get table info
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables: {[t[0] for t in tables]}\n")

# Count vehicles
cursor.execute("SELECT COUNT(*) FROM vehicles;")
count = cursor.fetchone()[0]
print(f"Total vehicles: {count}\n")

if count > 0:
    # Get all vehicles
    cursor.execute("""
        SELECT id, name, phone_number, vehicle_number, telegram_chat_id, created_at 
        FROM vehicles 
        ORDER BY created_at DESC
    """)
    vehicles = cursor.fetchall()
    
    print("=" * 60)
    print("REGISTERED VEHICLES")
    print("=" * 60)
    print(f"{'ID':<5} {'Name':<20} {'Phone':<15} {'Vehicle':<15} {'Telegram':<15} {'Created At':<20}")
    print("-" * 85)
    
    for vehicle in vehicles:
        vid, name, phone, vnum, telegram, created = vehicle
        telegram_str = telegram if telegram else "Not linked"
        print(f"{vid:<5} {name:<20} {phone:<15} {vnum:<15} {telegram_str:<15} {created:<20}")
    
    print("=" * 60)
else:
    print("No vehicles registered yet.")

# Close connection
conn.close()

