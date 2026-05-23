#!/bin/bash
# Enable SQLite WAL mode for better concurrency and crash resilience
# Run once after database creation

DB_PATH="/home/gaja/stradegy/data/stradegy.db"

if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH"
    exit 1
fi

python3 - << 'PYEOF'
import sqlite3
import sys

db_path = "/home/gaja/stradegy/data/stradegy.db"
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current journal mode
    cursor.execute("PRAGMA journal_mode;")
    current_mode = cursor.fetchone()[0]
    print(f"Current journal mode: {current_mode}")
    
    if current_mode != "wal":
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA journal_mode;")
        new_mode = cursor.fetchone()[0]
        print(f"Journal mode changed to: {new_mode}")
        
        # Set WAL auto-checkpoint to 1000 pages (default is 1000)
        cursor.execute("PRAGMA wal_autocheckpoint=1000;")
        print("WAL auto-checkpoint set to 1000 pages")
    else:
        print("WAL mode already enabled")
    
    conn.close()
    print("SQLite WAL mode configured successfully")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
PYEOF
