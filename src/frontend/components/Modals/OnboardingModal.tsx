import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Text,
  VStack,
  HStack,
  Box,
  Icon,
  Badge,
  useColorMode,
  Spinner,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import { FiFolder, FiCheck, FiInfo } from 'react-icons/fi';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
}

const OnboardingModal: React.FC<OnboardingModalProps> = ({ 
  isOpen, 
  onClose, 
  onComplete 
}) => {
  const [step, setStep] = useState<'welcome' | 'add-directory' | 'complete'>('welcome');
  const [isAddingDirectory, setIsAddingDirectory] = useState(false);
  const [selectedDirectory, setSelectedDirectory] = useState<string>('');
  const [error, setError] = useState<string>('');
  const { colorMode } = useColorMode();
  
  // Reset to welcome step when modal opens
  React.useEffect(() => {
    if (isOpen) {
      console.log('🔄 [OnboardingModal] Resetting to welcome step');
      setStep('welcome');
      setSelectedDirectory('');
      setError('');
    }
  }, [isOpen]);

  const handleAddDirectory = async () => {
    setIsAddingDirectory(true);
    setError('');

    try {
      // Open directory picker
      const result = await window.pywebview.api.select_directory();
      
      if (result && result.length > 0) {
        const path = result[0];
        setSelectedDirectory(path);
        
        // Add the directory
        const addResult = await window.pywebview.api.add_directory(path, true);
        
        if (addResult.error) {
          setError(addResult.error);
        } else {
          // Mark setup as completed
          await window.pywebview.api.mark_setup_completed();
          setStep('complete');
        }
      }
    } catch (error) {
      setError('Failed to add directory. Please try again.');
      console.error('Error adding directory:', error);
    } finally {
      setIsAddingDirectory(false);
    }
  };

  const handleComplete = () => {
    onComplete();
    onClose();
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      closeOnOverlayClick={false}
      size="lg"
    >
      <ModalOverlay />
      <ModalContent>
        {step === 'welcome' && (
          <>
            <ModalHeader>
              <HStack>
                <Text>Welcome to Nora</Text>
                <Badge colorScheme="gray">Trial Mode</Badge>
              </HStack>
            </ModalHeader>
            <ModalBody>
              <VStack spacing={4} align="stretch">
                <Box 
                  p={4} 
                  borderRadius="md" 
                  bg={colorMode === 'dark' ? 'gray.700' : 'gray.50'}
                >
                  <HStack mb={2}>
                    <Icon as={FiInfo} color="blue.500" />
                    <Text fontWeight="semibold">What is Nora?</Text>
                  </HStack>
                  <Text fontSize="sm">
                    Nora creates cryptographic timestamps of your files, proving they
                    existed at a specific time. This is perfect for protecting intellectual 
                    property, contracts, and important documents.
                  </Text>
                </Box>

                <Box 
                  p={4} 
                  borderRadius="md" 
                  bg={colorMode === 'dark' ? 'gray.700' : 'gray.50'}
                >
                  <HStack mb={2}>
                    <Badge colorScheme="gray">Trial Mode</Badge>
                    <Text fontWeight="semibold">Safe Testing Environment</Text>
                  </HStack>
                  <Text fontSize="sm">
                    You're starting in Trial Mode, which means:
                  </Text>
                  <VStack align="start" mt={2} spacing={1}>
                    <Text fontSize="sm">• No blockchain fees while you test</Text>
                    <Text fontSize="sm">• Files are timestamped locally</Text>
                    <Text fontSize="sm">• Perfect for learning how Nora works</Text>
                    <Text fontSize="sm">• Switch to Blockchain Mode when ready</Text>
                  </VStack>
                </Box>
              </VStack>
            </ModalBody>
            <ModalFooter>
              <Button variant="ghost" mr={3} onClick={onClose}>
                Skip for now
              </Button>
              <Button colorScheme="blue" onClick={() => setStep('add-directory')}>
                Let's Get Started
              </Button>
            </ModalFooter>
          </>
        )}

        {step === 'add-directory' && (
          <>
            <ModalHeader>Add Your First Directory</ModalHeader>
            <ModalBody>
              <VStack spacing={4} align="stretch">
                <Text>
                  Choose a directory containing files you want to protect. 
                  Nora will scan this directory and create timestamps for your files.
                </Text>

                {error && (
                  <Alert status="error" borderRadius="md">
                    <AlertIcon />
                    {error}
                  </Alert>
                )}

                {selectedDirectory && (
                  <Box 
                    p={3} 
                    borderRadius="md" 
                    bg={colorMode === 'dark' ? 'gray.700' : 'gray.100'}
                  >
                    <HStack>
                      <Icon as={FiFolder} />
                      <Text fontSize="sm" fontFamily="mono">{selectedDirectory}</Text>
                    </HStack>
                  </Box>
                )}

                <Button
                  size="lg"
                  colorScheme="blue"
                  leftIcon={<FiFolder />}
                  onClick={handleAddDirectory}
                  isLoading={isAddingDirectory}
                  loadingText="Selecting directory..."
                  isDisabled={!!selectedDirectory}
                >
                  Choose Directory
                </Button>

                <Text fontSize="sm" color="gray.500">
                  You can add more directories later in Settings.
                </Text>
              </VStack>
            </ModalBody>
            <ModalFooter>
              <Button variant="ghost" onClick={() => setStep('welcome')}>
                Back
              </Button>
            </ModalFooter>
          </>
        )}

        {step === 'complete' && (
          <>
            <ModalHeader>
              <HStack>
                <Icon as={FiCheck} color="green.500" />
                <Text>Setup Complete!</Text>
              </HStack>
            </ModalHeader>
            <ModalBody>
              <VStack spacing={4} align="stretch">
                <Text>
                  Great! You've added your first directory. Nora is now ready to
                  start protecting your files.
                </Text>

                <Box 
                  p={4} 
                  borderRadius="md" 
                  bg={colorMode === 'dark' ? 'green.900' : 'green.50'}
                  borderWidth={1}
                  borderColor={colorMode === 'dark' ? 'green.700' : 'green.200'}
                >
                  <Text fontWeight="semibold" mb={2}>What happens next?</Text>
                  <Text fontSize="sm">
                    Click "Start Registering" to begin scanning your directory and creating
                    timestamps for your files. You'll see the progress in real-time.
                  </Text>
                </Box>
              </VStack>
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="green" onClick={handleComplete}>
                Start Registering
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
};

export default OnboardingModal; 