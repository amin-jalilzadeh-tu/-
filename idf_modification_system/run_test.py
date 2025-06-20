#!/usr/bin/env python
"""
Simple script to run the IDF modification system
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import and run the test
from tests.unified_test import main

if __name__ == "__main__":
    main()
