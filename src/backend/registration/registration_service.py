"""
Unified Notarization Service - Merged FileScanner and NotarizationService.
This eliminates the wrapper layer and provides direct, self-reporting functionality.
"""
import os
import sys
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from database.repositories import FileRecordRepository, SettingsRepository, DirectoryRepository
from database.models import FileRecord
from ..blockchain.blockchain_service import BlockchainService


@dataclass
class OperationSettings:
    """Snapshot of all settings for an operation to avoid race conditions"""
    automatic: bool
    blockchain_target: str
    max_file_size: int
    api_key: str
    project_id: str


@dataclass
class ScanResult:
    """Result of a scan operation"""
    auto_processed: int  # Files with existing hashes (DB records created)
    new_files_count: int  # Files with new hashes needing blockchain
    files_needing_registration: List[Dict]  # Details of files needing blockchain
    verified_unchanged: int  # Files unchanged since last scan
    error_files: List[tuple]  # Files that had errors
    total_scanned: int
    blockchain_transactions_created: int = 0  # Number of on-chain transactions created (MintBlue only)
    db_records_created: int = 0  # Total DB records created (includes both reused-hash inserts and on-chain inserts)
    new_records_created: int = 0  # Number of DB records created for new hashes (trial or on-chain)
    was_stopped: bool = False  # Indicates if operation was stopped
    skipped_files: int = 0  # Number of skipped files when stopping


class RegistrationService:
    """
    Unified service for file scanning and registration.
    Combines FileScanner and RegistrationService functionality without wrapper layers.
    """

    def __init__(self):
        """Initialize the unified registration service."""
        # Repositories
        self.file_record_repo = FileRecordRepository()
        self.settings_repo = SettingsRepository()
        self.directory_repo = DirectoryRepository()

        # Blockchain service
        self.blockchain_service = BlockchainService()

        # Operation state
        self._should_stop = False
        self._operation_lock = threading.Lock()
        self._current_operation = None

        # Progress tracking
        self.progress_callback = None

    def set_progress_callback(self, callback: Optional[Callable]):
        """Set or update the progress callback for frontend communication."""
        self.progress_callback = callback

    def update_blockchain_client(self, new_client):
        """Update the blockchain client instance used by this service."""
        print(f"[NotarizationService] Updating blockchain client to: {type(new_client).__name__}")
        self.blockchain_service.update_client(new_client)

    def request_stop(self):
        """Request the current operation to stop."""
        print("[NotarizationService] Stop requested")
        self._should_stop = True

        # Immediately report stop status to frontend
        if self.progress_callback:
            self.progress_callback('stopping', {})

    def scan_and_process(self, record_new_files: bool = None) -> dict:
        """
        Unified method for all scanning and processing operations.

        Args:
            record_new_files:
                - None: Use the 'automatic' setting from database (for startup)
                - True: Process everything immediately (for manual action)
                - False: Only scan and count new files (startup with automatic=false)

        Returns:
            Dictionary with operation results
        """
        with self._operation_lock:
            if self._current_operation:
                return {
                    "success": False,
                    "message": "Another operation is already in progress"
                }
            self._current_operation = "scan_and_process"

        try:
            # Snapshot ALL settings at operation start to avoid race conditions
            operation_settings = self._snapshot_settings()

            # Determine operation mode
            if record_new_files is None:
                record_new_files = operation_settings.automatic
                print(f"[NotarizationService] Using automatic setting: {record_new_files}")

            print(f"[NotarizationService] Starting scan_and_process with record_new_files={record_new_files}")

            # Check for configured directories
            directories = self.directory_repo.get_enabled()
            if not directories:
                print("[NotarizationService] No directories configured")

                # Immediately report completion for no-directories case
                self._send_completion_event('no_directories', 0, 0, 0, 0, 0, 0, 0, False)

                return {
                    "success": True,
                    "message": "No directories configured",
                    "record_new_files": record_new_files,
                    "immediate_results": {
                        "status": "no_directories",
                        "directories_count": 0
                    }
                }

            # Reset operation state
            self._should_stop = False

            # Start the actual scanning
            scan_result = self._perform_scan(directories, record_new_files, operation_settings)

            # Determine final status
            final_status = "stopped" if scan_result.was_stopped else "complete"

            # Send completion event immediately (scanner self-reports)
            self._send_completion_event(
                status=final_status,
                files_examined=scan_result.total_scanned,
                files_verified=scan_result.verified_unchanged,
                files_updated=max(0, scan_result.db_records_created - scan_result.new_records_created),
                files_recorded=scan_result.new_records_created,
                files_error=len(scan_result.error_files),
                files_skipped=scan_result.skipped_files,
                files_needing_blockchain=scan_result.new_files_count,
                was_stopped=scan_result.was_stopped
            )

            # Persist last run summary for both complete and stopped states
            self._update_last_run_summary(scan_result, record_new_files, final_status)

            return {
                "success": True,
                "message": f"Operation {final_status}",
                "record_new_files": record_new_files,
                "immediate_results": {
                    "status": "started",
                    "directories_count": len(directories)
                }
            }

        finally:
            with self._operation_lock:
                self._current_operation = None

    def stop_registration(self) -> dict:
        """
        Stop any ongoing operation.

        Returns:
            Dictionary with stop status
        """
        self.request_stop()
        return {
            "success": True,
            "message": "Stop requested"
        }

    def _snapshot_settings(self) -> OperationSettings:
        """Capture all settings at operation start to avoid race conditions."""
        return OperationSettings(
            automatic=self.settings_repo.get_automatic(),
            blockchain_target=self.settings_repo.get_blockchain_target(),
            max_file_size=self.settings_repo.get_max_file_size(),
            api_key=self.settings_repo.get_api_key() or '',
            project_id=self.settings_repo.get_project_id() or ''
        )

    def _perform_scan(self, directories: List, record_new_files: bool,
                     settings: OperationSettings) -> ScanResult:
        """
        Perform the actual scanning operation.

        This is the core scanning logic merged from FileScanner.
        """
        print(f"[NotarizationService] Scanning {len(directories)} directories")

        # Initialize counters
        auto_processed = 0
        new_files = []
        verified_unchanged = 0
        error_files = []
        total_scanned = 0
        blockchain_transactions_created = 0
        db_records_created = 0
        new_records_created = 0
        files_processed = 0

        # Count total files for progress tracking
        total_files_to_process = 0
        for directory in directories:
            if self._should_stop:
                break
            total_files_to_process += self._count_physical_files(
                directory.path, directory.recursive
            )

        print(f"[NotarizationService] Total files to process: {total_files_to_process}")

        # Send initial progress
        self._send_progress_event(
            status="processing",
            files_examined=0,
            files_verified=0,
            files_updated=0,
            files_recorded=0,
            files_skipped=0,
            files_error=0,
            total_files=total_files_to_process,
            current_file="Starting..."
        )

        # Scan each directory
        for directory in directories:
            if self._should_stop:
                break

            print(f"[NotarizationService] Scanning {directory.path}")

            # Cumulative counters for real-time updates
            cumulative_counters = {
                'auto_processed': auto_processed,
                'new_files': len(new_files),
                'verified_unchanged': verified_unchanged,
                'error_files': len(error_files),
                'total_scanned': total_scanned,
                'blockchain_transactions_created': blockchain_transactions_created,
                'db_records_created': db_records_created,
                'new_records_created': new_records_created
            }

            # Scan the directory
            dir_result = self._scan_single_directory(
                directory_path=directory.path,
                recursive=directory.recursive,
                record_new_files=record_new_files,
                settings=settings,
                files_processed_so_far=files_processed,
                total_files=total_files_to_process,
                cumulative_counters=cumulative_counters
            )

            # Aggregate results
            auto_processed += dir_result['auto_processed']
            new_files.extend(dir_result['new_files'])
            verified_unchanged += dir_result['verified_unchanged']
            error_files.extend(dir_result['error_files'])
            total_scanned += dir_result['total_scanned']
            blockchain_transactions_created += dir_result.get('blockchain_transactions_created', 0)
            db_records_created += dir_result.get('db_records_created', 0)
            new_records_created += dir_result.get('new_records_created', 0)
            files_processed += dir_result['total_scanned']

        # Calculate skipped files if stopped
        was_stopped = self._should_stop
        skipped_count = max(0, total_files_to_process - files_processed) if was_stopped else 0

        print(f"[NotarizationService] Scan complete. Stopped: {was_stopped}, "
              f"Auto-processed: {auto_processed}, New files: {len(new_files)}, "
              f"Blockchain TXs: {blockchain_transactions_created}, Skipped: {skipped_count}")

        return ScanResult(
            auto_processed=auto_processed,
            new_files_count=len(new_files),
            files_needing_registration=new_files,
            verified_unchanged=verified_unchanged,
            error_files=error_files,
            total_scanned=total_scanned,
            blockchain_transactions_created=blockchain_transactions_created,
            db_records_created=db_records_created,
            new_records_created=new_records_created,
            was_stopped=was_stopped,
            skipped_files=skipped_count
        )

    def _scan_single_directory(self, directory_path: str, recursive: bool,
                               record_new_files: bool, settings: OperationSettings,
                               files_processed_so_far: int, total_files: int,
                               cumulative_counters: Dict) -> Dict:
        """Scan a single directory and process files."""
        directory_path = Path(directory_path)
        result = {
            'auto_processed': 0,
            'new_files': [],
            'verified_unchanged': 0,
            'error_files': [],
            'total_scanned': 0,
            'blockchain_transactions_created': 0,
            'db_records_created': 0,
            'new_records_created': 0
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
                            file_path=file_path,
                            record_new_files=record_new_files,
                            settings=settings,
                            result=result,
                            current_file_number=files_processed_so_far + files_in_dir_processed,
                            total_files=total_files,
                            cumulative_counters=cumulative_counters
                        )
                        files_in_dir_processed += 1
            else:
                for item in directory_path.iterdir():
                    if self._should_stop:
                        break
                    if item.is_file():
                        self._process_file(
                            file_path=item,
                            record_new_files=record_new_files,
                            settings=settings,
                            result=result,
                            current_file_number=files_processed_so_far + files_in_dir_processed,
                            total_files=total_files,
                            cumulative_counters=cumulative_counters
                        )
                        files_in_dir_processed += 1

        except PermissionError as e:
            result['error_files'].append((str(directory_path), f"Permission denied: {str(e)}"))
        except Exception as e:
            result['error_files'].append((str(directory_path), str(e)))

        return result

    def _process_file(self, file_path: Path, record_new_files: bool,
                     settings: OperationSettings, result: Dict,
                     current_file_number: int, total_files: int,
                     cumulative_counters: Dict):
        """Process a single file according to the operation mode."""
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
                settings.blockchain_target
            ):
                result['verified_unchanged'] += 1
                self._send_realtime_progress(
                    file_path, current_file_number, total_files,
                    result, cumulative_counters
                )
                return

            # File needs processing - generate hash
            file_hash = self._generate_hash(str(file_path), settings.max_file_size)
            if not file_hash:
                result['error_files'].append((str(file_path), "Hash generation failed"))
                self._send_realtime_progress(
                    file_path, current_file_number, total_files,
                    result, cumulative_counters
                )
                return

            # Check if hash exists in database
            existing_records = self.file_record_repo.find_by_hash(
                file_hash, settings.blockchain_target
            )

            if existing_records:
                # Hash exists - create DB record with existing tx_id (risk-free operation)
                self._create_db_record_with_existing_tx(
                    file_path, file_size, modified_date, file_hash,
                    existing_records[0].tx_id
                )
                result['auto_processed'] += 1
                # DB record inserted (reused-hash)
                result['db_records_created'] += 1
                print(f"[NotarizationService] Auto-processed file with existing hash: {file_path}")

            else:
                # New hash - behavior depends on record_new_files parameter
                if not record_new_files:
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
                    # Process new files
                    if settings.blockchain_target == 'local':
                        # Trial Mode: DB-only insert with deterministic local tx_id
                        tx_id = f"local_tx_{file_hash}"
                        self._create_db_record_with_new_tx(
                            file_path, file_size, modified_date, file_hash, tx_id
                        )
                        # Note: auto_processed is NOT incremented for new hashes
                        # auto_processed is only for reused hashes (existing records)
                        result['db_records_created'] += 1
                        result['new_records_created'] += 1
                        print(f"[NotarizationService] Trial mode: created DB record (no blockchain): {file_path}")
                    else:
                        # On-chain mode: create blockchain transaction first
                        tx_id = self.blockchain_service.create_transaction(file_hash, settings.blockchain_target)
                        if tx_id:
                            self._create_db_record_with_new_tx(
                                file_path, file_size, modified_date, file_hash, tx_id
                            )
                            # Note: auto_processed is NOT incremented for new hashes
                            # auto_processed is only for reused hashes (existing records)
                            result['blockchain_transactions_created'] += 1
                            result['db_records_created'] += 1
                            result['new_records_created'] += 1
                            print(f"[NotarizationService] Created blockchain TX and DB record: {file_path}")
                        else:
                            result['error_files'].append((str(file_path), "Blockchain transaction failed"))

            # Send real-time progress update
            self._send_realtime_progress(
                file_path, current_file_number, total_files,
                result, cumulative_counters
            )

        except PermissionError:
            result['error_files'].append((str(file_path), "Permission denied"))
        except Exception as e:
            result['error_files'].append((str(file_path), str(e)))

        # Always send progress update even for errors
        self._send_realtime_progress(
            file_path, current_file_number, total_files,
            result, cumulative_counters
        )

    def _send_realtime_progress(self, file_path: Path, current_file_number: int,
                                total_files: int, result: Dict, cumulative_counters: Dict):
        """Send real-time progress updates to frontend."""
        if not self.progress_callback or total_files == 0:
            return

        # Calculate cumulative counts
        total_scanned = cumulative_counters['total_scanned'] + result['total_scanned']
        total_verified = cumulative_counters['verified_unchanged'] + result['verified_unchanged']
        cumulative_counters['auto_processed'] + result['auto_processed']
        cumulative_counters['blockchain_transactions_created'] + result['blockchain_transactions_created']
        total_db_records = cumulative_counters['db_records_created'] + result['db_records_created']
        total_new_records = cumulative_counters['new_records_created'] + result['new_records_created']
        total_new_files = cumulative_counters['new_files'] + len(result['new_files'])
        total_errors = cumulative_counters['error_files'] + len(result['error_files'])

        # Calculate categories for Activity box
        # Updated semantics:
        # - files_updated = reused-hash DB inserts = total_db_records - total_new_records
        # - files_recorded = new DB records (new hashes)
        hash_verified_count = max(0, total_db_records - total_new_records)
        files_processed_so_far = current_file_number + 1
        skipped_count = max(0, total_files - files_processed_so_far) if self._should_stop else 0

        # Send progress event matching the frontend's NotarizationProgress interface (clean)
        self._send_progress_event(
            status="processing",
            files_examined=total_scanned,
            files_verified=total_verified,
            files_updated=hash_verified_count,           # "Updated" = reused-hash DB inserts
            files_recorded=total_new_records,            # "New records" = new-hash DB inserts (trial + onchain)
            files_skipped=skipped_count,
            files_error=total_errors,
            total_files=total_files,
            files_needing_blockchain=total_new_files,
            current_file=str(file_path)
        )

    def _send_progress_event(self, status: str, files_examined: int, files_verified: int,
                             files_updated: int, files_recorded: int, files_skipped: int,
                             files_error: int, total_files: int, files_needing_blockchain: int = 0,
                             current_file: str = None):
        """Send progress event matching the frontend's NotarizationProgress interface (clean)."""
        if not self.progress_callback:
            return

        self.progress_callback('registration-progress', {
            'status': status,
            'files_examined': files_examined,
            'files_verified': files_verified,
            'files_updated': files_updated,
            'files_recorded': files_recorded,
            'files_skipped': files_skipped,
            'files_error': files_error,
            'total_files': total_files,
            'files_needing_blockchain': files_needing_blockchain,
            'current_file': current_file
        })

    def _send_completion_event(self, status: str, files_examined: int, files_verified: int,
                               files_updated: int, files_recorded: int,
                               files_error: int, files_skipped: int,
                               files_needing_blockchain: int, was_stopped: bool):
        """Send completion event immediately when scanner finishes (clean payload)."""
        if not self.progress_callback:
            return

        # Determine completion status
        if status == 'no_directories':
            completion_status = status
        elif was_stopped:
            completion_status = 'stopped'
        else:
            completion_status = 'complete'

        # Send unified operation-complete event
        self.progress_callback('operation-complete', {
            'status': completion_status,
            'files_examined': files_examined,
            'files_verified': files_verified,
            'files_updated': files_updated,
            'files_recorded': files_recorded,
            'files_error': files_error,
            'files_skipped': files_skipped,
            'files_needing_blockchain': files_needing_blockchain
        })

        # Also send final progress update for Activity box
        self._send_progress_event(
            status=completion_status,
            files_examined=files_examined,
            files_verified=files_verified,
            files_updated=files_updated,
            files_recorded=files_recorded,
            files_skipped=files_skipped,
            files_error=files_error,
            total_files=files_examined,
            current_file=None
        )

    def _generate_hash(self, file_path: str, max_file_size: int) -> Optional[str]:
        """Generate SHA-256 hash for a file."""
        file_path = Path(file_path)

        try:
            if not file_path.exists():
                print(f"[NotarizationService] File not found: {file_path}")
                return None

            # Check for large files
            file_size = file_path.stat().st_size
            if file_size > max_file_size:
                warning_msg = f"Large file - processing may take longer ({file_size / (1024*1024):.2f} MB)"
                print(f"[NotarizationService] {warning_msg}")
                # Send warning to frontend
                if self.progress_callback:
                    self.progress_callback('scanner-warning', {'message': warning_msg})

            # Generate the hash
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            print(f"[NotarizationService] Error generating hash: {str(e)}")
            return None

    def _count_physical_files(self, directory_path: str, recursive: bool) -> int:
        """Count all physical files in a directory."""
        directory_path = Path(directory_path)
        file_count = 0

        try:
            if not directory_path.exists() or not directory_path.is_dir():
                return 0

            if recursive:
                items_to_scan = directory_path.rglob('*')
            else:
                items_to_scan = directory_path.glob('*')

            for item_path in items_to_scan:
                try:
                    if item_path.is_file() and not item_path.is_symlink():
                        file_count += 1
                except OSError:
                    pass  # Skip files we can't access

        except PermissionError:
            print(f"[NotarizationService] Permission denied: {directory_path}")
        except Exception as e:
            print(f"[NotarizationService] Error counting files: {e}")

        return file_count

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

    def _update_last_run_summary(self, scan_result: ScanResult, record_new_files: bool, final_status: str):
        """Update the last run summary in settings."""
        completion_time = datetime.now(tz=timezone.utc).isoformat()

        # Calculate derived values
        # hash_verified_count = reused hash records (auto_processed only counts reused hashes after the fix)
        hash_verified_count = scan_result.auto_processed
        scan_result.verified_unchanged + hash_verified_count
        total_processed = scan_result.db_records_created  # All DB inserts across modes

        summary = {
            "files_scanned": scan_result.total_scanned,
            "files_verified": scan_result.verified_unchanged,
            "hash_verified_count": hash_verified_count,
            "processed_files": total_processed,
            "new_records_count": scan_result.new_records_created,  # Fixed: use new_records_created, not db_records_created
            "skipped_files": scan_result.skipped_files,
            "error_files": len(scan_result.error_files),
            "status": final_status,
            "completion_time": completion_time
        }

        self.settings_repo.set_last_run_summary(summary)

        # Update successful run timestamp if processing was done
        if final_status == "complete" and record_new_files and len(scan_result.error_files) == 0:
            self.settings_repo.set_last_successful_run(completion_time)



    def verify_file(self, file_path: str) -> dict:
        """
        Verify a file's registration status.

        Args:
            file_path: Path to the file to verify

        Returns:
            Dictionary with verification results
        """
        try:
            # Generate hash for the current file
            current_file_hash = self._generate_hash(
                file_path,
                self.settings_repo.get_max_file_size()
            )

            if not current_file_hash:
                return {
                    "status": "error_hash_generation",
                    "message": "Hash generation failed for the provided file.",
                    "verified": False,
                    "records": [],
                    "blockchain_verification": None,
                    "current_hash": None
                }

            # Helper to format record details
            def get_record_details_list(records_list):
                if not records_list:
                    return []
                return [
                    {
                        "file_path": r.file_path,
                        "file_name": r.file_name,
                        "size": r.size,
                        "modified_date": r.modified_date.isoformat() if r.modified_date else None,
                        "sha256": r.sha256,
                        "tx_id": r.tx_id,
                        "registered_at": r.registered_at if r.registered_at else None
                    }
                    for r in records_list
                ]

            # Lookup records by hash
            blockchain_target = self.settings_repo.get_blockchain_target()
            all_records_for_hash = self.file_record_repo.find_by_hash(
                current_file_hash, blockchain_target
            )

            if all_records_for_hash:
                blockchain_records = [r for r in all_records_for_hash
                                    if r.tx_id and not r.tx_id.startswith("local_")]
                local_records = [r for r in all_records_for_hash
                               if r.tx_id and r.tx_id.startswith("local_")]

                if blockchain_records:
                    # Verify against blockchain
                    oldest_blockchain_record = blockchain_records[0]

                    blockchain_verification = self.blockchain_service.verify_transaction(
                        oldest_blockchain_record.tx_id,
                        current_file_hash
                    )

                    return {
                        "status": blockchain_verification.get("status", "error_blockchain_verification"),
                        "message": blockchain_verification.get("message", "Blockchain verification result."),
                        "verified": blockchain_verification.get("status") == "verified" and
                                  blockchain_verification.get("hash_match", False),
                        "records": get_record_details_list(all_records_for_hash),
                        "blockchain_verification": blockchain_verification,
                        "current_hash": current_file_hash,
                        "hash_match": blockchain_verification.get("hash_match", False)
                    }

                elif local_records:
                    # Only local records exist
                    return {
                        "status": "local_record_found",
                        "message": "File has been found in local database. No blockchain record exists for this hash.",
                        "verified": True,
                        "records": get_record_details_list(all_records_for_hash),
                        "blockchain_verification": None,
                        "current_hash": current_file_hash,
                        "hash_match": True
                    }
                else:
                    return {
                        "status": "unknown_record_type",
                        "message": "No processable registration records found for this hash.",
                        "verified": False,
                        "records": get_record_details_list(all_records_for_hash),
                        "blockchain_verification": None,
                        "current_hash": current_file_hash
                    }
            else:
                # No records found
                return {
                    "status": "not_found_in_db",
                    "message": "No registration records found for this file.",
                    "verified": False,
                    "records": [],
                    "blockchain_verification": None,
                    "current_hash": current_file_hash
                }

        except Exception as e:
            print(f"[NotarizationService] Verify error: {str(e)}")
            return {
                "status": "error_verification_exception",
                "message": f"An error occurred during verification: {str(e)}",
                "verified": False,
                "records": [],
                "blockchain_verification": None,
                "current_hash": None
            }
