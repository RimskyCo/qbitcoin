"""
Core blockchain implementation for QBitcoin.
Implements a quantum-resistant blockchain using Argon2, SPHINCS+, and SHA-3.
"""

import time
import json
from typing import List, Dict, Any, Optional
from .crypto import QBitcoinCrypto

# Blockchain configuration
DIFFICULTY = 3  # Initial mining difficulty (number of leading zeros)
BLOCK_REWARD = 50  # Initial block reward in QBitcoins
HALVING_INTERVAL = 210000  # Number of blocks between reward halvings
MAX_SUPPLY = 21000000  # Maximum supply of QBitcoins
DIFFICULTY_ADJUSTMENT_INTERVAL = 2016  # Blocks between difficulty adjustments
TARGET_BLOCK_TIME = 600  # Target time between blocks in seconds (10 minutes)

class Transaction:
    """Represents a QBitcoin transaction."""
    
    def __init__(self, sender: str, recipient: str, amount: float, 
                 fee: float, signature: Optional[str] = None):
        """
        Initialize a new transaction.
        
        Args:
            sender: Public key of sender (SPHINCS+ public key)
            recipient: Public key of recipient (SPHINCS+ public key)
            amount: Amount of QBitcoin to transfer
            fee: Transaction fee
            signature: Optional SPHINCS+ signature
        """
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.fee = fee
        self.timestamp = time.time()
        self.signature = signature
        self.txid = self._calculate_txid()
    
    def _calculate_txid(self) -> str:
        """Calculate the transaction ID using SHA-3."""
        tx_data = {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }
        tx_str = json.dumps(tx_data, sort_keys=True)
        return QBitcoinCrypto.sha3_256(tx_str)
    
    def sign(self, secret_key: str) -> None:
        """Sign the transaction using SPHINCS+."""
        # Only sign if not already signed
        if not self.signature:
            tx_data = json.dumps({
                'txid': self.txid,
                'sender': self.sender,
                'recipient': self.recipient,
                'amount': self.amount,
                'fee': self.fee,
                'timestamp': self.timestamp
            }, sort_keys=True)
            
            self.signature = QBitcoinCrypto.sign_message(tx_data, secret_key)
    
    def verify(self) -> bool:
        """Verify the transaction signature."""
        if not self.signature:
            return False
            
        tx_data = json.dumps({
            'txid': self.txid,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp
        }, sort_keys=True)
        
        return QBitcoinCrypto.verify_signature(tx_data, self.signature, self.sender)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'txid': self.txid,
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'fee': self.fee,
            'timestamp': self.timestamp,
            'signature': self.signature
        }
    
    @classmethod
    def from_dict(cls, tx_dict: Dict[str, Any]) -> 'Transaction':
        """Create a transaction from dictionary."""
        tx = cls(
            sender=tx_dict['sender'],
            recipient=tx_dict['recipient'],
            amount=tx_dict['amount'],
            fee=tx_dict['fee'],
            signature=tx_dict.get('signature')
        )
        tx.timestamp = tx_dict['timestamp']
        tx.txid = tx_dict['txid']
        return tx


class Block:
    """Represents a block in the QBitcoin blockchain."""
    
    def __init__(self, index: int, previous_hash: str, timestamp: float = None,
                 transactions: List[Transaction] = None, nonce: int = 0):
        """
        Initialize a new block.
        
        Args:
            index: Block height
            previous_hash: Hash of the previous block
            timestamp: Block creation time
            transactions: List of transactions in the block
            nonce: Nonce used for mining
        """
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.transactions = transactions or []
        self.nonce = nonce
        self.hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate block hash using SHA-3."""
        block_header = self._get_header_string()
        return QBitcoinCrypto.sha3_256(block_header)
    
    def _get_header_string(self) -> str:
        """Get the block header as a string for hashing."""
        tx_data = json.dumps([tx.to_dict() for tx in self.transactions], sort_keys=True)
        header_data = {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions_root': QBitcoinCrypto.sha3_256(tx_data),
            'nonce': self.nonce
        }
        return json.dumps(header_data, sort_keys=True)
    
    def mine_block(self, difficulty: int) -> bool:
        """
        Mine the block using Argon2 proof of work.
        
        Args:
            difficulty: Mining difficulty (number of leading zeros)
            
        Returns:
            True if mining successful
        """
        print(f"Mining block {self.index} with difficulty {difficulty}...")
        
        block_header = self._get_header_string()
        nonce, hash_value = QBitcoinCrypto.argon2_pow(block_header, difficulty)
        
        self.nonce = nonce
        self.hash = hash_value
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary."""
        return {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': [tx.to_dict() for tx in self.transactions],
            'nonce': self.nonce,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """Create a block from dictionary."""
        transactions = [Transaction.from_dict(tx) for tx in block_dict['transactions']]
        
        block = cls(
            index=block_dict['index'],
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict['timestamp'],
            transactions=transactions,
            nonce=block_dict['nonce']
        )
        block.hash = block_dict['hash']
        return block


class Blockchain:
    """QBitcoin blockchain implementation."""
    
    def __init__(self):
        """Initialize a new blockchain with genesis block."""
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.difficulty = DIFFICULTY
        self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """Create the genesis block."""
        # Create a coinbase transaction for the genesis block
        coinbase_tx = Transaction(
            sender="0" * 64,  # Genesis block has no sender
            recipient="QBitcoin Genesis Address",
            amount=BLOCK_REWARD,
            fee=0
        )
        
        # Create genesis block
        genesis_block = Block(
            index=0,
            previous_hash="0" * 64,
            transactions=[coinbase_tx]
        )
        
        # Add genesis block to chain
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> Block:
        """Get the latest block in the chain."""
        return self.chain[-1]
    
    def create_coinbase_transaction(self, miner_address: str) -> Transaction:
        """
        Create a coinbase transaction for block reward.
        
        Args:
            miner_address: Address of the miner
            
        Returns:
            Coinbase transaction
        """
        # Calculate current block reward
        block_height = len(self.chain)
        halvings = block_height // HALVING_INTERVAL
        reward = BLOCK_REWARD / (2 ** halvings)
        
        # Create coinbase transaction
        coinbase_tx = Transaction(
            sender="0" * 64,  # Coinbase has no sender
            recipient=miner_address,
            amount=reward,
            fee=0
        )
        
        return coinbase_tx
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Add a transaction to pending transactions.
        
        Args:
            transaction: Transaction to add
            
        Returns:
            True if transaction valid and added
        """
        # Verify transaction signature
        if not transaction.verify():
            print(f"Invalid signature for transaction {transaction.txid}")
            return False
        
        # Add to pending transactions
        self.pending_transactions.append(transaction)
        return True
    
    def mine_pending_transactions(self, miner_address: str) -> Block:
        """
        Mine a new block with pending transactions.
        
        Args:
            miner_address: Address to receive mining reward
            
        Returns:
            The mined block
        """
        # Sort pending transactions by fee (highest first)
        self.pending_transactions.sort(key=lambda tx: tx.fee, reverse=True)
        
        # Create a new block with coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(miner_address)
        
        # Add transactions to block (coinbase first)
        block_transactions = [coinbase_tx] + self.pending_transactions[:999]  # Limit transactions per block
        
        # Create the new block
        latest_block = self.get_latest_block()
        new_block = Block(
            index=latest_block.index + 1,
            previous_hash=latest_block.hash,
            transactions=block_transactions
        )
        
        # Mine the block
        start_time = time.time()
        new_block.mine_block(self.difficulty)
        end_time = time.time()
        
        print(f"Block {new_block.index} mined in {end_time - start_time:.2f} seconds")
        
        # Add block to chain
        self.chain.append(new_block)
        
        # Remove mined transactions from pending
        self.pending_transactions = self.pending_transactions[len(block_transactions)-1:]
        
        # Adjust difficulty if needed
        if new_block.index % DIFFICULTY_ADJUSTMENT_INTERVAL == 0:
            self._adjust_difficulty()
        
        return new_block
    
    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Check block hash
            if current_block.hash != current_block._calculate_hash():
                print(f"Invalid hash for block {current_block.index}")
                return False
            
            # Check block links
            if current_block.previous_hash != previous_block.hash:
                print(f"Invalid previous hash for block {current_block.index}")
                return False
            
            # Check transactions
            for tx in current_block.transactions[1:]:  # Skip coinbase
                if not tx.verify():
                    print(f"Invalid transaction {tx.txid} in block {current_block.index}")
                    return False
        
        return True
    
    def _adjust_difficulty(self) -> None:
        """Adjust mining difficulty to maintain target block time."""
        if len(self.chain) <= DIFFICULTY_ADJUSTMENT_INTERVAL:
            return
        
        # Get the first and last block in the adjustment period
        latest_block = self.get_latest_block()
        adjustment_block = self.chain[len(self.chain) - DIFFICULTY_ADJUSTMENT_INTERVAL]
        
        # Calculate time taken to mine the blocks
        time_taken = latest_block.timestamp - adjustment_block.timestamp
        expected_time = DIFFICULTY_ADJUSTMENT_INTERVAL * TARGET_BLOCK_TIME
        
        # Adjust difficulty
        if time_taken < expected_time / 2:
            self.difficulty += 1
        elif time_taken > expected_time * 2:
            self.difficulty = max(1, self.difficulty - 1)
        
        print(f"Difficulty adjusted to {self.difficulty}")
    
    def get_balance(self, address: str) -> float:
        """Get the balance of a given address."""
        balance = 0
        
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance += tx.amount
                if tx.sender == address:
                    balance -= (tx.amount + tx.fee)
        
        return balance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert blockchain to dictionary."""
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': [tx.to_dict() for tx in self.pending_transactions],
            'difficulty': self.difficulty
        }
    
    @classmethod
    def from_dict(cls, blockchain_dict: Dict[str, Any]) -> 'Blockchain':
        """Create a blockchain from dictionary."""
        blockchain = cls()
        blockchain.chain = [Block.from_dict(block_dict) for block_dict in blockchain_dict['chain']]
        blockchain.pending_transactions = [Transaction.from_dict(tx_dict) 
                                         for tx_dict in blockchain_dict['pending_transactions']]
        blockchain.difficulty = blockchain_dict['difficulty']
        return blockchain 