#!/usr/bin/env python
"""Test script for IDF modifications"""

import sys
import os
import json
from pathlib import Path

# Add your project root to Python path
PROJECT_ROOT = r"D:\Documents\daily\E_Plus_2040_py"
sys.path.insert(0, PROJECT_ROOT)

from idf_modification.modification_engine import ModificationEngine
from idf_modification.modification_tracker import ModificationTracker

def test_modifications():
    """Test if modifications are actually being applied"""
    
    # Load configuration
    with open(os.path.join(PROJECT_ROOT, "combined.json"), 'r') as f:
        config = json.load(f)
    
    mod_config = config['main_config']['modification']
    
    print("Configuration loaded:")
    print(f"  Modification enabled: {mod_config.get('perform_modification')}")
    
    # Initialize modification engine
    output_dir = "test_modifications"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a simple test
    print("\nTesting modification categories:")
    categories = mod_config.get('categories_to_modify', {})
    
    for cat_name, cat_config in categories.items():
        if cat_config.get('enabled', False):
            print(f"  {cat_name}: ENABLED")
            print(f"    Strategy: {cat_config.get('strategy', 'none')}")
            print(f"    Parameters: {list(cat_config.get('parameters', {}).keys())}")
        else:
            print(f"  {cat_name}: disabled")
    
    # Check if modifiers are being loaded
    print("\nChecking modifier loading...")
    
    # You can add more specific tests here

if __name__ == "__main__":
    test_modifications()
