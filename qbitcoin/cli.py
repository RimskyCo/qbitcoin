#!/usr/bin/env python3
"""
QBitcoin Command Line Interface
Allows users to manage wallets, send transactions, and control mining.
"""

import os
import sys
import argparse
import json
import time
from typing import Optional, List, Dict, Any

from .blockchain import Blockchain, Transaction
from .wallet import Wallet, WalletManager
from .node import Node
from .miner import Miner

DATA_DIR = os.path.expanduser("~/.qbitcoin")


def setup_directories() -> None:
    """Create necessary directories."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "wallets"), exist_ok=True)


class QBitcoinCLI:
    """QBitcoin command-line interface."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.blockchain = self._load_or_create_blockchain()
        self.wallet_manager = WalletManager(os.path.join(DATA_DIR, "wallets"))
        self.node: Optional[Node] = None
        self.miner: Optional[Miner] = None
    
    def _load_or_create_blockchain(self) -> Blockchain:
        """Load blockchain from disk or create a new one."""
        blockchain_path = os.path.join(DATA_DIR, "blockchain.json")
        
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
        blockchain_path = os.path.join(DATA_DIR, "blockchain.json")
        blockchain_dict = self.blockchain.to_dict()
        
        with open(blockchain_path, 'w') as f:
            json.dump(blockchain_dict, f)
        
        print(f"Saved blockchain to {blockchain_path}")
    
    def create_wallet(self, name: str) -> None:
        """Create a new wallet."""
        wallet = self.wallet_manager.create_wallet(name)
        print(f"Created wallet '{name}' with address: {wallet.get_public_key()}")
    
    def list_wallets(self) -> None:
        """List all available wallets."""
        wallets = self.wallet_manager.list_wallets()
        
        if not wallets:
            print("No wallets found")
            return
        
        print("Available wallets:")
        for name in wallets:
            wallet = self.wallet_manager.get_wallet(name)
            if wallet:
                balance = self.blockchain.get_balance(wallet.get_public_key())
                print(f"  {name}: {balance} QBT (Address: {wallet.get_public_key()[:16]}...)")
    
    def get_balance(self, wallet_name: str) -> None:
        """Get the balance of a wallet."""
        wallet = self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            print(f"Wallet '{wallet_name}' not found")
            return
        
        balance = self.blockchain.get_balance(wallet.get_public_key())
        print(f"Balance of {wallet_name}: {balance} QBT")
    
    def send(self, from_wallet: str, to_address: str, amount: float, fee: float = 0.0001) -> None:
        """Send QBitcoins to an address."""
        # Get wallet
        wallet = self.wallet_manager.get_wallet(from_wallet)
        if not wallet:
            print(f"Wallet '{from_wallet}' not found")
            return
        
        try:
            # Create and sign transaction
            tx = wallet.create_transaction(self.blockchain, to_address, amount, fee)
            
            # Add to blockchain
            if self.blockchain.add_transaction(tx):
                print(f"Transaction {tx.txid} added to pending transactions")
                
                # If node running, broadcast transaction
                if self.node:
                    self.node.add_transaction(tx)
                
                # Save blockchain
                self._save_blockchain()
            else:
                print("Transaction failed")
        
        except ValueError as e:
            print(f"Error: {e}")
    
    def start_node(self, host: str = "0.0.0.0", port: int = 9333, 
                   seed_peer: Optional[str] = None) -> None:
        """Start a node."""
        if self.node and self.node.running:
            print("Node already running")
            return
        
        # Parse seed peers
        seed_peers = []
        if seed_peer:
            seed_host, seed_port = seed_peer.split(":")
            seed_peers.append({
                'host': seed_host,
                'port': int(seed_port)
            })
        
        # Create and start node
        self.node = Node(
            host=host,
            port=port,
            data_dir=DATA_DIR,
            seed_peers=seed_peers
        )
        
        # Share the blockchain with the node
        self.node.blockchain = self.blockchain
        
        # Start the node
        self.node.start()
        print(f"Node started on {host}:{port}")
    
    def stop_node(self) -> None:
        """Stop the node."""
        if not self.node or not self.node.running:
            print("Node not running")
            return
        
        self.node.stop()
        print("Node stopped")
        
        # Update blockchain
        self.blockchain = self.node.blockchain
        self._save_blockchain()
    
    def start_mining(self, wallet_name: str) -> None:
        """Start mining with the specified wallet."""
        if self.miner and self.miner.is_mining:
            print("Mining already in progress")
            return
        
        # Get wallet
        wallet = self.wallet_manager.get_wallet(wallet_name)
        if not wallet:
            print(f"Wallet '{wallet_name}' not found")
            return
        
        # Create and start miner
        self.miner = Miner(self.blockchain, wallet, data_dir=DATA_DIR)
        self.miner.start_mining()
        print(f"Mining started with rewards going to wallet '{wallet_name}'")
    
    def stop_mining(self) -> None:
        """Stop mining."""
        if not self.miner or not self.miner.is_mining:
            print("Mining not in progress")
            return
        
        self.miner.stop_mining()
        print("Mining stopped")
        
        # Save blockchain
        self._save_blockchain()
    
    def show_blockchain(self) -> None:
        """Show blockchain information."""
        print(f"Blockchain height: {len(self.blockchain.chain)}")
        print(f"Mining difficulty: {self.blockchain.difficulty}")
        
        latest_block = self.blockchain.get_latest_block()
        print(f"Latest block: {latest_block.index} (hash: {latest_block.hash[:16]}...)")
        print(f"Pending transactions: {len(self.blockchain.pending_transactions)}")
    
    def is_valid(self) -> None:
        """Check if the blockchain is valid."""
        if self.blockchain.is_chain_valid():
            print("Blockchain is valid")
        else:
            print("Blockchain is INVALID")


def main():
    """Main CLI entry point."""
    # Create directories
    setup_directories()
    
    # Create CLI
    cli = QBitcoinCLI()
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="QBitcoin CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create wallet
    create_wallet_parser = subparsers.add_parser("create-wallet", help="Create a new wallet")
    create_wallet_parser.add_argument("name", help="Wallet name")
    
    # List wallets
    subparsers.add_parser("list-wallets", help="List all wallets")
    
    # Get balance
    balance_parser = subparsers.add_parser("balance", help="Get wallet balance")
    balance_parser.add_argument("wallet", help="Wallet name")
    
    # Send
    send_parser = subparsers.add_parser("send", help="Send QBitcoins")
    send_parser.add_argument("from_wallet", help="Sending wallet name")
    send_parser.add_argument("to_address", help="Recipient address")
    send_parser.add_argument("amount", type=float, help="Amount to send")
    send_parser.add_argument("--fee", type=float, default=0.0001, help="Transaction fee")
    
    # Start node
    node_parser = subparsers.add_parser("start-node", help="Start a node")
    node_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    node_parser.add_argument("--port", type=int, default=9333, help="Port to bind to")
    node_parser.add_argument("--seed-peer", help="Additional seed peer (host:port) - default seed nodes are automatically included")
    
    # Stop node
    subparsers.add_parser("stop-node", help="Stop the node")
    
    # Start mining
    mine_parser = subparsers.add_parser("start-mining", help="Start mining")
    mine_parser.add_argument("wallet", help="Wallet to receive mining rewards")
    
    # Stop mining
    subparsers.add_parser("stop-mining", help="Stop mining")
    
    # Show blockchain
    subparsers.add_parser("info", help="Show blockchain information")
    
    # Validate blockchain
    subparsers.add_parser("validate", help="Validate the blockchain")
    
    args = parser.parse_args()
    
    # Run command
    if args.command == "create-wallet":
        cli.create_wallet(args.name)
    elif args.command == "list-wallets":
        cli.list_wallets()
    elif args.command == "balance":
        cli.get_balance(args.wallet)
    elif args.command == "send":
        cli.send(args.from_wallet, args.to_address, args.amount, args.fee)
    elif args.command == "start-node":
        cli.start_node(args.host, args.port, args.seed_peer)
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping node...")
            cli.stop_node()
    elif args.command == "stop-node":
        cli.stop_node()
    elif args.command == "start-mining":
        cli.start_mining(args.wallet)
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping mining...")
            cli.stop_mining()
    elif args.command == "stop-mining":
        cli.stop_mining()
    elif args.command == "info":
        cli.show_blockchain()
    elif args.command == "validate":
        cli.is_valid()
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 