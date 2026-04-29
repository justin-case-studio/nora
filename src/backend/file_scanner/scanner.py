"""
File scanner module for the Notarizer application.
According to the architecture, FileScanner:
- Owns all file discovery and database operations
- Manages ALL database writes for file records
- Implements mode-based operation (dry_run vs automatic)
- Calls BlockchainService only when blockchain operations are needed
"""
import os
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Tuple, Callable, Optional, Dict, List
from dataclasses import dataclass

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from database.repositories import FileRecordRepository, SettingsRepository, DirectoryRepository
from database.models import FileRecord
from ..blockchain.blockchain_service import BlockchainService


@dataclass
class ScanResult:
    """Result of a scan operation"""
    auto_processed: int  # Files with existing hashes (DB records created)
    new_files_count: int  # Files with new hashes needing blockchain
    files_needing_registration: List[Dict]  # Details of files needing blockchain
    verified_unchanged: int  # Files unchanged since last scan
    error_files: List[tuple]  # Files that had errors
    total_scanned: int
    blockchain_transactions_created: int = 0  # New counter for actual blockchain transactions


class FileScanner:
    """
    Scans directories for files and owns ALL database operations.
    Implements the architecture's core principle: FileScanner owns all file discovery and database operations.
    """

    def __init__(self, status_update_callback: Optional[Callable[[str, str], None]] = None,
                 progress_callback: Optional[Callable[[str, int, int], None]] = None):
        """
        Initialize the file scanner.

        Args:
            status_update_callback: An optional function to call with status updates.
            progress_callback: An optional function to call with progress updates (current_file, processed, total).
        """
        self.file_record_repo = FileRecordRepository()
        self.settings_repo = SettingsRepository()
        self.directory_repo = DirectoryRepository()
        self.blockchain_service = BlockchainService()

        self.status_update_callback = status_update_callback
        self.progress_callback = progress_callback
        self._should_stop = False

    def set_progress_callback(self, callback: Optional[Callable[[str, int, int], None]]):
        """Set or update the progress callback."""
        self.progress_callback = callback

    def _send_status_update(self, message: str, level: str = 'info'):
        """Send a status update using the callback if it's available."""
        if self.status_update_callback:
            try:
                self.status_update_callback(message, level)
            except Exception as e:
                print(f"[FileScanner] Error in status update callback: {e}")

    def scan_directories(self, process_new_files: bool) -> ScanResult:
        """
        Scan all enabled directories.

        Args:
            process_new_files: If True, create blockchain transactions for new files.
                              If False, only count them.

        Returns:
            ScanResult with detailed information
        """
        print(f"[FileScanner] Starting scan with process_new_files={process_new_files}")
        self._should_stop = False

        # Initialize counters
        auto_processed = 0
        new_files = []
        verified_unchanged = 0
        error_files = []
        total_scanned = 0
        blockchain_transactions_created = 0
        files_processed = 0

        # Get all enabled directories
        directories = self.directory_repo.get_enabled()
        if not directories:
            print("[FileScanner] No directories configured")
            return ScanResult(0, 0, [], 0, [], 0, 0)

        # Get current blockchain target for mode-aware scanning
        blockchain_target = self.settings_repo.get_blockchain_target()

        # First pass: count total files for progress tracking
        total_files_to_process = 0
        if self.progress_callback:
            print("[FileScanner] Counting total files for progress tracking...")
            for directory in directories:
                total_files_to_process += self.count_physical_files(directory.path, directory.recursive)
            print(f"[FileScanner] Total files to process: {total_files_to_process}")

        # Scan each directory
        for directory in directories:
            if self._should_stop:
                break

            print(f"[FileScanner] Scanning {directory.path}")

            # Scan the directory
            dir_result = self._scan_single_directory(
                directory.path,
                directory.recursive,
                process_new_files,
                blockchain_target,
                files_processed,
                total_files_to_process,
                {
                    'auto_processed': auto_processed,
                    'new_files': len(new_files),
                    'verified_unchanged': verified_unchanged,
                    'error_files': len(error_files),
                    'total_scanned': total_scanned,
                    'blockchain_transactions_created': blockchain_transactions_created
                }
            )

            # Aggregate results
            auto_processed += dir_result['auto_processed']
            new_files.extend(dir_result['new_files'])
            verified_unchanged += dir_result['verified_unchanged']
            error_files.extend(dir_result['error_files'])
            total_scanned += dir_result['total_scanned']
            blockchain_transactions_created += dir_result.get('blockchain_transactions_created', 0)
            files_processed += dir_result['total_scanned']

        print(f"[FileScanner] Scan complete. Process new files: {process_new_files}, Auto-processed: {auto_processed}, New files: {len(new_files)}, Blockchain TXs created: {blockchain_transactions_created}")

        return ScanResult(
            auto_processed=auto_processed,
            new_files_count=len(new_files),
            files_needing_registration=new_files,
            verified_unchanged=verified_unchanged,
            error_files=error_files,
            total_scanned=total_scanned,
            blockchain_transactions_created=blockchain_transactions_created
        )

    def _scan_single_directory(self, directory_path: str, recursive: bool, process_new_files: bool,
                               blockchain_target: str, files_processed_so_far: int, total_files: int,
                               cumulative_counters: Dict = None) -> Dict:
        """Scan a single directory and process files according to mode."""
        # Get max file size for warnings
        max_file_size = self.settings_repo.get_max_file_size()

        # Initialize cumulative counters if not provided
        if cumulative_counters is None:
            cumulative_counters = {
                'auto_processed': 0,
                'new_files': 0,
                'verified_unchanged': 0,
                'error_files': 0,
                'total_scanned': 0,
                'blockchain_transactions_created': 0
            }

        directory_path = Path(directory_path)
        result = {
            'auto_processed': 0,
            'new_files': [],
            'verified_unchanged': 0,
            'error_files': [],
            'total_scanned': 0,
            'blockchain_transactions_created': 0
        }

        files_in_dir_processed = 0

        try:
            if not directory_path.exists() or not directory_path.is_dir():
                result['error_files'].append((str(directory_path), "Directory not found or not a directory"))
                return result

            # Get all files
            if recursive:
                for root, _, files in os.walk(directory_path):
                    for file in files:
                        if self._should_stop:
                            break
                        file_path = Path(root) / file
                        self._process_file(
                            file_path, process_new_files, blockchain_target,
                            max_file_size, result,
                            files_processed_so_far + files_in_dir_processed,
                            total_files, cumulative_counters
                        )
                        files_in_dir_processed += 1
            else:
                for item in directory_path.iterdir():
                    if self._should_stop:
                        break
                    if item.is_file():
                        self._process_file(
                            item, process_new_files, blockchain_target,
                            max_file_size, result,
                            files_processed_so_far + files_in_dir_processed,
                            total_files, cumulative_counters
                        )
                        files_in_dir_processed += 1

        except Exception as e:
            result['error_files'].append((str(directory_path), str(e)))

        return result

    def _process_file(self, file_path: Path, process_new_files: bool, blockchain_target: str,
                      max_file_size: int, result: Dict, current_file_number: int, total_files: int,
                      cumulative_counters: Dict):
        """Process a single file according to the mode."""
        try:
            # Skip symbolic links
            if file_path.is_symlink():
                return

            # Get file metadata
            file_stat = file_path.stat()
            file_size = file_stat.st_size
            modified_date = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

            result['total_scanned'] += 1

            # Check if file exists unchanged in database
            if self.file_record_repo.exists(
                str(file_path.parent),
                file_path.name,
                file_size,
                modified_date,
                blockchain_target
            ):
                result['verified_unchanged'] += 1
                return

            # File needs processing - generate hash
            file_hash = self.generate_hash(str(file_path))
            if not file_hash:
                result['error_files'].append((str(file_path), "Hash generation failed"))
                return

            # Check if hash exists in database
            existing_records = self.file_record_repo.find_by_hash(file_hash, blockchain_target)

            if existing_records:
                # Hash exists - create DB record with existing tx_id (risk-free operation)
                # This happens in BOTH dry_run and automatic modes
                self._create_db_record_with_existing_tx(
                    file_path, file_size, modified_date, file_hash,
                    existing_records[0].tx_id
                )
                result['auto_processed'] += 1
                print(f"[FileScanner] Auto-processed file with existing hash: {file_path}")

            else:
                # New hash - behavior depends on process_new_files parameter
                if not process_new_files:
                    # Don't process new files - just collect info about them
                    result['new_files'].append({
                        'path': str(file_path),
                        'hash': file_hash,
                        'info': {
                            'parent': str(file_path.parent),
                            'name': file_path.name,
                            'size': file_size,
                            'modified_date': modified_date
                        }
                    })

                else:
                    # Process new files - create blockchain transaction and DB record
                    tx_id = self.blockchain_service.create_transaction(file_hash)

                    if tx_id:
                        self._create_db_record_with_new_tx(
                            file_path, file_size, modified_date, file_hash, tx_id
                        )
                        result['auto_processed'] += 1
                        result['blockchain_transactions_created'] += 1
                        print(f"[FileScanner] Created blockchain transaction and DB record: {file_path}")
                    else:
                        result['error_files'].append((str(file_path), "Blockchain transaction failed"))

            # Send progress update with real-time category counters
            if self.progress_callback and total_files > 0:
                # Calculate cumulative counts (previous directories + current directory)
                total_scanned = cumulative_counters['total_scanned'] + result['total_scanned']
                total_verified = cumulative_counters['verified_unchanged'] + result['verified_unchanged']
                total_auto_processed = cumulative_counters['auto_processed'] + result['auto_processed']
                total_blockchain_txs = cumulative_counters['blockchain_transactions_created'] + result['blockchain_transactions_created']
                total_new_files = cumulative_counters['new_files'] + len(result['new_files'])
                total_errors = cumulative_counters['error_files'] + len(result['error_files'])

                # Calculate hash_verified_count (auto_processed - blockchain_transactions_created)
                hash_verified_count = total_auto_processed - total_blockchain_txs

                # Calculate skipped files (files not yet processed if stopped)
                files_processed_so_far = current_file_number + 1
                skipped_count = max(0, total_files - files_processed_so_far) if self._should_stop else 0

                # Create category counters for real-time updates
                category_counters = {
                    'scanned': total_scanned,
                    'verified': total_verified,
                    'updated': hash_verified_count,
                    'new_records': total_blockchain_txs,
                    'new_files': total_new_files,
                    'errors': total_errors,
                    'skipped': skipped_count
                }

                self.progress_callback(str(file_path), current_file_number + 1, total_files, category_counters)

        except Exception as e:
            result['error_files'].append((str(file_path), str(e)))

            # Send progress update even for errors to keep UI responsive
            if self.progress_callback and total_files > 0:
                # Calculate cumulative counts (previous directories + current directory)
                total_scanned = cumulative_counters['total_scanned'] + result['total_scanned']
                total_verified = cumulative_counters['verified_unchanged'] + result['verified_unchanged']
                total_auto_processed = cumulative_counters['auto_processed'] + result['auto_processed']
                total_blockchain_txs = cumulative_counters['blockchain_transactions_created'] + result['blockchain_transactions_created']
                total_new_files = cumulative_counters['new_files'] + len(result['new_files'])
                total_errors = cumulative_counters['error_files'] + len(result['error_files'])

                hash_verified_count = total_auto_processed - total_blockchain_txs

                # Calculate skipped files (files not yet processed if stopped)
                files_processed_so_far = current_file_number + 1
                skipped_count = max(0, total_files - files_processed_so_far) if self._should_stop else 0

                category_counters = {
                    'scanned': total_scanned,
                    'verified': total_verified,
                    'updated': hash_verified_count,
                    'new_records': total_blockchain_txs,
                    'new_files': total_new_files,
                    'errors': total_errors,
                    'skipped': skipped_count
                }
                self.progress_callback(str(file_path), current_file_number + 1, total_files, category_counters)

    def _create_db_record_with_existing_tx(self, file_path: Path, file_size: int,
                                          modified_date: str, file_hash: str, tx_id: str):
        """Create a database record reusing an existing transaction ID."""
        is_onchain = not tx_id.startswith('local_') if tx_id else False

        file_record = FileRecord.from_file(
            str(file_path.parent),
            file_path.name,
            file_size,
            modified_date,
            file_hash,
            tx_id,
            is_onchain
        )

        self.file_record_repo.create(file_record)

    def _create_db_record_with_new_tx(self, file_path: Path, file_size: int,
                                     modified_date: str, file_hash: str, tx_id: str):
        """Create a database record with a new transaction ID."""
        is_onchain = not tx_id.startswith('local_') if tx_id else False

        file_record = FileRecord.from_file(
            str(file_path.parent),
            file_path.name,
            file_size,
            modified_date,
            file_hash,
            tx_id,
            is_onchain
        )

        self.file_record_repo.create(file_record)

    def scan_directory(self, directory_path, recursive=True):
        """
        Legacy method for backward compatibility.
        Scans a directory and returns files to process.
        """
        print(f"[FileScanner] Legacy scan_directory called for: {directory_path}")

        # Use the new architecture but return in old format
        result = self._scan_single_directory(
            directory_path,
            recursive,
            False,  # Legacy method assumes dry_run behavior
            self.settings_repo.get_blockchain_target(),
            0,  # No progress tracking for legacy method
            0   # No total files count
        )

        # Convert to legacy format
        files_to_process = []
        for new_file in result['new_files']:
            files_to_process.append(new_file['info'])

        return {
            'files_to_process': files_to_process,
            'verified_unchanged_count': result['verified_unchanged'],
            'skipped_files': [],  # Legacy compatibility
            'error_files': result['error_files']
        }

    def generate_hash(self, file_path):
        """
        Generate a SHA-256 hash for a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as a hexadecimal string
        """
        # Fetch the current max file size setting to use as a warning threshold
        max_file_size_for_warning = self.settings_repo.get_max_file_size()

        print(f"[FileScanner] Generating hash for file: {file_path}")
        file_path = Path(file_path)

        try:
            # Check if the file exists
            if not file_path.exists():
                error_msg = f"File not found: {file_path}"
                print(f"[FileScanner] {error_msg}")
                raise FileNotFoundError(error_msg)

            # Check if the file is larger than the warning threshold
            file_size = file_path.stat().st_size
            if file_size > max_file_size_for_warning:
                warning_msg = f"Large file - processing may take longer ({file_size / (1024*1024):.2f} MB)"
                print(f"[FileScanner] {warning_msg}")
                self._send_status_update(warning_msg, 'warning')

            print(f"[FileScanner] File size: {file_size} bytes")

            # Generate the hash
            sha256 = hashlib.sha256()

            with open(file_path, 'rb') as f:
                # Read the file in chunks to avoid loading large files into memory
                chunk_count = 0
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
                    chunk_count += 1

            hash_value = sha256.hexdigest()
            print(f"[FileScanner] Hash generated: {hash_value[:8]}... ({chunk_count} chunks processed)")

            return hash_value

        except Exception as e:
            print(f"[FileScanner] Error generating hash: {str(e)}")
            return None

    def count_physical_files(self, directory_path, recursive=True):
        """Count all physical files in a directory, ignoring size limits."""
        print(f"[FileCounter] Counting all physical files in {directory_path} (Recursive: {recursive})")
        directory_path = Path(directory_path)
        file_count = 0

        try:
            if not directory_path.exists() or not directory_path.is_dir():
                print(f"[FileCounter] Directory not found or not a directory: {directory_path}")
                return 0

            items_to_scan = []
            if recursive:
                items_to_scan = directory_path.rglob('*')
            else:
                items_to_scan = directory_path.glob('*')

            for item_path in items_to_scan:
                try:
                    if item_path.is_file() and not item_path.is_symlink():
                        file_count += 1
                except OSError as e:
                    print(f"[FileCounter] Error accessing file info for {item_path}: {e}")

        except PermissionError:
             print(f"[FileCounter] Permission denied accessing directory: {directory_path}")
        except Exception as e:
            print(f"[FileCounter] Unexpected error counting files in {directory_path}: {e}")

        print(f"[FileCounter] Found {file_count} files in {directory_path}")
        return file_count

    def stop_scanning(self):
        """Request the scanning process to stop."""
        print("[FileScanner] Stop requested")
        self._should_stop = True

    def count_files_in_directory(self, directory_path: str, recursive: bool) -> Tuple[int, int]:
        """Legacy method for compatibility."""
        count = self.count_physical_files(directory_path, recursive)
        return count, 0
