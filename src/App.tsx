import React, { useEffect } from 'react';
import { ChakraProvider, extendTheme, ColorModeProvider } from '@chakra-ui/react';
import MainWindow from './frontend/components/MainWindow';

// Extend the theme to customize colors, fonts, etc.
const theme = extendTheme({
  colors: {
    brand: {
      50: '#e6f7ff',
      100: '#b3e0ff',
      500: '#0078d4',
      600: '#0067b8',
      700: '#005a9e',
    },
    primary: {
      50: '#e6f1fe',
      100: '#cce4fd',
      200: '#99c8fb',
      300: '#66adf9',
      400: '#3391f7',
      500: '#0076f5',
      600: '#005ec4',
      700: '#004793',
      800: '#002f62',
      900: '#001831',
    },
    secondary: {
      50: '#f5f8fa',
      100: '#eaf1f5',
      200: '#d5e3eb',
      300: '#c0d5e1',
      400: '#abc7d7',
      500: '#96b9cd',
      600: '#7894a4',
      700: '#5a6f7b',
      800: '#3c4a52',
      900: '#1e2529',
    },
  },
  fonts: {
    heading: 'Inter, system-ui, sans-serif',
    body: 'Inter, system-ui, sans-serif',
  },
  config: {
    initialColorMode: 'light',
    useSystemColorMode: false,
  },
});

const App = function() {
  useEffect(() => {
    const handlePywebviewReady = async () => {
      console.log('🚀 [App] pywebviewready event received! Checking autostart setting...');
      if (window.pywebview?.api?.scan_and_register) {
        try {
          // Check autostart setting before starting scan
          const settings = await window.pywebview.api.get_settings();
          const autostartEnabled = settings.automatic || false;
          
          if (autostartEnabled) {
            console.log('🚀 [App] Autostart enabled - triggering startup scan...');
            // Dispatch event to notify components about operation type
            window.dispatchEvent(new CustomEvent('operation-initiated', {
              detail: { type: 'startup-scan' }
            }));
            window.pywebview.api.scan_and_register();
          } else {
            console.log('⏸️ [App] Autostart disabled - skipping automatic startup scan');
          }
        } catch (error) {
          console.error('❌ [App] Error checking autostart setting:', error);
        }
      }
    };

    // Check if the API is already available (in case the event fired before the listener was attached)
    const checkAndStartScan = async () => {
      if (window.pywebview?.api?.scan_and_register) {
        try {
          console.log('🚀 [App] API available on mount. Checking autostart setting...');
          // Check autostart setting before starting scan
          const settings = await window.pywebview.api.get_settings();
          const autostartEnabled = settings.automatic || false;
          
          if (autostartEnabled) {
            console.log('🚀 [App] Autostart enabled - triggering startup scan...');
            // Dispatch event to notify components about operation type
            window.dispatchEvent(new CustomEvent('operation-initiated', {
              detail: { type: 'startup-scan' }
            }));
            window.pywebview.api.scan_and_register();
          } else {
            console.log('⏸️ [App] Autostart disabled - skipping automatic startup scan');
          }
        } catch (error) {
          console.error('❌ [App] Error checking autostart setting:', error);
        }
      } else {
        // Otherwise, wait for the event
        window.addEventListener('pywebviewready', handlePywebviewReady, { once: true });
      }
    };

    checkAndStartScan();

    return () => {
      window.removeEventListener('pywebviewready', handlePywebviewReady);
    };
  }, []); // Empty dependency array ensures this runs only once on mount

  return (
    <ChakraProvider theme={theme}>
      <ColorModeProvider>
        <MainWindow />
      </ColorModeProvider>
    </ChakraProvider>
  )
}

export default App; 