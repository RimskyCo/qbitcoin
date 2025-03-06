#!/usr/bin/env python3
"""
QBitcoin - Quantum-safe Bitcoin implementation
Main entry point for running QBitcoin components.
"""

import sys
import os
from qbitcoin.cli import main as cli_main

if __name__ == "__main__":
    # Make the package importable
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    cli_main() 