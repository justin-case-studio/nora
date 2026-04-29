"""
Blockchain Service - Pure blockchain operations only.
According to the architecture, this service:
- Creates blockchain transactions
- Returns success/failure status
- Has NO database operations whatsoever
- Single responsibility: blockchain interaction
"""
from typing import Optional, Dict


class BlockchainService:
    """Pure blockchain operations service - no database operations."""

    def __init__(self):
        """Initialize the blockchain client."""
        # Import here to avoid circular import
        from . import get_blockchain_client

        # Always use the real client; trial mode is DB-only and skips blockchain calls
        self.client = get_blockchain_client()
        print(f"[BlockchainService] Initialized with client: {type(self.client).__name__}")

    def create_transaction(self, file_hash: str, blockchain_target: str = None) -> Optional[str]:
        """
        Create a blockchain transaction for a file hash.

        Args:
            file_hash: The SHA-256 hash to record on blockchain
            blockchain_target: Target blockchain ('local' or 'MintBlue').
                             If None, uses the current default client.

        Returns:
            Transaction ID if successful, None if failed
        """
        try:
            # Only on-chain calls should reach here; trial mode path skips this entirely
            client = self.client
            print(f"[BlockchainService] Creating transaction with {type(client).__name__} for hash: {file_hash[:8]}...")
            tx_id = client.create_transaction(file_hash)

            if tx_id:
                print(f"[BlockchainService] Transaction created successfully: {tx_id}")
                return tx_id
            else:
                print("[BlockchainService] Transaction creation failed")
                return None

        except Exception as e:
            print(f"[BlockchainService] Error creating transaction: {str(e)}")
            return None

    def verify_transaction(self, tx_id: str, expected_hash: str) -> Dict:
        """
        Verify a blockchain transaction contains the expected hash.

        Args:
            tx_id: Transaction ID to verify
            expected_hash: The hash we expect to find

        Returns:
            Dictionary with verification results
        """
        try:
            print(f"[BlockchainService] Verifying transaction {tx_id}")
            result = self.client.verify_transaction(tx_id, expected_hash)
            return result
        except Exception as e:
            print(f"[BlockchainService] Error verifying transaction: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "verified": False
            }

    def update_client(self, new_client):
        """Update the blockchain client instance."""
        old_client_type = type(self.client).__name__
        self.client = new_client
        print(f"[BlockchainService] Client updated from {old_client_type} to {type(new_client).__name__}")

    def test_connection(self) -> bool:
        """Test if the blockchain client can connect."""
        try:
            return self.client.test_connection()
        except Exception as e:
            print(f"[BlockchainService] Connection test failed: {str(e)}")
            return False
