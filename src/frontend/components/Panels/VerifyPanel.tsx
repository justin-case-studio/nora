import React, { useState, useEffect, DragEvent } from 'react';
import {
  Box,
  Heading,
  VStack,
  HStack,
  Text,
  Button,
  Divider,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Progress,
  Icon,
  Center,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiUpload, FiCheck, FiX, FiSearch, FiFile, FiExternalLink, FiFolder } from 'react-icons/fi';

// --- Updated Backend Response Structure --- 
interface BlockchainVerificationDetails { // For the nested blockchain client response
  status: string;
  message: string;
  verified?: boolean;
  confirmed?: boolean;
  timestamp?: string;
  block_height?: number;
  tx_id?: string; 
  hash_match?: boolean;
  blockchain_explorer_url?: string; // Added from api.py logic
}

interface RecordDetail { // For items in the 'records' array
  file_path: string;
  file_name: string;
  size: number;
  modified_date: string | null;
  sha256: string;
  tx_id: string;
  registered_at: string | null;
}

interface AppSettings {
  date_format?: string;
}

interface VerificationApiResponse {
  status: string; // e.g., "local_record_found", "verified", "not_found_in_db", "pending", "mismatch", "error_..."
  message: string;
  verified: boolean; // Overall verification status from backend
  records?: RecordDetail[];
  primary_record_used?: RecordDetail | null; // The specific record used for verification
  blockchain_verification_details?: BlockchainVerificationDetails | null;
  current_hash?: string;
  hash_match?: boolean; // Top-level, indicates if current_hash matches a primary record being checked
}
// -------------------------------------------------

const VerifyPanel: React.FC = () => {
  const toast = useToast();

  const [filePath, setFilePath] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  // Updated state variables for verification results
  const [verificationApiStatus, setVerificationApiStatus] = useState<string | null>(null);
  const [verificationDisplayMessage, setVerificationDisplayMessage] = useState<string | null>(null); 
  const [dbRecords, setDbRecords] = useState<RecordDetail[] | null>(null);
  const [primaryRecordUsed, setPrimaryRecordUsed] = useState<RecordDetail | null>(null);
  const [blockchainInfo, setBlockchainInfo] = useState<BlockchainVerificationDetails | null>(null);
  const [currentVerifiedHash, setCurrentVerifiedHash] = useState<string | null>(null);

  // --- State for Drag and Drop ---
  const [isDragging, setIsDragging] = useState(false);
  // ---------------------------------

  const [appSettings, setAppSettings] = useState<AppSettings>({});

  useEffect(() => {
    (async () => {
      try {
        if (window.pywebview?.api) {
          const settings = await window.pywebview.api.get_settings();
          setAppSettings(settings || {});
        }
      } catch (error) {
        console.error('Error fetching app settings:', error);
      }
    })();
  }, []);

  // --- Colors for Drag and Drop --- 
  const dropZoneBg = useColorModeValue('gray.50', 'gray.700');
  const dropZoneBorderColor = useColorModeValue('gray.300', 'gray.600');
  const dropZoneHoverBg = useColorModeValue('blue.50', 'blue.900');
  const dropZoneHoverBorderColor = useColorModeValue('blue.400', 'blue.300');
  // ---------------------------------

  const clearVerificationState = () => {
    setVerificationApiStatus(null);
    setVerificationDisplayMessage(null);
    setDbRecords(null);
    setPrimaryRecordUsed(null);
    setBlockchainInfo(null);
    setCurrentVerifiedHash(null);
  };

  const acceptPath = (rawPath: string) => {
    const cleaned = rawPath.trim();
    if (!cleaned) return;
    const name = cleaned.split(/[\\/]/).pop() || cleaned;
    setFilePath(cleaned);
    setFileName(name);
  };

  const extractPathFromDrop = (e: DragEvent<HTMLDivElement>): string | null => {
    // WebKit2GTK (pywebview on Linux) does not populate a readable FileList
    // for OS-originated drops, so prefer URI-list / plain text which it does
    // expose. Fall back to a native .path on the File (some webviews inject it).
    const uriList = e.dataTransfer.getData('text/uri-list');
    if (uriList) {
      const firstUri = uriList.split(/\r?\n/).find(line => line && !line.startsWith('#'));
      if (firstUri) {
        if (firstUri.startsWith('file://')) {
          try {
            return decodeURIComponent(firstUri.replace(/^file:\/\//, ''));
          } catch {
            return firstUri.replace(/^file:\/\//, '');
          }
        }
        return firstUri;
      }
    }
    const plain = e.dataTransfer.getData('text/plain');
    if (plain && (plain.startsWith('/') || plain.startsWith('file://') || /^[A-Za-z]:[\\/]/.test(plain))) {
      return plain.startsWith('file://')
        ? decodeURIComponent(plain.replace(/^file:\/\//, ''))
        : plain.trim();
    }
    const file = e.dataTransfer.files?.[0] as (File & { path?: string }) | undefined;
    if (file?.path) return file.path;
    return null;
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    // Best-effort: drag-and-drop of OS files is unreliable across
    // WebKit2GTK versions. We try the two paths pywebview actually supports,
    // then silently give up and let the user use Browse.
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const syncPath = extractPathFromDrop(e);
    e.dataTransfer.clearData?.();
    if (syncPath) {
      clearVerificationState();
      setFilePath(null);
      setFileName(null);
      acceptPath(syncPath);
      return;
    }

    try {
      const result = await window.pywebview.api.consume_dropped_path();
      if (result && result.path) {
        clearVerificationState();
        setFilePath(null);
        setFileName(null);
        acceptPath(result.path);
      }
    } catch {
      // ignore — user can still click to browse
    }
  };

  const handleBrowse = async () => {
    try {
      const result = await window.pywebview.api.select_file();
      if (result && result.length > 0) {
        clearVerificationState();
        acceptPath(result[0]);
      }
    } catch (error) {
      console.error('Error opening file dialog:', error);
      toast({
        title: 'Could not open file dialog',
        description: error instanceof Error ? error.message : 'Unknown error',
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    }
  };

  const handleVerify = async () => {
    if (!filePath) {
      toast({
        title: 'No File Selected',
        description: 'Drop a file on the dropzone or click Browse to pick one.',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsVerifying(true);
    clearVerificationState();
    console.log(`Starting verification for file: ${filePath}`);

    try {
      const response = (await window.pywebview.api.verify_file(filePath)) as VerificationApiResponse;
      console.log('Verification response from backend:', response);

      if (response && response.status) {
        setVerificationApiStatus(response.status);
        setVerificationDisplayMessage(response.message);
        setDbRecords(response.records || null);
        setPrimaryRecordUsed(response.primary_record_used || null);
        setBlockchainInfo(response.blockchain_verification_details || null);
        setCurrentVerifiedHash(response.current_hash || null);

        let toastStatus: 'success' | 'info' | 'warning' | 'error' = 'info';
        let toastTitle = 'Verification Status';

        if (response.status === "verified") { 
          toastStatus = 'success';
          toastTitle = 'Blockchain Verification Successful';
        } else if (response.status === "local_record_found") {
          toastStatus = 'info'; 
          toastTitle = 'Local Record Found';
        } else if (response.status === "not_found_in_db") {
          toastStatus = 'warning';
          toastTitle = 'File Not Found';
        } else if (response.status.includes("error") || response.status === "mismatch" || response.status === "unknown_record_type") {
          toastStatus = 'error';
          toastTitle = 'Verification Issue';
        } else if (response.status === "pending") {
          toastStatus = 'info';
          toastTitle = 'Transaction Pending';
        }
        
        toast({
          title: toastTitle,
          description: response.message,
          status: toastStatus,
          duration: 5000,
          isClosable: true,
        });

      } else {
        // This case handles if 'response' or 'response.status' is null/undefined
        setVerificationApiStatus('error_frontend');
        setVerificationDisplayMessage('Invalid or empty response from backend.');
        toast({
          title: 'Frontend Error',
          description: 'Received an invalid response from the backend.',
          status: 'error',
          duration: 5000,
          isClosable: true,
        });
      }

    } catch (error) {
      console.error('Error verifying file:', error);
      setVerificationApiStatus('error_api_call');
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred.';
      setVerificationDisplayMessage(`API Call Failed: ${errorMessage}`);
      toast({
        title: 'Verification API Error',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const formatDate = (dateString: string | undefined | null) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid Date';

    const pad = (num: number) => num.toString().padStart(2, '0');
    const day = pad(date.getDate());
    const month = pad(date.getMonth() + 1);
    const year = date.getFullYear();
    const hours = pad(date.getHours());
    const minutes = pad(date.getMinutes());

    const formatPreference = appSettings.date_format || (navigator.language.startsWith('en-US') ? 'us' : 'eu');
    if (formatPreference === 'us') {
      return `${month}/${day}/${year}, ${hours}:${minutes}`;
    }
    return `${day}/${month}/${year}, ${hours}:${minutes}`;
  };

  const handleViewOnBlockchain = async () => {
    if (!blockchainInfo?.blockchain_explorer_url) {
      console.error('[VerifyPanel] No blockchain_explorer_url available in blockchainInfo.');
      toast({ title: 'Error', description: 'Blockchain explorer URL not available.', status: 'error' });
      return;
    }
    try {
      // @ts-ignore
      const response = await window.pywebview.api.open_external_url(blockchainInfo.blockchain_explorer_url);
      if (!response.success) {
        console.error("[VerifyPanel] Backend failed to open URL:", response.error);
        toast({ title: 'Error Opening Link', description: response.error || 'Could not open link.', status: 'error' });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Could not open link.';
      console.error('[VerifyPanel] Error calling open_external_url:', error);
      toast({ title: 'Error', description: errorMessage, status: 'error' });
    }
  };

  const getAlertStatus = (): 'success' | 'info' | 'warning' | 'error' => {
    if (!verificationApiStatus) return 'info'; // Default or initial state
    if (verificationApiStatus === 'verified') return 'success';
    if (verificationApiStatus === 'local_record_found') return 'info'; // Neutral blue/grey for local
    if (verificationApiStatus === 'not_found_in_db') return 'warning';
    if (verificationApiStatus.includes('error') || verificationApiStatus === 'mismatch' || verificationApiStatus === 'unknown_record_type') return 'error';
    if (verificationApiStatus === 'pending') return 'info';
    return 'info'; // Fallback
  };

  const getAlertTitle = (): string => {
    if (!verificationApiStatus) return 'Verify File Status';
    if (verificationApiStatus === 'verified') return 'File Verified Successfully!';
    if (verificationApiStatus === 'local_record_found') return 'File Found in Local Database';
    if (verificationApiStatus === 'not_found_in_db') return 'File Not Found in Database';
    if (verificationApiStatus === 'pending') return 'Transaction Pending Confirmation';
    if (verificationApiStatus.includes('error')) return 'Verification Error';
    if (verificationApiStatus === 'mismatch') return 'Hash Mismatch on Blockchain';
    if (verificationApiStatus === 'unknown_record_type') return 'Unknown Record Type';
    return 'Verification Status';
  };

  return (
    <Box p={6} h="full" overflowY="auto">
      <Heading size="lg" mb={6}>Verify File</Heading>
      
      <VStack spacing={8} align="stretch">
        <Box p={5} borderWidth="1px" borderRadius="md">
          <VStack spacing={4} align="stretch">
            <Text>Select a file to verify its registration status.</Text>

            <Center
              p={10}
              borderWidth="2px"
              borderRadius="md"
              borderStyle="dashed"
              borderColor={isDragging ? dropZoneHoverBorderColor : dropZoneBorderColor}
              bg={isDragging ? dropZoneHoverBg : dropZoneBg}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={handleBrowse}
              cursor="pointer"
            >
              <VStack spacing={3}>
                {filePath ? (
                  <>
                    <Icon as={FiFile} w={8} h={8} color="green.500" />
                    <Text fontWeight="medium">{fileName}</Text>
                    <Text fontSize="xs" color="gray.500" noOfLines={1} title={filePath}>{filePath}</Text>
                    <Text fontSize="sm" color="green.500">Ready to verify</Text>
                  </>
                ) : (
                  <>
                    <Icon as={FiUpload} w={8} h={8} color="gray.500" />
                    <Text fontWeight="medium">Click to select a file</Text>
                    <Text fontSize="xs" color="gray.500">(drag &amp; drop may also work)</Text>
                  </>
                )}
              </VStack>
            </Center>

            <HStack mt={4} spacing={3}>
              <Button
                variant="outline"
                onClick={handleBrowse}
                leftIcon={<FiFolder />}
                isDisabled={isVerifying}
              >
                Browse...
              </Button>
              <Button
                colorScheme="blue"
                isDisabled={!filePath || isVerifying}
                onClick={handleVerify}
                isLoading={isVerifying}
                loadingText="Verifying..."
                leftIcon={<FiSearch />}
                flex={1}
              >
                Verify File
              </Button>
            </HStack>
          </VStack>
        </Box>
        
        {isVerifying && (
          <Box>
            <Text mb={2}>Verifying registration status...</Text> {/* Generic message */}
            <Progress size="sm" isIndeterminate colorScheme="blue" />
          </Box>
        )}
        
        {verificationApiStatus && verificationDisplayMessage && (
          <Box>
            <Alert
              status={getAlertStatus()} // Use helper function for status color
              variant="subtle"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              borderRadius="md"
              py={6}
            >
              <AlertIcon boxSize="40px" mr={0} />
              <AlertTitle mt={4} mb={1} fontSize="lg">
                {getAlertTitle()} {/* Use helper function for title */}
              </AlertTitle>
              <AlertDescription maxWidth="sm">
                {verificationDisplayMessage} {/* This now comes directly from backend response.message */}
              </AlertDescription>
            </Alert>
            
            {/* Display Details Section - Reworked */} 
            { (dbRecords && dbRecords.length > 0) && (
              <Box mt={6} p={5} borderWidth="1px" borderRadius="md">
                <Heading size="md" mb={4}>
                  {verificationApiStatus === 'local_record_found' ? 'Local Record Details' : 
                   (verificationApiStatus === 'verified' || verificationApiStatus === 'pending' || verificationApiStatus === 'mismatch') ? 'Verification Details' :
                   'File Record Information' /* Fallback title for details */}
                </Heading>
                <VStack spacing={3} align="stretch">
                  <Heading size="sm" color="gray.600">File Being Verified</Heading>
                  <HStack><Text fontWeight="semibold" width="150px">Current Hash:</Text><Text fontFamily="monospace" noOfLines={1} title={currentVerifiedHash || 'N/A'}>{currentVerifiedHash || 'N/A'}</Text></HStack>
                  {fileName && <HStack><Text fontWeight="semibold" width="150px">Selected File:</Text><Text noOfLines={1} title={filePath || fileName}>{fileName}</Text></HStack>}
                  
                  {/* Section 2: Blockchain Confirmation Details (if applicable) */}
                  {blockchainInfo && (verificationApiStatus === 'verified' || verificationApiStatus === 'pending' || verificationApiStatus === 'mismatch') && (
                    <>
                      <Divider my={3} />
                      <Heading size="sm" color="gray.600">Blockchain Confirmation Details</Heading>
                      <HStack>
                        <Text fontWeight="semibold" width="150px">Status:</Text>
                        <Text color={blockchainInfo.status === 'verified' ? 'green.500' : blockchainInfo.status === 'pending' ? 'orange.500' : 'red.500' }>
                          {blockchainInfo.status ? blockchainInfo.status.charAt(0).toUpperCase() + blockchainInfo.status.slice(1) : 'N/A'}
                        </Text>
                      </HStack>
                      {blockchainInfo.status === 'verified' &&
                        <HStack>
                          <Icon as={blockchainInfo.hash_match ? FiCheck : FiX} color={blockchainInfo.hash_match ? 'green.500' : 'red.500'} />
                          <Text>
                            {blockchainInfo.hash_match
                              ? 'File is unchanged since registration'
                              : 'File has been modified since registration'}
                          </Text>
                        </HStack>
                      }
                      {blockchainInfo.block_height && (
                        <Text>Recorded at {formatDate(blockchainInfo.timestamp)} in block {blockchainInfo.block_height}</Text>
                      )}
                      {blockchainInfo.status === 'verified' && blockchainInfo.tx_id && (
                        <HStack>
                          <Text fontWeight="semibold" width="150px">Blockchain TX ID:</Text>
                          <Text fontFamily="monospace">{blockchainInfo.tx_id}</Text>
                        </HStack>
                      )}
                      
                      {/* Buttons for Blockchain section */}
                      <HStack justifyContent="flex-end" mt={3} spacing={3}>
                        {blockchainInfo.blockchain_explorer_url &&
                            <Button 
                                variant="outline" 
                                colorScheme="blue" 
                                size="sm" 
                                leftIcon={<FiExternalLink />}
                                onClick={handleViewOnBlockchain}
                                isDisabled={!blockchainInfo?.blockchain_explorer_url}
                            >
                              View on Blockchain
                            </Button>
                        }
                        {verificationApiStatus === 'verified' && (
                            <Button 
                                colorScheme="blue" 
                                size="sm" 
                                isDisabled={false} // Enable the button
                            >
                            Export Certificate
                            </Button>
                        )}
                      </HStack>
                    </>
                  )}

                  {/* Section 3: Database Record(s) */}
                  <Divider my={2}/>
                  <Heading size="sm" color="gray.600">Database Record(s)</Heading>
                  
                  {/* Show primary record first with highlighting */}
                  {primaryRecordUsed && (
                    <Box pl={2} borderLeftWidth="3px" borderColor="blue.400" mb={3} bg="blue.50" p={3} borderRadius="md">
                      <Text fontWeight="bold" color="blue.600" mb={2}>
                        ⭐ Primary Record Used for Verification (Oldest)
                      </Text>
                      <HStack><Text fontWeight="semibold" width="150px">Original Path:</Text><Text noOfLines={1} title={primaryRecordUsed.file_path}>{primaryRecordUsed.file_path}</Text></HStack>
                      <HStack><Text fontWeight="semibold" width="150px">Original Name:</Text><Text>{primaryRecordUsed.file_name}</Text></HStack>
                      <HStack><Text fontWeight="semibold" width="150px">Size:</Text><Text>{primaryRecordUsed.size} bytes</Text></HStack>
                      <HStack><Text fontWeight="semibold" width="150px">DB SHA256:</Text><Text fontFamily="monospace" noOfLines={1} title={primaryRecordUsed.sha256}>{primaryRecordUsed.sha256}</Text></HStack>
                      <HStack><Text fontWeight="semibold" width="150px">Tx ID:</Text><Text fontFamily="monospace" noOfLines={1} title={primaryRecordUsed.tx_id}>{primaryRecordUsed.tx_id}</Text></HStack>
                      <HStack><Text fontWeight="semibold" width="150px">Registered (DB):</Text><Text>{formatDate(primaryRecordUsed.registered_at)}</Text></HStack>
                    </Box>
                  )}
                  
                  {/* Show other records if there are multiple */}
                  {dbRecords && dbRecords.length > 1 && (
                    <>
                      <Text fontWeight="semibold" color="gray.600" mt={3} mb={2}>
                        Other Records for this Hash
                      </Text>
                      {dbRecords.filter(record => 
                        !primaryRecordUsed || 
                        record.tx_id !== primaryRecordUsed.tx_id || 
                        record.registered_at !== primaryRecordUsed.registered_at
                      ).map((record, index) => (
                        <Box key={index} pl={2} borderLeftWidth="2px" borderColor="gray.200" mb={2}>
                          <HStack><Text fontWeight="semibold" width="150px">Original Path:</Text><Text noOfLines={1} title={record.file_path}>{record.file_path}</Text></HStack>
                          <HStack><Text fontWeight="semibold" width="150px">Original Name:</Text><Text>{record.file_name}</Text></HStack>
                          <HStack><Text fontWeight="semibold" width="150px">Size:</Text><Text>{record.size} bytes</Text></HStack>
                          <HStack><Text fontWeight="semibold" width="150px">DB SHA256:</Text><Text fontFamily="monospace" noOfLines={1} title={record.sha256}>{record.sha256}</Text></HStack>
                          <HStack><Text fontWeight="semibold" width="150px">Tx ID:</Text><Text fontFamily="monospace" noOfLines={1} title={record.tx_id}>{record.tx_id}</Text></HStack>
                          <HStack><Text fontWeight="semibold" width="150px">Registered (DB):</Text><Text>{formatDate(record.registered_at)}</Text></HStack>
                        </Box>
                      ))}
                    </>
                  )}
                  
                  {/* Fallback: show all records if no primary record is specified */}
                  {!primaryRecordUsed && dbRecords && dbRecords.map((record, index) => (
                    <Box key={index} pl={2} borderLeftWidth="2px" borderColor="gray.200" mb={2}>
                        <HStack><Text fontWeight="semibold" width="150px">Original Path:</Text><Text noOfLines={1} title={record.file_path}>{record.file_path}</Text></HStack>
                        <HStack><Text fontWeight="semibold" width="150px">Original Name:</Text><Text>{record.file_name}</Text></HStack>
                        <HStack><Text fontWeight="semibold" width="150px">Size:</Text><Text>{record.size} bytes</Text></HStack>
                        <HStack><Text fontWeight="semibold" width="150px">DB SHA256:</Text><Text fontFamily="monospace" noOfLines={1} title={record.sha256}>{record.sha256}</Text></HStack>
                        <HStack><Text fontWeight="semibold" width="150px">Tx ID:</Text><Text fontFamily="monospace" noOfLines={1} title={record.tx_id}>{record.tx_id}</Text></HStack>
                        <HStack><Text fontWeight="semibold" width="150px">Registered (DB):</Text><Text>{formatDate(record.registered_at)}</Text></HStack>
                    </Box>
                  ))}
                  
                  {/* Informational text if only local record */}
                  {(verificationApiStatus === 'local_record_found') && (
                    <Text fontSize="sm" color="gray.500" mt={3} fontStyle="italic">
                      This file's record was found in the local database only.
                    </Text>
                  )}
                </VStack>
              </Box>
            )}
          </Box>
        )}
      </VStack>
    </Box>
  );
};

export default VerifyPanel; 