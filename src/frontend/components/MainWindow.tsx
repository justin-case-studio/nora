import React, { useState } from 'react';
import { Box, Flex } from '@chakra-ui/react';
import Header from './Header/Header';
import Sidebar from './Navigation/Sidebar';
import DashboardPanel from './Panels/DashboardPanel';
import SettingsPanel from './Panels/SettingsPanel';
import DatabasePanel from './Panels/DatabasePanel';
import VerifyPanel from './Panels/VerifyPanel';
import AboutPanel from './Panels/AboutPanel';
import StatusBar from './StatusBar/StatusBar';

// Define the sections of the app
export type AppSection = 'dashboard' | 'settings' | 'database' | 'verify' | 'about';

const MainWindow: React.FC = () => {
  // State to track the active section
  const [activeSection, setActiveSection] = useState<AppSection>('dashboard');

  // Function to handle section changes
  const handleSectionChange = (section: AppSection) => {
    setActiveSection(section);
  };

  // Function to navigate to dashboard
  const handleDashboardClick = () => {
    setActiveSection('dashboard');
  };

  return (
    <Flex 
      direction="column" 
      h="100vh" 
      bg="gray.50"
      color="gray.800"
    >
      {/* Header */}
      <Header onDashboardClick={handleDashboardClick} />
      
      {/* Main Content Area with Sidebar */}
      <Flex flex="1" overflow="hidden">
        {/* Sidebar Navigation */}
        <Sidebar 
          activeSection={activeSection} 
          onSectionChange={handleSectionChange} 
        />
        
        {/* Content Area - Only render the active panel */}
        <Box 
          flex="1" 
          p={5} 
          overflowY="auto"
          position="relative"
        >
          {activeSection === 'dashboard' && <DashboardPanel />}
          {activeSection === 'settings' && <SettingsPanel />}
          {activeSection === 'database' && <DatabasePanel />}
          {activeSection === 'verify' && <VerifyPanel />}
          {activeSection === 'about' && <AboutPanel />}
        </Box>
      </Flex>
      
      {/* Status Bar */}
      <StatusBar />
    </Flex>
  );
};

export default MainWindow; 