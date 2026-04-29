from pathlib import Path
import tempfile
import json
from datetime import datetime, timezone
from src.blockchain.mock_chain import MockBlockchain

def main():
    # Set up a temporary blockchain file
    temp_dir = Path(tempfile.mkdtemp())
    chain_file = temp_dir / "test_chain.txt"
    blockchain = MockBlockchain(chain_file)
    
    # Test filenames with various quote patterns
    test_files = [
        'simple"quote".txt',
        '"start_quote.txt',
        'end_quote".txt',
        'multiple""quotes""here.txt',
        'mixed"quo\'tes".txt',
        '"completely"quoted"',
    ]
    
    print("\nTesting filenames with quotes:")
    print("-" * 50)
    
    transactions = []
    # Write transactions
    for filename in test_files:
        print(f"\nProcessing: {filename}")
        metadata = {
            'filename': filename,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        tx_id = blockchain.write_transaction(f"hash_for_{filename}", metadata)
        print(f"Transaction ID: {tx_id}")
        transactions.append((tx_id, filename))
    
    print("\nVerifying stored data:")
    print("-" * 50)
    
    # Read and verify the raw JSON
    print("\nRaw stored data:")
    with open(chain_file, 'r') as f:
        for line in f:
            parsed = json.loads(line)
            stored_filename = parsed['metadata']['filename']
            print(f"\nStored JSON: {line.strip()}")
            print(f"Parsed filename: {stored_filename}")
            
    # Verify each transaction
    print("\nVerifying transactions:")
    print("-" * 50)
    
    for tx_id, original_filename in transactions:
        transaction = blockchain.verify_transaction(tx_id)
        stored_filename = transaction['metadata']['filename']
        print(f"\nOriginal : {original_filename}")
        print(f"Retrieved: {stored_filename}")
        print(f"Match    : {original_filename == stored_filename}")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main() 