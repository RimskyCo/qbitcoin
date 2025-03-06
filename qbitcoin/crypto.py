"""
Quantum-safe cryptographic primitives for QBitcoin.
Implements SPHINCS+ signatures, Argon2 for PoW, and SHA-3 hashing.
"""

import os
import hashlib
import binascii
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from Crypto.Hash import SHA3_256
import pyspx.shake256_128f as sphincs  # Real SPHINCS+ implementation

# Parameters for Argon2 (tuned for mining)
# These parameters can be adjusted to change mining difficulty
ARGON2_TIME_COST = 2        # Number of iterations
ARGON2_MEMORY_COST = 102400  # Memory usage in KiB (100 MB)
ARGON2_PARALLELISM = 8      # Number of threads
ARGON2_HASH_LEN = 32        # Output hash length

# SPHINCS+ parameters
SPHINCS_PUBLIC_KEY_SIZE = sphincs.crypto_sign_PUBLICKEYBYTES
SPHINCS_SECRET_KEY_SIZE = sphincs.crypto_sign_SECRETKEYBYTES
SPHINCS_SIGNATURE_SIZE = sphincs.crypto_sign_BYTES


class QBitcoinCrypto:
    """Implements quantum-safe cryptographic operations for QBitcoin."""
    
    @staticmethod
    def generate_keypair():
        """Generate a new SPHINCS+ keypair."""
        # Generate a random seed for key generation
        seed = os.urandom(sphincs.crypto_sign_SEEDBYTES)
        public_key, secret_key = sphincs.generate_keypair(seed)
        return {
            'public_key': binascii.hexlify(public_key).decode(),
            'secret_key': binascii.hexlify(secret_key).decode()
        }
    
    @staticmethod
    def sign_message(message, secret_key):
        """Sign a message using SPHINCS+."""
        if isinstance(message, str):
            message = message.encode()
        secret_key_bytes = binascii.unhexlify(secret_key)
        signature = sphincs.sign(message, secret_key_bytes)
        return binascii.hexlify(signature).decode()
    
    @staticmethod
    def verify_signature(message, signature, public_key):
        """Verify a SPHINCS+ signature."""
        if isinstance(message, str):
            message = message.encode()
        try:
            signature_bytes = binascii.unhexlify(signature)
            public_key_bytes = binascii.unhexlify(public_key)
            return sphincs.verify(message, signature_bytes, public_key_bytes)
        except Exception as e:
            print(f"Verification error: {e}")
            return False
    
    @staticmethod
    def sha3_256(data):
        """Compute SHA3-256 hash of data."""
        if isinstance(data, str):
            data = data.encode()
        h = SHA3_256.new()
        h.update(data)
        return h.hexdigest()
    
    @staticmethod
    def argon2_pow(block_header, target_difficulty):
        """
        Proof of work using Argon2 memory-hard function.
        
        Args:
            block_header: Header data to hash
            target_difficulty: Target number of leading zeros
            
        Returns:
            (nonce, hash) tuple if successful
        """
        ph = PasswordHasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN
        )
        
        nonce = 0
        target_prefix = '0' * target_difficulty
        
        while True:
            data = f"{block_header}{nonce}"
            hash_output = ph.hash(data)
            
            # Extract the actual hash part (after the parameters)
            hash_value = hash_output.split('$')[-1]
            
            # Convert to hex for comparison with target
            hex_hash = binascii.hexlify(
                hashlib.sha3_256(hash_value.encode()).digest()
            ).decode()
            
            if hex_hash.startswith(target_prefix):
                return nonce, hex_hash
            
            nonce += 1
    
    @staticmethod
    def verify_argon2_pow(block_header, nonce, target_difficulty):
        """Verify an Argon2 proof of work."""
        ph = PasswordHasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN
        )
        
        data = f"{block_header}{nonce}"
        hash_output = ph.hash(data)
        
        # Extract the actual hash part
        hash_value = hash_output.split('$')[-1]
        
        # Convert to hex for comparison with target
        hex_hash = binascii.hexlify(
            hashlib.sha3_256(hash_value.encode()).digest()
        ).decode()
        
        target_prefix = '0' * target_difficulty
        return hex_hash.startswith(target_prefix) 