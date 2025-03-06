#!/bin/bash
# QBitcoin setup script

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Detect OS type
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="linux"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS_TYPE="windows"
else
    OS_TYPE="unknown"
fi

# Check for OpenSSL development headers
check_openssl() {
    echo "Checking for OpenSSL development headers..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        if brew list openssl &>/dev/null || brew list openssl@1.1 &>/dev/null; then
            echo -e "${GREEN}OpenSSL development headers found.${NC}"
            
            # Set environment variables for OpenSSL on macOS
            if [[ "$(uname -m)" == "arm64" ]]; then
                # M1/M2 Mac
                export LDFLAGS="-L/opt/homebrew/opt/openssl/lib"
                export CPPFLAGS="-I/opt/homebrew/opt/openssl/include"
                echo "Set OpenSSL paths for Apple Silicon Mac."
            else
                # Intel Mac
                export LDFLAGS="-L/usr/local/opt/openssl/lib"
                export CPPFLAGS="-I/usr/local/opt/openssl/include"
                echo "Set OpenSSL paths for Intel Mac."
            fi
            return 0
        else
            echo -e "${YELLOW}OpenSSL development headers not found.${NC}"
            echo -e "Please install OpenSSL with: ${GREEN}brew install openssl${NC}"
            return 1
        fi
    elif [[ "$OS_TYPE" == "linux" ]]; then
        if ldconfig -p | grep -q libssl; then
            echo -e "${GREEN}OpenSSL development headers found.${NC}"
            return 0
        else
            echo -e "${YELLOW}OpenSSL development headers not found.${NC}"
            echo -e "Please install OpenSSL development headers with one of the following:"
            echo -e "${GREEN}sudo apt-get install libssl-dev${NC} (Debian/Ubuntu)"
            echo -e "${GREEN}sudo yum install openssl-devel${NC} (CentOS/RHEL/Fedora)"
            return 1
        fi
    elif [[ "$OS_TYPE" == "windows" ]]; then
        echo -e "${YELLOW}On Windows, you may need to install OpenSSL manually.${NC}"
        echo -e "Please visit https://slproweb.com/products/Win32OpenSSL.html to download and install OpenSSL."
        return 0  # Continue anyway as we can't easily check on Windows
    else
        echo -e "${YELLOW}Unknown OS. Please ensure OpenSSL development headers are installed.${NC}"
        return 0  # Continue anyway
    fi
}

# Detect Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo -e "${RED}Error: Python not found. Please install Python 3.6 or higher.${NC}"
    exit 1
fi

# Ensure we have the correct version
$PYTHON -c "import sys; sys.exit(0) if sys.version_info >= (3,6) else sys.exit(1)" || {
    echo -e "${RED}Error: Python 3.6 or higher is required.${NC}"
    exit 1
}

# Check for OpenSSL headers
check_openssl

# Create a virtual environment
echo "Creating virtual environment..."
$PYTHON -m venv qbitcoin_env || {
    echo -e "${RED}Error: Failed to create virtual environment. Please install venv package.${NC}"
    exit 1
}

# Determine activation script based on OS
if [[ "$OS_TYPE" == "macos" ]] || [[ "$OS_TYPE" == "linux" ]]; then
    # macOS or Linux
    source qbitcoin_env/bin/activate || {
        echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
        exit 1
    }
elif [[ "$OS_TYPE" == "windows" ]]; then
    # Windows
    source qbitcoin_env/Scripts/activate || {
        echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
        exit 1
    }
else
    echo -e "${RED}Unknown OS. Please activate the virtual environment manually.${NC}"
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip || {
    echo -e "${YELLOW}Warning: Failed to upgrade pip. Continuing with installation...${NC}"
}

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt || {
    echo -e "${RED}Error: Failed to install dependencies.${NC}"
    echo -e "${YELLOW}If pyspx installation failed, please ensure OpenSSL development headers are installed.${NC}"
    exit 1
}

# Ensure run_qbitcoin.sh exists and is executable
if [ ! -f "run_qbitcoin.sh" ]; then
    echo "Creating run_qbitcoin.sh wrapper script..."
    cat > run_qbitcoin.sh << 'EOL'
#!/bin/bash
# Wrapper script to ensure QBitcoin runs with the virtual environment

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Detect OS type for activation script path
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    ACTIVATE_SCRIPT="qbitcoin_env/Scripts/activate"
else
    ACTIVATE_SCRIPT="qbitcoin_env/bin/activate"
fi

# Check if virtual environment exists
if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo "Virtual environment not found. Running setup first..."
    bash setup.sh
fi

# Activate virtual environment and run command
source "$ACTIVATE_SCRIPT"
python3 main.py "$@"
EOL
fi

# Make wrapper script executable
chmod +x run_qbitcoin.sh

echo ""
echo -e "${GREEN}QBitcoin setup complete!${NC}"
echo ""
echo "To run QBitcoin, use the wrapper script:"
echo -e "  ${GREEN}./run_qbitcoin.sh [command] [options]${NC}"
echo ""
echo "Example commands:"
echo "  ./run_qbitcoin.sh create-wallet mywallet   # Create a new wallet"
echo "  ./run_qbitcoin.sh start-node               # Start a node on default port"
echo "  ./run_qbitcoin.sh start-node --port 9334   # Start a node on custom port"
echo "  ./run_qbitcoin.sh --help                   # Show all available commands"
echo ""
echo "For multi-node testing on the same machine:"
echo "  1. Start first node:  ./run_qbitcoin.sh start-node"
echo "  2. Start second node: ./run_qbitcoin.sh start-node --port 9334 --seed-peer 127.0.0.1:9333"
echo ""
echo -e "For detailed multi-node testing instructions, see: ${GREEN}MULTI_NODE_TESTING.md${NC}"
echo ""
echo -e "${YELLOW}Note:${NC} The virtual environment is managed automatically by the wrapper script." 