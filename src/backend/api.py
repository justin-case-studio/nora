"""
API module for the Nora application.
Exposes backend functionality to the frontend.
"""
import os
import sys
import math
import csv
from pathlib import Path
from datetime import datetime
from .registration.registration_service import RegistrationService
from .blockchain import get_blockchain_client
from .file_scanner.scanner import FileScanner

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from database.repositories import DirectoryRepository, FileRecordRepository, SettingsRepository
from database.models import Directory

# DEBUG: Print the file path of the loaded SettingsRepository module
if 'database.repositories' in sys.modules:
    print(f"[API DEBUG] Loaded database.repositories from: {sys.modules['database.repositories'].__file__}")
else:
    print("[API DEBUG] database.repositories module not found in sys.modules at initial check.")


class NoraAPI:
    """API for the Nora application."""

    def __init__(self):
        """Initialize the API."""
        print("[API DEBUG] In NoraAPI.__init__ - BEFORE SettingsRepository()") # DEBUG LINE
        self.settings_repo = SettingsRepository()
        print(f"[API DEBUG] In __init__ - self.settings_repo ID: {id(self.settings_repo)}")
        try:
            print(f"[API DEBUG] In __init__ - self.settings_repo.DB_SCHEMA_VERSION_FOR_TEST: {self.settings_repo.DB_SCHEMA_VERSION_FOR_TEST}")
        except AttributeError:
            print("[API DEBUG] In __init__ - self.settings_repo has NO DB_SCHEMA_VERSION_FOR_TEST")
        self.registration_service = RegistrationService()
        self.blockchain_client = get_blockchain_client()
        self.directory_repo = DirectoryRepository()
        self.file_record_repo = FileRecordRepository()
        print("[API DEBUG] Re-initializing self.settings_repo in NoraAPI.__init__")

        # This internal callback storage might be unnecessary now, review later if needed.
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """Set a callback function provided by the wrapper."""
        # This should store the NoraApiWrapper.progress_callback method
        self.progress_callback = callback
        # Crucially, also pass it down to the service instance immediately
        # This ensures the service always uses the *latest* callback set on the API
        if self.registration_service:
             self.registration_service.set_progress_callback(callback)

    def _get_and_notify_dashboard_stats(self):
        """Helper to calculate stats and notify frontend via the assigned callback."""
        print("[API] Recalculating and notifying dashboard stats...")
        stats = self.get_dashboard_stats()
        if stats and self.progress_callback: # Check if callback is set
            event_package = {
                'event_name': 'dashboard-stats-updated',
                'data': stats
            }
            # Call the stored wrapper's callback directly, passing None for event_name
            # because the actual event name is packaged inside event_package.
            print(f"  Calling stored callback for dashboard stats: {self.progress_callback}")
            self.progress_callback(None, event_package)
        elif not self.progress_callback:
             print("[API] Cannot notify dashboard stats, progress_callback not set.")

    def register_now(self):
        """
        Start the registration process immediately.
        Always processes everything (record_new_files=True).

        Returns:
            Dictionary with registration results
        """
        # Always process everything immediately when manually triggered
        return self.registration_service.scan_and_process(record_new_files=True)

    def verify_file(self, file_path):
        """Verify a file by path: hash it server-side, then delegate to verify_by_hash.

        Used by the Verify dialog when the frontend cannot read the File contents
        itself (e.g. OS-to-webview drops on WebKit2GTK, where dataTransfer.files
        does not expose readable File objects).
        """
        print(f"[API] verify_file called for {file_path}")
        if not file_path or not os.path.exists(file_path):
            return {
                "status": "error_file_not_found",
                "message": f"File not found: {file_path}",
                "verified": False,
                "records": [],
                "primary_record_used": None,
                "blockchain_verification_details": None,
                "current_hash": None
            }

        file_hash = self.registration_service._generate_hash(
            file_path,
            self.settings_repo.get_max_file_size()
        )
        if not file_hash:
            return {
                "status": "error_hash_generation",
                "message": "Could not compute hash for the selected file.",
                "verified": False,
                "records": [],
                "primary_record_used": None,
                "blockchain_verification_details": None,
                "current_hash": None
            }

        return self.verify_by_hash(file_hash)

    def verify_by_hash(self, sha256_hash):
        """
        Verify a file based on its SHA-256 hash, respecting the current blockchain_target setting.

        Args:
            sha256_hash: The SHA-256 hash of the file to verify.

        Returns:
            Dictionary structured similarly to RegistrationService.verify_file responses.
        """
        print(f"[API] Verifying hash: {sha256_hash[:10]}...{sha256_hash[-10:]}")
        try:
            blockchain_target = self.settings_repo.get_blockchain_target()
            print(f"  [Verify] Current blockchain_target: {blockchain_target}")

            # Get records already filtered by the repository based on blockchain_target
            relevant_records_for_hash = self.file_record_repo.find_by_hash(sha256_hash, blockchain_target)
            formatted_records = [self._record_to_dict(r) for r in relevant_records_for_hash]

            if not relevant_records_for_hash:
                print(f"  [Verify] Hash not found in database for target '{blockchain_target}'.")
                return {
                    "status": "not_found_in_db",
                    "message": f"No registration records found for this file in the current mode ({blockchain_target}).",
                    "verified": False,
                    "records": [], # No records for this mode
                    "primary_record_used": None,
                    "blockchain_verification_details": None,
                    "current_hash": sha256_hash
                }

            print(f"  [Verify] Found {len(relevant_records_for_hash)} record(s) for hash in '{blockchain_target}' mode.")

            # If in 'local' mode, these are local records.
            if blockchain_target == 'local':
                print("  [Verify] Operating in 'local' mode. Records are considered local.")
                # oldest_local_record = relevant_records_for_hash[0] # find_by_hash sorts by date
                oldest_local_record = relevant_records_for_hash[0] # find_by_hash sorts by date ASC (oldest first)
                return {
                    "status": "local_record_found",
                    "message": "File record found in the local trial ledger.",
                    "verified": True, # Considered 'verified' as it's known in this local context
                    "records": formatted_records,
                    "primary_record_used": self._record_to_dict(oldest_local_record), # The specific record used for verification
                    "blockchain_verification_details": None, # No blockchain check in local mode from here
                    "current_hash": sha256_hash,
                    "hash_match": True
                }

            # If in 'MintBlue' mode (or any other non-local mode that implies blockchain)
            elif blockchain_target == 'MintBlue':
                print("  [Verify] Operating in 'MintBlue' mode. Attempting blockchain verification.")
                # Assuming find_by_hash sorts by date, oldest is first
                oldest_onchain_candidate_record = relevant_records_for_hash[0]
                tx_id_to_verify = oldest_onchain_candidate_record.tx_id

                if not tx_id_to_verify or tx_id_to_verify.startswith('mock_'): # Should not happen if repo filter is correct
                    print(f"  [Verify Error] Record in MintBlue mode has invalid tx_id: {tx_id_to_verify}")
                    return {
                        "status": "error_invalid_record_for_mode",
                        "message": "Found record unsuitable for blockchain verification in the current mode.",
                        "verified": False,
                        "records": formatted_records,
                        "primary_record_used": None,
                        "blockchain_verification_details": None,
                        "current_hash": sha256_hash
                    }

                print(f"   Verifying blockchain TX ID: {tx_id_to_verify} for hash {sha256_hash[:10]}...")
                blockchain_verification_result = self.blockchain_client.verify_transaction(tx_id_to_verify, sha256_hash)
                print(f"  [Verify] Blockchain client validation result: {blockchain_verification_result}")

                explorer_url = ""
                if blockchain_verification_result.get("status") == "verified":
                    explorer_url_template = self.settings_repo.get_blockchain_explorer_url()
                    tx_id_from_bc_client = blockchain_verification_result.get('tx_id', tx_id_to_verify)
                    if explorer_url_template and tx_id_from_bc_client:
                        explorer_url = explorer_url_template.format(txid=tx_id_from_bc_client)

                details_payload = {
                    **(blockchain_verification_result if isinstance(blockchain_verification_result, dict) else {}),
                    "blockchain_explorer_url": explorer_url
                    # Removed timestamp override - use blockchain timestamp for blockchain verification details
                }

                return {
                    "status": blockchain_verification_result.get("status", "error_blockchain_verification"),
                    "message": blockchain_verification_result.get("message", "Blockchain verification result."),
                    # Overall 'verified' is true if BC status is 'verified' AND hash matches
                    "verified": blockchain_verification_result.get("status") == "verified" and blockchain_verification_result.get("hash_match", False),
                    "records": formatted_records, # These are the on-chain DB records for this hash
                    "primary_record_used": self._record_to_dict(oldest_onchain_candidate_record), # The specific record used for verification
                    "blockchain_verification_details": details_payload,
                    "current_hash": sha256_hash,
                    "hash_match": blockchain_verification_result.get("hash_match", False)
                }
            else:
                # Fallback for unknown blockchain_target, though settings should prevent this.
                print(f"  [Verify Error] Unknown blockchain_target: {blockchain_target}")
                return {
                    "status": "error_unknown_target_mode",
                    "message": f"Verification cannot proceed with unknown mode: {blockchain_target}",
                    "verified": False,
                    "records": formatted_records,
                    "primary_record_used": None,
                    "blockchain_verification_details": None,
                    "current_hash": sha256_hash
                }

        except Exception as e:
            print(f"[API Verify Error] Error during verification for hash {sha256_hash[:10]}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error_api_verification_exception",
                "message": f"An internal API error occurred during verification: {str(e)}",
                "verified": False,
                "records": [],
                "primary_record_used": None,
                "blockchain_verification_details": None,
                "current_hash": sha256_hash
            }

    def get_directories(self):
        """
        Get all directories.

        Returns:
            List of directories
        """
        directories = self.directory_repo.get_all()
        return [self._directory_to_dict(d) for d in directories]

    def add_directory(self, path, recursive=True):
        """
        Add a directory to monitor.

        Args:
            path: Path to the directory
            recursive: Whether to scan subdirectories

        Returns:
            Dictionary with the added directory
        """
        # Normalize path
        path = str(Path(path).resolve())

        # Check if the directory exists
        if not os.path.exists(path) or not os.path.isdir(path):
            return {"error": "Directory does not exist"}

        # Check if the directory is already monitored
        if self.directory_repo.exists(path):
            return {"error": "Directory is already monitored"}

        # Create directory
        directory = Directory.from_path(path, recursive)

        # Save to database
        directory = self.directory_repo.create(directory)
        self._get_and_notify_dashboard_stats() # Notify after adding

        return self._directory_to_dict(directory)

    def remove_directory(self, directory_id):
        """
        Remove a directory from monitoring.

        Args:
            directory_id: ID of the directory to remove

        Returns:
            Dictionary with the result
        """
        # Check if the directory exists
        directory = self.directory_repo.find_by_id(directory_id)

        if not directory:
            return {"error": "Directory not found"}

        # Delete from database
        self.directory_repo.delete(directory_id)
        self._get_and_notify_dashboard_stats() # Notify after removing

        return {"success": True}

    def update_directory(self, directory_id, recursive=None, enabled=None):
        """
        Update a directory's settings.

        Args:
            directory_id: ID of the directory to update
            recursive: Whether to scan subdirectories
            enabled: Whether the directory is enabled

        Returns:
            Dictionary with the updated directory
        """
        # Check if the directory exists
        directory = self.directory_repo.find_by_id(directory_id)

        if not directory:
            return {"error": "Directory not found"}

        # Update settings
        if recursive is not None:
            directory.recursive = recursive

        if enabled is not None:
            directory.enabled = enabled

        # Save to database
        directory = self.directory_repo.update(directory)
        self._get_and_notify_dashboard_stats() # Notify after updating

        return self._directory_to_dict(directory)

    def get_records(self, limit=100, offset=0):
        """
        Get registration records, filtered by the current blockchain_target setting.

        Args:
            limit: Maximum number of records to return
            offset: Offset for pagination

        Returns:
            Dictionary with records and pagination info
        """
        blockchain_target = self.settings_repo.get_blockchain_target()
        print(f"[API GetRecords] Fetching records for blockchain_target: {blockchain_target}")

        records = self.file_record_repo.get_all(blockchain_target, limit, offset)
        total = self.file_record_repo.count(blockchain_target)

        return {
            "records": [self._record_to_dict(r) for r in records],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def search_records(self, search_term, limit=100, offset=0, start_date=None, end_date=None):
        """
        Search for file records with pagination and optional date filtering.

        Args:
            search_term: The term to search for (can be empty).
            limit: Max number of records to return.
            offset: Number of records to skip for pagination.
            start_date: The start of the date range (YYYY-MM-DD).
            end_date: The end of the date range (YYYY-MM-DD).

        Returns:
            Dictionary containing records and pagination info.
        """
        try:
            blockchain_target = self.settings_repo.get_blockchain_target()

            # The search method now handles an empty search_term and date ranges
            records = self.file_record_repo.search(
                search_term, blockchain_target, limit, offset, start_date, end_date
            )

            # Get an accurate total count based on the same search criteria
            total = self.file_record_repo.count_search_results(
                search_term, blockchain_target, start_date, end_date
            )

            return {
                "records": [self._record_to_dict(r) for r in records],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            print(f"Error in search_records: {e}")
            # Consider more specific error handling
            return {"records": [], "total": 0, "limit": limit, "offset": offset, "error": str(e)}

    def get_settings(self):
        """
        Get all application settings.

        Returns:
            Dictionary with settings, including the blockchain explorer URL template.
        """
        blockchain_mode = self.get_blockchain_mode()
        blockchain_target_preference = self.settings_repo.get_blockchain_target()
        explorer_url_template = self.settings_repo.get_blockchain_explorer_url() # Get the template

        return {
            "max_file_size": self.settings_repo.get_max_file_size(),
            "sdk_token": self.settings_repo.get_api_key() or "", # Use get_api_key
            "project_id": self.settings_repo.get_project_id() or "",
            "date_format": self.settings_repo.get_date_format(),
            "blockchain_mode": blockchain_mode["mode"],
            "is_local_blockchain": blockchain_mode["is_local"],
            "apiEndpoint": self.settings_repo.get_api_endpoint(),
            "blockchainTarget": blockchain_target_preference,
            "blockchainExplorerUrlTemplate": explorer_url_template,
            "has_completed_setup": not self.settings_repo.is_first_launch(),
            "first_setup_date": self.settings_repo.get_first_setup_date(),
            "automatic": self.settings_repo.get_automatic()
        }

    def update_settings(self, max_file_size=None, sdk_token=None, api_key=None, project_id=None, date_format=None):
        """
        Update application settings.

        Args:
            max_file_size: Maximum file size in bytes
            sdk_token: MintBlue SDK token
            api_key: (deprecated) same as sdk_token
            project_id: MintBlue project ID
            date_format: Date format preference

        Returns:
            Dictionary with updated settings
        """
        # Update settings
        if max_file_size is not None:
            self.settings_repo.set_max_file_size(max_file_size)

        if date_format is not None:
            self.settings_repo.set_date_format(date_format)

        if sdk_token is not None or api_key is not None or project_id is not None:
            # Get current values for any missing parameters
            current_sdk_token = self.settings_repo.get_api_key()
            current_project_id = self.settings_repo.get_project_id()

            # Use current values if not provided
            effective_token = sdk_token if sdk_token is not None else (api_key if api_key is not None else current_sdk_token)
            project_id = project_id if project_id is not None else current_project_id

            # Save credentials persistently via repository
            self.settings_repo.set_api_key(effective_token)
            self.settings_repo.set_project_id(project_id)

            # Update blockchain client (in memory)
            self.blockchain_client.set_credentials(effective_token, project_id)

        return self.get_settings()

    def test_api_connection(self):
        """
        Test the connection to the MintBlue API.

        Returns:
            Dictionary with test results
        """
        # Test connection
        success = self.blockchain_client.test_connection()

        return {"success": success}

    def get_blockchain_mode(self):
        """
        Get the current blockchain mode based on settings.
        Trial Mode is represented by blockchainTarget == 'local'.
        """
        target = self.settings_repo.get_blockchain_target()
        is_local = (target == 'local')
        return {
            "mode": target,
            "is_local": is_local
        }

    def _directory_to_dict(self, directory):
        """Convert a Directory object to a dictionary."""
        return {
            "id": directory.id,
            "path": directory.path,
            "recursive": directory.recursive,
            "enabled": directory.enabled,
            "added_date": directory.added_date
        }

    def _record_to_dict(self, record):
        """Convert a FileRecord object to a dictionary."""
        return {
            "id": record.id,
            "file_path": record.file_path,
            "file_name": record.file_name,
            "size": record.size,
            "modified_date": record.modified_date,
            "sha256": record.sha256,
            "tx_id": record.tx_id,
            "registered_at": record.registered_at,
            "user_notes": record.user_notes
        }

    def update_file_record_notes(self, record_id, user_notes):
        """
        Update the user notes for a file record.

        Args:
            record_id: ID of the file record to update
            user_notes: The new user notes text

        Returns:
            Dictionary with the result
        """
        try:
            # Validate that the record exists
            record = self.file_record_repo.find_by_id(record_id)
            if not record:
                return {"success": False, "error": "File record not found"}

            # Update the notes
            success = self.file_record_repo.update_user_notes(record_id, user_notes)

            if success:
                return {"success": True, "message": "User notes updated successfully"}
            else:
                return {"success": False, "error": "Failed to update user notes"}

        except Exception as e:
            print(f"[API] Error updating user notes for record {record_id}: {str(e)}")
            return {"success": False, "error": f"An error occurred: {str(e)}"}

    # --- New Method for Dashboard Stats ---
    def get_dashboard_stats(self):
        """
        Calculate and return statistics for the dashboard, respecting the current blockchain_target.
        """
        print("[API] Calculating dashboard stats...")
        try:
            blockchain_target = self.settings_repo.get_blockchain_target()
            print(f"  [Stats Detail] Using blockchain_target: {blockchain_target} for registered counts and last date.")

            # 1. Count Monitored Directories
            directories = self.directory_repo.get_all() # Get all, not just enabled
            dir_count = len(directories)
            print(f"  [Stats Detail] Directory Count: {dir_count}")

            # 2. Count Registered Files (Records) for the current blockchain_target
            registered_count = self.file_record_repo.count(blockchain_target)
            print(f"  [Stats Detail] Registered Record Count ({blockchain_target}): {registered_count}")

            # 3. Count Total Physical Files in Enabled Directories
            temp_scanner = FileScanner()
            total_physical_files = 0
            enabled_directories = [d for d in directories if d.enabled]
            print(f"  [Stats Detail] Counting in {len(enabled_directories)} enabled directories...")
            for directory in enabled_directories:
                count_in_dir = temp_scanner.count_physical_files(directory.path, directory.recursive)
                total_physical_files += count_in_dir
            print(f"  [Stats Detail] Total Physical File Count: {total_physical_files}")

            # 4. Get Last Successful Notarization Run Timestamp
            last_successful_run = self.settings_repo.get_last_successful_run()
            print(f"  [Stats Detail] Last Successful Registration Run: {last_successful_run}")

            # 5. Get Last Run Summary (for activity display)
            last_run_summary = self.settings_repo.get_last_run_summary()
            print(f"  [Stats Detail] Last Run Summary: {last_run_summary}")

            stats = {
                "directories": dir_count,
                "registered_files": registered_count,
                "total_files": total_physical_files, # Use the accurate count
                "last_registration": last_successful_run if last_successful_run else '',
                "last_run_summary": last_run_summary  # Add last run summary data
            }
            print(f"[API] Dashboard stats calculated successfully: {stats}")
            return stats

        except Exception as e:
            # Log the specific error before returning zeros
            print(f"[API CRITICAL] Error during dashboard stats calculation: {str(e)}")
            import traceback
            traceback.print_exc() # Print full traceback
            # Return default/zeroed stats on error
            return {
                "directories": 0,
                "registered_files": 0,
                "total_files": 0,
                "last_registration": '',
                "last_run_summary": {}
            }
    # ------------------------------------

    # --- Granular Update Methods for Auto-Save ---
    def update_single_setting(self, key, value):
        """Update a single setting value."""
        print(f"[API] Updating single setting: Key='{key}', Value='{value}'")
        try:
            db_key = key # Default, will be overridden by specific handlers

            if key == 'dateFormat':
                 db_key = 'date_format'
                 self.settings_repo.set_date_format(value)
            elif key == 'maxFileSize':
                 db_key = 'max_file_size'
                 self.settings_repo.set_max_file_size(int(value))
            elif key == 'max_file_size':
                 db_key = 'max_file_size'
                 self.settings_repo.set_max_file_size(int(value))
            elif key == 'sdkToken' or key == 'apiKey':
                 db_key = 'mintblue_api_key'
                 self.settings_repo.set_api_key(value) # Set only the API key
                 # Update blockchain client with the new token and current project ID
                 current_project_id = self.settings_repo.get_project_id()
                 self.blockchain_client.set_credentials(value, current_project_id)
            elif key == 'projectId':
                 db_key = 'mintblue_project_id'
                 self.settings_repo.set_project_id(value) # Set only the project ID
                 # Update blockchain client with current token and new project ID
                 current_sdk_token = self.settings_repo.get_api_key()
                 self.blockchain_client.set_credentials(current_sdk_token, value)
            elif key == 'apiEndpoint':
                 db_key = 'api_endpoint'
                 self.settings_repo.set_api_endpoint(value)
            elif key == 'blockchainTarget':
                 db_key = 'blockchain_target'
                 self.settings_repo.set_blockchain_target(value)
                 # restart_required = True # No longer required

                 # Re-initialize our own blockchain client
                 self.blockchain_client = get_blockchain_client()
                 print(f"[API] Blockchain client re-initialized for API. New mode: {value}")

                 # Update the RegistrationService with the new client
                 if self.registration_service:
                     self.registration_service.update_blockchain_client(self.blockchain_client)
                     print("[API] RegistrationService's blockchain client updated.")
                 else:
                     print("[API] RegistrationService not available to update blockchain client.")

            elif key == 'automatic':
                 db_key = 'automatic'
                 # Convert string to boolean if needed
                 if isinstance(value, bool):
                     bool_value = value
                 elif isinstance(value, str):
                     bool_value = value.lower() in ['true', '1', 'yes', 'on']
                 else:
                     bool_value = bool(value)
                 self.settings_repo.set_automatic(bool_value)
                 print(f"[API] Automatic setting updated from '{value}' (type: {type(value).__name__}) to: {bool_value}")

            else:
                 print(f"[API] Received unhandled single setting key: '{key}'")
                 return { "success": False, "error": f"Unhandled setting key: {key}" }

            # Changed log message slightly for clarity
            print(f"[API] Setting '{key}' (DB key '{db_key}') processed. Value: '{value}'.")
            response = { "success": True, "key": key, "value": value }
            # if restart_required: # No longer used
            #    response["message"] = "Setting saved. Restart required for change to take effect."
            # Instead, provide a direct confirmation if it was blockchainTarget
            if key == 'blockchainTarget':
                response["message"] = f"Operating Mode changed to {value}. Change is now active."
            elif key in ['sdkToken', 'apiKey', 'projectId'] and self.settings_repo.get_blockchain_target() == 'MintBlue':
                response["message"] = f"{key} updated. Restart may be required if switching from Trial to Blockchain mode was just performed."
            return response

        except ValueError as e:
            print(f"[API] Type Error updating single setting '{key}' with value '{value}': {str(e)}")
            return { "success": False, "error": f"Invalid value type for {key}: {str(e)}" }
        except Exception as e:
            print(f"[API] Error updating single setting '{key}': {str(e)}")
            import traceback
            traceback.print_exc()
            return { "success": False, "error": str(e) }
    # -------------------------------------------

    def get_registration_activity(self, days=30):
        """
        Get the daily registration activity for the current mode.

        Args:
            days (int): The number of days of activity to retrieve.

        Returns:
            list: A list of dictionaries with 'date' and 'count'.
        """
        try:
            # Get the current blockchain mode from settings to filter the activity
            blockchain_target = self.settings_repo.get_blockchain_target()
            print(f"[API] Fetching registration activity for target '{blockchain_target}' for the last {days} days.")

            activity_data = self.file_record_repo.get_registration_activity_by_day(
                blockchain_target=blockchain_target,
                days=days
            )

            return activity_data
        except Exception as e:
            print(f"❌ [API] Error fetching registration activity: {e}")
            # Return an empty list or an error structure in case of failure
            return {"error": f"An unexpected error occurred: {str(e)}"}

    # --- Add Stop Endpoint ---
    def stop_registration(self):
        """Request the ongoing registration process to stop."""
        print("[API] Received request to stop registration.")
        try:
            if self.registration_service:
                self.registration_service.request_stop()
                return {"success": True, "message": "Stop request sent."}
            else:
                return {"success": False, "message": "Registration service not available."}
        except Exception as e:
            print(f"[API Stop Error] Error requesting stop: {str(e)}")
            return {"success": False, "message": f"Error requesting stop: {str(e)}"}
    def start_background_scan(self):
        """
        Start a background scan of all directories.
        Uses scan_and_process with record_new_files=False for discovery only.

        Returns:
            Dictionary with scan initiation status
        """
        print("[API] Starting background scan (discovery mode)")
        # Use scan_and_register with False to only scan, not process
        return self.scan_and_register(process_new_files=False)

    def clear_registration_cache(self):
        """
        Clear any cached state.
        Note: The new architecture doesn't use caching, so this is a no-op.

        Returns:
            Dictionary with success status
        """
        print("[API] Cache clearing requested (no-op in new architecture)")
        return {
            "success": True,
            "message": "Cache cleared (no-op)"
        }

    def scan_and_register(self, process_new_files: bool = None):
        """
        Unified scanning/registration endpoint.

        Args:
            process_new_files:
                - None: Use the 'automatic' setting from database (for startup)
                - True: Process everything immediately (for manual action)
                - False: Count only (for future use)

        Returns:
            Dictionary with scan initiation status
        """
        print(f"[API] Starting scan_and_register with process_new_files={process_new_files}")
        try:
            # Start the scan in a separate thread to avoid blocking
            import threading

            def run_scan():
                try:
                    # Set progress callback
                    self.registration_service.set_progress_callback(self.progress_callback)

                    # Run the unified scan method
                    result = self.registration_service.scan_and_process(process_new_files)

                    print(f"[API] Scan complete: {result.get('message', 'completed')}")

                    # Update dashboard stats
                    self._get_and_notify_dashboard_stats()

                except Exception as e:
                    print(f"[API] Error in scan thread: {str(e)}")
                    import traceback
                    traceback.print_exc()

            # Create and start thread
            scan_thread = threading.Thread(
                target=run_scan,
                name="ScanAndRegisterThread"
            )
            scan_thread.daemon = True
            scan_thread.start()

            return {
                "success": True,
                "message": "Scan started",
                "process_new_files": process_new_files
            }

        except Exception as e:
            print(f"[API] Error starting scan: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Failed to start scan: {str(e)}"
            }

    # --- CSV Export Methods ---
    def export_records_csv(self, search_term="", start_date="", end_date="", filename="nora_export.csv"):
        """Export filtered records to CSV file."""
        try:
            # Determine blockchain target from settings
            blockchain_target = self.settings_repo.get_blockchain_target()

            # Prepare export path
            export_dir = Path.home() / "Downloads"
            export_dir.mkdir(exist_ok=True)
            filepath = export_dir / filename

            # Stream results in pages to avoid hard caps and high memory usage
            page_size = 10000
            offset = 0
            total_exported = 0

            fieldnames = [
                'ID', 'File Name', 'File Path', 'Size (Bytes)', 'Size (Formatted)',
                'Modified Date', 'SHA256', 'Transaction ID', 'Registered At',
                'Blockchain Type', 'User Notes'
            ]

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                while True:
                    records = self.file_record_repo.search(
                        search_term if search_term else None,
                        blockchain_target,
                        limit=page_size,
                        offset=offset,
                        start_date=start_date if start_date else None,
                        end_date=end_date if end_date else None
                    )

                    if not records:
                        break

                    for record in records:
                        writer.writerow({
                            'ID': record.id,
                            'File Name': record.file_name,
                            'File Path': record.file_path,
                            'Size (Bytes)': record.size,
                            'Size (Formatted)': self._format_file_size(record.size),
                            'Modified Date': self._format_date_for_csv(record.modified_date),
                            'SHA256': record.sha256,
                            'Transaction ID': record.tx_id,
                            'Registered At': self._format_date_for_csv(record.registered_at),
                            'Blockchain Type': 'Local Blockchain' if not record.is_onchain else 'Bitcoin SV (MintBlue)',
                            'User Notes': record.user_notes or ''
                        })
                    total_exported += len(records)
                    offset += page_size

            print(f"[API] CSV export successful: {total_exported} records exported to {filepath}")
            return {
                'success': True,
                'filepath': str(filepath),
                'count': total_exported
            }

        except Exception as e:
            print(f"❌ [API] Error exporting CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def export_all_records_csv(self, filename="nora_all_records.csv"):
        """Export all records to CSV file."""
        try:
            # Determine blockchain target from settings
            blockchain_target = self.settings_repo.get_blockchain_target()

            # Prepare export path
            export_dir = Path.home() / "Downloads"
            export_dir.mkdir(exist_ok=True)
            filepath = export_dir / filename

            # Stream all records in pages
            page_size = 10000
            offset = 0
            total_exported = 0

            fieldnames = [
                'ID', 'File Name', 'File Path', 'Size (Bytes)', 'Size (Formatted)',
                'Modified Date', 'SHA256', 'Transaction ID', 'Registered At',
                'Blockchain Type', 'User Notes'
            ]

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                while True:
                    records = self.file_record_repo.get_all(blockchain_target, limit=page_size, offset=offset)
                    if not records:
                        break
                    for record in records:
                        writer.writerow({
                            'ID': record.id,
                            'File Name': record.file_name,
                            'File Path': record.file_path,
                            'Size (Bytes)': record.size,
                            'Size (Formatted)': self._format_file_size(record.size),
                            'Modified Date': self._format_date_for_csv(record.modified_date),
                            'SHA256': record.sha256,
                            'Transaction ID': record.tx_id,
                            'Registered At': self._format_date_for_csv(record.registered_at),
                            'Blockchain Type': 'Local Blockchain' if not record.is_onchain else 'Bitcoin SV (MintBlue)',
                            'User Notes': record.user_notes or ''
                        })
                    total_exported += len(records)
                    offset += page_size

            print(f"[API] CSV export all successful: {total_exported} records exported to {filepath}")
            return {
                'success': True,
                'filepath': str(filepath),
                'count': total_exported
            }

        except Exception as e:
            print(f"❌ [API] Error exporting all records CSV: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _format_file_size(self, bytes_size):
        """Helper method to format file size in human-readable format."""
        if bytes_size == 0:
            return '0 Bytes'
        k = 1024
        sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
        i = int(math.floor(math.log(bytes_size) / math.log(k)))
        return f"{round(bytes_size / math.pow(k, i), 2)} {sizes[i]}"

    def _format_date_for_csv(self, iso_date_string):
        """Format ISO date for better spreadsheet compatibility."""
        if not iso_date_string:
            return ''

        try:
            # Handle various ISO formats that might be stored
            iso_string = iso_date_string.replace('Z', '+00:00')

            # Try parsing with microseconds first
            try:
                dt = datetime.fromisoformat(iso_string)
            except ValueError:
                # Fallback: try without microseconds
                if '.' in iso_string:
                    # Remove microseconds part
                    iso_string = iso_string.split('.')[0]
                    if '+' in iso_string or iso_string.endswith('Z'):
                        # Handle timezone info
                        iso_string = iso_string.replace('Z', '').split('+')[0].split('-')[0]
                dt = datetime.fromisoformat(iso_string)

            # Return in universally recognized format: YYYY-MM-DD HH:MM:SS
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        except (ValueError, AttributeError) as e:
            print(f"⚠️ [API] Warning: Could not parse date '{iso_date_string}': {e}")
            return iso_date_string  # Fallback to original string

    def mark_setup_completed(self):
        """
        Mark that the user has completed the initial setup.

        Returns:
            Dictionary with success status
        """
        try:
            self.settings_repo.set_setup_completed()
            print("[API] Marked setup as completed")
            return {"success": True, "message": "Setup marked as completed"}
        except Exception as e:
            print(f"[API] Error marking setup completed: {str(e)}")
            return {"success": False, "error": str(e)}
