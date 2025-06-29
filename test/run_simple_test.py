#!/usr/bin/env python
# Simple test script to verify setup

import sys
from pathlib import Path

# Add test directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run
from modifier import StandaloneModifier
from run_simulation import StandaloneSimulator

print("Testing modifier import... OK")
print("Testing simulator import... OK")

# Try to load config
import json
config_path = Path(__file__).parent / 'test_config.json'
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    print(f"Config loaded: {config['test_name']}")
else:
    print("test_config.json not found!")

print("\nSetup verification complete!")
print("Run 'python main_test.py' to start tests")
