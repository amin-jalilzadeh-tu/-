#!/usr/bin/env python3
"""Test sensitivity analysis data loading after fixes"""

import pandas as pd
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Test paths
job_dir = Path("output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6")
mod_file = job_dir / "modified_idfs/modifications_detail_wide_20250629_030549.parquet"
comp_dir = job_dir / "parsed_modified_results/comparisons"

print("Testing Sensitivity Analysis Data Loading")
print("=" * 50)

# 1. Test modification tracking loading
print("\n1. Testing modification tracking...")
try:
    df = pd.read_parquet(mod_file)
    print(f"✓ Loaded {len(df)} modifications")
    
    # Test field column
    if 'field' in df.columns:
        print(f"✓ 'field' column exists")
        
        # Test string concatenation with type conversion
        df['field_clean'] = df['field'].fillna('').str.strip()
        df['field_clean'] = df['field_clean'].replace('', 'value')
        
        df['param_key'] = (
            df['category'].astype(str) + '*' + 
            df['object_type'].astype(str) + '*' + 
            df['object_name'].astype(str) + '*' + 
            df['field_clean']
        )
        
        print(f"✓ Successfully created param_key")
        print(f"  Sample keys: {df['param_key'].unique()[:3].tolist()}")
    else:
        print("✗ 'field' column missing")
        
except Exception as e:
    print(f"✗ Failed to load modifications: {e}")

# 2. Test comparison data loading
print("\n2. Testing comparison data loading...")
try:
    comp_files = list(comp_dir.glob("var_*.parquet"))
    print(f"✓ Found {len(comp_files)} comparison files")
    
    # Test loading a specific file
    heating_file = comp_dir / "var_heating_energytransfer_na_monthly_b4136733.parquet"
    if heating_file.exists():
        df_comp = pd.read_parquet(heating_file)
        print(f"✓ Loaded heating comparison data: {df_comp.shape}")
        
        # Check structure
        value_cols = [col for col in df_comp.columns if col.endswith('_value')]
        print(f"  Value columns: {len(value_cols)} variants")
        
        # Check base values
        base_vals = df_comp['base_value']
        non_nan = base_vals.notna().sum()
        print(f"  Base values: {non_nan}/{len(base_vals)} non-NaN")
        
        # Check variant values
        var_col = 'variant_0_value'
        if var_col in df_comp.columns:
            var_vals = df_comp[var_col]
            var_non_nan = var_vals.notna().sum()
            print(f"  Variant 0 values: {var_non_nan}/{len(var_vals)} non-NaN")
            
except Exception as e:
    print(f"✗ Failed to load comparison data: {e}")

# 3. Test data manager loading
print("\n3. Testing data manager integration...")
try:
    from c_sensitivity.data_manager import SensitivityDataManager
    
    data_mgr = SensitivityDataManager(job_dir, logger)
    
    # Test loading simulation results
    results = data_mgr.load_simulation_results(
        result_type='monthly',
        variables=['Heating:EnergyTransfer', 'Cooling:EnergyTransfer'],
        load_modified=True
    )
    
    print(f"✓ Data manager loaded results")
    print(f"  Keys: {list(results.keys())}")
    
    if 'comparison_data' in results:
        print(f"  Comparison variables: {len(results['comparison_data'])}")
        for var, df in results['comparison_data'].items():
            print(f"    - {var}: {df.shape}")
            
    if 'base' in results:
        print(f"  Base categories: {len(results['base'])}")
        
except Exception as e:
    print(f"✗ Failed data manager test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("Test complete!")