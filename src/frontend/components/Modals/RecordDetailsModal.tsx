import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Box,
  HStack,
  Text,
  IconButton,
  Divider,
  Flex,
} from '@chakra-ui/react';
import { FiExternalLink, FiClipboard, FiDownload } from 'react-icons/fi';

// Interface for the file record
interface FileRecord {
  id: number;
  file_path: string;
  file_name: string;
  size: number;
  modified_date: string;
  sha256: string;
  tx_id: string;
  registered_at: string;
  user_notes?: string;
}

// Props for the component
interface RecordDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  record: FileRecord;
  formatDate: (date: string) => string;
  formatFileSize: (size: number) => string;
}

/**
 * Modal component for displaying detailed information about a registered file record
 */
const RecordDetailsModal: React.FC<RecordDetailsModalProps> = ({
  isOpen,
  onClose,
  record,
  formatDate,
  formatFileSize,
}) => {
  // Copy text to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        console.log('Text copied to clipboard');
      })
      .catch(err => {
        console.error('Failed to copy:', err);
      });
  };

  // Open blockchain explorer to view transaction
  const openBlockchainExplorer = () => {
    if (!record.tx_id) return;
    
    if (record.tx_id.startsWith('mock_')) {
      console.log('Mock transaction ID, no blockchain explorer available');
      return;
    }
    
    const url = `https://whatsonchain.com/tx/${record.tx_id}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>File Details</ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <Box>
            <DetailItem label="File Name" value={record.file_name} />
            <Divider my={2} />
            
            <DetailItem 
              label="File Path" 
              value={record.file_path}
              isCode
            />
            <Divider my={2} />
            
            <DetailItem 
              label="File Size" 
              value={formatFileSize(record.size)} 
            />
            <Divider my={2} />
            
            <DetailItem 
              label="SHA-256 Hash" 
              value={record.sha256}
              isCode
              action={
                <IconButton
                  aria-label="Copy hash"
                  icon={<FiClipboard />}
                  size="sm"
                  variant="ghost"
                  onClick={() => copyToClipboard(record.sha256)}
                />
              }
            />
            <Divider my={2} />
            
            <DetailItem 
              label="Modified Date" 
              value={formatDate(record.modified_date)} 
            />
            <Divider my={2} />
            
            <DetailItem 
              label="Registered Date" 
              value={formatDate(record.registered_at)} 
            />
            <Divider my={2} />
            
            <DetailItem 
              label="User Notes" 
              value={record.user_notes || "No notes added"} 
            />
            <Divider my={2} />
            
            {record.tx_id && (
              <DetailItem 
                label="Transaction ID" 
                value={record.tx_id}
                isCode
                action={
                  <IconButton
                    aria-label="View on blockchain"
                    icon={<FiExternalLink />}
                    size="sm"
                    variant="ghost"
                    onClick={openBlockchainExplorer}
                  />
                }
              />
            )}
          </Box>
        </ModalBody>
        
        <ModalFooter>
          <Button variant="outline" leftIcon={<FiDownload />} mr={3}>
            Export Certificate
          </Button>
          <Button colorScheme="blue" onClick={onClose}>
            Close
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// Helper component for displaying a label-value pair
interface DetailItemProps {
  label: string;
  value: string;
  isCode?: boolean;
  action?: React.ReactNode;
}

const DetailItem: React.FC<DetailItemProps> = ({ 
  label, 
  value, 
  isCode = false,
  action
}) => (
  <Flex direction={{ base: 'column', sm: 'row' }} mb={2}>
    <Text fontWeight="bold" width="130px" flexShrink={0}>
      {label}:
    </Text>
    <Box flex="1">
      <Text 
        fontSize={isCode ? "sm" : "md"} 
        fontFamily={isCode ? "mono" : "body"}
        wordBreak="break-all"
      >
        {value}
      </Text>
      {action && (
        <Box mt={1}>
          {action}
        </Box>
      )}
    </Box>
  </Flex>
);

export default RecordDetailsModal; 