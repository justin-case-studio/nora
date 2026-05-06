import React, { useState, useEffect } from 'react';
import { 
  Box,
  Button,
  Flex,
  Heading,
  Image,
  Spacer, 
  useColorMode,
  useToast
} from '@chakra-ui/react';
import logo from '../../../assets/logo.png';
import OnboardingModal from '../Modals/OnboardingModal';

interface HeaderProps {
  onDashboardClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({ onDashboardClick }) => {
  const { colorMode } = useColorMode();
  const toast = useToast();
  const [isFirstLaunch, setIsFirstLaunch] = useState(false);
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);
  const [cachedFilesCount, setCachedFilesCount] = useState(0);
  
  // Check if this is the first launch
  useEffect(() => {
    const checkFirstLaunch = async () => {
      try {
        const settings = await window.pywebview.api.get_settings();
        const directories = await window.pywebview.api.get_directories();
        
        // If has_completed_setup is not set but directories exist, this is an existing user
        const hasDirectories = directories && directories.length > 0;
        const firstLaunch = !settings.has_completed_setup && !hasDirectories;
        
        console.log('🔍 [Header] First launch check:', {
          has_completed_setup: settings.has_completed_setup,
          hasDirectories,
          firstLaunch
        });
        
        setIsFirstLaunch(firstLaunch);
        
        // If this is an existing user without the flag, mark setup as completed
        if (!settings.has_completed_setup && hasDirectories) {
          console.log('📝 [Header] Existing user detected - marking setup as completed');
          await window.pywebview.api.mark_setup_completed();
        }
      } catch (error) {
        console.error('Error checking first launch status:', error);
      }
    };
    
    checkFirstLaunch();
  }, []);
  
  // Re-check first launch status when modal closes to ensure state is synced
  useEffect(() => {
    if (!showOnboardingModal) {
      const recheckFirstLaunch = async () => {
        try {
          const settings = await window.pywebview.api.get_settings();
          const firstLaunch = !settings.has_completed_setup;
          console.log('🔄 [Header] Re-checking first launch after modal close:', firstLaunch);
          setIsFirstLaunch(firstLaunch);
        } catch (error) {
          console.error('Error re-checking first launch status:', error);
        }
      };
      recheckFirstLaunch();
    }
  }, [showOnboardingModal]);
  
  // Listen for cached files events
  useEffect(() => {
    const handleCachedFilesAvailable = (event: CustomEvent<{ count: number }>) => {
      console.log('📁 [Header] Cached files available:', event.detail.count);
      setCachedFilesCount(event.detail.count);
    };
    
    window.addEventListener('cached-files-available', handleCachedFilesAvailable as EventListener);
    
    return () => {
      window.removeEventListener('cached-files-available', handleCachedFilesAvailable as EventListener);
    };
  }, []);
  
  const handleRegisterClick = async () => {
    console.log('🔍 [Register] Button clicked - Initiating registration process');
    
    try {
      // Check if directories are configured
      const directories = await window.pywebview.api.get_directories();
      
      if (!directories || directories.length === 0) {
        console.log('📁 [Notarize] No directories configured');
        
        // Fetch current settings to ensure we have the latest setup status
        const currentSettings = await window.pywebview.api.get_settings();
        const hasCompletedSetup = currentSettings.has_completed_setup || false;
        
        console.log('🔍 [Notarize] Setup status check - has_completed_setup:', hasCompletedSetup);
        
        // Only show onboarding if setup has NOT been completed
        if (!hasCompletedSetup) {
          console.log('🆕 [Notarize] First launch detected - showing onboarding');
          setShowOnboardingModal(true);
        } else {
          console.log('⚠️ [Notarize] Setup already completed - showing toast instead of onboarding');
          toast({
            title: "No Directories Configured",
            description: "Please add directories in Settings to start registering files.",
            status: "warning",
            duration: 5000,
            isClosable: true,
            position: "top"
          });
        }
        return;
      }
    
      // Dispatch event to notify components about operation type
      window.dispatchEvent(new CustomEvent('operation-initiated', {
        detail: { type: 'manual-processing' }
      }));
      
      // Call the backend API to start the registration process
      const response = await window.pywebview.api.scan_and_register(true);  // true = force process all files
      console.log('✅ [Notarize] API response received:', response);
      
      if (response.success) {
        console.log('🚀 [Notarize] Process started successfully');
        // Clear cached files count since we're starting registration
        setCachedFilesCount(0);
        // No toast notification needed - progress bar provides visual feedback
      } else {
        console.warn('⚠️ [Notarize] Failed to start:', response.message);
        toast({
          title: "Failed to start registration",
          description: response.message || "An error occurred",
          status: "error",
          duration: 5000,
          isClosable: true,
          position: "top"
        });
      }
    } catch (error) {
      console.error('❌ [Notarize] Error starting process:', error);
      toast({
        title: "Error",
        description: "Failed to start registration process. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
        position: "top"
      });
    }
  };
  
  const handleOnboardingComplete = async () => {
    console.log('✅ [Onboarding] Complete - starting registration');
    setIsFirstLaunch(false);
    
    // Re-fetch settings to ensure state is synced
    try {
      const settings = await window.pywebview.api.get_settings();
      console.log('📊 [Onboarding] Settings after completion:', settings);
    } catch (error) {
      console.error('Error fetching updated settings:', error);
    }
    
    // Start registration automatically after onboarding
    handleRegisterClick();
  };
  
  return (
    <>
      <Box
        as="header"
        bg={colorMode === 'dark' ? 'gray.800' : 'white'}
        py={3}
        pr={5}
        borderBottom="1px solid"
        borderColor={colorMode === 'dark' ? 'gray.700' : 'gray.200'}
        boxShadow="sm"
      >
        <Flex align="center">
          {/* Logo centered above sidebar (80px), title beside it */}
          <Flex w="96px" justify="center" flexShrink={0}>
            <Image
              src={logo}
              alt="Nora Logo"
              boxSize="120px"
              objectFit="contain"
            />
          </Flex>
          <Heading size="xl" fontWeight="bold" color="gray.800" letterSpacing="wide" ml={2}>Nora</Heading>
          
          <Spacer />
          
          {/* Action Buttons */}
          <Button
            colorScheme={cachedFilesCount > 0 ? "green" : "blue"}
            variant={cachedFilesCount > 0 ? "solid" : "outline"}
            onClick={handleRegisterClick}
            size="md"
            fontWeight="medium"
            className={isFirstLaunch ? 'subtle-pulse' : ''}
            _hover={{
              bg: cachedFilesCount > 0 ? "green.600" : "blue.50",
              borderColor: cachedFilesCount > 0 ? "green.600" : "blue.300",
            }}
          >
            Register files
          </Button>
        </Flex>
      </Box>
        
      <OnboardingModal 
        isOpen={showOnboardingModal}
        onClose={() => setShowOnboardingModal(false)}
        onComplete={handleOnboardingComplete}
      />
    </>
  );
};

export default Header; 