#!/usr/bin/env python3
"""Test the modification analyzer's delta calculation directly"""

import pandas as pd
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# New job directory
job_dir = Path("output/1098634b-b67a-49af-bc58-2b61152efa12")

print("Testing Modification Analyzer Delta Calculation")
print("=" * 60)

try:
    # Mock the necessary parts to test just the delta calculation
    comparison_path = job_dir / "parsed_modified_results/comparisons"
    modified_parsed_dir = job_dir / "parsed_modified_results"
    
    # Test the new logic
    frequency = 'daily'
    output_variables = ['Electricity:Facility', 'Heating:EnergyTransfer', 'Cooling:EnergyTransfer']
    
    # Get all comparison files for the frequency
    all_comparison_files = list(comparison_path.glob(f"var_*_{frequency}_*.parquet"))
    print(f"\nFound {len(all_comparison_files)} {frequency} comparison files")
    
    for var in output_variables:
        # Clean variable name - remove colons, brackets and convert to lowercase
        var_clean = var.split('[')[0].strip().lower()
        var_clean_normalized = var_clean.replace(':', '').replace('_', '')
        
        print(f"\nVariable: {var}")
        print(f"  Cleaned: {var_clean}")
        print(f"  Normalized: {var_clean_normalized}")
        
        # Find matching files by checking if the normalized variable name matches
        var_files = []
        for file_path in all_comparison_files:
            # Parse filename to get variable name
            parts = file_path.stem.split('_')
            building_part = next((i for i, p in enumerate(parts) if p.startswith('b')), -1)
            
            if building_part > 0:
                file_var_name = '_'.join(parts[1:building_part-2])
                file_var_normalized = file_var_name.lower().replace('_', '')
                
                print(f"  Checking file: {file_path.name}")
                print(f"    File var: {file_var_name} -> {file_var_normalized}")
                
                # Check if this file matches our variable
                if var_clean_normalized in file_var_normalized or file_var_normalized in var_clean_normalized:
                    var_files.append(file_path)
                    print(f"    ✓ MATCHED!")
        
        print(f"  Total matches: {len(var_files)}")
        
        # Test loading the matched files
        for file_path in var_files:
            df = pd.read_parquet(file_path)
            print(f"\n  Loading {file_path.name}:")
            print(f"    Shape: {df.shape}")
            print(f"    Base values non-NaN: {df['base_value'].notna().sum()}/{len(df)}")
            print(f"    Variant columns: {len([c for c in df.columns if c.startswith('variant_') and c.endswith('_value')])}")
            
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)