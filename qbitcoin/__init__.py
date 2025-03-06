"""
QBitcoin - Quantum-safe cryptocurrency implementation.

Uses Argon2 for proof-of-work mining, SPHINCS+ for post-quantum signatures,
and SHA-3 for various hashing operations.
"""

__version__ = "0.1.0"

from .blockchain import Blockchain, Block, Transaction
from .crypto import QBitcoinCrypto
from .wallet import Wallet, WalletManager
from .node import Node
from .miner import Miner 