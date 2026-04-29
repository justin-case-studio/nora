import React from 'react';
import { Box, VStack, Tooltip, Icon, Text, Center } from '@chakra-ui/react';
import { FiHome, FiSettings, FiDatabase, FiSearch, FiInfo } from 'react-icons/fi';
import { AppSection } from '../MainWindow';

interface SidebarProps {
  activeSection: AppSection;
  onSectionChange: (section: AppSection) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeSection, onSectionChange }) => {
  // Navigation items configuration
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: FiHome },
    { id: 'settings', label: 'Settings', icon: FiSettings },
    { id: 'database', label: 'Database', icon: FiDatabase },
    { id: 'verify', label: 'Verify', icon: FiSearch },
    { id: 'about', label: 'About', icon: FiInfo },
  ];

  return (
    <Box
      w="96px"
      bg="white"
      borderRight="1px solid"
      borderColor="gray.200"
      py={5}
      display="flex"
      flexDirection="column"
      alignItems="center"
    >
      <VStack spacing={4} align="center" w="full">
        {navItems.map((item) => (
          <Tooltip key={item.id} label={item.label} placement="right" hasArrow>
            <Box
              as="button"
              w="86px"
              h="86px"
              borderRadius="md"
              display="flex"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
              bg={activeSection === item.id ? 'blue.50' : 'transparent'}
              color={activeSection === item.id ? 'blue.500' : 'gray.600'}
              _hover={{
                bg: activeSection === item.id ? 'blue.50' : 'gray.100',
              }}
              onClick={() => onSectionChange(item.id as AppSection)}
              transition="all 0.2s"
            >
              <Icon as={item.icon} boxSize={9} mb={1} />
              <Text fontSize="xs">{item.label}</Text>
            </Box>
          </Tooltip>
        ))}
      </VStack>
    </Box>
  );
};

export default Sidebar; 