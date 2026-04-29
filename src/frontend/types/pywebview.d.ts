/**
 * TypeScript declarations for pywebview JavaScript API
 */

interface RegistrationProgress {
  // Core status
  status: 'processing' | 'complete' | 'stopped';

  // Unified progress model (clean, no legacy fields)
  files_examined: number;            // Total files examined so far
  files_verified: number;            // Unchanged files
  files_updated: number;             // Existing hash, DB updated (no blockchain)
  files_recorded: number;            // New blockchain transactions created
  files_skipped: number;             // Skipped due to stop or other reasons
  files_error: number;               // Errors encountered

  // Progress calculation support
  total_files: number;               // Total files to examine
  files_needing_blockchain?: number; // Files that need blockchain work (for discovery context)

  // Current status display
  current_file?: string;
}

interface PywebviewApi {
  // Database records
  get_records: (limit: number, offset: number) => Promise<{
    records: Array<{
      id: number;
      file_path: string;
      file_name: string;
      size: number;
      modified_date: string;
      sha256: string;
      tx_id: string;
      registered_at: string;
      user_notes?: string;
    }>;
    total: number;
    limit: number;
    offset: number;
  }>;
  
  search_records: (
    search_term: string, 
    limit: number, 
    offset: number,
    start_date?: string,
    end_date?: string
  ) => Promise<{
    records: Array<{
      id: number;
      file_path: string;
      file_name: string;
      size: number;
      modified_date: string;
      sha256: string;
      tx_id: string;
      registered_at: string;
      user_notes?: string;
    }>;
    total: number;
    limit: number;
    offset: number;
  }>;
  
  // Directory management
  get_directories: () => Promise<Array<{
    id: number;
    path: string;
    recursive: boolean;
    enabled: boolean;
    added_date: string;
  }>>;
  
  add_directory: (path: string, recursive: boolean) => Promise<{
    id?: number;
    path?: string;
    recursive?: boolean;
    enabled?: boolean;
    added_date?: string;
    error?: string;
  }>;
  
  remove_directory: (directory_id: number) => Promise<boolean>;
  
  update_directory: (
    directory_id: number, 
    recursive?: boolean, 
    enabled?: boolean
  ) => Promise<{
    id: number;
    path: string;
    recursive: boolean;
    enabled: boolean;
    added_date: string;
  }>;
  
  // Registration
  register_now: () => Promise<{ status: string }>;
  stop_registration: () => Promise<{ success: boolean; message: string }>;

  scan_and_register: (process_new_files?: boolean) => Promise<{
    success: boolean;
    message: string;
    process_new_files?: boolean;
  }>;
  
  start_background_scan: () => Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;
  
  clear_registration_cache: () => Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;
  
  verify_file: (file_path: string) => Promise<{
    status: string;
    message: string;
    verified: boolean;
    records?: any[];
    primary_record_used?: any | null;
    blockchain_verification_details?: any | null;
    current_hash?: string;
    hash_match?: boolean;
  }>;
  
  // Settings
  get_settings: () => Promise<{
    max_file_size?: number;
    sdk_token?: string;
    project_id?: string;
    date_format?: string;
    blockchain_mode?: string;
    is_local_blockchain?: boolean;
    apiEndpoint?: string;
    blockchainTarget?: string;
    blockchainExplorerUrlTemplate?: string;
    has_completed_setup?: boolean;
    first_setup_date?: string;
    automatic?: boolean;
  }>;
  
  update_settings: (
    max_file_size?: number,
    api_key?: string,
    project_id?: string,
    date_format?: string
  ) => Promise<{
    max_file_size: number;
    api_key_set: boolean;
    project_id_set: boolean;
    date_format: string;
  }>;
  
  test_api_connection: () => Promise<{ success: boolean }>;
  
  // File dialogs
  select_directory: () => Promise<string[]>;
  select_file: () => Promise<string[]>;

  // Consume a file path captured by pywebview from an OS drag-and-drop.
  // Returns null if no drop is pending. Used by the Verify dropzone to
  // get the file path on WebKit2GTK, where dataTransfer is empty.
  consume_dropped_path: () => Promise<{ path: string; name: string } | null>;
  
  // New dashboard stats method
  get_dashboard_stats: () => Promise<{
    directories: number;
    registered_files: number;
    total_files: number;
    last_registration: string; // ISO format string or empty string
    last_run_summary?: any;
  }>;

  // Method to update a single setting
  update_single_setting: (key: string, value: any) => Promise<{ 
    success: boolean; 
    key?: string; 
    value?: any; 
    error?: string;
    message?: string;
  }>;

  // Method to open external URLs
  open_external_url: (url: string) => Promise<{ 
    success: boolean; 
    message?: string; 
    error?: string 
  }>;

  // Update file record notes
  update_file_record_notes: (record_id: number, user_notes: string) => Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;

  // Mark setup as completed
  mark_setup_completed: () => Promise<{
    success: boolean;
    message?: string;
    error?: string;
  }>;

  get_registration_activity: (days: number) => Promise<{ date: string; count: number }[] | { error: string }>;

  export_records_csv: (
    search_term: string,
    start_date: string,
    end_date: string,
    filename: string
  ) => Promise<{
    success: boolean;
    filepath?: string;
    count?: number;
    error?: string;
  }>;

  export_all_records_csv: (filename: string) => Promise<{
    success: boolean;
    filepath?: string;
    count?: number;
    error?: string;
  }>;
}

interface Pywebview {
  api: PywebviewApi;
}

// Define structure for the stats payload
interface DashboardStatsPayload {
  directories: number;
  registered_files: number;
  total_files: number;
  last_registration: string;
}

// Define structure for the unified operation complete event (clean fields)
interface OperationCompleteEvent {
  status: 'complete' | 'stopped' | 'no_directories';
  files_examined: number;
  files_verified: number;
  files_updated: number;
  files_recorded: number;
  files_error: number;
  files_skipped: number;
  files_needing_blockchain: number;
}

interface Window {
  pywebview?: Pywebview;
  
  // Custom events
  addEventListener(type: 'pywebviewready', listener: EventListener, options?: boolean | AddEventListenerOptions): void;
  addEventListener(type: 'operation-initiated', listener: (event: CustomEvent<{ type: string }>) => void, options?: boolean | AddEventListenerOptions): void;
  addEventListener(type: 'registration-progress', listener: (event: CustomEvent<RegistrationProgress>) => void, options?: boolean | AddEventListenerOptions): void;
  addEventListener(type: 'operation-complete', listener: (event: CustomEvent<OperationCompleteEvent>) => void, options?: boolean | AddEventListenerOptions): void;
  addEventListener(type: 'dashboard-stats-updated', listener: (event: CustomEvent<DashboardStatsPayload>) => void, options?: boolean | AddEventListenerOptions): void;
  
  removeEventListener(type: 'pywebviewready', listener: EventListener, options?: boolean | EventListenerOptions): void;
  removeEventListener(type: 'operation-initiated', listener: (event: CustomEvent<{ type: string }>) => void, options?: boolean | EventListenerOptions): void;
  removeEventListener(type: 'registration-progress', listener: (event: CustomEvent<RegistrationProgress>) => void, options?: boolean | EventListenerOptions): void;
  removeEventListener(type: 'operation-complete', listener: (event: CustomEvent<OperationCompleteEvent>) => void, options?: boolean | EventListenerOptions): void;
  removeEventListener(type: 'dashboard-stats-updated', listener: (event: CustomEvent<DashboardStatsPayload>) => void, options?: boolean | EventListenerOptions): void;
} 