"""
SPHINCS+ wallet implementation for QBitcoin.
Provides key generation, transaction signing, and balance checking.
"""

import os
import json
from typing import Dict, Any, List, Optional
from .crypto import QBitcoinCrypto

class Wallet:
    """QBitcoin wallet implementation using SPHINCS+ signatures."""
    
    def __init__(self, keyfile_path: Optional[str] = None):
        """
        Initialize a new wallet or load from file.
        
        Args:
            keyfile_path: Path to key file (or None to generate new keys)
        """
        self.keyfile_path = keyfile_path
        self.keys = self._load_or_generate_keys()
    
    def _load_or_generate_keys(self) -> Dict[str, str]:
        """Load keys from file or generate new ones."""
        if self.keyfile_path and os.path.exists(self.keyfile_path):
            # Load keys from file
            try:
                with open(self.keyfile_path, 'r') as f:
                    keys = json.load(f)
                print(f"Loaded wallet from {self.keyfile_path}")
                return keys
            except Exception as e:
                print(f"Error loading wallet: {e}")
        
        # Generate new keys
        keys = QBitcoinCrypto.generate_keypair()
        print("Generated new SPHINCS+ keypair")
        
        # Save to file if path provided
        if self.keyfile_path:
            self._save_keys(keys)
        
        return keys
    
    def _save_keys(self, keys: Dict[str, str]) -> None:
        """Save keys to file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(self.keyfile_path)), exist_ok=True)
        
        with open(self.keyfile_path, 'w') as f:
            json.dump(keys, f)
        
        print(f"Saved wallet to {self.keyfile_path}")
    
    def get_public_key(self) -> str:
        """Get the wallet's public key (address)."""
        return self.keys['public_key']
    
    def sign_transaction(self, transaction) -> None:
        """
        Sign a transaction with the wallet's private key.
        
        Args:
            transaction: Transaction to sign
        """
        # Ensure the sender is this wallet's address
        if transaction.sender != self.get_public_key():
            raise ValueError("Transaction sender doesn't match wallet public key")
        
        # Sign the transaction
        transaction.sign(self.keys['secret_key'])
    
    def create_transaction(self, blockchain, recipient: str, amount: float, fee: float = 0.0001):
        """
        Create and sign a new transaction.
        
        Args:
            blockchain: Blockchain instance to check balance
            recipient: Recipient's public key
            amount: Amount to send
            fee: Transaction fee
            
        Returns:
            Signed Transaction object
        """
        from .blockchain import Transaction
        
        # Check balance
        balance = blockchain.get_balance(self.get_public_key())
        if balance < amount + fee:
            raise ValueError(f"Insufficient balance: {balance} < {amount + fee}")
        
        # Create transaction
        transaction = Transaction(
            sender=self.get_public_key(),
            recipient=recipient,
            amount=amount,
            fee=fee
        )
        
        # Sign transaction
        self.sign_transaction(transaction)
        
        return transaction
    
    def get_balance(self, blockchain) -> float:
        """
        Get the wallet's balance.
        
        Args:
            blockchain: Blockchain instance to check balance
            
        Returns:
            Current balance
        """
        return blockchain.get_balance(self.get_public_key())


class WalletManager:
    """Manages multiple QBitcoin wallets."""
    
    def __init__(self, wallet_dir: str = "wallets"):
        """
        Initialize wallet manager.
        
        Args:
            wallet_dir: Directory to store wallet files
        """
        self.wallet_dir = wallet_dir
        os.makedirs(wallet_dir, exist_ok=True)
        self.wallets: Dict[str, Wallet] = {}
        self.default_wallet_name: Optional[str] = None
    
    def create_wallet(self, name: str) -> Wallet:
        """
        Create a new wallet.
        
        Args:
            name: Wallet name
            
        Returns:
            New Wallet instance
        """
        keyfile_path = os.path.join(self.wallet_dir, f"{name}.json")
        wallet = Wallet(keyfile_path)
        self.wallets[name] = wallet
        
        # Set as default if first wallet
        if self.default_wallet_name is None:
            self.default_wallet_name = name
        
        return wallet
    
    def load_wallet(self, name: str) -> Optional[Wallet]:
        """
        Load a wallet by name.
        
        Args:
            name: Wallet name
            
        Returns:
            Wallet instance or None if not found
        """
        keyfile_path = os.path.join(self.wallet_dir, f"{name}.json")
        
        if not os.path.exists(keyfile_path):
            print(f"Wallet {name} not found")
            return None
        
        wallet = Wallet(keyfile_path)
        self.wallets[name] = wallet
        
        # Set as default if no default wallet
        if self.default_wallet_name is None:
            self.default_wallet_name = name
        
        return wallet
    
    def get_wallet(self, name: Optional[str] = None) -> Optional[Wallet]:
        """
        Get a wallet by name or the default wallet.
        
        Args:
            name: Wallet name or None for default
            
        Returns:
            Wallet instance or None if not found
        """
        if name is None:
            name = self.default_wallet_name
        
        if name is None:
            print("No default wallet set")
            return None
        
        if name not in self.wallets:
            return self.load_wallet(name)
        
        return self.wallets[name]
    
    def set_default_wallet(self, name: str) -> bool:
        """
        Set the default wallet.
        
        Args:
            name: Wallet name
            
        Returns:
            True if successful
        """
        if name not in self.wallets and not self.load_wallet(name):
            return False
        
        self.default_wallet_name = name
        return True
    
    def list_wallets(self) -> List[str]:
        """
        List all available wallets.
        
        Returns:
            List of wallet names
        """
        wallets = []
        
        for filename in os.listdir(self.wallet_dir):
            if filename.endswith('.json'):
                wallets.append(filename[:-5])  # Remove .json extension
        
        return wallets 