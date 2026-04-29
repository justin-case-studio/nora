"""
Repository for settings in the Notarizer application.
Handles database operations related to application settings.
"""
from ..db_manager import DatabaseManager
from ..models import Setting


class SettingsRepository:
    """Repository for application settings."""
    DB_SCHEMA_VERSION_FOR_TEST = "v_FINAL_TEST_123"

    def __init__(self):
        """Initialize the repository with a database manager."""
        self.db_manager = DatabaseManager()

    def get(self, key, default=None):
        """Get a setting value by its key."""
        query = 'SELECT * FROM settings WHERE key = ?'
        row = self.db_manager.execute_read(query, (key,), fetch_one=True)

        if row is None:
            return default

        setting = Setting.from_row(row)
        value_retrieved = setting.value
        return value_retrieved

    def set(self, key, value, encrypted=False):
        """Set a setting value."""
        query = '''
        INSERT OR REPLACE INTO settings (key, value, encrypted)
        VALUES (?, ?, ?)
        '''
        params = (key, str(value), int(encrypted))

        self.db_manager.execute_write(query, params)

    def get_all(self):
        """Get all settings."""
        query = 'SELECT * FROM settings'
        rows = self.db_manager.execute_read(query)

        return [Setting.from_row(row) for row in rows] if rows else []

    def get_max_file_size(self):
        """Get the maximum file size setting."""
        size_str = self.get('max_file_size', '2147483648')  # Default: 2GB
        return int(size_str)

    def set_max_file_size(self, size_bytes):
        """Set the maximum file size setting."""
        self.set('max_file_size', str(size_bytes))

    def get_api_key(self):
        """Get the MintBlue API key."""
        return self.get('mintblue_api_key', '')

    def set_api_key(self, api_key):
        """Set the MintBlue API key."""
        self.set('mintblue_api_key', api_key, encrypted=True)

    def get_project_id(self):
        """Get the MintBlue project ID."""
        return self.get('mintblue_project_id', '')

    def set_project_id(self, project_id):
        """Set the MintBlue project ID."""
        self.set('mintblue_project_id', project_id)

    def get_date_format(self):
        """Get the date format preference."""
        return self.get('date_format', 'default')

    def set_date_format(self, date_format):
        """Set the date format preference."""
        self.set('date_format', date_format)

    # --- Methods for api_endpoint (KEEP) ---
    def get_api_endpoint(self):
        """Get the API endpoint setting."""
        # Assuming a default value is needed, adjust if necessary
        return self.get('api_endpoint', '')

    def set_api_endpoint(self, endpoint):
        """Set the API endpoint setting."""
        self.set('api_endpoint', endpoint)

    # --- Blockchain Target Methods ---
    def get_blockchain_target(self):
        """Get the blockchain target preference ('local' or 'MintBlue', etc.)."""
        return self.get('blockchain_target', 'local') # Default to local

    def set_blockchain_target(self, target):
        """Set the blockchain target preference."""
        # Optional: Add validation for allowed target values?
        self.set('blockchain_target', target)
    # ---------------------------------

    # --- Blockchain Explorer URL Methods ---
    def get_blockchain_explorer_url(self):
        """Get the blockchain explorer URL template."""
        # Default to whatsonchain.com if not set
        return self.get('blockchain_explorer_url', 'https://whatsonchain.com/tx/{txid}')

    def set_blockchain_explorer_url(self, url_template):
        """Set the blockchain explorer URL template."""
        self.set('blockchain_explorer_url', url_template)
    # ------------------------------------

    # --- REMOVE automatic_scanning and scan_interval methods ---
    # def get_automatic_scanning(self):
    #     """Get the automatic scanning setting (True/False)."""
    #     # Store as 1 or 0, return as boolean. Default to False (0).
    #     return bool(int(self.get('automatic_scanning', '0')))
    #
    # def set_automatic_scanning(self, enabled):
    #     """Set the automatic scanning setting."""
    #     # Convert boolean to 1 or 0 for storage
    #     self.set('automatic_scanning', '1' if enabled else '0')
    #
    # def get_scan_interval(self):
    #     """Get the scan interval setting (in minutes)."""
    #     # Assuming a default, e.g., 60 minutes
    #     return int(self.get('scan_interval', '60'))
    #
    # def set_scan_interval(self, minutes):
    #     """Set the scan interval setting."""
    #     self.set('scan_interval', str(minutes))

    # --- SDK Token helpers (preferred terminology) ---
    def get_sdk_token(self):
        """Get the MintBlue SDK token (preferred)."""
        return self.get_api_key()  # Alias

    def set_sdk_token(self, sdk_token):
        """Set the MintBlue SDK token (preferred)."""
        self.set_api_key(sdk_token)
    # -------------------------------------------------

    def get_dummy_version_method_FINAL_TEST(self):
        return self.DB_SCHEMA_VERSION_FOR_TEST

    # --- Last Successful Registration Run Methods ---
    def get_last_successful_run(self):
        """Get the timestamp of the last successful registration run (no errors)."""
        return self.get('last_successful_registration_run', '')

    def set_last_successful_run(self, timestamp):
        """Set the timestamp of the last successful registration run."""
        self.set('last_successful_registration_run', timestamp)

    # --- Last Run Summary Methods ---
    def get_last_run_summary(self):
        """Get the complete summary of the last registration run."""
        import json
        summary_json = self.get('last_run_summary', '{}')
        try:
            return json.loads(summary_json) if summary_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_last_run_summary(self, summary):
        """Set the summary of the last registration run."""
        import json
        self.set('last_run_summary', json.dumps(summary))
    # -----------------------------------------------

    # --- Background Service Settings ---
    def get_automation_level(self):
        """Get the automation level setting ('manual', 'notify', 'autopilot')."""
        return self.get('automation_level', 'manual')  # Default to manual control

    def set_automation_level(self, level):
        """Set the automation level setting."""
        allowed_levels = ['manual', 'notify', 'autopilot']
        if level not in allowed_levels:
            raise ValueError(f"Invalid automation level: {level}. Must be one of {allowed_levels}")
        self.set('automation_level', level)

    def get_scan_interval_minutes(self):
        """Get the background scan interval in minutes."""
        return int(self.get('scan_interval_minutes', '30'))  # Default: 30 minutes

    def set_scan_interval_minutes(self, minutes):
        """Set the background scan interval in minutes."""
        if minutes < 5:  # Minimum 5 minutes to prevent excessive scanning
            raise ValueError("Scan interval must be at least 5 minutes")
        self.set('scan_interval_minutes', str(minutes))

    def get_quiet_hours_enabled(self):
        """Get whether quiet hours are enabled."""
        return bool(int(self.get('quiet_hours_enabled', '0')))  # Default: disabled

    def set_quiet_hours_enabled(self, enabled):
        """Set whether quiet hours are enabled."""
        self.set('quiet_hours_enabled', '1' if enabled else '0')

    def get_quiet_hours_start(self):
        """Get quiet hours start time (24-hour format, e.g., '22:00')."""
        return self.get('quiet_hours_start', '22:00')  # Default: 10 PM

    def set_quiet_hours_start(self, time_str):
        """Set quiet hours start time."""
        # Basic validation
        if ':' not in time_str or len(time_str) != 5:
            raise ValueError("Time must be in HH:MM format")
        self.set('quiet_hours_start', time_str)

    def get_quiet_hours_end(self):
        """Get quiet hours end time (24-hour format, e.g., '08:00')."""
        return self.get('quiet_hours_end', '08:00')  # Default: 8 AM

    def set_quiet_hours_end(self, time_str):
        """Set quiet hours end time."""
        # Basic validation
        if ':' not in time_str or len(time_str) != 5:
            raise ValueError("Time must be in HH:MM format")
        self.set('quiet_hours_end', time_str)

    def get_auto_notify_enabled(self):
        """Get whether desktop notifications are enabled for new files."""
        return bool(int(self.get('auto_notify_enabled', '1')))  # Default: enabled

    def set_auto_notify_enabled(self, enabled):
        """Set whether desktop notifications are enabled."""
        self.set('auto_notify_enabled', '1' if enabled else '0')
    # ----------------------------------------

    # --- First Launch Methods ---
    def is_first_launch(self):
        """Check if this is the first launch of the application."""
        return self.get('has_completed_setup', 'false') == 'false'

    def set_setup_completed(self):
        """Mark that the user has completed initial setup."""
        self.set('has_completed_setup', 'true')
        # Also record the date of first setup for analytics
        from datetime import datetime, timezone
        self.set('first_setup_date', datetime.now(tz=timezone.utc).isoformat())

    def get_first_setup_date(self):
        """Get the date when setup was first completed."""
        return self.get('first_setup_date', '')
    # ----------------------------

    # --- Automatic Registration Setting ---
    def get_automatic(self):
        """
        Get the automatic registration setting.
        Controls whether new files are automatically processed at startup.
        """
        return bool(int(self.get('automatic', '0')))  # Default: False

    def set_automatic(self, enabled):
        """
        Set the automatic registration setting.

        Args:
            enabled: Boolean indicating whether to automatically process new files at startup
        """
        self.set('automatic', '1' if enabled else '0')
    # -------------------------------------
