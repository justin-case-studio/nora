import React, { useState, useEffect } from 'react';
import { 
  Box, 
  HStack, 
  Text, 
  Badge, 
  Tooltip, 
  Icon,
  Spacer,
  useColorModeValue
} from '@chakra-ui/react';
import { FiInfo } from 'react-icons/fi';

// Define the structure for API settings response (consistent with SettingsPanel)
interface ApiSettings {
  max_file_size?: number;
  sdk_token?: string;
  project_id?: string;
  date_format?: string;
  blockchain_mode?: string; // This might be the old key, or a general mode
  is_local_blockchain?: boolean; // Could also be used
  apiEndpoint?: string;
  blockchainTarget?: string; // This is the key we expect from SettingsPanel
  blockchainExplorerUrlTemplate?: string;
}

interface StatusBarProps {
  pendingTasks?: number;
}

const StatusBar: React.FC<StatusBarProps> = ({ 
  pendingTasks = 0
}) => {
  const [operatingMode, setOperatingMode] = useState<string | null>(null);
  const [modeLabel, setModeLabel] = useState<string>('Loading Mode...');
  const [modeColorScheme, setModeColorScheme] = useState<string>('gray');

  const modeIconColor = useColorModeValue('gray.600', 'gray.400');
  const trialModeBg = useColorModeValue('gray.200', 'gray.600');
  const trialModeColor = useColorModeValue('gray.800', 'gray.100');

  useEffect(() => {
    let isMounted = true; // To prevent state updates on unmounted component

    const fetchMode = async () => {
      if (!isMounted) return;

      try {
        // @ts-ignore
        if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.get_settings === 'function') {
          // @ts-ignore
          const settingsResponse: ApiSettings | null = await window.pywebview.api.get_settings();
          
          if (!isMounted) return; // Check again after await

          // Default to 'local' if blockchainTarget is not provided or settingsResponse is null/undefined
          const currentBlockchainTarget = (settingsResponse && settingsResponse.blockchainTarget) 
                                          ? settingsResponse.blockchainTarget 
                                          : 'local';
          
          setOperatingMode(currentBlockchainTarget);

          if (currentBlockchainTarget === 'local') {
            setModeLabel('Trial Mode');
            setModeColorScheme('gray');
          } else if (currentBlockchainTarget === 'MintBlue') {
            setModeLabel('Blockchain Mode');
            setModeColorScheme('green');
          } else {
            // Handles any unexpected values, though 'local' default makes it less likely
            setModeLabel(`Unknown Mode: ${currentBlockchainTarget}`);
            setModeColorScheme('yellow');
          }
        } else {
          if (isMounted) {
            setModeLabel('Mode API N/A');
            setModeColorScheme('red');
            console.warn('[StatusBar] Pywebview API or get_settings not available. Retrying in 1s.');
            setTimeout(fetchMode, 1000); // Retry after 1 second
          }
        }
      } catch (error) {
        console.error('Error fetching operating mode for status bar:', error);
        if (isMounted) {
          setModeLabel('Mode Error');
          setModeColorScheme('red');
          console.warn('[StatusBar] Error fetching mode. Retrying in 3s.');
          setTimeout(fetchMode, 3000); // Retry after 3 seconds on error
        }
      }
    };

    fetchMode(); // Initial fetch

    const handleOperatingModeUpdate = () => {
      console.log('[StatusBar] Received operatingModeUpdated event, refetching mode.');
      fetchMode(); // Refetch mode on event
    };

    window.addEventListener('operatingModeUpdated', handleOperatingModeUpdate);

    // Cleanup listener and flag on component unmount
    return () => {
      isMounted = false;
      window.removeEventListener('operatingModeUpdated', handleOperatingModeUpdate);
    };
  }, []); // Empty dependency array ensures this runs once on mount and cleans on unmount

  return (
    <Box 
      py={2} 
      px={4} 
      borderTop="1px solid" 
      borderColor={useColorModeValue('gray.200', 'gray.700')}
      bg={useColorModeValue('gray.50', 'gray.800')}
    >
      <HStack spacing={4}>
        {operatingMode && (
          <Tooltip
            label={
              operatingMode === 'local' 
                ? 'Records are saved locally.'
                : operatingMode === 'MintBlue' 
                ? 'Records are registered and verified on the public blockchain.'
                : `Current operating mode: ${modeLabel}` // Fallback for other states
            }
            hasArrow
          >
            <Badge
              colorScheme={modeColorScheme}
              variant={operatingMode === 'local' ? 'subtle' : 'solid'}
              px={2}
              py={0.5}
              borderRadius="md"
              display="inline-flex"
              alignItems="center"
            >
              <Icon as={FiInfo} mr={operatingMode === 'local' ? 1 : 0} display={operatingMode === 'local' ? 'inline-block' : 'none'} />
              <Text fontSize="xs" fontWeight="medium">
                {modeLabel}
              </Text>
            </Badge>
          </Tooltip>
        )}
        
        <Spacer />
        
        {pendingTasks > 0 && (
          <Tooltip label={`${pendingTasks} pending tasks`} hasArrow>
            <Badge colorScheme="blue" borderRadius="full" px={2}>
              {pendingTasks}
            </Badge>
          </Tooltip>
        )}
      </HStack>
    </Box>
  );
};

export default StatusBar; 