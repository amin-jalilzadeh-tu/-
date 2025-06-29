#!/usr/bin/env python3
"""
Test to find DataFrame comparison issue with more details
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
import numpy as np
import logging

# Import sensitivity modules
from c_sensitivity.modification_analyzer import ModificationSensitivityAnalyzer

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test data paths
JOB_DIR = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a")

def test_dataframe_operations():
    """Test various DataFrame operations that might cause issues"""
    print("\n=== Testing DataFrame Operations ===\n")
    
    # Create test DataFrame
    df = pd.DataFrame({
        'scope': ['zone', 'building', 'zone', 'equipment'],
        'value': [1, 2, 3, 4]
    })
    
    print("Testing scope comparisons:")
    
    # This is fine - creates a boolean Series
    zone_mask = df['scope'] == 'zone'
    print(f"1. df['scope'] == 'zone' creates: {type(zone_mask)} with shape {zone_mask.shape}")
    
    # This would fail - can't use boolean Series in if
    try:
        if df['scope'] == 'zone':
            print("This won't work")
    except ValueError as e:
        print(f"2. if df['scope'] == 'zone': causes error: {e}")
    
    # Correct way
    if (df['scope'] == 'zone').any():
        print("3. if (df['scope'] == 'zone').any(): works fine")
    
    # Test with modification analyzer
    print("\n\nTesting with ModificationSensitivityAnalyzer:")
    
    try:
        analyzer = ModificationSensitivityAnalyzer(JOB_DIR, logger)
        analyzer.load_modification_tracking()
        
        # Check modification tracking structure
        print(f"\nModification tracking shape: {analyzer.modification_tracking.shape}")
        print(f"Columns: {list(analyzer.modification_tracking.columns)}")
        
        # Look for potential problematic comparisons
        if 'scope' in analyzer.modification_tracking.columns:
            print(f"\nScope values: {analyzer.modification_tracking['scope'].unique()}")
        
        # Try the main calculation
        print("\nCalculating sensitivity...")
        results = analyzer.calculate_sensitivity(['Electricity:Facility'], 'elasticity')
        
        if isinstance(results, list):
            print(f"Results: list of {len(results)} items")
        elif isinstance(results, pd.DataFrame):
            print(f"Results: DataFrame with shape {results.shape}")
            if results.empty:
                print("DataFrame is empty!")
        else:
            print(f"Results type: {type(results)}")
        
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dataframe_operations()