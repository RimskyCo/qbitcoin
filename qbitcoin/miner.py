"""
QBitcoin miner implementation using Argon2 memory-hard proof of work.
"""

import time
import threading
import multiprocessing
import os
import json
from typing import Optional
from .blockchain import Blockchain, Block
from .wallet import Wallet
import socket  # Add this import if not already present

class Miner:
    """QBitcoin miner for creating new blocks."""
    
    def __init__(self, blockchain: Blockchain, wallet: Wallet, data_dir: str = "data", num_threads: int = None):
        """
        Initialize a miner.
        
        Args:
            blockchain: Blockchain to mine on
            wallet: Wallet to receive mining rewards
            data_dir: Directory to save blockchain data
            num_threads: Number of mining threads (auto-detected if None)
        """
        self.blockchain = blockchain
        self.wallet = wallet
        self.data_dir = data_dir
        
        # Determine optimal number of parallel mining threads if not specified
        if num_threads is None:
            self.num_threads = max(1, multiprocessing.cpu_count() - 1)
        else:
            self.num_threads = num_threads
        
        # Mining thread
        self.is_mining = False
        self.mining_thread = None
        
        # Node reference for broadcasting blocks (optional)
        self.node = None
        self.external_node_host = None
        self.external_node_port = None
    
    def set_node(self, node) -> None:
        """Set a reference to the node for broadcasting blocks."""
        self.node = node
        self.external_node_host = None
        self.external_node_port = None
        print("Miner connected to node for block propagation.")
    
    def set_external_node(self, host: str, port: int) -> None:
        """
        Set an external node for broadcasting blocks.
        Used when mining with a node started in a different process.
        
        Args:
            host: External node host
            port: External node port
        """
        self.node = None
        self.external_node_host = host
        self.external_node_port = port
        print(f"Miner connected to external node at {host}:{port} for block propagation.")
    
    def start_mining(self) -> None:
        """Start mining in a background thread."""
        if self.is_mining:
            print("Mining already in progress")
            return
        
        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously)
        self.mining_thread.daemon = True
        self.mining_thread.start()
        
        print(f"Started mining with {self.num_threads} threads...")
    
    def stop_mining(self) -> None:
        """Stop mining."""
        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=1.0)
            self.mining_thread = None
        print("Mining stopped")
        self._save_blockchain()
    
    def _save_blockchain(self) -> None:
        """Save blockchain to disk if data_dir is configured."""
        if not self.data_dir:
            return
            
        os.makedirs(self.data_dir, exist_ok=True)
        blockchain_path = os.path.join(self.data_dir, "blockchain.json")
        blockchain_dict = self.blockchain.to_dict()
        
        try:
            with open(blockchain_path, 'w') as f:
                json.dump(blockchain_dict, f)
            print(f"Saved blockchain to {blockchain_path}")
        except Exception as e:
            print(f"Error saving blockchain: {e}")
    
    def _mine_continuously(self) -> None:
        """Mine blocks continuously until stopped."""
        while self.is_mining:
            try:
                # Get miner's address from wallet
                miner_address = self.wallet.get_public_key()
                
                # Mine a block
                start_time = time.time()
                new_block = self.blockchain.mine_pending_transactions(miner_address)
                end_time = time.time()
                
                # Calculate hashrate (approximately)
                hashrate = 2**self.blockchain.difficulty / (end_time - start_time)
                
                print(f"Mined block {new_block.index} with {len(new_block.transactions)} transactions")
                print(f"Block hash: {new_block.hash}")
                print(f"Mining time: {end_time - start_time:.2f} seconds")
                print(f"Approximate hashrate: {hashrate:.2f} H/s")
                print(f"Current balance: {self.wallet.get_balance(self.blockchain)}")
                
                # Save blockchain after successful mining
                self._save_blockchain()
                
                # Broadcast the new block to the network if connected to a node
                if self.node and hasattr(self.node, '_broadcast_new_block'):
                    try:
                        self.node._broadcast_new_block(new_block)
                        print(f"Block {new_block.index} broadcast to the network via internal node ✅")
                    except Exception as e:
                        print(f"Failed to broadcast block to network via internal node: {e}")
                # If we have external node details, broadcast to it
                elif self.external_node_host and self.external_node_port:
                    try:
                        self._broadcast_to_external_node(new_block)
                        print(f"Block {new_block.index} broadcast to the network via external node ✅")
                    except Exception as e:
                        print(f"Failed to broadcast block to network via external node: {e}")
                
            except Exception as e:
                print(f"Mining error: {e}")
                time.sleep(5)  # Wait before retrying on error
                
    def _broadcast_to_external_node(self, block):
        """
        Broadcast a newly mined block to an external node.
        
        Args:
            block: The Block object to broadcast
        """
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((self.external_node_host, self.external_node_port))
            
            message = {
                'type': 'new_block',
                'block': block.to_dict()
            }
            
            client.sendall(json.dumps(message).encode('utf-8'))
            client.close()
            return True
        except Exception as e:
            print(f"Error broadcasting to external node: {e}")
            return False


def main():
    """Run the QBitcoin miner."""
    from .wallet import Wallet
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description="QBitcoin Miner")
    parser.add_argument("--wallet", default="miner", help="Wallet name to use for mining rewards")
    parser.add_argument("--data-dir", default="data", help="Data directory to save blockchain")
    args = parser.parse_args()
    
    # Ensure directories exist
    data_dir = args.data_dir
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "wallets"), exist_ok=True)
    
    # Load or create wallet
    wallet_path = os.path.join(data_dir, "wallets", f"{args.wallet}.json")
    wallet = Wallet(wallet_path)
    print(f"Mining rewards will go to: {wallet.get_public_key()}")
    
    # Load or create blockchain
    blockchain_path = os.path.join(data_dir, "blockchain.json")
    if os.path.exists(blockchain_path):
        try:
            with open(blockchain_path, 'r') as f:
                blockchain_dict = json.load(f)
            from .blockchain import Blockchain
            blockchain = Blockchain.from_dict(blockchain_dict)
            print(f"Loaded blockchain from {blockchain_path}")
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            blockchain = Blockchain()
    else:
        blockchain = Blockchain()
    
    # Create and start miner
    miner = Miner(blockchain, wallet, data_dir)
    try:
        miner.start_mining()
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping miner...")
        miner.stop_mining()


if __name__ == "__main__":
    main() 