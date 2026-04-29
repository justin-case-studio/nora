import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

class MockBlockchain:
    def __init__(self, chain_file: Path):
        """Initialize mock blockchain with a file to store transactions."""
        self.chain_file = Path(chain_file)
        self.chain_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file if it doesn't exist
        if not self.chain_file.exists():
            self.chain_file.write_text("")

    def write_transaction(self, file_hash: str, metadata: Dict) -> Optional[str]:
        """
        Write a transaction to the mock blockchain.
        Returns transaction ID if successful, None if failed.

        Raises:
            ValueError: If metadata is not a dictionary or file_hash is invalid
        """
        # Validate inputs first, outside try block
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        if not file_hash or not isinstance(file_hash, str):
            raise ValueError("File hash must be a non-empty string")

        try:
            transaction = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'file_hash': file_hash,
                'metadata': metadata,
                'tx_id': self._generate_tx_id()
            }

            # Append transaction to file (atomic write)
            with open(self.chain_file, 'a') as f:
                json.dump(transaction, f)
                f.write('\n')

            return transaction['tx_id']
        except Exception as e:
            print(f"Error writing transaction: {e}")
            return None

    def verify_transaction(self, tx_id: str) -> Optional[Dict]:
        """
        Verify a transaction exists in the mock blockchain.
        Returns transaction data if found, None if not found.
        """
        try:
            with open(self.chain_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            transaction = json.loads(line)
                            if transaction['tx_id'] == tx_id:
                                return transaction
                        except json.JSONDecodeError:
                            # Skip corrupted lines
                            continue
            return None
        except Exception as e:
            print(f"Error verifying transaction: {e}")
            return None

    def verify_file_hash(self, file_hash: str) -> Optional[Dict]:
        """
        Verify a file hash exists in the mock blockchain.
        Returns the most recent transaction for this hash if found.
        """
        try:
            latest_transaction = None
            with open(self.chain_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            transaction = json.loads(line)
                            if transaction['file_hash'] == file_hash:
                                latest_transaction = transaction
                        except json.JSONDecodeError:
                            # Skip corrupted lines
                            continue
            return latest_transaction
        except Exception as e:
            print(f"Error verifying file hash: {e}")
            return None

    def _generate_tx_id(self) -> str:
        """Generate a mock transaction ID."""
        import uuid
        return f"tx_{uuid.uuid4().hex[:8]}"
