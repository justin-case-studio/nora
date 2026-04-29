"""
Database models for the Notarizer application.
Defines the data structures used in the application.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class FileRecord:
    """Represents a registered file record."""
    id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    size: int = 0
    modified_date: str = ""
    sha256: str = ""
    tx_id: str = ""
    registered_at: str = ""
    is_onchain: bool = False
    user_notes: str = ""  # User-defined notes/comments for this file record

    @classmethod
    def from_row(cls, row):
        """Create a FileRecord from a database row."""
        if row is None:
            return None

        is_onchain_bool = bool(row['is_onchain']) if 'is_onchain' in row.keys() else False

        # Handle user_notes column - check if it exists in the row
        try:
            user_notes_str = row['user_notes'] if 'user_notes' in row.keys() else ''
        except (KeyError, IndexError):
            user_notes_str = ''

        return cls(
            id=row['id'],
            file_path=row['file_path'],
            file_name=row['file_name'],
            size=row['size'],
            modified_date=row['modified_date'],
            sha256=row['sha256'],
            tx_id=row['tx_id'],
            registered_at=row['registered_at'],
            is_onchain=is_onchain_bool,
            user_notes=user_notes_str
        )

    @classmethod
    def from_file(cls, file_path, file_name, size, modified_date, sha256, tx_id, is_onchain):
        """Create a FileRecord from file information."""
        return cls(
            file_path=file_path,
            file_name=file_name,
            size=size,
            modified_date=modified_date,
            sha256=sha256,
            tx_id=tx_id,
            registered_at=datetime.now().isoformat(),
            is_onchain=is_onchain,
            user_notes=""  # Default to empty string for new records
        )


@dataclass
class Directory:
    """Represents a directory to be monitored."""
    id: Optional[int] = None
    path: str = ""
    recursive: bool = True
    enabled: bool = True
    added_date: str = ""

    @classmethod
    def from_row(cls, row):
        """Create a Directory from a database row."""
        if row is None:
            return None

        return cls(
            id=row['id'],
            path=row['path'],
            recursive=bool(row['recursive']),
            enabled=bool(row['enabled']),
            added_date=row['added_date']
        )

    @classmethod
    def from_path(cls, path, recursive=True):
        """Create a Directory from a path."""
        return cls(
            path=path,
            recursive=recursive,
            enabled=True,
            added_date=datetime.now(timezone.utc).isoformat()
        )


@dataclass
class Setting:
    """Represents an application setting."""
    key: str
    value: str
    encrypted: bool = False

    @classmethod
    def from_row(cls, row):
        """Create a Setting from a database row."""
        if row is None:
            return None

        return cls(
            key=row['key'],
            value=row['value'],
            encrypted=bool(row['encrypted'])
        )
