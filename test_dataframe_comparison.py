#!/usr/bin/env python3
"""
Test to find DataFrame comparison issue
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

def find_dataframe_comparison_issue():
    """Find where DataFrame comparison causes issues"""
    print("\n=== Finding DataFrame Comparison Issue ===\n")
    
    try:
        analyzer = ModificationSensitivityAnalyzer(JOB_DIR, logger)
        
        # Load modifications
        print("Loading modifications...")
        analyzer.load_modification_tracking()
        print(f"Loaded {len(analyzer.modification_tracking)} modifications")
        
        # Try calculate_sensitivity which triggers the error
        print("\nTrying calculate_sensitivity...")
        results = analyzer.calculate_sensitivity(['Electricity:Facility'], 'elasticity')
        print(f"Success! Got {len(results)} results")
        
    except ValueError as e:
        if "The truth value of a DataFrame is ambiguous" in str(e):
            print(f"\nFound DataFrame comparison error!")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        else:
            raise
    except Exception as e:
        print(f"\nUnexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_dataframe_comparison_issue()