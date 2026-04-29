"""
Database manager for the Notarizer application.
Provides a clean API for database operations.
"""
import sqlite3
import threading # Keep lock for singleton
from .schema import get_db_path, create_tables
# Removed os import

class DatabaseManager:
    """
    Manages database operations, ensuring each is self-contained.
    Uses a Singleton pattern.
    """
    _instance = None
    _lock = threading.Lock()
    # Add attribute to hold the persistent connection
    _connection = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                # Defer initialization steps to __init__ or a dedicated method
                # Using __init__ is more conventional here.
            return cls._instance

    # Use __init__ for initialization logic that needs the instance
    def __init__(self):
        # Ensure initialization runs only once using a flag
        if not hasattr(self, '_initialized') or not self._initialized:
            with self._lock: # Ensure thread-safety for initialization
                 # Double-check instance creation within lock
                if DatabaseManager._instance is None:
                   DatabaseManager._instance = self # Should already be set by __new__ but safe check

                # Check again if another thread initialized it while waiting for the lock
                if DatabaseManager._connection is None:
                    self.db_path = get_db_path() # db_path is a Path object
                    # Explicitly encode path for printing to avoid console issues
                    try:
                        db_path_str = str(self.db_path)
                    except UnicodeEncodeError:
                         # Fallback for unprintable paths (less likely needed now but safe)
                         db_path_str = self.db_path.as_posix().encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')

                    print(f"[DB Manager] Initializing Singleton. Using DB path: {db_path_str}")
                    try:
                        # Create and store the persistent connection
                        # Explicitly convert Path object to string for sqlite3.connect
                        db_path_as_string = str(self.db_path)
                        DatabaseManager._connection = sqlite3.connect(db_path_as_string, check_same_thread=False)
                        DatabaseManager._connection.row_factory = sqlite3.Row # Set row factory once
                        DatabaseManager._connection.execute("PRAGMA foreign_keys = ON") # Enable FKs once
                        # Optional: Explicitly set WAL mode once if desired
                        # DatabaseManager._connection.execute("PRAGMA journal_mode = WAL")
                        create_tables(DatabaseManager._connection) # Initialize schema using the connection
                        print("[DB Manager] Persistent connection established and schema verified.")
                        self._initialized = True # Mark as initialized
                    except sqlite3.Error as e:
                        print(f"[DB Init] CRITICAL Error initializing database connection or schema: {e}")
                        # Attempt cleanup if connection object exists
                        if DatabaseManager._connection:
                            DatabaseManager._connection.close()
                            DatabaseManager._connection = None
                        raise # Re-raise critical error

    # --- Add a method to close the connection ---
    def close_connection(self):
        """Closes the persistent database connection."""
        with self._lock:
            if DatabaseManager._connection:
                print("[DB Manager] Closing persistent database connection.")
                try:
                    DatabaseManager._connection.commit() # Commit any pending changes
                    DatabaseManager._connection.close()
                    DatabaseManager._connection = None
                    self._initialized = False # Reset initialized flag
                except sqlite3.Error as e:
                    print(f"[DB Close] Error closing database connection: {e}")
    # -----------------------------------------

    def execute_read(self, query, params=None, fetch_one=False):
        """Execute a read query (SELECT) using the persistent connection."""
        if not DatabaseManager._connection:
             print("[DB Read] Database connection is not available.")
             # Consider raising an error or attempting re-initialization
             return None
        # print(f"ℹ️ [DB Manager Read] Executing query: {query[:50]}...") # Reduced verbosity
        try:
            # Use the persistent connection directly
            cursor = DatabaseManager._connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            result = cursor.fetchone() if fetch_one else cursor.fetchall()
            # Do NOT close the connection here
            return result
        except sqlite3.Error as e:
            print(f"[DB Read] Error executing query '{query[:50]}...': {e}")
            # Do not close the connection on read error
            return None # Return None on error

    def execute_write(self, query, params=None):
        """Execute a write query (INSERT, UPDATE, DELETE) and commit using the persistent connection."""
        if not DatabaseManager._connection:
             print("[DB Write] Database connection is not available.")
             # Consider raising an error or attempting re-initialization
             return False
        # print(f"ℹ️ [DB Manager Write] Executing query: {query[:50]}...") # Reduced verbosity
        try:
            # Use the persistent connection directly
            cursor = DatabaseManager._connection.cursor()
            # No need to set PRAGMAs per write if done during init
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            DatabaseManager._connection.commit() # Commit the change on the persistent connection
            # Removed explicit WAL checkpoint and os.sync()
            # Do NOT close the connection here
            # print(f"💾 [DB Write] Query committed successfully. Affected rows: {rowcount}") # Reduced verbosity
            return True # Indicate success
        except sqlite3.Error as e:
            print(f"[DB Write] Error executing query '{query[:50]}...': {e}")
            # Attempt rollback on the persistent connection for this specific error
            try:
                 DatabaseManager._connection.rollback()
                 print("[DB Write] Transaction rolled back due to error.")
            except sqlite3.Error as rb_e:
                 print(f"[DB Write] CRITICAL Error during rollback: {rb_e}")
            # Do NOT close the connection on write error
            return False # Indicate failure

    # Ensure __del__ tries to close connection on garbage collection, though not guaranteed to run reliably
    def __del__(self):
        self.close_connection()

# Removed Transaction class as it's no longer used

# REMOVED Transaction class
# class Transaction:
#    ...
