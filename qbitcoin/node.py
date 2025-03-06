"""
QBitcoin P2P network node implementation.
Handles peer discovery, blockchain synchronization, and transaction propagation.
"""

import socket
import threading
import json
import time
import random
import os
from typing import Dict, List, Any, Set, Optional
from .blockchain import Blockchain, Block, Transaction
from .wallet import Wallet, WalletManager

# Network configuration
DEFAULT_PORT = 9333
MAX_PEERS = 8
PING_INTERVAL = 30  # Seconds between peer pings
SYNC_INTERVAL = 60  # Seconds between blockchain syncs

# Default seed nodes - production servers that are always online
DEFAULT_SEED_PEERS = [
    {"host": "195.201.33.112", "port": 9333}  # Main QBitcoin seed node
]

class Message:
    """Message types for P2P communication."""
    PING = "ping"
    PONG = "pong"
    GET_PEERS = "get_peers"
    PEERS = "peers"
    GET_BLOCKS = "get_blocks"
    BLOCKS = "blocks"
    NEW_BLOCK = "new_block"
    NEW_TRANSACTION = "new_transaction"


class Peer:
    """Represents a remote peer in the network."""
    
    def __init__(self, host: str, port: int):
        """
        Initialize a peer.
        
        Args:
            host: Peer hostname or IP
            port: Peer port
        """
        self.host = host
        self.port = port
        self.last_seen = 0
    
    def __eq__(self, other):
        if not isinstance(other, Peer):
            return False
        return self.host == other.host and self.port == other.port
    
    def __hash__(self):
        return hash((self.host, self.port))
    
    def __str__(self):
        return f"{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert peer to dictionary."""
        return {
            'host': self.host,
            'port': self.port
        }
    
    @classmethod
    def from_dict(cls, peer_dict: Dict[str, Any]) -> 'Peer':
        """Create peer from dictionary."""
        return cls(
            host=peer_dict['host'],
            port=peer_dict['port']
        )


class Node:
    """QBitcoin P2P network node."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT, 
                 data_dir: str = "data", seed_peers: List[Dict[str, Any]] = None):
        """
        Initialize a QBitcoin node.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            data_dir: Directory for blockchain and wallet data
            seed_peers: List of seed peers to connect to
        """
        self.host = host
        self.port = port
        self.data_dir = data_dir
        self.peers: Set[Peer] = set()
        self.blockchain = self._load_or_create_blockchain()
        self.wallet_manager = WalletManager(os.path.join(data_dir, "wallets"))
        
        # Create directories
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, "wallets"), exist_ok=True)
        
        # Load existing peers from disk first
        self._load_peers()
        
        # Add seed peers from parameter or defaults
        seed_peers_to_add = seed_peers if seed_peers else DEFAULT_SEED_PEERS
        if seed_peers_to_add:
            for peer_dict in seed_peers_to_add:
                # Skip adding ourselves as a peer
                if peer_dict['host'] == self.host and int(peer_dict['port']) == self.port:
                    continue
                self.peers.add(Peer(peer_dict['host'], int(peer_dict['port'])))
        
        # Setup server socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Flags
        self.running = False
        self.syncing = False
        
        # Background threads
        self.server_thread: Optional[threading.Thread] = None
        self.peer_manager_thread: Optional[threading.Thread] = None
    
    def _load_or_create_blockchain(self) -> Blockchain:
        """Load blockchain from disk or create a new one."""
        blockchain_path = os.path.join(self.data_dir, "blockchain.json")
        
        if os.path.exists(blockchain_path):
            try:
                with open(blockchain_path, 'r') as f:
                    blockchain_dict = json.load(f)
                print(f"Loaded blockchain from {blockchain_path}")
                return Blockchain.from_dict(blockchain_dict)
            except Exception as e:
                print(f"Error loading blockchain: {e}")
        
        # Create new blockchain
        print("Creating new blockchain")
        return Blockchain()
    
    def _save_blockchain(self) -> None:
        """Save blockchain to disk."""
        blockchain_path = os.path.join(self.data_dir, "blockchain.json")
        blockchain_dict = self.blockchain.to_dict()
        
        with open(blockchain_path, 'w') as f:
            json.dump(blockchain_dict, f)
        
        print(f"Saved blockchain to {blockchain_path}")
    
    def _save_peers(self) -> None:
        """Save peers to disk."""
        peers_path = os.path.join(self.data_dir, "peers.json")
        peers_list = [peer.to_dict() for peer in self.peers]
        
        with open(peers_path, 'w') as f:
            json.dump(peers_list, f)
        
        print(f"Saved {len(self.peers)} peers to {peers_path}")
    
    def _load_peers(self) -> None:
        """Load peers from disk."""
        peers_path = os.path.join(self.data_dir, "peers.json")
        
        if os.path.exists(peers_path):
            try:
                with open(peers_path, 'r') as f:
                    peers_list = json.load(f)
                
                for peer_dict in peers_list:
                    self.peers.add(Peer.from_dict(peer_dict))
                
                print(f"Loaded {len(self.peers)} peers from {peers_path}")
            except Exception as e:
                print(f"Error loading peers: {e}")
    
    def start(self) -> None:
        """Start the node server and background tasks."""
        if self.running:
            print("Node already running")
            return
        
        self.running = True
        
        # Bind socket
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"Node listening on {self.host}:{self.port}")
        except Exception as e:
            print(f"Error binding socket: {e}")
            self.running = False
            return
        
        # Load peers from disk
        self._load_peers()
        
        # Start threads
        self.server_thread = threading.Thread(target=self._server_loop)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        self.peer_manager_thread = threading.Thread(target=self._peer_manager_loop)
        self.peer_manager_thread.daemon = True
        self.peer_manager_thread.start()
        
        # Initial blockchain sync
        self._sync_blockchain()
    
    def stop(self) -> None:
        """Stop the node server and background tasks."""
        if not self.running:
            return
        
        self.running = False
        
        # Save data
        self._save_blockchain()
        self._save_peers()
        
        # Close socket
        try:
            self.socket.close()
        except:
            pass
        
        # Wait for threads to stop
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
        
        if self.peer_manager_thread:
            self.peer_manager_thread.join(timeout=1.0)
        
        print("Node stopped")
    
    def _server_loop(self) -> None:
        """Main server loop to accept incoming connections."""
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:
                    print(f"Server error: {e}")
                    time.sleep(1)
    
    def _handle_client(self, client_socket: socket.socket, addr: tuple) -> None:
        """Handle an incoming client connection."""
        print(f"New connection from {addr[0]}:{addr[1]}")
        
        try:
            # Receive message
            data = client_socket.recv(1024 * 1024)  # 1MB max
            if not data:
                return
            
            # Parse message
            message = json.loads(data.decode('utf-8'))
            
            # Handle message
            if message['type'] == Message.PING:
                self._handle_ping(client_socket, message)
            elif message['type'] == Message.GET_PEERS:
                self._handle_get_peers(client_socket, message)
            elif message['type'] == Message.GET_BLOCKS:
                self._handle_get_blocks(client_socket, message)
            elif message['type'] == Message.NEW_BLOCK:
                self._handle_new_block(client_socket, message)
            elif message['type'] == Message.NEW_TRANSACTION:
                self._handle_new_transaction(client_socket, message)
        
        except Exception as e:
            print(f"Error handling client: {e}")
        
        finally:
            client_socket.close()
    
    def _handle_ping(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """Handle a ping message."""
        response = {
            'type': Message.PONG,
            'timestamp': time.time()
        }
        client_socket.sendall(json.dumps(response).encode('utf-8'))
        
        # Add peer
        peer = Peer(message['host'], message['port'])
        if peer not in self.peers and len(self.peers) < MAX_PEERS:
            self.peers.add(peer)
            print(f"Added new peer: {peer}")
    
    def _handle_get_peers(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """Handle a get_peers message."""
        peers_list = [peer.to_dict() for peer in self.peers]
        response = {
            'type': Message.PEERS,
            'peers': peers_list
        }
        client_socket.sendall(json.dumps(response).encode('utf-8'))
    
    def _handle_get_blocks(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """Handle a get_blocks message."""
        # Get requested blocks
        start_index = message.get('start_index', 0)
        end_index = message.get('end_index', len(self.blockchain.chain) - 1)
        
        # Limit block range
        end_index = min(end_index, len(self.blockchain.chain) - 1)
        if start_index > end_index:
            start_index = end_index
        
        # Get blocks
        blocks = []
        for i in range(start_index, end_index + 1):
            blocks.append(self.blockchain.chain[i].to_dict())
        
        # Send response
        response = {
            'type': Message.BLOCKS,
            'blocks': blocks
        }
        client_socket.sendall(json.dumps(response).encode('utf-8'))
    
    def _handle_new_block(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """Handle a new_block message."""
        block_dict = message['block']
        
        # Convert to Block object
        block = Block.from_dict(block_dict)
        
        # Validate block (simplified)
        if block.index != len(self.blockchain.chain):
            return  # Ignore block with wrong index
        
        if block.previous_hash != self.blockchain.get_latest_block().hash:
            return  # Ignore block with wrong previous hash
        
        # Add block to blockchain
        self.blockchain.chain.append(block)
        print(f"Added new block {block.index} from peer")
        
        # Save blockchain
        self._save_blockchain()
        
        # Propagate to peers
        self._broadcast_new_block(block)
    
    def _handle_new_transaction(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """Handle a new_transaction message."""
        tx_dict = message['transaction']
        
        # Convert to Transaction object
        tx = Transaction.from_dict(tx_dict)
        
        # Validate and add transaction
        if self.blockchain.add_transaction(tx):
            print(f"Added new transaction {tx.txid} from peer")
            
            # Propagate to peers
            self._broadcast_new_transaction(tx)
    
    def _peer_manager_loop(self) -> None:
        """Background loop for peer management."""
        last_ping_time = 0
        last_sync_time = 0
        
        while self.running:
            current_time = time.time()
            
            # Ping peers periodically
            if current_time - last_ping_time > PING_INTERVAL:
                self._ping_peers()
                last_ping_time = current_time
            
            # Sync blockchain periodically
            if current_time - last_sync_time > SYNC_INTERVAL:
                self._sync_blockchain()
                last_sync_time = current_time
            
            # Sleep
            time.sleep(1)
    
    def _ping_peers(self) -> None:
        """Ping all peers to check if they're alive."""
        dead_peers = set()
        
        for peer in self.peers:
            if not self._send_ping(peer):
                print(f"Peer {peer} is dead")
                dead_peers.add(peer)
        
        # Remove dead peers
        self.peers -= dead_peers
        
        # Request new peers if needed
        if len(self.peers) < MAX_PEERS / 2:
            self._discover_peers()
    
    def _send_ping(self, peer: Peer) -> bool:
        """Send ping message to peer."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((peer.host, peer.port))
            
            message = {
                'type': Message.PING,
                'host': self.host,
                'port': self.port,
                'timestamp': time.time()
            }
            
            client.sendall(json.dumps(message).encode('utf-8'))
            
            response = client.recv(1024)
            if not response:
                return False
            
            response_data = json.loads(response.decode('utf-8'))
            if response_data['type'] == Message.PONG:
                peer.last_seen = time.time()
                return True
            
            return False
        
        except Exception:
            return False
        
        finally:
            client.close()
    
    def _discover_peers(self) -> None:
        """Discover new peers by querying existing peers."""
        if not self.peers:
            return
        
        # Select a random peer
        peer = random.choice(list(self.peers))
        
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((peer.host, peer.port))
            
            message = {
                'type': Message.GET_PEERS
            }
            
            client.sendall(json.dumps(message).encode('utf-8'))
            
            response = client.recv(1024 * 10)  # 10KB max
            if not response:
                return
            
            response_data = json.loads(response.decode('utf-8'))
            if response_data['type'] == Message.PEERS:
                for peer_dict in response_data['peers']:
                    new_peer = Peer(peer_dict['host'], peer_dict['port'])
                    if new_peer not in self.peers and len(self.peers) < MAX_PEERS:
                        self.peers.add(new_peer)
                        print(f"Discovered new peer: {new_peer}")
        
        except Exception as e:
            print(f"Error discovering peers: {e}")
        
        finally:
            client.close()
    
    def _sync_blockchain(self) -> None:
        """Synchronize blockchain with peers."""
        if not self.peers or self.syncing:
            return
        
        self.syncing = True
        
        try:
            # Find the peer with the longest chain
            best_peer = None
            max_height = len(self.blockchain.chain) - 1
            
            for peer in self.peers:
                height = self._get_peer_blockchain_height(peer)
                if height > max_height:
                    max_height = height
                    best_peer = peer
            
            # If we found a better chain, sync with it
            if best_peer and max_height > len(self.blockchain.chain) - 1:
                print(f"Found peer with longer blockchain: {best_peer} (height: {max_height})")
                self._download_blocks(best_peer, len(self.blockchain.chain) - 1, max_height)
        
        except Exception as e:
            print(f"Error syncing blockchain: {e}")
        
        finally:
            self.syncing = False
    
    def _get_peer_blockchain_height(self, peer: Peer) -> int:
        """Get the blockchain height of a peer."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)
            client.connect((peer.host, peer.port))
            
            # Request only the latest block
            message = {
                'type': Message.GET_BLOCKS,
                'start_index': -1,
                'end_index': -1
            }
            
            client.sendall(json.dumps(message).encode('utf-8'))
            
            response = client.recv(1024 * 10)  # 10KB max
            if not response:
                return 0
            
            response_data = json.loads(response.decode('utf-8'))
            if response_data['type'] == Message.BLOCKS and response_data['blocks']:
                latest_block = response_data['blocks'][0]
                return latest_block['index']
            
            return 0
        
        except Exception:
            return 0
        
        finally:
            client.close()
    
    def _download_blocks(self, peer: Peer, start_index: int, end_index: int) -> bool:
        """Download blocks from a peer."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(30)  # Longer timeout for block download
            client.connect((peer.host, peer.port))
            
            message = {
                'type': Message.GET_BLOCKS,
                'start_index': start_index,
                'end_index': end_index
            }
            
            client.sendall(json.dumps(message).encode('utf-8'))
            
            # Receive blocks (large response)
            chunks = []
            while True:
                chunk = client.recv(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                chunks.append(chunk)
            
            data = b''.join(chunks)
            if not data:
                return False
            
            response_data = json.loads(data.decode('utf-8'))
            if response_data['type'] == Message.BLOCKS and response_data['blocks']:
                # Process blocks
                for block_dict in response_data['blocks']:
                    block = Block.from_dict(block_dict)
                    
                    # Simple validation
                    if block.index == len(self.blockchain.chain):
                        self.blockchain.chain.append(block)
                        print(f"Added block {block.index} from peer")
                
                # Save blockchain
                self._save_blockchain()
                return True
            
            return False
        
        except Exception as e:
            print(f"Error downloading blocks: {e}")
            return False
        
        finally:
            client.close()
    
    def _broadcast_new_block(self, block: Block) -> None:
        """Broadcast a new block to all peers."""
        message = {
            'type': Message.NEW_BLOCK,
            'block': block.to_dict()
        }
        
        for peer in self.peers:
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.settimeout(5)
                client.connect((peer.host, peer.port))
                client.sendall(json.dumps(message).encode('utf-8'))
                client.close()
            except Exception:
                pass
    
    def _broadcast_new_transaction(self, transaction: Transaction) -> None:
        """Broadcast a new transaction to all peers."""
        message = {
            'type': Message.NEW_TRANSACTION,
            'transaction': transaction.to_dict()
        }
        
        for peer in self.peers:
            try:
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.settimeout(5)
                client.connect((peer.host, peer.port))
                client.sendall(json.dumps(message).encode('utf-8'))
                client.close()
            except Exception:
                pass
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction to the blockchain and broadcast to peers.
        
        Args:
            transaction: Transaction to add
            
        Returns:
            True if transaction added successfully
        """
        # Add to blockchain
        if not self.blockchain.add_transaction(transaction):
            return False
        
        # Broadcast to peers
        self._broadcast_new_transaction(transaction)
        return True


def main():
    """Run a QBitcoin node."""
    import argparse
    
    parser = argparse.ArgumentParser(description="QBitcoin Node")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--seed-peer", action="append", help="Seed peer (host:port)")
    args = parser.parse_args()
    
    # Parse seed peers
    seed_peers = []
    if args.seed_peer:
        for peer_str in args.seed_peer:
            host, port = peer_str.split(":")
            seed_peers.append({
                'host': host,
                'port': int(port)
            })
    
    # Create and start node
    node = Node(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir,
        seed_peers=seed_peers
    )
    
    try:
        node.start()
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping node...")
        node.stop()


if __name__ == "__main__":
    main() 