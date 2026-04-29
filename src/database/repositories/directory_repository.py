"""
Repository for directories in the Notarizer application.
Handles database operations related to monitored directories.
"""
from ..db_manager import DatabaseManager
from ..models import Directory


class DirectoryRepository:
    """Repository for monitored directories."""

    def __init__(self):
        """Initialize the repository with a database manager."""
        self.db_manager = DatabaseManager()

    def create(self, directory):
        """Create a new directory in the database."""
        query = '''
        INSERT INTO directories (path, recursive, enabled, added_date)
        VALUES (?, ?, ?, ?)
        '''
        params = (
            directory.path,
            int(directory.recursive),
            int(directory.enabled),
            directory.added_date
        )
        success = self.db_manager.execute_write(query, params)
        if success:
            # Need to get the last inserted ID - this is tricky without cursor
            # Re-fetch by path for now
            new_dir = self.find_by_path(directory.path)
            return new_dir
        else:
            print(f"❌ [DirectoryRepo] Failed to create directory: {directory.path}")
            return None

    def update(self, directory):
        """Update a directory in the database."""
        query = '''
        UPDATE directories
        SET path = ?, recursive = ?, enabled = ?
        WHERE id = ?
        '''
        params = (
            directory.path,
            int(directory.recursive),
            int(directory.enabled),
            directory.id
        )
        success = self.db_manager.execute_write(query, params)
        if success:
            return directory # Assume update worked
        else:
            print(f"❌ [DirectoryRepo] Failed to update directory ID: {directory.id}")
            # Should ideally re-fetch to confirm state, but return original for now
            return directory

    def delete(self, directory_id):
        """Delete a directory from the database."""
        query = 'DELETE FROM directories WHERE id = ?'
        success = self.db_manager.execute_write(query, (directory_id,))
        if not success:
            print(f"❌ [DirectoryRepo] Failed to delete directory ID: {directory_id}")
        return success

    def find_by_id(self, directory_id):
        """Find a directory by its ID."""
        query = 'SELECT * FROM directories WHERE id = ?'
        row = self.db_manager.execute_read(query, (directory_id,), fetch_one=True)
        return Directory.from_row(row) if row else None

    def find_by_path(self, path):
        """Find a directory by its path."""
        query = 'SELECT * FROM directories WHERE path = ?'
        row = self.db_manager.execute_read(query, (path,), fetch_one=True)
        return Directory.from_row(row) if row else None

    def get_all(self):
        """Get all directories."""
        query = 'SELECT * FROM directories ORDER BY path'
        rows = self.db_manager.execute_read(query)
        return [Directory.from_row(row) for row in rows] if rows else []

    def get_enabled(self):
        """Get all enabled directories."""
        query = 'SELECT * FROM directories WHERE enabled = 1 ORDER BY path'
        rows = self.db_manager.execute_read(query)
        return [Directory.from_row(row) for row in rows] if rows else []

    def exists(self, path):
        """Check if a directory exists with the given path."""
        query = 'SELECT 1 FROM directories WHERE path = ? LIMIT 1'
        row = self.db_manager.execute_read(query, (path,), fetch_one=True)
        return row is not None
