import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Flex,
  Icon,
  Divider,
  Progress,
  VStack,
  HStack,
  Badge,
  useColorModeValue,
  Spinner,
  Center,
  Alert,
  AlertIcon,
  CloseButton,
  IconButton,
  Button,
  useToast,
} from '@chakra-ui/react';
import { 
  FiFolder, 
  FiFileText, 
  FiClock, 
  FiCheckCircle, 
  FiAlertCircle,
  FiRefreshCw,
  FiX,
  FiInfo,
} from 'react-icons/fi';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import WelcomeBanner from '../WelcomeBanner';

// Define type for AppSettings
interface AppSettings {
  date_format?: string;
  sdk_token?: string;
  project_id?: string;
  automatic?: boolean; // Added for operation context logic
  // Add other settings fields if needed from API response
  last_registration?: string;
}

interface DashboardStats {
  totalFiles: number;
  registeredFiles: number;
  pendingFiles: number;
  lastRegistration: string;
  directories: number;
}

interface RegistrationProgress {
  status: 'processing' | 'complete' | 'stopped';
  // Clean progress model
  files_examined: number;
  files_verified: number;
  files_updated: number;
  files_recorded: number;
  files_skipped: number;
  files_error: number;
  total_files: number;
  files_needing_blockchain?: number;
  current_file?: string;
}

// Define type for the new event payload (matches pywebview.d.ts)
interface DashboardStatsPayload {
  directories: number;
  registered_files: number;
  total_files: number;
  last_registration: string;
  last_run_summary?: any;
}

interface ActivityData {
  date: string;
  count: number;
}

/**
 * Shorten a full file path for display relative to its monitored directory.
 * e.g. "/home/user/Documents/projects/myproject/src/components/Header.tsx"
 *   with monitoredDir "/home/user/Documents/projects/"
 *   → "projects/.../components/Header.tsx"
 */
function shortenDisplayPath(fullPath: string, monitoredDirs: string[]): string {
  const matchedDir = monitoredDirs.find(dir => fullPath.startsWith(dir));
  if (!matchedDir) return fullPath;

  const dirName = matchedDir.replace(/[/\\]+$/, '').split(/[/\\]/).pop() || '';
  const relative = fullPath.slice(matchedDir.replace(/[/\\]+$/, '').length + 1);
  const parts = relative.split(/[/\\]/);

  if (parts.length <= 2) return `${dirName}/${relative}`;
  return `${dirName}/.../${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
}

const DashboardPanel: React.FC = () => {
  // Helper functions for localStorage persistence
  const STORAGE_KEYS = {
    REGISTRATION_IN_PROGRESS: 'nora_registration_in_progress',
    REGISTRATION_PROGRESS: 'nora_registration_progress',
    LAST_RUN_SUMMARY: 'nora_last_run_summary',
    IS_STOPPING: 'nora_is_stopping'
  };

  const loadFromStorage = (key: string, defaultValue: any) => {
    try {
      // Check if localStorage is available first
      if (typeof localStorage === 'undefined' || localStorage === null) {
        return defaultValue;
      }
      const stored = localStorage.getItem(key);
      if (stored) {
        console.log(`[STORAGE] Loading key='${key}', value=`, JSON.parse(stored));
        return JSON.parse(stored);
      }
    } catch (error) {
      console.warn(`Failed to load ${key} from localStorage:`, error);
    }
    return defaultValue;
  };

  const saveToStorage = (key: string, value: any) => {
    try {
      // Check if localStorage is available first
      if (typeof localStorage === 'undefined' || localStorage === null) {
        return;
      }
      localStorage.setItem(key, JSON.stringify(value));
      console.log(`[STORAGE] Saving key='${key}', value=`, JSON.stringify(value));
    } catch (error) {
      console.warn(`Failed to save ${key} to localStorage:`, error);
    }
  };

  const clearProgressFromStorage = () => {
    try {
      if (typeof localStorage === 'undefined' || localStorage === null) {
        return;
      }
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key);
      });
    } catch (error) {
      console.warn('Failed to clear progress from localStorage:', error);
    }
  };

  const [stats, setStats] = useState<DashboardStats>({
    totalFiles: 0,
    registeredFiles: 0,
    pendingFiles: 0,
    lastRegistration: '',
    directories: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const monitoredDirPaths = useRef<string[]>([]);
  
  // Initialize state from localStorage to prevent flicker on load
  const [registrationInProgress, setRegistrationInProgress] = useState(() => 
    loadFromStorage(STORAGE_KEYS.REGISTRATION_IN_PROGRESS, false)
  );
  const [registrationProgress, setRegistrationProgress] = useState(() => 
    loadFromStorage(STORAGE_KEYS.REGISTRATION_PROGRESS, null)
  );
  const [lastRunSummary, setLastRunSummary] = useState(() => {
    console.log('[STATE INIT] Initializing lastRunSummary from localStorage.');
    const storedSummary = loadFromStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, null);
    console.log('[STATE INIT] Loaded summary from storage:', storedSummary);
    if (storedSummary && storedSummary.completionTime) {
      storedSummary.completionTime = new Date(storedSummary.completionTime);
    }
    return storedSummary;
  });
  const [isStopping, setIsStopping] = useState(() => 
    loadFromStorage(STORAGE_KEYS.IS_STOPPING, false)
  );

  const [notificationMessage, setNotificationMessage] = useState<string | null>(null);
  const [notificationType, setNotificationType] = useState<'info' | 'success' | 'warning' | 'error'>('info');
  const [appSettings, setAppSettings] = useState<AppSettings>({}); // Added state for app settings
  const [largeFileWarning, setLargeFileWarning] = useState<string | null>(null); // Add state for large file warning
  const [activityData, setActivityData] = useState<ActivityData[]>([]);
  const [isActivityLoading, setIsActivityLoading] = useState(true);
  const [cachedFilesCount, setCachedFilesCount] = useState(0);
  const [currentOperation, setCurrentOperation] = useState<string | null>(null);
  const [showWelcomeBanner, setShowWelcomeBanner] = useState(false);

  const toast = useToast();
  const cardBg = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const tooltipBg = useColorModeValue('white', 'gray.800');
  const tooltipBorderColor = useColorModeValue('gray.200', 'gray.600');

  // Reference to store event listeners for cleanup
  const eventListenersRef = useRef<{ type: string; listener: EventListener }[]>([]);
  // Ref to store the fallback timer ID
  const fallbackTimerId = useRef<number | null>(null);

  // --- Function to fetch application settings ---
  const fetchAppSettings = async () => {
    console.log('⚙️ [Dashboard] Fetching application settings');
    try {
      if (window.pywebview?.api?.get_settings) {
        const settings = await window.pywebview.api.get_settings();
        setAppSettings(settings);
        console.log('✅ [Dashboard] App settings fetched:', settings);
        return settings; // Return settings for immediate use
      } else {
        console.warn('⚠️ [Dashboard] pywebview API for settings not available.');
        return {}; // Return empty settings as fallback
      }
    } catch (error) {
      console.error('❌ [Dashboard] Error fetching app settings:', error);
      return {}; // Return empty settings as fallback in case of error
    }
  };

  // Main effect for setting up listeners and initial fetch
  useEffect(() => {
    console.log('🔄 [Dashboard] Initializing dashboard and setting up event listeners');
    
    // Log if we're loading persistent data
    const hasPersistedProgress = loadFromStorage(STORAGE_KEYS.REGISTRATION_PROGRESS, null) !== null;
    const hasPersistedSummary = loadFromStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, null) !== null;
    if (hasPersistedProgress || hasPersistedSummary) {
      console.log('📦 [Dashboard] Loading persisted registration state from localStorage');
    }
    
    // Fetch settings immediately on mount - don't wait for dashboard stats
    fetchAppSettings();

    // Check if we should show the welcome banner (first-time users)
    const checkFirstTimeUser = async () => {
      try {
        const settings = await window.pywebview.api.get_settings();
        const directories = await window.pywebview.api.get_directories();
        
        const hasDirectories = directories && directories.length > 0;
        if (hasDirectories) {
          monitoredDirPaths.current = directories.map((d: { path: string }) => d.path);
        }
        const firstLaunch = !settings.has_completed_setup && !hasDirectories;

        setShowWelcomeBanner(firstLaunch);
      } catch (error) {
        console.error('Error checking first-time user status:', error);
      }
    };
    
    checkFirstTimeUser();

    // Listen for operation-initiated events to track current operation type
    const operationListener = (event: CustomEvent<{ type: string }>) => {
      console.log('📋 [Dashboard] Operation initiated:', event.detail.type);
      setCurrentOperation(event.detail.type);
    };
    window.addEventListener('operation-initiated', operationListener as EventListener);

    // --- Function to trigger initial data fetch --- 
    const triggerInitialFetch = async () => {
        // Cancel fallback timer if fetch is triggered by event or initial check
        if (fallbackTimerId.current) {
            clearTimeout(fallbackTimerId.current);
            fallbackTimerId.current = null;
            console.log('🚫 [Dashboard] Fallback timer cancelled.');
        }
        
        // First fetch settings, then fetch dashboard data
        await fetchAppSettings(); // Ensure settings are loaded first
        
        console.log('🚀 [Dashboard] Triggering initial data fetch...');
        fetchDashboardData();
    };

    // --- Listener for pywebviewready event --- 
    const handlePywebviewReady = () => {
        console.log('✅ [Dashboard] pywebviewready event received!');
        triggerInitialFetch();
    };
    window.addEventListener('pywebviewready', handlePywebviewReady);
    
    // --- Immediate Check (in case API ready before listener attached) --- 
    if (typeof window !== 'undefined' && window.pywebview?.api?.get_dashboard_stats) {
      console.log('🏃 [Dashboard] API detected immediately on mount.');
      triggerInitialFetch();
    } else {
       // --- Fallback Timer (if pywebviewready doesn't fire) --- 
       console.log('⏱️ [Dashboard] API not ready immediately, setting fallback timer (5s).');
       fallbackTimerId.current = setTimeout(() => {
           console.warn('⏰ [Dashboard] Fallback timer expired. Attempting fetch anyway...');
           triggerInitialFetch(); // Attempt fetch even if event didn't fire
       }, 5000); // Wait 5 seconds as a last resort
    }
    
    // --- Other Event Listeners (Stats Update, Progress, Complete) --- 
    const statsUpdateListener = (event: CustomEvent<DashboardStatsPayload>) => {
      console.log('📊 [Dashboard Stats Update] Event received:', event.detail);
      const backendStats = event.detail;
      const pendingFiles = Math.max(0, backendStats.total_files - backendStats.registered_files);
      setStats({
          directories: backendStats.directories,
          registeredFiles: backendStats.registered_files,
          totalFiles: backendStats.total_files,
          pendingFiles: pendingFiles,
          lastRegistration: backendStats.last_registration,
      });

      // Use stored last run summary from backend if available (stats update event)
      if (backendStats.last_run_summary && Object.keys(backendStats.last_run_summary).length > 0) {
        console.log('📝 [Dashboard] Using stored last run summary from backend (stats update event):', backendStats.last_run_summary);
        const summary = {
          ...backendStats.last_run_summary,
          completionTime: backendStats.last_run_summary.completion_time ? new Date(backendStats.last_run_summary.completion_time) : (backendStats.last_registration ? new Date(backendStats.last_registration) : null)
        };
        setLastRunSummary(summary);
        saveToStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, summary);
      }

      setIsLoading(false);
      setHasError(false);
    };

    const scannerWarningListener = (event: CustomEvent<{ message: string }>) => {
      console.log('⚠️ [Scanner Warning] Event received:', event.detail);
      if (event.detail?.message) {
        // Store the warning message instead of showing a toast
        setLargeFileWarning(event.detail.message);
      }
    };

    const progressListener = (event: CustomEvent<RegistrationProgress>) => {
    const progress = event.detail;
      console.log(`📊 [PROGRESS LISTENER] Status: ${progress?.status}, Detail:`, progress);

      // Clean model does not use background_scan_* statuses

      setRegistrationProgress(progress);
      saveToStorage(STORAGE_KEYS.REGISTRATION_PROGRESS, progress);

      if (progress.status === 'complete') {
          const completionTime = new Date();
          console.log(`✅ [PROGRESS LISTENER] Status is COMPLETE. Setting lastRunSummary, setting inProgress=false.`);
          const processedCount = (progress.files_verified || 0) + (progress.files_updated || 0) + (progress.files_recorded || 0);
          const summary = { 
            files_scanned: progress.files_examined,
            files_verified: progress.files_verified,
            hash_verified_count: progress.files_updated,
            new_records_count: progress.files_recorded,
            error_files: progress.files_error,
            skipped_files: progress.files_skipped,
            processed_files: processedCount,
            status: 'complete',
            completionTime
          } as any;
          setLastRunSummary(summary);
          saveToStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, summary);
          
          setRegistrationInProgress(false);
          saveToStorage(STORAGE_KEYS.REGISTRATION_IN_PROGRESS, false);
          
          setIsStopping(false);
          saveToStorage(STORAGE_KEYS.IS_STOPPING, false);
          
          setRegistrationProgress(null); 
          saveToStorage(STORAGE_KEYS.REGISTRATION_PROGRESS, null);
          
          setLargeFileWarning(null);
          
          // Only set notification if this is NOT from a registration-complete event
          // (registration-complete event will set a more accurate message)
          if (!progress.files_examined || progress.files_examined === 0) {
            setNotificationMessage(`Registration finished. Examined: ${progress.files_examined}, Verified: ${progress.files_verified}, Updated: ${progress.files_updated || 0}, New records: ${progress.files_recorded}, Skipped: ${progress.files_skipped || 0}, Errors: ${progress.files_error}.`);
            setNotificationType((progress.files_error || 0) > 0 ? 'warning' : 'success');
          }
      } else if (progress.status === 'stopped') {
          const stopTime = new Date();
          console.log(`⏹️ [PROGRESS LISTENER] Status is STOPPED. Setting lastRunSummary (stopped), setting inProgress=false.`);
          const processedCount = (progress.files_verified || 0) + (progress.files_updated || 0) + (progress.files_recorded || 0);
          const summary = { 
            files_scanned: progress.files_examined,
            files_verified: progress.files_verified,
            hash_verified_count: progress.files_updated,
            new_records_count: progress.files_recorded,
            error_files: progress.files_error,
            skipped_files: progress.files_skipped,
            processed_files: processedCount,
            status: 'stopped',
            completionTime: stopTime
          } as any;
          setLastRunSummary(summary);
          saveToStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, summary);
          
          setRegistrationInProgress(false);
          saveToStorage(STORAGE_KEYS.REGISTRATION_IN_PROGRESS, false);
          
          setIsStopping(false);
          saveToStorage(STORAGE_KEYS.IS_STOPPING, false);
          
          setRegistrationProgress(null); 
          saveToStorage(STORAGE_KEYS.REGISTRATION_PROGRESS, null);
          
          setLargeFileWarning(null);
          
          setNotificationMessage(`Registration process stopped by user. Examined: ${progress.files_examined}, Verified: ${progress.files_verified}, Updated: ${progress.files_updated || 0}, New records: ${progress.files_recorded}, Skipped: ${progress.files_skipped || 0}, Errors: ${progress.files_error}.`);
          setNotificationType('warning'); 
      } else {
          // Process is starting or ongoing.
          // No explicit 'starting' status in the clean model; treat non-complete/non-stopped as active
              console.log(`   >> New run starting. Clearing previous summary (if any).`);
              setLastRunSummary(null);
              saveToStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, null);
              setNotificationMessage(null);
              setNotificationType('info');
              setLargeFileWarning(null);
          
          setRegistrationInProgress(true);
          saveToStorage(STORAGE_KEYS.REGISTRATION_IN_PROGRESS, true);
          
          // No separate scanning_complete state in the clean model
      }
    };
    
    window.addEventListener('dashboard-stats-updated', statsUpdateListener as EventListener);
    window.addEventListener('registration-progress', progressListener as EventListener);
    window.addEventListener('scanner-warning', scannerWarningListener as EventListener);
    
    // Removed legacy 'scan-complete' listener; rely on 'operation-complete'
    
    // Add unified listener for operation completion
    const operationCompleteListener = (event: CustomEvent<{
      status: 'complete' | 'stopped' | 'no_directories';
      files_examined: number;
      files_verified: number;
      files_updated: number;
      files_recorded: number;
      files_error: number;
      files_skipped: number;
      files_needing_blockchain: number;
    }>) => {
      console.log('✅ [Dashboard] Operation complete event received:', event.detail);
      const data = event.detail;
      
      // Handle no directories case (first-time users)
      if (data.status === 'no_directories') {
        // Don't show notification message if welcome banner is visible (first-time users)
        if (!showWelcomeBanner) {
          setNotificationMessage("Welcome to Nora! To get started, please add directories to monitor in the Settings panel.");
          setNotificationType('info');
        }
        setRegistrationInProgress(false);
        setCurrentOperation('no-directories'); // Special state for first-time users
        // Don't fetch dashboard data since there are no directories
        return;
      }
      
      // Determine if this was a scan-only operation based on operation context and settings
      const isScanning = currentOperation === 'startup-scan' && !appSettings?.automatic;
      
      if (isScanning) {
        // Show scan UI: Simple message for discovery
        const filesNeedingProcessing = data.files_needing_blockchain === 0 ? 'no' : data.files_needing_blockchain.toString();
        setNotificationMessage(`${data.files_examined} files examined, found ${filesNeedingProcessing} new files to register`);
        setNotificationType('info');
        
        // Update cached files count and notify Header
        const remainingFiles = Math.max(0, data.files_needing_blockchain || 0);
        setCachedFilesCount(remainingFiles);
        if (remainingFiles > 0) {
          window.dispatchEvent(new CustomEvent('cached-files-available', {
            detail: { count: remainingFiles }
          }));
        }

        // Show action message if files need processing
        if (data.files_needing_blockchain === 0 && cachedFilesCount > 0) {
          setNotificationMessage(`${data.files_examined} files examined, found ${cachedFilesCount} new files to register. Press 'Register files now!' to proceed with registration.`);
        }
      } else {
        // Show processing UI: Full detailed breakdown
        setNotificationMessage(`Registration finished. Examined: ${data.files_examined}, Verified: ${data.files_verified}, Updated: ${data.files_updated || 0}, New records: ${data.files_recorded}, Errors: ${data.files_error}.`);
        setNotificationType((data.files_error || 0) > 0 ? 'warning' : 'success');
        
        // Clear cached files count since everything was processed
        setCachedFilesCount(0);
        
        // Dispatch event to clear Header button too
        window.dispatchEvent(new CustomEvent('cached-files-available', {
          detail: { count: 0 }
        }));
      }
      
      // Common completion logic
      setRegistrationInProgress(false);
      setCurrentOperation(null); // Reset operation tracking
      
      // Refresh dashboard stats
      fetchDashboardData();
      fetchActivityData();
    };
    
    window.addEventListener('operation-complete', operationCompleteListener as EventListener);
    
    // Store references for cleanup
    eventListenersRef.current = [
      { type: 'pywebviewready', listener: handlePywebviewReady },
      { type: 'operation-initiated', listener: operationListener as EventListener },
      { type: 'dashboard-stats-updated', listener: statsUpdateListener as EventListener },
      { type: 'registration-progress', listener: progressListener as EventListener },
      { type: 'scanner-warning', listener: scannerWarningListener as EventListener },
      
      { type: 'operation-complete', listener: operationCompleteListener as EventListener }
    ];

    // --- Cleanup function --- 
    return () => {
      console.log('🧹 [Dashboard] Cleaning up event listeners and timer');
      eventListenersRef.current.forEach(({ type, listener }) => {
        window.removeEventListener(type, listener);
      });
      // Clear fallback timer on unmount
      if (fallbackTimerId.current) {
         clearTimeout(fallbackTimerId.current);
      }
      // Note: We don't clear localStorage here to maintain persistence across navigation
      // Only clear if the process is actually complete to avoid losing active progress
    };
  }, []); // Empty dependency array ensures this runs only once on mount

  const fetchActivityData = async () => {
    console.log('📊 [Dashboard] Fetching registration activity data...');
    setIsActivityLoading(true);
    try {
      if (window.pywebview?.api?.get_registration_activity) {
        const data = await window.pywebview.api.get_registration_activity(30);
        if (data && Array.isArray(data)) {
          // Format date for display
          const formattedData = data.map((item: ActivityData) => ({
            ...item,
            // Keep the full date for potential tooltips, but format for axis
            date: new Date(item.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
          }));
          setActivityData(formattedData);
          console.log('✅ [Dashboard] Notarization activity data fetched:', formattedData);
        } else if (data && 'error' in data) {
          console.error('❌ [Dashboard] Error in activity data response:', data.error);
          setActivityData([]);
        } else {
          // Handle cases where data is null or in an unexpected format
          console.warn('⚠️ [Dashboard] Received unexpected data format for activity.');
          setActivityData([]);
        }
      } else {
        console.warn('⚠️ [Dashboard] pywebview API for activity data not available.');
        setActivityData([]);
      }
    } catch (error) {
      console.error('❌ [Dashboard] Error fetching activity data:', error);
      setActivityData([]);
    } finally {
      setIsActivityLoading(false);
    }
  };

  useEffect(() => {
    fetchActivityData();
  }, []); // Fetch once on mount

  // fetchDashboardData is now ONLY for fetching data, not scheduling retries
  const fetchDashboardData = async () => {
     console.log(`📊 [Dashboard] Fetching initial dashboard data...`);
      setIsLoading(true);
      setHasError(false);
      try {
          if (typeof window !== 'undefined' && window.pywebview?.api?.get_dashboard_stats) {
              const backendStats = await window.pywebview.api.get_dashboard_stats();
              console.log('📊 [Dashboard] Stats received from backend:', backendStats);
              console.log('📊 [Dashboard] Backend last_run_summary:', backendStats.last_run_summary);
              console.log('📊 [Dashboard] Current lastRunSummary state before update:', lastRunSummary);
              const pendingFiles = Math.max(0, backendStats.total_files - backendStats.registered_files);
              setStats({
                  directories: backendStats.directories,
                  registeredFiles: backendStats.registered_files,
                  totalFiles: backendStats.total_files,
                  pendingFiles: pendingFiles,
                  lastRegistration: backendStats.last_registration,
              });

              // Always use stored last run summary from backend if available (override any cached data)
              if (backendStats.last_run_summary && Object.keys(backendStats.last_run_summary).length > 0) {
                console.log('📝 [Dashboard] Using stored last run summary from backend (overriding any cached data):', backendStats.last_run_summary);
                const summary = {
                  ...backendStats.last_run_summary,
                  completionTime: backendStats.last_run_summary.completion_time ? new Date(backendStats.last_run_summary.completion_time) : (backendStats.last_registration ? new Date(backendStats.last_registration) : null)
                };
                setLastRunSummary(summary);
                saveToStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, summary);
                console.log('📝 [Dashboard] setLastRunSummary called with:', summary);
              } else if (backendStats.last_registration) {
                // Fallback: If we have a last registration date but no stored summary, show message
                console.log('⚠️ [Dashboard] No stored last run summary available - registration completed before this feature was added');
                const summary = {
                  status: 'legacy_run',
                  files_scanned: 0,
                  processed_files: 0,
                  files_verified: 0,
                  new_records_count: 0,
                  error_files: 0,
                  skipped_files: 0,
                  completionTime: new Date(backendStats.last_registration),
                  legacy_message: 'Last run completed before detailed tracking was available'
                };
                setLastRunSummary(summary);
                saveToStorage(STORAGE_KEYS.LAST_RUN_SUMMARY, summary);
              }
          } else {
               console.error('❌ [Dashboard] fetchDashboardData called but API not ready!');
               setHasError(true);
               setStats({ totalFiles: 0, registeredFiles: 0, pendingFiles: 0, lastRegistration: '', directories: 0 }); 
          }
      } catch (error) {
          console.error('❌ [Dashboard] Error fetching initial data:', error);
          setHasError(true);
          setStats({ totalFiles: 0, registeredFiles: 0, pendingFiles: 0, lastRegistration: '', directories: 0 }); 
      } finally {
           setIsLoading(false);
      }
  };

  // More robust date formatting function
  const formatDate = (dateString: string) => {
    console.log('[DashboardPanel] formatDate called with dateString:', dateString);
    console.log('[DashboardPanel] appSettings at time of call:', { 
      ...appSettings, 
      sdk_token: appSettings.sdk_token ? '[REDACTED]' : undefined,
      project_id: appSettings.project_id ? '[REDACTED]' : undefined 
    });
    
    if (!dateString) return 'Never';
    
    try {
      // Parse the date string to a Date object
      const date = new Date(dateString);
      
      if (isNaN(date.getTime())) {
        console.warn('[DashboardPanel] Invalid date created from:', dateString);
        return dateString; // Return original string if date is invalid
      }
      
      // Get date components
      const year = date.getFullYear();
      const month = date.getMonth() + 1; // getMonth is 0-indexed
      const day = date.getDate();
      const hours = date.getHours();
      const minutes = date.getMinutes();
      
      // Format numbers to ensure 2 digits
      const pad = (num: number) => num.toString().padStart(2, '0');
      
      // Get formatting preference
      const preferredFormat = appSettings.date_format || 'default';
      console.log('[DashboardPanel] Using format preference:', preferredFormat);
      
      // Format based on preference with explicit string construction
      switch (preferredFormat) {
        case 'us':
          // MM/DD/YYYY, 12-hour (AM/PM)
          const period = hours >= 12 ? 'PM' : 'AM';
          const hours12 = hours % 12 || 12; // Convert to 12-hour format
          return `${pad(month)}/${pad(day)}/${year}, ${pad(hours12)}:${pad(minutes)} ${period}`;
          
        case 'eu':
          // DD/MM/YYYY, 24-hour
          return `${pad(day)}/${pad(month)}/${year}, ${pad(hours)}:${pad(minutes)}`;
          
        case 'default':
        default:
          // Default format based on browser locale, but with explicit construction
          if (new Intl.DateTimeFormat().resolvedOptions().locale.startsWith('en-US')) {
            const period = hours >= 12 ? 'PM' : 'AM';
            const hours12 = hours % 12 || 12;
            return `${pad(month)}/${pad(day)}/${year}, ${pad(hours12)}:${pad(minutes)} ${period}`;
          } else {
            return `${pad(day)}/${pad(month)}/${year}, ${pad(hours)}:${pad(minutes)}`;
          }
      }
    } catch (e) {
      console.error('[DashboardPanel] Error in formatDate:', e);
      return dateString;
    }
  };

  const formatTimeAgo = (dateString: string): string => {
    if (!dateString) return 'Never';

    try {
      const date = new Date(dateString);
      
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }

      // Calculate time difference
      const now = new Date();
      const seconds = Math.round((now.getTime() - date.getTime()) / 1000);
      const minutes = Math.round(seconds / 60);
      const hours = Math.round(minutes / 60);
      const days = Math.round(hours / 24);

      if (seconds < 60) {
        return seconds <= 1 ? 'Just now' : `${seconds} seconds ago`;
      } else if (minutes < 60) {
        return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
      } else if (hours < 24) {
        return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
      } else {
        return days === 1 ? '1 day ago' : `${days} days ago`;
      }
    } catch (e) {
      console.error("Error in formatTimeAgo:", e);
      return dateString; // Return original string on error
    }
  };

  const calculatePercentage = () => {
    if (stats.totalFiles === 0) return 0;
    return Math.round((stats.registeredFiles / stats.totalFiles) * 100);
  };

  const calculateProgressPercentage = () => {
    // Overall progress: files_examined / total_files (consistent across modes)
    if (!registrationProgress) return 0;
    const total = registrationProgress.total_files || 0;
    const examined = registrationProgress.files_examined || 0;
    if (!total) return 0;
    return Math.round((examined / total) * 100);
  };

  // --- New Handler for Stop Button ---
  const handleStopClick = async () => {
    console.log('🛑 [Dashboard] Stop button clicked.');
    setIsStopping(true);
    saveToStorage(STORAGE_KEYS.IS_STOPPING, true);
    setNotificationMessage('Requesting registration stop...');
    setNotificationType('info');
    try {
      if (window.pywebview?.api?.stop_registration) {
        const response = await window.pywebview.api.stop_registration();
        console.log('  [Stop API] Response:', response);
        if (!response.success) {
           console.error('  [Stop API] Failed to send stop request:', response.message);
           setNotificationMessage(`Failed to send stop request: ${response.message}`);
           setNotificationType('error');
           setIsStopping(false); // Allow retry if API call failed
           saveToStorage(STORAGE_KEYS.IS_STOPPING, false);
        }
        // If successful, we just wait for the 'stopped' progress event
      } else {
         throw new Error('Stop API function not available.');
      }
    } catch (error) {
      console.error('❌ [Dashboard] Error calling stop_registration API:', error);
      setNotificationMessage(`Error requesting stop: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setNotificationType('error');
      setIsStopping(false); // Allow retry if API call failed
      saveToStorage(STORAGE_KEYS.IS_STOPPING, false);
    }
  };
  // ----------------------------------

  console.log(`[RENDER] DashboardPanel rendering. InProgress: ${registrationInProgress}, HasSummary: ${!!lastRunSummary}`);
  if (isLoading) {
    return (
      <Center h="full" p={8}>
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text>Loading dashboard data...</Text>
        </VStack>
      </Center>
    );
  }

  return (
    <Box p={6} h="full" overflowY="auto">
      <Heading size="lg" mb={6}>Dashboard</Heading>
      
      {/* Welcome Banner for first-time users */}
      {showWelcomeBanner && (
        <Box mb={6}>
          <WelcomeBanner onClose={() => setShowWelcomeBanner(false)} />
        </Box>
      )}
      
      {/* Notification Alert - hidden when welcome banner is shown for no-directories case */}
      {notificationMessage && !(showWelcomeBanner && currentOperation === 'no-directories') && (
        <Alert status={notificationType} mb={6} borderRadius="md">
          <AlertIcon />
          {notificationMessage}
          <CloseButton 
            position="absolute" 
            right="8px" 
            top="8px" 
            onClick={() => setNotificationMessage(null)} 
          />
        </Alert>
      )}
      
      {/* Key Metrics */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} mb={8}>
        <Stat
          px={4}
          py={5}
          bg={cardBg}
          borderRadius="lg"
          boxShadow="sm"
          borderWidth="1px"
          borderColor={borderColor}
        >
          <Flex justifyContent="space-between">
            <Box>
              <StatLabel color="gray.500">Monitored Directories</StatLabel>
              <StatNumber fontSize="3xl">{stats.directories}</StatNumber>
              <StatHelpText>Source of files to register</StatHelpText>
            </Box>
            <Box
              p={2}
              bg="blue.50"
              borderRadius="md"
              color="blue.500"
              height="fit-content"
            >
              <Icon as={FiFolder} boxSize={6} />
            </Box>
          </Flex>
        </Stat>
        
        <Stat
          px={4}
          py={5}
          bg={cardBg}
          borderRadius="lg"
          boxShadow="sm"
          borderWidth="1px"
          borderColor={borderColor}
        >
          <Flex justifyContent="space-between">
            <Box>
              <StatLabel color="gray.500">Total Files</StatLabel>
              <StatNumber fontSize="3xl">{stats.totalFiles}</StatNumber>
              <StatHelpText>Files in monitored directories</StatHelpText>
            </Box>
            <Box
              p={2}
              bg="purple.50"
              borderRadius="md"
              color="purple.500"
              height="fit-content"
            >
              <Icon as={FiFileText} boxSize={6} />
            </Box>
          </Flex>
        </Stat>
        
        <Stat
          px={4}
          py={5}
          bg={cardBg}
          borderRadius="lg"
          boxShadow="sm"
          borderWidth="1px"
          borderColor={borderColor}
        >
          <Flex justifyContent="space-between">
            <Box>
              <StatLabel color="gray.500">Secure Records</StatLabel>
              <StatNumber fontSize="3xl">{stats.registeredFiles}</StatNumber>
              <StatHelpText>
                Total events recorded
              </StatHelpText>
            </Box>
            <Box
              p={2}
              bg="green.50"
              borderRadius="md"
              color="green.500"
              height="fit-content"
            >
              <Icon as={FiCheckCircle} boxSize={6} />
            </Box>
          </Flex>
        </Stat>
        
        <Stat
          px={4}
          py={5}
          bg={cardBg}
          borderRadius="lg"
          boxShadow="sm"
          borderWidth="1px"
          borderColor={borderColor}
        >
          <Flex justifyContent="space-between">
            <Box>
              <StatLabel color="gray.500">Last Successful Run</StatLabel>
              <StatNumber fontSize="xl">{formatTimeAgo(stats.lastRegistration)}</StatNumber>
              <StatHelpText fontSize="xs" color="gray.400">
                {stats.lastRegistration ? formatDate(stats.lastRegistration) : 'No successful runs yet'}
              </StatHelpText>
            </Box>
            <Box
              p={2}
              bg="orange.50"
              borderRadius="md"
              color="orange.500"
              height="fit-content"
            >
              <Icon as={FiClock} boxSize={6} />
            </Box>
          </Flex>
        </Stat>
      </SimpleGrid>
      
      {/* Registration Progress */}
      <Box
        mb={8}
        p={5}
        bg={cardBg}
        borderRadius="lg"
        boxShadow="sm"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <Heading size="md" mb={4}>Activity</Heading>
        
        {stats.directories === 0 ? (
          <Text fontSize="sm" color="gray.600">
            No scans have been performed yet.
          </Text>
        ) : registrationInProgress && registrationProgress ? (
          
          // Active progress content
          <>
            <Text mb={2}>
              {/* Update text based on status */}
              {`Examining... `}
            </Text>
            <Progress 
              value={calculateProgressPercentage()} // Uses updated calculation
              size="lg" 
              colorScheme="blue" 
              borderRadius="md"
              hasStripe
              isAnimated
            />
            {/* Display intermediate counts */}
            <HStack mt={3} spacing={4} flexWrap="wrap">
                <Text fontSize="sm"><Badge colorScheme="gray" mr={1} minW="2.5rem" display="inline-flex" justifyContent="center">{registrationProgress?.files_examined || 0}</Badge> Examined</Text>
                <Text fontSize="sm"><Badge colorScheme="cyan" mr={1} minW="2.5rem" display="inline-flex" justifyContent="center">{registrationProgress?.files_verified || 0}</Badge> Verified</Text>
                <Text fontSize="sm"><Badge colorScheme="purple" mr={1} minW="2.5rem" display="inline-flex" justifyContent="center">{registrationProgress?.files_updated || 0}</Badge> Updated</Text>
                <Text fontSize="sm"><Badge colorScheme="green" mr={1} minW="2.5rem" display="inline-flex" justifyContent="center">{registrationProgress?.files_recorded || 0}</Badge> New records</Text>
                <Text fontSize="sm"><Badge colorScheme="yellow" mr={1} minW="2.5rem" display="inline-flex" justifyContent="center">{registrationProgress?.files_skipped || 0}</Badge> Skipped</Text>
                <Text fontSize="sm"><Badge colorScheme="red" mr={1} minW="2.5rem" display="inline-flex" justifyContent="center">{registrationProgress?.files_error || 0}</Badge> Errors</Text>
            </HStack>
            {/* --- Add Stop Button --- */}
            <Button 
              mt={4} 
              colorScheme="red" 
              variant="outline"
              leftIcon={<Icon as={FiX} />}
              onClick={handleStopClick}
              isDisabled={isStopping}
              isLoading={isStopping}
              loadingText="Stopping..."
            >
              Stop Registration
            </Button>
            {/* --------------------- */}
            {/* Current file display at bottom to prevent layout shift from long paths */}
            {registrationProgress?.current_file && (
              <Box mt={4} pt={3} borderTopWidth="1px" borderColor={borderColor}>
                <HStack spacing={2} align="center" flexWrap="wrap">
                  <Text fontSize="sm" color="gray.500">
                    Current file: {shortenDisplayPath(registrationProgress.current_file, monitoredDirPaths.current)}
                  </Text>
                  {largeFileWarning && (
                    <>
                      <Icon as={FiInfo} color="orange.400" boxSize={4} />
                      <Text fontSize="xs" color="orange.600">
                        {largeFileWarning}
                      </Text>
                    </>
                  )}
                </HStack>
              </Box>
            )}
          </>
        ) : lastRunSummary ? (
          <>
            <Text mb={1} fontSize="sm" color="gray.600">
              Completed: {lastRunSummary.completionTime.toLocaleString()}
            </Text>
            <Text mb={2}>
              Status: <Badge colorScheme={
                lastRunSummary.status === 'stopped' ? 'orange' : (lastRunSummary.error_files > 0 ? 'red' : 'green')
              }>
                {lastRunSummary.status === 'stopped'
                  ? 'STOPPED by user'
                  : (currentOperation === 'startup-scan' && !appSettings?.automatic && lastRunSummary.new_records_count === 0
                      ? 'SCAN COMPLETE'
                      : `COMPLETE${lastRunSummary.error_files > 0 ? ' with errors' : ''}`)
                }
              </Badge>
            </Text>
            
            {/* Handle legacy runs */}
            {lastRunSummary.status === 'legacy_run' ? (
              <Text fontSize="sm" color="gray.500" fontStyle="italic">
                {lastRunSummary.legacy_message}
              </Text>
            ) : (
              /* Updated summary display using new fields */
              <HStack mt={3} spacing={4} flexWrap="wrap">
                <Text fontSize="sm"><Badge colorScheme="gray" mr={1}>{lastRunSummary.files_scanned || 0}</Badge> Examined</Text>
                <Text fontSize="sm"><Badge colorScheme="cyan" mr={1}>{lastRunSummary.files_verified || 0}</Badge> Verified</Text>
                <Text fontSize="sm"><Badge colorScheme="purple" mr={1}>{lastRunSummary.hash_verified_count || 0}</Badge> Updated</Text>
                <Text fontSize="sm"><Badge colorScheme="green" mr={1}>{lastRunSummary.new_records_count || 0}</Badge> New records</Text>
                <Text fontSize="sm"><Badge colorScheme="yellow" mr={1}>{lastRunSummary.skipped_files || 0}</Badge> Skipped</Text>
                <Text fontSize="sm"><Badge colorScheme="red" mr={1}>{lastRunSummary.error_files || 0}</Badge> Errors</Text>
              </HStack>
            )}
            
            {/* Display stop status in summary if applicable */}
            {lastRunSummary.status === 'stopped' && (
               <Text mt={2} fontSize="sm" color="orange.600" fontWeight="semibold">
                   Process stopped by user.
               </Text>
            )}
          </>
        ) : (
          <>
            {/* Dynamic subtitle based on operation context */}
            {(registrationInProgress || currentOperation) && (
              <Text mb={2} fontSize="sm" color="gray.600">
                {currentOperation === 'startup-scan' && !appSettings?.automatic
                  ? "Scanning directories for new files"
                  : "Processing files in the directories"
                }
              </Text>
            )}
            <Text color="gray.500">No registration process is currently active.</Text>
          </>
        )}
      </Box>

      {/* Daily Registration Chart */}
      <Box
        mt={8}
        p={5}
        bg={cardBg}
        borderRadius="lg"
        boxShadow="sm"
        borderWidth="1px"
        borderColor={borderColor}
      >
        <Heading size="md" mb={4}>Daily Registration Trends (Last 30 Days)</Heading>
        {isActivityLoading ? (
          <Center h="250px">
            <VStack>
              <Spinner size="lg" />
              <Text mt={2}>Loading chart data...</Text>
            </VStack>
          </Center>
        ) : activityData.length > 0 ? (
          <Box h="250px">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={activityData}
                margin={{
                  top: 5, right: 20, left: -10, bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" fontSize="12px" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} fontSize="12px" tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    background: tooltipBg,
                    border: '1px solid',
                    borderColor: tooltipBorderColor,
                    borderRadius: 'md',
                  }}
                  labelStyle={{ fontWeight: 'bold' }}
                  formatter={(value: number) => [`${value} registrations`, 'Count']}
                />
                <Bar dataKey="count" fill="#4299E1" name="Registrations" barSize={20} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        ) : (
          <Center h="250px">
            <Text color="gray.500">No registration activity data available to display.</Text>
          </Center>
        )}
      </Box>
    </Box>
  );
};

export default DashboardPanel; 