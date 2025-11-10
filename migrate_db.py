"""
Migration script to add user_name column to existing database
Run this once: python migrate_db.py
"""
import sqlite3

db_path = 'spotted.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if user_name column exists
    cursor.execute("PRAGMA table_info(scores)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'user_name' not in columns:
        print("Adding user_name column to database...")
        cursor.execute("ALTER TABLE scores ADD COLUMN user_name TEXT")
        conn.commit()
        print("✅ Migration complete! user_name column added.")
    else:
        print("✅ Database already has user_name column. No migration needed.")
    
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nIf migration fails, you can start fresh by deleting spotted.db")

