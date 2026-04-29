import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone
from src.blockchain.mock_chain import MockBlockchain

class TestBlockchain:
    @pytest.fixture
    def setup_blockchain(self):
        """Set up a temporary blockchain file."""
        temp_dir = Path(tempfile.mkdtemp())
        chain_file = temp_dir / "mock_chain.txt"
        blockchain = MockBlockchain(chain_file)
        
        yield {
            'temp_dir': temp_dir,
            'chain_file': chain_file,
            'blockchain': blockchain
        }
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
    
    def test_transaction_writing(self, setup_blockchain):
        """Test writing and verifying transactions."""
        env = setup_blockchain
        blockchain = env['blockchain']
        
        # Test writing a transaction
        test_hash = "test_hash_123"
        test_metadata = {
            'filename': 'test.txt',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        tx_id = blockchain.write_transaction(test_hash, test_metadata)
        assert tx_id is not None, "Failed to write transaction"
        assert tx_id.startswith("tx_"), "Invalid transaction ID format"
        
        # Verify transaction by ID
        transaction = blockchain.verify_transaction(tx_id)
        assert transaction is not None, "Failed to verify transaction"
        assert transaction['file_hash'] == test_hash, "Hash mismatch"
        assert transaction['metadata'] == test_metadata, "Metadata mismatch"
        assert 'timestamp' in transaction, "Missing timestamp"
        
        # Verify by file hash
        hash_transaction = blockchain.verify_file_hash(test_hash)
        assert hash_transaction is not None, "Failed to verify by hash"
        assert hash_transaction['tx_id'] == tx_id, "Transaction ID mismatch"
        
        # Verify file content
        with open(env['chain_file'], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 1, "Incorrect number of transactions"
            stored_tx = json.loads(lines[0])
            assert stored_tx['tx_id'] == tx_id, "Stored transaction ID mismatch"
    
    def test_multiple_transactions(self, setup_blockchain):
        """Test handling multiple transactions."""
        env = setup_blockchain
        blockchain = env['blockchain']
        
        # Write multiple transactions for the same file hash
        test_hash = "test_hash_456"
        transactions = []
        
        for i in range(3):
            metadata = {
                'filename': f'test_{i}.txt',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            tx_id = blockchain.write_transaction(test_hash, metadata)
            assert tx_id is not None, f"Failed to write transaction {i}"
            transactions.append(tx_id)
        
        # Verify all transactions exist
        for tx_id in transactions:
            transaction = blockchain.verify_transaction(tx_id)
            assert transaction is not None, f"Failed to verify transaction {tx_id}"
        
        # Verify latest transaction is returned for file hash
        latest = blockchain.verify_file_hash(test_hash)
        assert latest is not None, "Failed to get latest transaction"
        assert latest['tx_id'] == transactions[-1], "Did not get most recent transaction"
        
        # Verify file contains all transactions
        with open(env['chain_file'], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3, "Incorrect number of transactions"
    
    def test_error_handling(self, setup_blockchain):
        """Test error handling scenarios."""
        env = setup_blockchain
        blockchain = env['blockchain']
        
        # Test nonexistent transaction
        assert blockchain.verify_transaction("nonexistent_tx") is None, "Should return None for nonexistent transaction"
        
        # Test nonexistent hash
        assert blockchain.verify_file_hash("nonexistent_hash") is None, "Should return None for nonexistent hash"
        
        # Test with invalid metadata
        with pytest.raises(ValueError, match="Metadata must be a dictionary"):
            blockchain.write_transaction("test_hash", None)
        
        # Test with empty hash
        with pytest.raises(ValueError, match="File hash must be a non-empty string"):
            blockchain.write_transaction("", {'filename': 'test.txt'})
        
        # Test file corruption handling
        with open(env['chain_file'], 'a') as f:
            f.write("invalid json\n")
        
        test_hash = "test_hash_789"
        metadata = {'filename': 'test.txt'}
        tx_id = blockchain.write_transaction(test_hash, metadata)
        assert tx_id is not None, "Should handle corrupted file gracefully"
        
        # Verify transaction was written despite corruption
        transaction = blockchain.verify_transaction(tx_id)
        assert transaction is not None, "Failed to write transaction after corruption"