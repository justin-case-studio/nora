import React from 'react';
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  Link,
  Divider,
  Icon,
} from '@chakra-ui/react';
import {
  FiExternalLink,
  FiGithub,
  FiCheck,
  FiShield,
  FiDatabase,
  FiSearch,
  FiClock,
} from 'react-icons/fi';

const AboutPanel: React.FC = () => {
  return (
    <Box p={6} h="full" overflowY="auto">
      <VStack spacing={8} align="stretch">
        <Box textAlign="center">
          <Heading size="lg" mb={2}>Nora</Heading>
          <Text fontSize="md" color="gray.600">
            Permanent proof your files existed
          </Text>
        </Box>

        <Divider />

        <Box>
          <Heading size="md" mb={4}>About Nora</Heading>
          <Text mb={4}>
            You never know which files will matter later. A contract, a draft, a photo,
            a spreadsheet — most likely you'll never need to prove anything about them.
            But for the few you do, having a tamper-proof record of when the file existed,
            in exactly that form, can be the difference between a clean resolution and an
            expensive one. Think of Nora as a safety net for your files: pay fractions of
            a cent to timestamp anything that <i>might</i> matter someday, and you'll have
            permanent proof if it ever does.
          </Text>
          <Text mb={4}>
            Nora is a desktop application that creates those records. It monitors a folder
            you choose, fingerprints each file with a SHA-256 hash, and permanently registers
            that fingerprint on the Bitcoin SV blockchain. The proof is yours forever,
            independent of Nora or any third party.
          </Text>
        </Box>

        <Box>
          <Heading size="md" mb={4}>Features</Heading>
          <VStack align="stretch" spacing={2}>
            <HStack>
              <Icon as={FiClock} color="green.500" />
              <Text>Automatic folder watching with configurable recursion and file size limits</Text>
            </HStack>
            <HStack>
              <Icon as={FiShield} color="green.500" />
              <Text>Permanent, tamper-proof registration on the Bitcoin blockchain</Text>
            </HStack>
            <HStack>
              <Icon as={FiCheck} color="green.500" />
              <Text>Private by design — only a SHA-256 fingerprint leaves your computer</Text>
            </HStack>
            <HStack>
              <Icon as={FiSearch} color="green.500" />
              <Text>Per-file verification against the blockchain record</Text>
            </HStack>
            <HStack>
              <Icon as={FiDatabase} color="green.500" />
              <Text>Local database of registered files with search, pagination, and CSV export</Text>
            </HStack>
          </VStack>
        </Box>

        <Box>
          <Heading size="md" mb={4}>Resources</Heading>
          <VStack align="stretch" spacing={3}>
            <Link href="https://github.com/ekseesse/nora/releases" isExternal color="blue.500">
              <HStack>
                <Icon as={FiGithub} />
                <Text>GitHub Releases — Download Nora</Text>
              </HStack>
            </Link>
            <Link href="https://github.com/ekseesse/nora" isExternal color="blue.500">
              <HStack>
                <Icon as={FiExternalLink} />
                <Text>Source Code</Text>
              </HStack>
            </Link>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
};

export default AboutPanel;
