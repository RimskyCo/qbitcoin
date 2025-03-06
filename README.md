# QBitcoin - Quantum-Safe Bitcoin Implementation

QBitcoin is a quantum-resistant implementation of a cryptocurrency inspired by Bitcoin. It incorporates several quantum-safe cryptographic primitives to ensure resilience against attacks from quantum computers.

## Key Features

- **Argon2 Proof-of-Work**: Uses the memory-hard Argon2 algorithm instead of SHA-256 to make mining quantum-resistant
- **SPHINCS+ Signatures**: Implements post-quantum SPHINCS+ signature scheme instead of ECDSA
- **SHA-3 Hashing**: Utilizes SHA-3 for various hashing operations within the blockchain

## Installation

### Using the Setup Script (Recommended)

The easiest way to get started is using the provided setup script:

```bash
# Make the script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

This will:
1. Create a virtual environment
2. Install all dependencies
3. Set up your environment for running QBitcoin
4. Create the wrapper script for easy operation

### Manual Installation

If you prefer to install manually:

```bash
# Create a virtual environment
python3 -m venv qbitcoin_env

# Activate the environment
source qbitcoin_env/bin/activate  # On Linux/macOS
# or
qbitcoin_env\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

QBitcoin provides a comprehensive command-line interface for all operations through the included wrapper script:

```bash
# Use the wrapper script for all commands
./run_qbitcoin.sh [command] [options]
```

This wrapper script automatically handles virtual environment activation, ensuring all dependencies are properly loaded.

### Wallet Operations

```bash
# Create a new wallet
./run_qbitcoin.sh create-wallet mywallet

# List all wallets
./run_qbitcoin.sh list-wallets

# Check wallet balance
./run_qbitcoin.sh balance mywallet
```

### Mining

```bash
# Start mining with rewards going to your wallet
./run_qbitcoin.sh start-mining mywallet

# Stop mining
./run_qbitcoin.sh stop-mining
```

### Node Operations

```bash
# Start a node on the default port (9333)
./run_qbitcoin.sh start-node

# Start a node with custom parameters
./run_qbitcoin.sh start-node --host 0.0.0.0 --port 9334

# Start a node with a seed peer
./run_qbitcoin.sh start-node --seed-peer 192.168.1.100:9333

# Stop a running node
./run_qbitcoin.sh stop-node
```

### Multi-Node Testing

You can run multiple nodes on the same machine for testing by using different ports:

```bash
# Terminal 1: Start the first node on the default port (9333)
./run_qbitcoin.sh start-node

# Terminal 2: Start the second node on a different port and connect to the first
./run_qbitcoin.sh start-node --port 9334 --seed-peer 127.0.0.1:9333
```

When starting a node with `--host 0.0.0.0`, it will listen on all available network interfaces, making it accessible from other machines on your network.

### Transactions

```bash
# Send QBitcoins
./run_qbitcoin.sh send mywallet RECIPIENT_ADDRESS 10.0

# Show blockchain information
./run_qbitcoin.sh info

# Validate the blockchain
./run_qbitcoin.sh validate
```

## Data Storage

QBitcoin stores data in the following locations:

- **Wallets**: `~/.qbitcoin/wallets/`
- **Blockchain**: `~/.qbitcoin/blockchain.json`
- **Peers**: `~/.qbitcoin/peers.json`

You should back up these files regularly to prevent data loss.

## Development

See the [SECURITY.md](./SECURITY.md) file for security considerations when developing with QBitcoin.

## Project Structure

- `qbitcoin/blockchain.py`: Core blockchain implementation
- `qbitcoin/crypto.py`: Cryptographic functions (SPHINCS+, Argon2, SHA-3)
- `qbitcoin/miner.py`: Mining implementation using Argon2 PoW
- `qbitcoin/node.py`: P2P network node implementation
- `qbitcoin/wallet.py`: Wallet implementation using SPHINCS+
- `qbitcoin/cli.py`: Command-line interface
- `run_qbitcoin.sh`: Wrapper script that manages the virtual environment

## Security Considerations

This implementation aims to be quantum-resistant by using:
1. Argon2 - A memory-hard algorithm that is resistant to ASICs and potentially quantum algorithms
2. SPHINCS+ - A stateless hash-based signature scheme that is believed to be quantum-resistant
3. SHA-3 - A modern hash function more resilient to theoretical quantum attacks than SHA-2

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## Disclaimer

This project is for educational purposes only and should not be used in production without thorough security audits. 