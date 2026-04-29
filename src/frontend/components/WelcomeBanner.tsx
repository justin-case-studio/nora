import React from 'react';
import {
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  CloseButton,
  Box,
  Text,
  HStack,
  VStack,
  Badge
} from '@chakra-ui/react';

interface WelcomeBannerProps {
  onClose: () => void;
}

const WelcomeBanner: React.FC<WelcomeBannerProps> = ({ onClose }) => {
  return (
    <Alert 
      status="info" 
      variant="subtle" 
      flexDirection="column"
      alignItems="flex-start"
      justifyContent="space-between"
      textAlign="left"
      borderRadius="md"
      p={4}
      mb={4}
    >
      <HStack width="100%" alignItems="flex-start">
        <AlertIcon boxSize="20px" mt={1} />
        <Box flex="1">
          <HStack mb={2}>
            <AlertTitle fontSize="lg">Welcome to Nora!</AlertTitle>
            <Badge colorScheme="gray" ml={2}>Trial Mode</Badge>
          </HStack>
          <AlertDescription>
            <Text mb={2}>
              You're starting in Trial Mode - perfect for testing how Nora works.
            </Text>
            <Text fontSize="sm" color="gray.600">
              In Trial Mode, your files are timestamped locally without blockchain fees. 
              To get started:
            </Text>
            <VStack align="start" mt={2} spacing={1} fontSize="sm" color="gray.600">
              <Text>1) Go to the Settings and select one or more directories</Text>
              <Text>2) Click on "Register Now!"</Text>
              <Text>3) Check the results in the Database panel</Text>
            </VStack>
          </AlertDescription>
        </Box>
        <CloseButton 
          position="relative"
          right={-2}
          top={-2}
          onClick={onClose}
        />
      </HStack>
    </Alert>
  );
};

export default WelcomeBanner; 