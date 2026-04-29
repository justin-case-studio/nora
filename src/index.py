"""
Main entry point for the Nora application.
"""
import os
import sys

# WebKit2 version compatibility: pywebview prefers 4.1, falls back to 4.0.
# No patching needed as long as WebKit2-4.1.typelib is installed.
# On Ubuntu 22.04, compile from the .gir if missing:
#   sudo g-ir-compiler /usr/share/gir-1.0/JavaScriptCore-4.1.gir -o /usr/lib/x86_64-linux-gnu/girepository-1.0/JavaScriptCore-4.1.typelib
#   sudo g-ir-compiler /usr/share/gir-1.0/WebKit2-4.1.gir -o /usr/lib/x86_64-linux-gnu/girepository-1.0/WebKit2-4.1.typelib

import json
import webview
from webview.dom import _dnd_state
import threading
import subprocess
import webbrowser

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Trial mode no longer uses an env var or mock blockchain. No early env configuration needed.

# Import our modules AFTER setting env var
from backend.api import NoraAPI


# --- Explicit API for Frontend ---
class FrontendApi:
    """A clean API surface specifically for the pywebview frontend.
    It delegates calls to the main NoraApiWrapper instance.
    This prevents pywebview from introspecting complex internal objects.
    """
    def __init__(self, api_wrapper: 'NoraApiWrapper'):
        self._api = api_wrapper # Store the real wrapper

    # Expose only the methods needed by the frontend
    def get_dashboard_stats(self):
        return self._api.nora_api.get_dashboard_stats() # Delegate to underlying API

    def get_directories(self):
        return self._api.get_directories()

    def add_directory(self, path, recursive=True):
        return self._api.add_directory(path, recursive)

    def remove_directory(self, directory_id):
        return self._api.remove_directory(directory_id)

    def update_directory(self, directory_id, recursive=None, enabled=None):
        return self._api.update_directory(directory_id, recursive, enabled)

    def get_records(self, limit=100, offset=0):
        return self._api.get_records(limit, offset)

    def search_records(self, search_term, limit=100, offset=0, start_date=None, end_date=None):
        return self._api.search_records(search_term, limit, offset, start_date, end_date)

    def get_settings(self):
        return self._api.get_settings()

    def update_settings(self, max_file_size=None, api_key=None, project_id=None, date_format=None):
        return self._api.update_settings(max_file_size, api_key, project_id, date_format)

    def register_now(self):
        # Note: This still triggers the background thread logic in the original wrapper
        return self._api.register_now()

    def verify_file(self, file_path):
        return self._api.verify_file(file_path)

    def test_api_connection(self):
        return self._api.test_api_connection()

    def select_directory(self):
        return self._api.select_directory()

    def select_file(self):
        return self._api.select_file()

    def consume_dropped_path(self):
        """Return and clear the most recently captured OS file drop path.

        pywebview captures file URIs from OS drags at the toolkit level into
        webview.dom._dnd_state['paths'] whenever at least one drop listener is
        registered via its Python DOM API. On WebKit2GTK this is the only way
        to learn the real file path, because dataTransfer is empty in the HTML
        drop event. The webview start-up code registers a sentinel listener
        to keep num_listeners > 0 so capture stays active.
        """
        paths = _dnd_state.get('paths') or []
        if not paths:
            return None
        # Paths are tuples of (basename, full_path) appended by GTK's
        # on_drag_data. Take the most recent drop.
        name, full_path = paths[-1]
        _dnd_state['paths'] = []
        return {'name': name, 'path': full_path}

    def update_single_setting(self, key, value):
        """Exposed method to update a single setting."""
        return self._api.update_single_setting(key, value)

    def verify_by_hash(self, sha256_hash):
        """Exposed method to verify a file by its hash."""
        return self._api.nora_api.verify_by_hash(sha256_hash)

    # --- Add stop_registration to FrontendApi ---
    def stop_registration(self):
        """Request the ongoing registration process to stop."""
        return self._api.nora_api.stop_registration()
    # ------------------------------------------

    def get_registration_activity(self, days=30):
        """Exposed method to get daily registration activity."""
        return self._api.nora_api.get_registration_activity(days)

    def update_file_record_notes(self, record_id, user_notes):
        """Update the user notes for a file record."""
        return self._api.nora_api.update_file_record_notes(record_id, user_notes)

    def start_background_scan(self):
        return self._api.nora_api.start_background_scan()

    def scan_and_register(self, process_new_files=None):
        """
        Unified scanning/registration endpoint.

        Args:
            process_new_files:
                - None: Use the 'automatic' setting (for startup)
                - True: Process everything (for manual action)
                - False: Count only (for future use)
        """
        return self._api.nora_api.scan_and_register(process_new_files)

    def mark_setup_completed(self):
        """Mark that the user has completed initial setup."""
        return self._api.nora_api.mark_setup_completed()

    def open_external_url(self, url):
        """Opens the given URL in the default system browser using a platform-specific method."""
        print(f"[FrontendApi] Attempting to open external URL: {url} on platform {sys.platform}")
        try:
            if sys.platform == 'linux' or sys.platform == 'linux2':
                # Linux: Use xdg-open (target is native execution)
                print("  [Platform] Detected Linux, using xdg-open...")
                subprocess.run(['xdg-open', url], check=True)
            elif sys.platform == 'darwin':
                # macOS: Use the 'open' command
                print("  [Platform] Detected macOS, using open...")
                subprocess.run(['open', url], check=True)
            elif sys.platform == 'win32':
                # Windows: Use os.startfile (similar to 'start' command)
                print("  [Platform] Detected Windows, using os.startfile...")
                os.startfile(url)
            else:
                # Fallback for other platforms
                print(f"  [Platform] Detected unknown platform ({sys.platform}), falling back to webbrowser.open...")
                webbrowser.open(url, new=2)

            return {"success": True, "message": "URL opened successfully."}

        except FileNotFoundError:
             # Specific error if command like 'xdg-open' or 'open' isn't found
             command = "Unknown Command"
             if sys.platform.startswith('linux'):
                 command = "xdg-open"
             elif sys.platform == 'darwin':
                 command = "open"

             print(f"[FrontendApi] Error opening URL {url}: Required command '{command}' not found.")
             return {"success": False, "error": f"Required command '{command}' not found. Please ensure it's installed and in your PATH."}
        except subprocess.CalledProcessError as e:
            # Error specific to subprocess calls (xdg-open, open)
            print(f"[FrontendApi] Error opening URL {url} with command '{e.cmd}': {e}")
            error_msg = f"Failed to open URL using '{' '.join(e.cmd)}': Exit status {e.returncode}"
            if e.stderr:
                 error_msg += f" - Error: {e.stderr.decode().strip()}"
            elif e.stdout:
                 error_msg += f" - Output: {e.stdout.decode().strip()}"

            # Add specific hints for xdg-open failures on Linux
            if sys.platform.startswith('linux') and e.cmd[0] == 'xdg-open':
                 if "portal" in error_msg.lower() or "dbus" in error_msg.lower() or "operation not supported" in error_msg.lower():
                    error_msg += " (This might indicate an issue with desktop integration like xdg-desktop-portal or missing handlers for https URLs.)"
                 else:
                    error_msg += " (Check if xdg-utils is installed and a default browser is configured.)"
            return {"success": False, "error": error_msg}
        except Exception as e:
            # Catch any other unexpected errors
            print(f"[FrontendApi] Unexpected error opening URL {url}: {str(e)}")
            return {"success": False, "error": f"An unexpected error occurred while trying to open the URL: {str(e)}"}

    def export_records_csv(self, search_term="", start_date="", end_date="", filename="nora_export.csv"):
        """Export filtered records to CSV file."""
        return self._api.nora_api.export_records_csv(search_term, start_date, end_date, filename)

    def export_all_records_csv(self, filename="nora_all_records.csv"):
        """Export all records to CSV file."""
        return self._api.nora_api.export_all_records_csv(filename)

    def clear_registration_cache(self):
        return self._api.nora_api.clear_registration_cache()

class NoraApiWrapper:
    """API exposed to the frontend."""

    def __init__(self):
        """Initialize the API."""
        self.nora_api = NoraAPI()
        self.window = None

    def set_window(self, window):
        """Set the window for callbacks."""
        self.window = window

    def notify_frontend(self, event_name, data):
        """Send an event to the frontend. (Used directly or via progress_callback)."""
        print(f"[Wrapper->Frontend] Event='{event_name}', Data={data}") # Added logging
        if self.window:
            # Ensure data is valid JSON before sending
            try:
                json_data = json.dumps(data)
                self.window.evaluate_js(f"window.dispatchEvent(new CustomEvent('{event_name}', {{ detail: {json_data} }}))")
            except TypeError as e:
                print(f"[Wrapper] Failed to serialize data for event '{event_name}': {e} - Data: {data}")

    def progress_callback(self, event_name, data):
        """Handle progress updates AND custom events dispatched from the backend API.
        This acts as the central dispatcher to notify_frontend.
        """
        print(f"[Wrapper Callback] Received: event_name='{event_name}', data keys='{list(data.keys()) if isinstance(data, dict) else type(data)}'")
        actual_event_name = event_name if event_name else data.get('event_name', 'unknown-event')
        actual_data = data.get('data', data) if not event_name else data

        # Now notify the frontend with the correctly extracted name and data
        self.notify_frontend(actual_event_name, actual_data)

    def register_now(self):
        """Start the registration process in a separate thread."""
        def run_registration():
            print("[Backend Thread] Starting registration...")
            # --- Crucial: Pass the wrapper's progress_callback to the API instance ---
            # This ensures the API uses this wrapper's dispatch logic.
            self.nora_api.set_progress_callback(self.progress_callback)
            # ------------------------------------------------------------------
            try:
                result = self.nora_api.register_now() # This triggers progress events via callback
                print(f"[Backend Thread] Registration complete: {result}")
                # Send completion event (could potentially be merged into stats update)
                self.notify_frontend('registration-complete', result)
            except Exception as e:
                print(f"[Backend Thread] Registration error: {str(e)}")
                error_result = {"status": "error", "message": str(e)}
                self.notify_frontend('registration-complete', error_result)
            finally:
                 # --- Trigger stats update AFTER registration attempt ---
                 print("[Backend Thread] Triggering dashboard stats update after registration.")
                 # Directly call the API's internal method to calculate and notify
                 # This will use the callback mechanism set above to dispatch the event.
                 self.nora_api._get_and_notify_dashboard_stats()
                 # -------------------------------------------------------

        # Run in a separate thread to avoid blocking the UI
        thread = threading.Thread(target=run_registration)
        thread.daemon = True
        thread.start()

        print("[Backend] Registration thread started")
        return {"status": "started"}

    def verify_file(self, file_path):
        """Verify a file's registration status."""
        return self.nora_api.verify_file(file_path)

    def get_directories(self):
        """Get all directories."""
        return self.nora_api.get_directories()

    def add_directory(self, path, recursive=True):
        """Add a directory to monitor."""
        return self.nora_api.add_directory(path, recursive)

    def remove_directory(self, directory_id):
        """Remove a directory from monitoring."""
        return self.nora_api.remove_directory(directory_id)

    def update_directory(self, directory_id, recursive=None, enabled=None):
        """Update a directory's settings."""
        return self.nora_api.update_directory(directory_id, recursive, enabled)

    def get_records(self, limit=100, offset=0):
        """Get registration records."""
        return self.nora_api.get_records(limit, offset)

    def search_records(self, search_term, limit=100, offset=0, start_date=None, end_date=None):
        """Search records, passing all parameters to the core API."""
        return self.nora_api.search_records(search_term, limit, offset, start_date, end_date)

    def get_settings(self):
        """Get application settings."""
        return self.nora_api.get_settings()

    def update_settings(self, max_file_size=None, api_key=None, project_id=None, date_format=None):
        """Update application settings."""
        return self.nora_api.update_settings(max_file_size, api_key, project_id, date_format)

    def test_api_connection(self):
        """Test the connection to the MintBlue API."""
        return self.nora_api.test_api_connection()

    def select_directory(self):
        """Open a directory selection dialog."""
        if self.window:
            return self.window.create_file_dialog(webview.FileDialog.FOLDER)
        return None

    def select_file(self):
        """Open a file selection dialog."""
        if self.window:
            return self.window.create_file_dialog(webview.FileDialog.OPEN)
        return None

    def update_single_setting(self, key, value):
        """Wrapper method to update a single setting via the API."""
        # Delegate directly to the NoraAPI instance
        return self.nora_api.update_single_setting(key, value)


class NoraApp:
    """Main application class for the Nora application."""

    def __init__(self):
        """Initialize the application."""
        self.api_wrapper = NoraApiWrapper()

        # Configure blockchain mode (now redundant, but keep for clarity/potential future use)
        # self._configure_blockchain() # Env var is now set earlier

    # def _configure_blockchain(self):
    #     """Configure the blockchain mode."""
    #     # Set the environment variable to use the local blockchain for development
    #     # os.environ['USE_LOCAL_BLOCKCHAIN'] = '1' # Moved earlier
    #     # print(" [Blockchain] Using LOCAL blockchain for development") # Moved earlier

    def get_resource_path(self, relative_path):
        """Get the absolute path to a resource."""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)

    def _create_dev_window(self):
        """Create a window for development mode."""
        url = "http://localhost:3000"
        print(f"[Development Mode] Using development server at {url}")
        print(f"[Debug] Make sure to use the pywebview window, not direct browser access to {url}")
        print("[Debug] The pywebview window should open automatically when running this script")
        print("[Debug] If no window opens, check if there are any errors in the console")

        # --- Pass the CLEAN FrontendApi instance to pywebview ---
        frontend_api_instance = FrontendApi(self.api_wrapper)
        # ---------------------------------------------------------

        return webview.create_window(
            'Nora (Dev)',
            url,
            js_api=frontend_api_instance, # Use the clean API
            width=1024,
            height=768,
            min_size=(800, 600)
        )

    def _create_prod_window(self):
        """Create a window for production mode."""
        # Get the path to the GUI
        gui_dir = self.get_resource_path('gui')

        # Check if the GUI directory exists
        if not os.path.exists(gui_dir):
            gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gui')
            if not os.path.exists(gui_dir):
                raise FileNotFoundError(f"GUI directory not found at {gui_dir}")

        # Add debug prints
        print(f"GUI directory path: {gui_dir}")
        print(f"GUI directory contents: {os.listdir(gui_dir)}")

        # Use the absolute path to the index.html file
        index_html = os.path.join(gui_dir, 'index.html')
        if not os.path.exists(index_html):
            raise FileNotFoundError(f"index.html not found at {index_html}")

        print(f"Index.html path: {index_html}")

        # --- Pass the CLEAN FrontendApi instance to pywebview ---
        frontend_api_instance = FrontendApi(self.api_wrapper)
        # ---------------------------------------------------------

        return webview.create_window(
            'Nora',
            index_html,
            js_api=frontend_api_instance, # Use the clean API
            width=1024,
            height=768,
            min_size=(800, 600)
        )

    def run(self, dev_mode=True):
        """Run the application."""
        # Create the window based on the mode
        window = self._create_dev_window() if dev_mode else self._create_prod_window()

        # --- Critical: Set window and callback on the ORIGINAL wrapper ---
        # The FrontendApi doesn't handle events directly.
        self.api_wrapper.set_window(window)
        self.api_wrapper.nora_api.set_progress_callback(self.api_wrapper.progress_callback)
        # ----------------------------------------------------------------

        # Keep pywebview's GTK drag capture active. Its on_drag_data handler
        # only populates _dnd_state['paths'] when num_listeners > 0. We do not
        # actually use pywebview's DOM drop-handler delivery path, we read the
        # captured paths directly in consume_dropped_path().
        _dnd_state['num_listeners'] = max(1, _dnd_state.get('num_listeners', 0))

        # Start webview
        webview.start(debug=dev_mode)


def main():
    """Main entry point."""
    print("[Main] Script started.")
    # Env var is now set globally near imports
    try:
        print("[Main] Entering try block.")
        # Create and run the application
        app = NoraApp()
        print("[Main] NoraApp initialized.")

        # Development mode flag - controls pywebview debug and URL loading
        # Set to False for production builds
        dev_mode = False # <<< SET TO FALSE FOR PRODUCTION/VM TESTING
        # dev_mode = True # <<< DEBUGGING ENABLED
        print(f"[Main] Running app with dev_mode={dev_mode}") # <<< ADDED LOGGING

        # Enable detailed logging for debugging database issues
        import logging

        # Create a file handler for persistent logging in the same directory as the database
        from pathlib import Path
        app_dir = Path.home() / ".nora"
        app_dir.mkdir(exist_ok=True)  # Ensure the directory exists
        log_file = app_dir / "nora_debug.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Configure root logger
        logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
        print(f"[Main] Debug logging enabled - Console + File: {log_file}")
        logging.info(f"Nora application starting - Log file: {log_file}")

        app.run(dev_mode)
        print("[Main] app.run finished (should not happen if window opened).")

    except Exception as e:
        print(f"[Fatal Error] Failed to start application: {str(e)}")
        # Also try writing to a file in case console output is lost
        try:
            with open("error_log.txt", "w") as f:
                import traceback
                f.write(f"Fatal Error: {str(e)}\n")
                f.write(traceback.format_exc())
            print("[Main] Fatal error also written to error_log.txt")
        except Exception as log_e:
            print(f"[Main] Failed to write error log: {log_e}")
        sys.exit(1)


if __name__ == '__main__':
    print("[Main] __name__ == '__main__' block reached.")
    main()
