import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { flushSync } from 'react-dom';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  HStack,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Center,
  Spinner,
  Stack,
  Flex,
  Button,
  useDisclosure,
  useToast,
  Select,
  Link,
  useColorModeValue,
  Textarea,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Icon
} from '@chakra-ui/react';
import { 
  FiSearch, 
  FiExternalLink, 
  FiClipboard, 
  FiInfo, 
  FiCheck,
  FiChevronLeft,
  FiChevronRight,
  FiMoreVertical,
  FiEdit,
  FiSave,
  FiX,
  FiDownload
} from 'react-icons/fi';
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  SortingState,
  ColumnDef,
} from '@tanstack/react-table';
import RecordDetailsModal from '../Modals/RecordDetailsModal';
import DatePicker from 'react-datepicker';
import { DatabaseTable, EditableCell } from './DatabaseTable';

// Define the FileRecord interface based on the backend model
interface FileRecord {
  id: number;
  file_path: string;
  file_name: string;
  size: number;
  modified_date: string;
  sha256: string;
  tx_id: string;
  registered_at: string;
  user_notes?: string; // Make optional for backward compatibility
}

interface RecordsResponse {
  records: FileRecord[];
  total: number;
  limit: number;
  offset: number;
}

// Define pagination state interface
interface PaginationState {
  limit: number;
  offset: number;
  total: number;
}

// Define search criteria state
interface SearchCriteria {
  query: string;
  startDate: string;
  endDate: string;
}

// Define Settings interface
interface AppSettings {
  date_format?: string;
  blockchainExplorerUrlTemplate?: string;
  // Add other settings fields if needed
}

// Create a column helper for type-safe column definitions
const columnHelper = createColumnHelper<FileRecord>();

// Standalone search box component with isolated state and minimal parent coupling
const SearchControls = React.memo(({ onSearchChange, onClear, dateFormat }: { 
  onSearchChange: (criteria: Partial<SearchCriteria>) => void, 
  onClear: () => void,
  dateFormat: string 
}) => {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);

  // Helper function to format Date object to YYYY-MM-DD string
  const formatDateForApi = (date: Date | null): string => {
    if (!date) return '';
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Debounce the query separately from immediate input updates
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300); // Faster debounce for better UX

    return () => {
      clearTimeout(handler);
    };
  }, [query]);

  // Only trigger search when debounced query or dates change
  useEffect(() => {
    onSearchChange({ 
      query: debouncedQuery, 
      startDate: formatDateForApi(startDate), 
      endDate: formatDateForApi(endDate) 
    });
  }, [debouncedQuery, startDate, endDate]);

  const handleClearFilters = () => {
    setQuery('');
    setDebouncedQuery('');
    setStartDate(null);
    setEndDate(null);
    onClear();
  };

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    
    // Use flushSync for immediate updates to prevent input lag
    flushSync(() => {
      setQuery(newValue);
    });
  }, []);
  
  // Determine date format for the date picker component
  const getDatePickerFormat = () => {
    switch (dateFormat) {
      case 'us':
        return 'MM/dd/yyyy';
      case 'eu':
        return 'dd/MM/yyyy';
      default:
        // Attempt to match browser locale for default
        return navigator.language.startsWith('en-US') ? 'MM/dd/yyyy' : 'dd/MM/yyyy';
    }
  };

  return (
    <Box mb={5}>
      <Stack direction={{ base: 'column', md: 'row' }} spacing={4} align="center">
        <InputGroup flex="2">
          <InputLeftElement pointerEvents="none">
            <FiSearch color="gray.300" />
          </InputLeftElement>
          <Input
            placeholder="Search by name, path, hash, tx_id, or notes"
            value={query}
            onChange={handleQueryChange}
            borderRadius="md"
          />
        </InputGroup>
        
        <HStack flex="1.2" justify="center">
          <DatePicker
            selected={startDate}
            onChange={(date: Date | null) => setStartDate(date)}
            selectsStart
            startDate={startDate}
            endDate={endDate}
            dateFormat={getDatePickerFormat()}
            placeholderText="Start Date"
            isClearable
            customInput={<Input borderRadius="md" />}
          />
          <Text>to</Text>
          <DatePicker
            selected={endDate}
            onChange={(date: Date | null) => setEndDate(date)}
            selectsEnd
            startDate={startDate}
            endDate={endDate}
            minDate={startDate}
            dateFormat={getDatePickerFormat()}
            placeholderText="End Date"
            isClearable
            customInput={<Input borderRadius="md" />}
          />
        </HStack>
        
        <Button onClick={handleClearFilters} variant="outline">Clear</Button>
      </Stack>
    </Box>
  );
});

const DatabasePanel: React.FC = () => {
  // State management
  const [records, setRecords] = useState<FileRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchCriteria, setSearchCriteria] = useState<SearchCriteria>({
    query: '',
    startDate: '',
    endDate: ''
  });
  const [pagination, setPagination] = useState<PaginationState>({
    limit: 10,
    offset: 0,
    total: 0
  });
  const [selectedRecord, setSelectedRecord] = useState<FileRecord | null>(null);
  const [appSettings, setAppSettings] = useState<AppSettings>({}); // Store fetched settings
  const [sorting, setSorting] = useState<SortingState>([]);

  // Notes editing state for the MODAL ONLY
  const [noteText, setNoteText] = useState<string>('');
  const [isNotesModalOpen, setIsNotesModalOpen] = useState<boolean>(false);
  const [selectedRecordForNotes, setSelectedRecordForNotes] = useState<FileRecord | null>(null);
  
  // Export functionality state
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Modals and toast
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  // Ref to track if it's the initial load for the main data fetching effect
  const isInitialLoad = useRef(true);
  const prevSearchCriteriaRef = useRef<SearchCriteria>(searchCriteria);

  // Refs to access latest state in event listeners without causing re-renders
  const searchCriteriaRef = useRef(searchCriteria);
  const paginationRef = useRef(pagination);

  // Update refs when state changes
  useEffect(() => {
    searchCriteriaRef.current = searchCriteria;
  }, [searchCriteria]);

  useEffect(() => {
    paginationRef.current = pagination;
  }, [pagination]);

  // Function to fetch application settings
  const fetchAppSettings = useCallback(async () => {
    try {
      if (window.pywebview?.api) {
        const settings = await window.pywebview.api.get_settings();
        setAppSettings(settings);
      }
    } catch (error) {
      console.error('Error fetching app settings:', error);
    }
  }, []);

  // Define the fetchRecords function using useCallback to ensure stability
  const fetchRecords = useCallback(async (criteria: SearchCriteria, limit: number, offset: number) => {
    setLoading(true);

    try {
      if (!window.pywebview || !window.pywebview.api) {
        setRecords([]);
        setPagination(prev => ({ ...prev, total: 0 }));
        setLoading(false);
        return;
      }

      let response: RecordsResponse;
      const isSearching = criteria.query.trim() !== '' || criteria.startDate !== '' || criteria.endDate !== '';

      if (!isSearching) {
        response = await window.pywebview.api.get_records(limit, offset);
      } else {
        response = await window.pywebview.api.search_records(
          criteria.query,
          limit,
          offset,
          criteria.startDate,
          criteria.endDate
        );
      }

      setRecords(response.records);
      setPagination({
        limit: response.limit,
        offset: response.offset,
        total: response.total
      });

    } catch (error) {
      console.error('Error fetching records:', error);
      setRecords([]);
      setPagination(prev => ({ ...prev, total: 0 }));
      toast({
        title: "Error",
        description: "Failed to fetch records. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  // Define event listeners for registration events
  const completeListener = useCallback(() => {
    toast({
      title: "Refreshing database",
      description: "Updating the records list with newly registered files",
      status: "info",
      duration: 3000,
      isClosable: true
    });

    setTimeout(() => {
      fetchRecords(searchCriteriaRef.current, paginationRef.current.limit, paginationRef.current.offset);
    }, 2000);
    setTimeout(() => {
      fetchRecords(searchCriteriaRef.current, paginationRef.current.limit, paginationRef.current.offset);
    }, 5000);
  }, [fetchRecords, toast]);

  // Handle search criteria changes from the SearchControls component
  const handleSearchChange = useCallback((newCriteria: Partial<SearchCriteria>) => {
    setPagination(prev => ({ ...prev, offset: 0 })); // Reset to first page on new search
    setSearchCriteria(prev => ({ ...prev, ...newCriteria }));
  }, []);

  const handleClearSearch = useCallback(() => {
    setPagination(prev => ({ ...prev, offset: 0 }));
    setSearchCriteria({ query: '', startDate: '', endDate: '' });
  }, []);

  // Main effect for setting up listeners and initial fetch
  useEffect(() => {
    fetchAppSettings();

    const registrationCompleteListener = () => completeListener();
    window.addEventListener('operation-complete', registrationCompleteListener);

    return () => {
      window.removeEventListener('operation-complete', registrationCompleteListener);
    };
  }, [fetchAppSettings, completeListener]);

  // Effect for fetching records when searchCriteria or pagination changes
  useEffect(() => {
    if (isInitialLoad.current) {
      fetchRecords(searchCriteria, pagination.limit, pagination.offset);
      isInitialLoad.current = false;
      prevSearchCriteriaRef.current = searchCriteria;
      return;
    }

    if (JSON.stringify(prevSearchCriteriaRef.current) !== JSON.stringify(searchCriteria)) {
      if (pagination.offset !== 0) {
        setPagination(prev => ({ ...prev, offset: 0 }));
      } else {
        fetchRecords(searchCriteria, pagination.limit, 0);
      }
    } else {
      fetchRecords(searchCriteria, pagination.limit, pagination.offset);
    }

    prevSearchCriteriaRef.current = searchCriteria;
  }, [searchCriteria, pagination.limit, pagination.offset, fetchRecords]);

  // View details modal handler
  const viewDetails = useCallback((record: FileRecord) => {
    setSelectedRecord(record);
    onOpen();
  }, [onOpen]);
  
  // Handle copying to clipboard
  const onCopyToClipboard = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: "Copied to clipboard!",
        status: "success",
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Failed to copy:', error);
      toast({
        title: "Error",
        description: "Failed to copy to clipboard.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  }, [toast]);

  const handleSaveNote = async (recordId: number, newNotes: string) => {
    try {
      if (window.pywebview?.api) {
        await window.pywebview.api.update_file_record_notes(recordId, newNotes);
        toast({
          title: "Note Saved",
          status: "success",
          duration: 2000,
          isClosable: true
        });
        
        // Optimistically update the local state to avoid a full refresh
        setRecords(prevRecords => 
          prevRecords.map(r => 
            r.id === recordId ? { ...r, user_notes: newNotes } : r
          )
        );
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save note.",
        status: "error",
        duration: 5000,
        isClosable: true
      });
      console.error("Failed to save note: ", error);
    }
  };

  const updateTableData = (rowIndex: number, columnId: string, value: string) => {
    const record = records[rowIndex];
    if (record && columnId === 'user_notes') {
      handleSaveNote(record.id, value);
    }
  };

  // Modal handlers
  const openNotesModal = useCallback((record: FileRecord) => {
    setSelectedRecordForNotes(record);
    setNoteText(record.user_notes || '');
    setIsNotesModalOpen(true);
  }, []);

  const handleCloseNotesModal = useCallback(() => {
    setIsNotesModalOpen(false);
    setSelectedRecordForNotes(null);
    setNoteText('');
  }, []);

  const handleSaveNoteFromModal = useCallback(async () => {
    if (!selectedRecordForNotes) return;
    await handleSaveNote(selectedRecordForNotes.id, noteText);
    handleCloseNotesModal(); // Close modal after attempting save
  }, [noteText, selectedRecordForNotes, handleCloseNotesModal, handleSaveNote]);

  // CSV Export handler
  const handleExportCSV = useCallback(async (exportType: 'current' | 'all') => {
    setIsExporting(true);
    try {
      if (window.pywebview?.api) {
        const filename = `nora_records_${new Date().toISOString().split('T')[0]}.csv`;
        
        let result;
        if (exportType === 'current') {
          // Export current filtered/searched results
          result = await window.pywebview.api.export_records_csv(
            searchCriteria.query,
            searchCriteria.startDate,
            searchCriteria.endDate,
            filename
          );
        } else {
          // Export all records
          result = await window.pywebview.api.export_all_records_csv(filename);
        }
        
        if (result.success) {
          toast({
            title: "Export Successful",
            description: `${result.count} records exported to ${filename}`,
            status: "success",
            duration: 5000,
            isClosable: true
          });
        } else {
          throw new Error(result.error || 'Export failed');
        }
      }
    } catch (error) {
      console.error('CSV Export Error:', error);
      toast({
        title: "Export Failed",
        description: "Failed to export records to CSV",
        status: "error",
        duration: 5000,
        isClosable: true
      });
    } finally {
      setIsExporting(false);
    }
  }, [searchCriteria, toast]);

  // --- Handle opening blockchain explorer ---
  const viewOnBlockchain = useCallback((txId: string) => {
    if (appSettings.blockchainExplorerUrlTemplate) {
      window.open(appSettings.blockchainExplorerUrlTemplate.replace('{txId}', txId), '_blank');
    }
  }, [appSettings.blockchainExplorerUrlTemplate]);

  // Memoize handlers to prevent re-creating them on every render.
  // This is crucial for stabilizing the `columns` prop passed to the table.
  const formatDate = useCallback((dateString: string) => {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
        return 'Invalid Date';
    }

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
  }, [appSettings.date_format]);

  const formatHash = useCallback((hash: string | null | undefined) => {
    if (!hash) return 'N/A';
    return `${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}`;
  }, []);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // UI colors
  const thBg = useColorModeValue("gray.50", "gray.700");
  const rowHoverBg = useColorModeValue("gray.100", "gray.600");

  const columns = useMemo<ColumnDef<FileRecord>[]>(() => [
    {
      accessorKey: 'registered_at',
      header: 'Registered',
      cell: info => <Text userSelect="text">{formatDate(info.getValue() as string)}</Text>,
      size: 180,
    },
    {
      accessorKey: 'file_name',
      header: 'File Name',
      cell: info => <Text maxW="250px" isTruncated title={info.getValue() as string} userSelect="text">{info.getValue() as string}</Text>,
      size: 250,
    },
    {
      accessorKey: 'file_path',
      header: 'File Path',
       cell: info => <Text maxW="300px" isTruncated title={info.getValue() as string} userSelect="text">{info.getValue() as string}</Text>,
       size: 300,
    },
    {
      accessorKey: 'user_notes',
      header: 'Notes',
      cell: EditableCell, // Use our new editable cell component
      enableSorting: false, // It doesn't make sense to sort by notes
      size: 250,
    },
    {
      accessorKey: 'sha256',
      header: 'SHA-256 Hash',
      cell: info => (
        <HStack spacing={1}>
          <Text fontSize="sm" fontFamily="mono" userSelect="text">
            {formatHash(info.getValue() as string)}
          </Text>
          <IconButton
            aria-label="Copy SHA-256 Hash"
            icon={<FiClipboard size="0.9em" />}
            size="xs"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onCopyToClipboard(info.getValue() as string);
            }}
          />
        </HStack>
      ),
      size: 150,
    },
    {
      accessorKey: 'tx_id',
      header: 'Transaction ID',
      cell: info => (
        <HStack spacing={1}>
          <Text fontSize="sm" fontFamily="mono" userSelect="text">
            {formatHash(info.getValue() as string)}
          </Text>
          <IconButton
            aria-label="Copy Transaction ID"
            icon={<FiClipboard size="0.9em" />}
            size="xs"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              onCopyToClipboard(info.getValue() as string);
            }}
          />
        </HStack>
      ),
      size: 150,
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => {
        const record = row.original;
        return (
          <Menu>
            <MenuButton
              as={IconButton}
              aria-label="Options"
              icon={<FiMoreVertical />}
              variant="ghost"
              size="sm"
            />
            <MenuList>
              <MenuItem 
                icon={<FiInfo />} 
                onClick={() => viewDetails(record)}
              >
                View Details
              </MenuItem>
               <MenuItem 
                icon={<FiEdit />} 
                onClick={() => openNotesModal(record)}
              >
                Edit Note (Modal)
              </MenuItem>
              <MenuItem 
                icon={<FiExternalLink />} 
                onClick={() => viewOnBlockchain(record.tx_id)}
                isDisabled={!record.tx_id || record.tx_id.startsWith('mock_')}
              >
                View on Blockchain
              </MenuItem>
              <MenuItem 
                icon={<FiClipboard />} 
                onClick={() => onCopyToClipboard(record.sha256)}
              >
                Copy File Hash
              </MenuItem>
            </MenuList>
          </Menu>
        );
      },
      enableSorting: false,
      size: 50,
    }
  ], [appSettings.date_format, onCopyToClipboard, formatDate, formatHash, viewDetails, openNotesModal, viewOnBlockchain]);

  // Pagination handlers
  const handlePageChange = (newOffset: number) => {
    if (newOffset < 0 || (newOffset >= pagination.total && pagination.total > 0)) return;
    setPagination(prev => ({ ...prev, offset: newOffset }));
  };

  const handleLimitChange = (newLimit: number) => {
    setPagination(prev => ({ ...prev, limit: newLimit, offset: 0 }));
  };

  const totalPages = Math.ceil(pagination.total / pagination.limit);
  const currentPage = Math.floor(pagination.offset / pagination.limit) + 1;

  return (
    <Box p={5}>
      <Flex justify="space-between" align="center" mb={5}>
        <Heading as="h2" size="lg">
          Database Records
        </Heading>
        <HStack>
          <Menu>
            <MenuButton 
              as={Button} 
              leftIcon={<FiDownload />} 
              isLoading={isExporting}
              loadingText="Exporting..."
              size="sm"
            >
              Export CSV
            </MenuButton>
            <MenuList>
              <MenuItem onClick={() => handleExportCSV('current')}>
                Export Current Results ({pagination.total} records)
              </MenuItem>
              <MenuItem onClick={() => handleExportCSV('all')}>
                Export All Records
              </MenuItem>
            </MenuList>
          </Menu>
        </HStack>
      </Flex>
      <SearchControls 
        onSearchChange={handleSearchChange} 
        onClear={handleClearSearch}
        dateFormat={useMemo(() => appSettings.date_format || 'default', [appSettings.date_format])}
      />
      
      {loading ? (
        <Center p={10}>
          <Spinner size="xl" />
        </Center>
      ) : pagination.total === 0 ? (
         <Center p={10}>
          <Text>No records found.</Text>
        </Center>
      ) : (
        <>
        <DatabaseTable
          data={records}
          columns={columns}
          sorting={sorting}
          setSorting={setSorting}
           // Disable client-side global filtering to avoid hiding backend search results
           // (e.g., searching by sha256 which is not a visible column in the table)
           globalFilter={''}
           setGlobalFilter={() => {}}
          updateData={updateTableData}
        />

        {/* Pagination Controls */}
        <Flex justify="space-between" align="center" mt={4}>
            <HStack>
                <Text fontSize="sm">Rows per page:</Text>
                <Select
                    value={pagination.limit}
                    onChange={(e) => handleLimitChange(parseInt(e.target.value, 10))}
                    width="85px"
                    size="sm"
                >
                    {[10, 20, 50, 100].map(pageSize => (
                        <option key={pageSize} value={pageSize}>
                            {pageSize}
                        </option>
                    ))}
                </Select>
            </HStack>
            <HStack>
                 <Text fontSize="sm" pr={4}>
                    Page {currentPage} of {totalPages}
                </Text>
                <IconButton
                    aria-label="Go to first page"
                    icon={<FiChevronLeft />}
                    onClick={() => handlePageChange(0)}
                    isDisabled={currentPage === 1}
                    size="sm"
                />
                <IconButton
                    aria-label="Go to previous page"
                    icon={<FiChevronLeft />}
                    onClick={() => handlePageChange(pagination.offset - pagination.limit)}
                    isDisabled={currentPage === 1}
                    size="sm"
                />

                <IconButton
                    aria-label="Go to next page"
                    icon={<FiChevronRight />}
                    onClick={() => handlePageChange(pagination.offset + pagination.limit)}
                    isDisabled={currentPage >= totalPages}
                    size="sm"
                />
                <IconButton
                    aria-label="Go to last page"
                    icon={<FiChevronRight />}
                    onClick={() => handlePageChange((totalPages - 1) * pagination.limit)}
                    isDisabled={currentPage >= totalPages}
                    size="sm"
                />
            </HStack>
            <Text fontSize="sm">
                Total Records: {pagination.total}
            </Text>
        </Flex>
       </>
      )}

      {/* Notes Editing Modal */}
      <Modal isOpen={isNotesModalOpen} onClose={handleCloseNotesModal} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Edit Note</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Box>
              <Text fontWeight="bold" mb={2}>File:</Text>
              <Text fontSize="sm" color="gray.600" mb={4}>
                {selectedRecordForNotes?.file_name}
              </Text>
              <Text fontWeight="bold" mb={2}>Note:</Text>
              <Textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Add your note about this file..."
                resize="vertical"
                minH="100px"
                fontSize="sm"
              />
            </Box>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={handleCloseNotesModal}>
              Cancel
            </Button>
            <Button colorScheme="blue" onClick={handleSaveNoteFromModal}>
              Save Note
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Record Details Modal */}
      {selectedRecord && (
        <RecordDetailsModal
          isOpen={isOpen}
          onClose={onClose}
          record={selectedRecord}
          formatDate={formatDate}
          formatFileSize={formatFileSize}
        />
      )}
    </Box>
  );
};

export default DatabasePanel; 