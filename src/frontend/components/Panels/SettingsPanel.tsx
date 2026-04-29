import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Heading,
  FormControl,
  FormLabel,
  Input,
  Switch,
  Button,
  VStack,
  HStack,
  Text,
  useToast,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
  Badge,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Spinner,
  Center,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Tooltip,
  Select,
  InputGroup,
  InputRightElement,
  Link,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2, FiEdit, FiFolder, FiRefreshCw, FiInfo, FiEye, FiEyeOff } from 'react-icons/fi';

// Define the directory type
interface Directory {
  id: number;
  path: string;
  recursive: boolean;
  enabled: boolean;
  added_date: string;
}

// Define the structure for API settings response
interface ApiSettings {
  max_file_size?: number;
  sdk_token?: string;
  project_id?: string;
  date_format?: string;
  blockchain_mode?: string;
  is_local_blockchain?: boolean;
  apiEndpoint?: string;
  blockchainTarget?: string;
  blockchainExplorerUrlTemplate?: string;
  automatic?: boolean;
}

// Define the structure for the form data state
interface SettingsFormData {
  sdkToken: string;
  projectId: string;
  dateFormat: string;
  maxFileSizeGB: number;
  blockchainTarget: string;
  automatic: boolean;
}

// Helper function to convert bytes to GB
const bytesToGB = (bytes: number): number => {
  if (bytes <= 0) return 0;
  return parseFloat((bytes / (1024 ** 3)).toFixed(2));
};

// Helper function to convert GB to bytes
const gbToBytes = (gb: number): number => {
  if (gb <= 0) return 0;
  return Math.round(gb * (1024 ** 3));
};

// This is a final test comment to confirm the fix.
// And this is another test comment.

const SettingsPanel: React.FC = () => {
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();
  
  // State for showing/hiding the SDK token
  const [showSdkToken, setShowSdkToken] = useState(false);

  // State for settings
  const [settings, setSettings] = useState<SettingsFormData>({
    sdkToken: '',
    projectId: '',
    dateFormat: 'default',
    maxFileSizeGB: 2,
    blockchainTarget: 'local',
    automatic: false,
  });

  // State for directories
  const [directories, setDirectories] = useState<Directory[]>([]);
  const [newDirectory, setNewDirectory] = useState({
    path: '',
    recursive: true,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Ref for debounce timers
  const debounceTimers = useRef<{ [key: string]: ReturnType<typeof setTimeout> }>({});

  // Fetch directories on component mount
  useEffect(() => {
    console.log('SettingsPanel mounted, fetching data...');
    
    // Immediate fetch when component mounts
    fetchDirectories();
    fetchSettings();
    
    // Set up a small delay to ensure pywebview API is fully initialized
    const timer = setTimeout(() => {
      console.log('Checking if we need to retry fetching data...');
      if ((directories.length === 0 || !settings.dateFormat) && !isLoading) {
        console.log('Retrying fetch...');
        fetchDirectories();
        fetchSettings();
      }
    }, 500);
    
    return () => clearTimeout(timer);
  }, []);

  // Fetch directories from the backend
  const fetchDirectories = async () => {
    setIsLoading(true);
    setHasError(false);
    
    try {
      // Check if window.pywebview is available
      if (typeof window !== 'undefined' && window.pywebview && window.pywebview.api) {
        // @ts-ignore - window.pywebview is injected by pywebview
        const dirs = await window.pywebview.api.get_directories();
        setDirectories(dirs || []);
        setIsInitialLoad(false);
      } else {
        console.warn('pywebview API not available yet');
        // Only set error if not initial load
        if (!isInitialLoad) {
          setHasError(true);
        }
        
        // Try again after a short delay during initial load
        if (isInitialLoad) {
          setTimeout(() => {
            fetchDirectories();
          }, 1000);
        }
      }
    } catch (error) {
      console.error('Error fetching directories:', error);
      // Only set error if not initial load
      if (!isInitialLoad) {
        setHasError(true);
        toast({
          title: 'Error',
          description: 'Failed to fetch directories.',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch settings from the API
  const fetchSettings = useCallback(async () => {
    console.log('Fetching settings...');
    try {
      setIsLoading(true);
      // @ts-ignore - window.pywebview is injected by pywebview
      const response: ApiSettings = await window.pywebview.api.get_settings();
      
      console.log('Fetched settings from API:', response);
      
      setSettings(prevSettings => ({
        ...prevSettings,
        sdkToken: response.sdk_token || '',
        projectId: response.project_id || '',
        dateFormat: response.date_format || 'default',
        maxFileSizeGB: response.max_file_size ? bytesToGB(response.max_file_size) : 2,
        blockchainTarget: response.blockchainTarget || 'local',
        automatic: response.automatic || false,
      }));
      
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching settings:', error);
      setIsLoading(false);
    }
  }, []);

  // Debounced function to update a single setting
  const debouncedUpdateSetting = useCallback((key: string, value: any) => {
    // Clear existing timer for this key
    if (debounceTimers.current[key]) {
      clearTimeout(debounceTimers.current[key]);
    }

    // Set a new timer
    debounceTimers.current[key] = setTimeout(async () => {
      console.log(`🚀 Debounced update for ${key}:`, value);
      let valueToSend = value;
      // Special handling for max file size (convert GB to Bytes)
      if (key === 'maxFileSizeGB') {
          valueToSend = gbToBytes(value as number);
          key = 'max_file_size'; // Send the correct key to backend
      }

      try {
          // @ts-ignore
          const result = await window.pywebview.api.update_single_setting(key, valueToSend);
          if (result.success) {
              let toastMessage = `Setting '${key}' updated`;
              // Check if the backend sent a specific message (e.g., restart required)
              if (result.message) {
                  toastMessage = result.message; 
              }
              toast({ 
                  title: result.message ? "Setting Updated" : `Setting '${key}' updated`, 
                  description: result.message || null,
                  status: 'success', 
                  duration: result.message ? 5000 : 1500, // Longer duration if restart needed
                  isClosable: true 
              });

              // If the blockchainTarget was successfully updated, notify other components
              if (key === 'blockchainTarget') {
                  console.log('[SettingsPanel] Operating mode updated, dispatching event.');
                  window.dispatchEvent(new CustomEvent('operatingModeUpdated'));
              }
          } else {
              toast({ title: `Error updating '${key}'`, description: result.error, status: 'error', duration: 3000, isClosable: true });
              // Consider reverting the UI state on error?
          }
      } catch (error) {
          console.error(`Error updating setting ${key}:`, error);
          toast({ title: 'API Error', description: `Failed to update setting '${key}'.`, status: 'error', duration: 3000, isClosable: true });
      }
    }, 750); // Wait 750ms after last change before sending update
  }, [toast]); // Add toast dependency

  // Generic change handler for simple inputs, selects, switches
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    const isCheckbox = type === 'checkbox';
    const checked = isCheckbox ? (e.target as HTMLInputElement).checked : undefined;
    const finalValue = isCheckbox ? checked : value;

    console.log(`Changing setting ${name} to ${finalValue}`);
    // Update local state immediately for responsiveness
    setSettings(prevSettings => ({
      ...prevSettings,
      [name]: finalValue,
    }));
    
    // Special handling for date format changes - refresh directories to apply new format
    if (name === 'dateFormat') {
      console.log(`[SettingsPanel] Date format changed to ${finalValue}, refreshing directories`);
      // Allow state update to complete before refreshing
      setTimeout(() => fetchDirectories(), 100);
    }
    
    // Debounce the backend update call
    // Add specific key mappings if form state key differs from backend key
    const backendKey = name === 'sdkToken' ? 'sdkToken' : name; // direct mapping
    debouncedUpdateSetting(backendKey, finalValue);
  };

  // Specific handler for NumberInput (maxFileSizeGB)
  const handleMaxFileSizeChange = (valueAsString: string, valueAsNumber: number) => {
    const finalValue = isNaN(valueAsNumber) ? 0 : valueAsNumber;
    console.log(`Changing setting maxFileSizeGB to ${finalValue}`);
    // Update local state immediately
    setSettings(prevSettings => ({
      ...prevSettings,
      maxFileSizeGB: finalValue,
    }));
    // Debounce the backend update call (will be converted to bytes inside debounce func)
    debouncedUpdateSetting('maxFileSizeGB', finalValue);
  };

  // Handle directory selection
  const handleSelectDirectory = async () => {
    try {
      // @ts-ignore - window.pywebview is injected by pywebview
      const result = await window.pywebview.api.select_directory();
      if (result && result.length > 0) {
        setNewDirectory({
          ...newDirectory,
          path: result[0],
        });
      }
    } catch (error) {
      console.error('Error selecting directory:', error);
    }
  };

  // Handle adding a new directory
  const handleAddDirectory = async () => {
    if (!newDirectory.path) {
      toast({
        title: 'Error',
        description: 'Please select a directory.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      // @ts-ignore - window.pywebview is injected by pywebview
      const result = await window.pywebview.api.add_directory(
        newDirectory.path,
        newDirectory.recursive
      );

      if (result.error) {
        toast({
          title: 'Error',
          description: result.error,
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
      } else {
        toast({
          title: 'Directory added',
          description: 'The directory has been added for monitoring.',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        
        // Reset form and fetch updated directories
        setNewDirectory({
          path: '',
          recursive: true,
        });
        onClose();
        fetchDirectories();
      }
    } catch (error) {
      console.error('Error adding directory:', error);
      toast({
        title: 'Error',
        description: 'Failed to add directory.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Handle removing a directory
  const handleRemoveDirectory = async (id: number) => {
    try {
      // @ts-ignore - window.pywebview is injected by pywebview
      await window.pywebview.api.remove_directory(id);
      
      toast({
        title: 'Directory removed',
        description: 'The directory has been removed from monitoring.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      // Fetch updated directories
      fetchDirectories();
    } catch (error) {
      console.error('Error removing directory:', error);
      toast({
        title: 'Error',
        description: 'Failed to remove directory.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Handle toggling directory enabled state
  const handleToggleEnabled = async (directory: Directory) => {
    try {
      // @ts-ignore - window.pywebview is injected by pywebview
      await window.pywebview.api.update_directory(
        directory.id,
        directory.recursive,
        !directory.enabled
      );
      
      toast({
        title: directory.enabled ? 'Directory disabled' : 'Directory enabled',
        description: `The directory has been ${directory.enabled ? 'disabled' : 'enabled'}.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      // Fetch updated directories
      fetchDirectories();
    } catch (error) {
      console.error('Error updating directory:', error);
      toast({
        title: 'Error',
        description: 'Failed to update directory.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Format date for display - improved to use date format preferences
  const formatDate = (dateString: string) => {
    console.log('[SettingsPanel] formatDate called with:', dateString, 'using format:', settings.dateFormat);
    if (!dateString) return 'N/A';
    
    try {
      // Parse the date string to a Date object
      const date = new Date(dateString);
      
      if (isNaN(date.getTime())) {
        console.warn('[SettingsPanel] Invalid date created from:', dateString);
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
      
      // Get formatting preference and ensure it's the current value
      const preferredFormat = settings.dateFormat || 'default';
      console.log('[SettingsPanel] Using format preference:', preferredFormat);
      
      // Format based on preference with explicit string construction
      switch (preferredFormat) {
        case 'us':
          // MM/DD/YYYY, 12-hour (AM/PM)
          const period = hours >= 12 ? 'PM' : 'AM';
          const hours12 = hours % 12 || 12; // Convert to 12-hour format
          const usFormat = `${pad(month)}/${pad(day)}/${year}, ${pad(hours12)}:${pad(minutes)} ${period}`;
          console.log('[SettingsPanel] Formatted as US:', usFormat);
          return usFormat;
          
        case 'eu':
          // DD/MM/YYYY, 24-hour
          const euFormat = `${pad(day)}/${pad(month)}/${year}, ${pad(hours)}:${pad(minutes)}`;
          console.log('[SettingsPanel] Formatted as EU:', euFormat);
          return euFormat;
          
        case 'default':
        default:
          // Use system default as fallback
          const defaultFormat = date.toLocaleString();
          console.log('[SettingsPanel] Formatted as default:', defaultFormat);
          return defaultFormat;
      }
    } catch (e) {
      console.error("Error formatting date:", e);
      return dateString; // Return original string on error
    }
  };

  // Render the directories section content based on loading state
  const renderDirectoriesContent = () => {
    if (isLoading || isInitialLoad) {
      return (
        <Center p={8}>
          <Spinner size="md" color="blue.500" mr={3} />
          <Text>Preparing directory list...</Text>
        </Center>
      );
    }
    
    if (hasError && !isInitialLoad) {
      return (
        <Box p={4} borderWidth={1} borderRadius="md" borderColor="red.300" bg="red.50">
          <HStack justifyContent="space-between">
            <Text color="red.500">Failed to load directories</Text>
            <Button 
              leftIcon={<FiRefreshCw />} 
              colorScheme="red" 
              size="sm" 
              variant="outline"
              onClick={fetchDirectories}
            >
              Retry
            </Button>
          </HStack>
        </Box>
      );
    }
    
    if (directories.length === 0) {
      return (
        <Box 
          p={4} 
          borderWidth={1} 
          borderRadius="md" 
          borderStyle="dashed"
          textAlign="center"
        >
          <Text color="gray.500">No directories added yet</Text>
        </Box>
      );
    }
    
    return (
      <Table variant="simple" size="sm">
        <Thead>
          <Tr>
            <Th>Path</Th>
            <Th>Recursive</Th>
            <Th>Status</Th>
            <Th>Added</Th>
            <Th>Actions</Th>
          </Tr>
        </Thead>
        <Tbody>
          {directories.map((dir) => (
            <Tr key={dir.id}>
              <Td>{dir.path}</Td>
              <Td>{dir.recursive ? 'Yes' : 'No'}</Td>
              <Td>
                <Badge 
                  colorScheme={dir.enabled ? 'green' : 'gray'}
                  cursor="pointer"
                  onClick={() => handleToggleEnabled(dir)}
                >
                  {dir.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </Td>
              <Td>{formatDate(dir.added_date)}</Td>
              <Td>
                <IconButton
                  aria-label="Remove directory"
                  icon={<FiTrash2 />}
                  size="sm"
                  colorScheme="red"
                  variant="ghost"
                  onClick={() => handleRemoveDirectory(dir.id)}
                />
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    );
  };

  // Memoize the formatted table body to re-render only when data or format changes
  const FormattedTableBody = React.useMemo(() => {
    return renderDirectoriesContent();
  }, [directories, settings.dateFormat, isLoading]);

  return (
    <Box p={6} h="full" overflowY="auto">
      <Heading size="lg" mb={6}>Settings</Heading>
      
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="md" mb={4}>Monitored Directories</Heading>
          <VStack spacing={4} align="stretch">
            <HStack justifyContent="space-between">
              <Text>Directories to scan for files to register</Text>
              <Button 
                leftIcon={<FiPlus />} 
                colorScheme="blue" 
                size="sm"
                onClick={onOpen}
              >
                Add Directory
              </Button>
            </HStack>
            
            {FormattedTableBody}
          </VStack>
        </Box>
        
        <Box>
          <Heading size="md" mb={2}>API Configuration</Heading>
          <Text fontSize="sm" color="gray.500" mb={4}>
            Need credentials? See the{' '}
            <Link
              href="https://github.com/ekseesse/nora#getting-a-mintblue-api-key"
              isExternal
              color="blue.500"
            >
              MintBlue setup guide
            </Link>
            .
          </Text>
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel>MintBlue SDK Token</FormLabel>
              <InputGroup>
                <Input
                  name="sdkToken"
                  value={settings.sdkToken}
                  onChange={handleChange}
                  placeholder="Enter your SDK token"
                  type={showSdkToken ? 'text' : 'password'}
                />
                <InputRightElement>
                  <IconButton
                    aria-label={showSdkToken ? 'Hide token' : 'Show token'}
                    icon={showSdkToken ? <FiEyeOff /> : <FiEye />}
                    onClick={() => setShowSdkToken(!showSdkToken)}
                    variant="ghost"
                  />
                </InputRightElement>
              </InputGroup>
            </FormControl>
            
            <FormControl>
              <FormLabel>MintBlue Project ID</FormLabel>
              <Input
                name="projectId"
                value={settings.projectId}
                onChange={handleChange}
                placeholder="Enter your project ID"
                type="text"
              />
            </FormControl>

            <FormControl>
              <FormLabel>Operating Mode</FormLabel>
              <Select
                name="blockchainTarget"
                value={settings.blockchainTarget}
                onChange={handleChange}
              >
                <option value="local">Trial Mode (Local records, for testing)</option>
                <option value="MintBlue">Blockchain Mode (Live, onchain)</option>
              </Select>
            </FormControl>
          </VStack>
        </Box>
        
        <Box>
          <Heading size="md" mb={4}>Scanning Options</Heading>
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel htmlFor="maxFileSizeGB" display="inline-flex" alignItems="center">
                Large File Warning Threshold (GB)
                <Tooltip label="Warn when hashing files larger than this size. Hashing large files may take a significant amount of time, but they will still be processed." fontSize="sm" placement="right">
                  <span style={{ display: 'inline-flex', alignItems: 'center', marginLeft: '4px', color: 'gray' }}>
                    <FiInfo size="1em" />
                  </span>
                </Tooltip>
              </FormLabel>
              <NumberInput id="maxFileSizeGB" name="maxFileSizeGB" value={settings.maxFileSizeGB} onChange={handleMaxFileSizeChange} min={0.01} step={0.1} precision={2} >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>

            <FormControl>
              <FormLabel>Date Format</FormLabel>
              <Select name="dateFormat" value={settings.dateFormat} onChange={handleChange} style={{
                width: '100%',
                padding: '8px',
                borderRadius: '5px',
                border: '1px solid #E2E8F0'
              }}>
                <option value="default">System Default</option>
                <option value="us">US Format (MM/DD/YYYY, 12-hour)</option>
                <option value="eu">European Format (DD/MM/YYYY, 24-hour)</option>
              </Select>
            </FormControl>
            
            <FormControl display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <FormLabel htmlFor="automatic" mb="0">
                  Automatically register new files on startup
                </FormLabel>
                <Text fontSize="sm" color="gray.500">
                  When enabled, new files will be processed automatically when the app starts
                </Text>
              </Box>
              <Switch
                id="automatic"
                name="automatic"
                isChecked={settings.automatic}
                onChange={handleChange}
              />
            </FormControl>
          </VStack>
        </Box>
      </VStack>
      
      {/* Add Directory Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Add Directory</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <FormControl>
                <FormLabel>Directory Path</FormLabel>
                <HStack>
                  <Input
                    value={newDirectory.path}
                    readOnly
                    placeholder="Select a directory"
                  />
                  <IconButton
                    aria-label="Select directory"
                    icon={<FiFolder />}
                    onClick={handleSelectDirectory}
                  />
                </HStack>
              </FormControl>
              
              <FormControl display="flex" alignItems="center">
                <FormLabel htmlFor="recursive" mb="0">
                  Include Subdirectories
                </FormLabel>
                <Switch
                  id="recursive"
                  isChecked={newDirectory.recursive}
                  onChange={(e) => setNewDirectory({
                    ...newDirectory,
                    recursive: e.target.checked,
                  })}
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button 
              colorScheme="blue" 
              onClick={handleAddDirectory}
              isDisabled={!newDirectory.path}
            >
              Add Directory
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default SettingsPanel; 