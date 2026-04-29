"""
Database schema definition for the Nora application.
"""
import sqlite3
import os
from pathlib import Path

# Define the database schema version
SCHEMA_VERSION = 3

def get_db_path():
    """Get the path to the SQLite database file."""
    # Store the database in the user's home directory
    home_dir = Path.home()
    app_dir = home_dir / ".nora"

    # Create the directory if it doesn't exist
    os.makedirs(app_dir, exist_ok=True)

    return app_dir / "nora.db"

def create_tables(conn):
    """Create the database tables if they don't exist."""
    cursor = conn.cursor()

    # Create the settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        encrypted INTEGER DEFAULT 0
    )
    ''')

    # Create the file_records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS file_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        size INTEGER NOT NULL,
        modified_date TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        tx_id TEXT NOT NULL,
        registered_at TEXT NOT NULL,
        is_onchain INTEGER DEFAULT 0 NOT NULL,
        user_notes TEXT DEFAULT '',
        UNIQUE(file_path, file_name, size, modified_date, is_onchain)
    )
    ''')

    # Create an index on the sha256 column for faster lookups
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_file_records_sha256 ON file_records(sha256)
    ''')

    # Create an index on the is_onchain column
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_file_records_is_onchain ON file_records(is_onchain)
    ''')

    # Create the directories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS directories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        recursive INTEGER DEFAULT 1,
        enabled INTEGER DEFAULT 1,
        added_date TEXT NOT NULL
    )
    ''')

    # Store the schema version
    cursor.execute('''
    INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
    ''', ('schema_version', str(SCHEMA_VERSION)))

    # Set default settings
    cursor.execute('''
    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
    ''', ('max_file_size', str(2 * 1024 * 1024 * 1024)))  # 2GB default

    # Set default date format
    cursor.execute('''
    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
    ''', ('date_format', 'default'))

    # Set default blockchain target
    cursor.execute('''
    INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
    ''', ('blockchain_target', 'local'))

    conn.commit()

def init_db():
    """Initialize the database with the schema."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)

    create_tables(conn)

    conn.close()

    return db_path

if __name__ == "__main__":
    # Initialize the database when run directly
    db_path = init_db()
    print(f"Database initialized at {db_path}")
