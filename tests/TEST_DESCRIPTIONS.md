# Test Descriptions

## File Processor Test
Tests the basic file processing functionality:
- Single file processing
- Hash calculation
- Metadata extraction
- Database storage
- Datetime handling

## Bulk Processing Test
Tests processing multiple files at once:
- Multiple file creation
- Batch processing
- Database verification
- Hash consistency
- Metadata consistency

## Directory Watching Test
Tests real-time file monitoring:
- Directory watching setup
- New file detection
- File modification detection
- Hash recalculation
- Size change detection
- Cleanup of watchers

## Config Management Test
Tests configuration handling:
- Config file watching
- Directory management (add/validate)
- Config validation
  - Valid config acceptance
  - Invalid config rejection
- Real-time config updates
- Theme/settings changes

## Database Operations Test
Tests database CRUD operations:
- Single file insertion
- Bulk file insertion
- File retrieval by path
- Pending files listing
- Status updates
- Transaction ID updates
- Timestamp handling
- Record count verification 

## Mock Blockchain Test
Tests the mock blockchain functionality:
- Transaction writing and verification
  - Single transaction handling
  - Transaction ID generation
  - Hash verification
- Multiple transaction handling
  - Sequential transactions
  - Same hash tracking
  - Latest transaction retrieval
- Error handling
  - Invalid transaction IDs
  - File handling
  - Malformed data 