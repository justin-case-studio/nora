"""
Database initialization script for the Notarizer application.
Sets up the database on application startup.
"""
import sqlite3
from .schema import get_db_path, create_tables, SCHEMA_VERSION


def initialize_database():
    """
    Initialize the database — creates tables if they don't exist.
    No migration logic; schema is managed via schema.py create_tables().
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)

    create_tables(conn)

    conn.close()

    print(f"[DB Init] Database initialized at {db_path}")
    print(f"[DB Init] Schema version (from schema.py): {SCHEMA_VERSION}")

    return db_path, True


if __name__ == "__main__":
    # Initialize the database when run directly
    db_path, _ = initialize_database()
    print(f"Database initialization script run for {db_path}")
