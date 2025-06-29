#!/usr/bin/env python3
"""
Debug modification analyzer to find DataFrame comparison issue
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test data paths
JOB_DIR = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a")

def debug_analyzer():
    """Debug the analyzer step by step"""
    
    analyzer = ModificationSensitivityAnalyzer(JOB_DIR, logger)
    
    # Load modifications
    print("Loading modifications...")
    analyzer.load_modification_tracking()
    print(f"Loaded {len(analyzer.modification_tracking)} modifications")
    
    # Step 1: Try calculate_output_deltas
    print("\nStep 1: calculate_output_deltas")
    try:
        deltas = analyzer.calculate_output_deltas(['Electricity:Facility'], 'sum')
        print(f"Success! Got {len(deltas)} deltas")
        print(f"Delta type: {type(deltas)}")
        if isinstance(deltas, pd.DataFrame):
            print(f"Delta shape: {deltas.shape}")
            print(f"Delta columns: {list(deltas.columns)}")
    except Exception as e:
        print(f"Error in calculate_output_deltas: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Try calculate_sensitivity
    print("\nStep 2: calculate_sensitivity")
    try:
        results = analyzer.calculate_sensitivity(['Electricity:Facility'], 'elasticity')
        print(f"Results type: {type(results)}")
        if isinstance(results, list):
            print(f"Got list with {len(results)} results")
            if results:
                print(f"First result type: {type(results[0])}")
                print(f"First result: {results[0]}")
        elif isinstance(results, pd.DataFrame):
            print(f"Got DataFrame with shape {results.shape}")
            if not results.empty:
                print(f"Columns: {list(results.columns)}")
                print(f"First few rows:\n{results.head()}")
        else:
            print(f"Unexpected result type: {type(results)}")
    except Exception as e:
        print(f"Error in calculate_sensitivity: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_analyzer()