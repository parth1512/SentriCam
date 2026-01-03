#!/usr/bin/env python3
"""
Database migration script to add telegram_chat_id column to vehicles table
"""
import sqlite3
from pathlib import Path
import sys

# Get database path
db_path = Path(__file__).resolve().parent / 'vehicles.db'

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    print("   Database will be created automatically on next server start.")
    sys.exit(0)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("🔧 DATABASE MIGRATION: Adding telegram_chat_id column")
print("=" * 60)
print(f"Database: {db_path}\n")

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(vehicles);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'telegram_chat_id' in columns:
        print("✅ Column 'telegram_chat_id' already exists. Migration not needed.")
    else:
        print("📝 Adding 'telegram_chat_id' column...")
        
        # Add the column
        cursor.execute("""
            ALTER TABLE vehicles 
            ADD COLUMN telegram_chat_id VARCHAR(50) NULL;
        """)
        
        # Create index for faster lookups
        print("📝 Creating index on telegram_chat_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS ix_vehicles_telegram_chat_id 
            ON vehicles(telegram_chat_id);
        """)
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print("   - Added telegram_chat_id column")
        print("   - Created index on telegram_chat_id")
    
    # Verify migration
    cursor.execute("PRAGMA table_info(vehicles);")
    columns = cursor.fetchall()
    print("\n📊 Current table structure:")
    print(f"{'Column Name':<25} {'Type':<15} {'Nullable':<10}")
    print("-" * 50)
    for col in columns:
        # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
        col_name = col[1]
        col_type = col[2]
        not_null = col[3]
        nullable = "NO" if not_null else "YES"
        print(f"{col_name:<25} {col_type:<15} {nullable:<10}")
    
    conn.close()
    print("\n✅ Migration script completed successfully!")

except sqlite3.Error as e:
    print(f"❌ Database error: {e}")
    conn.rollback()
    conn.close()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
    conn.close()
    sys.exit(1)

