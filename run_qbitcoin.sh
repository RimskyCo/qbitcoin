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