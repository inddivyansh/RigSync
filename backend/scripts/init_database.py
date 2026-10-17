#!/usr/bin/env python3
"""
Initialize SQLite database with schema
"""
import sqlite3
import os
from pathlib import Path

# Get project root
BACKEND_DIR = Path(__file__).parent.parent
DB_PATH = BACKEND_DIR / "data" / "db" / "oilwells.db"
SCHEMA_PATH = BACKEND_DIR / "data" / "db" / "schema.sql"

def init_database():
    """Create database and execute schema"""
    print(f"📂 Database path: {DB_PATH}")
    print(f"📄 Schema path: {SCHEMA_PATH}")
    
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Read schema
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    # Create database and execute schema
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.executescript(schema_sql)
        conn.commit()
        print("✅ Database created successfully")
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
