#!/usr/bin/env python3
"""Test sensitivity analysis on the new job that just ran"""

import pandas as pd
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# New job directory
job_dir = Path("output/1098634b-b67a-49af-bc58-2b61152efa12")

print("Testing Sensitivity Analysis on New Job")
print("=" * 60)

# Test the modification analyzer's delta calculation
try:
    from c_sensitivity.data_manager import SensitivityDataManager
    
    # Create data manager
    data_mgr = SensitivityDataManager(job_dir, logger)
    
    # Load simulation results with daily frequency (as requested in the logs)
    print("\n1. Loading daily simulation results...")
    results = data_mgr.load_simulation_results(
        result_type='daily',
        variables=['Electricity:Facility', 'Heating:EnergyTransfer', 'Cooling:EnergyTransfer'],
        load_modified=True
    )
    
    print(f"✓ Loaded results: {list(results.keys())}")
    if 'comparison_data' in results:
        print(f"  Comparison variables: {len(results['comparison_data'])}")
        for var, df in results['comparison_data'].items():
            print(f"    - {var}: {df.shape}")
            
    # Test the modification analyzer's delta calculation directly
    print("\n2. Testing delta calculation from modification analyzer...")
    
    # Import the fixed modification analyzer
    import sys
    sys.path.insert(0, '.')
    
    # Create a simple test of the fixed pattern matching
    comparison_path = job_dir / "parsed_modified_results/comparisons"
    
    output_variables = ['Electricity:Facility', 'Heating:EnergyTransfer', 'Cooling:EnergyTransfer']
    frequency = 'daily'
    
    print(f"\nSearching for comparison files:")
    for var in output_variables:
        var_clean = var.split('[')[0].strip().lower()
        var_clean_no_colon = var_clean.replace(':', '')
        
        pattern = f"var_*{var_clean_no_colon}*_{frequency}_*.parquet"
        var_files = list(comparison_path.glob(pattern))
        
        print(f"\n  Variable: {var} -> {var_clean_no_colon}")
        print(f"  Pattern: {pattern}")
        print(f"  Found files: {len(var_files)}")
        for f in var_files:
            print(f"    - {f.name}")
            
            # Test loading
            df = pd.read_parquet(f)
            base_non_nan = df['base_value'].notna().sum()
            print(f"      Base values: {base_non_nan}/{len(df)} non-NaN")
            
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")