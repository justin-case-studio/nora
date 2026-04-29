"""
Database module for the Notarizer application.
"""
from .db_manager import DatabaseManager
from .models import FileRecord, Directory, Setting
from .repositories.file_record_repository import FileRecordRepository
from .repositories.directory_repository import DirectoryRepository
from .repositories.settings_repository import SettingsRepository
from .init_db import initialize_database

# Initialize the database on import
db_path, is_new = initialize_database()

# Export the repositories
__all__ = [
    'DatabaseManager',
    'FileRecord',
    'Directory',
    'Setting',
    'FileRecordRepository',
    'DirectoryRepository',
    'SettingsRepository',
]
