#!/usr/bin/env python3
"""
One-off migration script: copies ~/.notarizer/notarizer.db to ~/.nora/nora.db,
mapping notarized_date -> registered_at and renaming the settings key
last_successful_notarization_run -> last_successful_registration_run.

Usage:
    python scripts/migrate_notarizer_to_nora_db.py [--dry-run]

Flags:
    --dry-run   Print what would be done without writing to ~/.nora/nora.db.
"""
import sqlite3
import sys
import os
from pathlib import Path

SRC_DB = Path.home() / ".notarizer" / "notarizer.db"
DST_DB = Path.home() / ".nora" / "nora.db"

OLD_SETTINGS_KEY = "last_successful_notarization_run"
NEW_SETTINGS_KEY = "last_successful_registration_run"


def migrate(dry_run: bool = False) -> None:
    if not SRC_DB.exists():
        print(f"Source database not found: {SRC_DB}")
        print("Nothing to migrate.")
        return

    print(f"Source: {SRC_DB}")
    print(f"Destination: {DST_DB}")

    if dry_run:
        print("[DRY RUN] No changes will be written.")

    # Open source connection
    src_conn = sqlite3.connect(SRC_DB)
    src_conn.row_factory = sqlite3.Row

    # Count source rows
    src_file_count = src_conn.execute("SELECT COUNT(*) FROM file_records").fetchone()[0]
    src_settings_count = src_conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    src_dir_count = src_conn.execute("SELECT COUNT(*) FROM directories").fetchone()[0]
    print(f"Source rows: file_records={src_file_count}, settings={src_settings_count}, directories={src_dir_count}")

    if dry_run:
        src_conn.close()
        print("[DRY RUN] Would create destination DB and copy rows with column/key renaming.")
        return

    # Ensure destination directory exists
    DST_DB.parent.mkdir(parents=True, exist_ok=True)

    # Connect to destination (creates it fresh)
    dst_conn = sqlite3.connect(DST_DB)
    dst_conn.row_factory = sqlite3.Row

    try:
        # Create destination schema
        dst_conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            encrypted INTEGER DEFAULT 0
        );

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
        );

        CREATE INDEX IF NOT EXISTS idx_file_records_sha256 ON file_records(sha256);
        CREATE INDEX IF NOT EXISTS idx_file_records_is_onchain ON file_records(is_onchain);

        CREATE TABLE IF NOT EXISTS directories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            recursive INTEGER DEFAULT 1,
            enabled INTEGER DEFAULT 1,
            added_date TEXT NOT NULL
        );
        """)

        # Migrate file_records: map notarized_date -> registered_at
        src_records = src_conn.execute("SELECT * FROM file_records").fetchall()
        for row in src_records:
            dst_conn.execute(
                """
                INSERT OR IGNORE INTO file_records
                    (file_path, file_name, size, modified_date, sha256, tx_id,
                     registered_at, is_onchain, user_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["file_path"],
                    row["file_name"],
                    row["size"],
                    row["modified_date"],
                    row["sha256"],
                    row["tx_id"],
                    row["notarized_date"],   # old column -> new column
                    row["is_onchain"],
                    row["user_notes"] if "user_notes" in row.keys() else "",
                ),
            )

        # Migrate directories (no column renames needed)
        src_dirs = src_conn.execute("SELECT * FROM directories").fetchall()
        for row in src_dirs:
            dst_conn.execute(
                "INSERT OR IGNORE INTO directories (path, recursive, enabled, added_date) VALUES (?, ?, ?, ?)",
                (row["path"], row["recursive"], row["enabled"], row["added_date"]),
            )

        # Migrate settings: rename key if present
        src_settings = src_conn.execute("SELECT * FROM settings").fetchall()
        for row in src_settings:
            key = row["key"]
            if key == OLD_SETTINGS_KEY:
                key = NEW_SETTINGS_KEY
            dst_conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, encrypted) VALUES (?, ?, ?)",
                (key, row["value"], row["encrypted"]),
            )

        # Bump schema_version to 3
        dst_conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('schema_version', '3')"
        )

        dst_conn.commit()

        # Verify row counts match
        dst_file_count = dst_conn.execute("SELECT COUNT(*) FROM file_records").fetchone()[0]
        dst_settings_count = dst_conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
        dst_dir_count = dst_conn.execute("SELECT COUNT(*) FROM directories").fetchone()[0]

        print(f"Destination rows: file_records={dst_file_count}, settings={dst_settings_count}, directories={dst_dir_count}")

        assert dst_file_count == src_file_count, f"file_records mismatch: src={src_file_count} dst={dst_file_count}"
        assert dst_dir_count == src_dir_count, f"directories mismatch: src={src_dir_count} dst={dst_dir_count}"
        print("Migration complete. Row counts verified.")

    except Exception as e:
        dst_conn.rollback()
        raise
    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    migrate(dry_run=dry_run)
