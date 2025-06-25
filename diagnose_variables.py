"""
diagnose_variables.py

Diagnose what variables are actually available in the output data
to fix the target variable matching issue.
"""

import pandas as pd
import sys
from pathlib import Path

def diagnose_output_variables(job_output_dir: str):
    """Check what variables are available in the output data"""
    
    print("="*80)
    print("DIAGNOSING OUTPUT VARIABLES")
    print("="*80)
    
    # Load the extracted outputs that were saved
    test_output_dir = Path(job_output_dir) / "surrogate_test_output"
    
    # Check base outputs
    print("\n1. BASE OUTPUTS:")
    base_outputs_file = test_output_dir / "extracted_base_outputs.parquet"
    if base_outputs_file.exists():
        base_outputs = pd.read_parquet(base_outputs_file)
        print(f"   Shape: {base_outputs.shape}")
        print(f"   Columns: {list(base_outputs.columns)}")
        
        if 'Variable' in base_outputs.columns:
            unique_vars = base_outputs['Variable'].unique()
            print(f"\n   Unique Variables ({len(unique_vars)}):")
            for var in sorted(unique_vars)[:20]:  # Show first 20
                count = len(base_outputs[base_outputs['Variable'] == var])
                print(f"     - {var} (count: {count})")
            if len(unique_vars) > 20:
                print(f"     ... and {len(unique_vars) - 20} more")
                
            # Check for heating/cooling/electricity
            print("\n   Checking for target-like variables:")
            for keyword in ['Heating', 'Cooling', 'Electricity', 'Energy']:
                matching = [v for v in unique_vars if keyword.lower() in v.lower()]
                if matching:
                    print(f"     {keyword}: {len(matching)} variables")
                    for var in matching[:5]:
                        print(f"       - {var}")
    
    # Check modified outputs
    print("\n2. MODIFIED OUTPUTS:")
    mod_outputs_file = test_output_dir / "extracted_modified_outputs.parquet"
    if mod_outputs_file.exists():
        mod_outputs = pd.read_parquet(mod_outputs_file)
        print(f"   Shape: {mod_outputs.shape}")
        print(f"   Columns: {list(mod_outputs.columns)}")
        
        if 'Variable' in mod_outputs.columns:
            unique_vars = mod_outputs['Variable'].unique()
            print(f"\n   Unique Variables ({len(unique_vars)}):")
            for var in sorted(unique_vars)[:20]:
                count = len(mod_outputs[mod_outputs['Variable'] == var])
                print(f"     - {var} (count: {count})")
                
    # Check the actual parquet files in parsed data
    print("\n3. CHECKING ORIGINAL PARSED DATA:")
    zones_daily = Path(job_output_dir) / "parsed_data" / "sql_results" / "timeseries" / "aggregated" / "daily" / "zones_daily.parquet"
    if zones_daily.exists():
        zones_df = pd.read_parquet(zones_daily)
        print(f"\n   zones_daily.parquet:")
        print(f"     Shape: {zones_df.shape}")
        print(f"     Columns: {list(zones_df.columns)}")
        
        if 'Variable' in zones_df.columns:
            zone_vars = zones_df['Variable'].unique()
            print(f"     Variables: {len(zone_vars)}")
            # Show all heating/cooling/electricity variables
            for keyword in ['Heating', 'Cooling', 'Electricity']:
                matching = [v for v in zone_vars if keyword in v]
                if matching:
                    print(f"\n     {keyword} variables:")
                    for var in matching:
                        print(f"       - {var}")
    
    # Suggest correct target variables
    print("\n4. SUGGESTED TARGET VARIABLES:")
    print("   Based on the data, you should update your configuration to use these exact variable names:")
    
    # Create a mapping of what to use
    if base_outputs_file.exists() and 'Variable' in base_outputs.columns:
        all_vars = base_outputs['Variable'].unique()
        
        suggestions = {
            'heating': [v for v in all_vars if 'Heating' in v and 'Energy' in v],
            'cooling': [v for v in all_vars if 'Cooling' in v and 'Energy' in v],
            'electricity': [v for v in all_vars if 'Electricity' in v]
        }
        
        print("\n   Recommended target_variables configuration:")
        print("   target_variables = [")
        for category, vars in suggestions.items():
            if vars:
                print(f"       '{vars[0]}',  # {category}")
        print("   ]")
        
        # Also check if the variable names have different formatting
        print("\n5. VARIABLE NAME PATTERNS:")
        sample_vars = list(all_vars)[:10]
        for var in sample_vars:
            print(f"   - {repr(var)}")  # Use repr to see exact formatting


def fix_preprocessor_targets(job_output_dir: str):
    """Create a fixed version of the preprocessing configuration"""
    
    print("\n" + "="*80)
    print("CREATING FIXED CONFIGURATION")
    print("="*80)
    
    # Load the outputs to get actual variable names
    test_output_dir = Path(job_output_dir) / "surrogate_test_output"
    base_outputs_file = test_output_dir / "extracted_base_outputs.parquet"
    
    if base_outputs_file.exists():
        base_outputs = pd.read_parquet(base_outputs_file)
        
        if 'Variable' in base_outputs.columns:
            all_vars = base_outputs['Variable'].unique()
            
            # Find the closest matches to what we want
            target_mapping = {}
            
            # Look for heating
            heating_vars = [v for v in all_vars if 'Zone Air System Sensible Heating Energy' in v]
            if heating_vars:
                target_mapping['heating'] = heating_vars[0]
            
            # Look for cooling  
            cooling_vars = [v for v in all_vars if 'Zone Air System Sensible Cooling Energy' in v]
            if cooling_vars:
                target_mapping['cooling'] = cooling_vars[0]
                
            # Look for electricity
            electricity_vars = [v for v in all_vars if 'Electricity:Facility' in v]
            if electricity_vars:
                target_mapping['electricity'] = electricity_vars[0]
            
            print("\nFixed configuration:")
            print("""
config = {
    'aggregation_level': 'building',
    'temporal_resolution': 'daily', 
    'use_sensitivity_filter': False,
    'normalize_features': True,
    'target_variables': [""")
            
            for key, var in target_mapping.items():
                print(f"        '{var}',  # {key}")
                
            print("""    ]
}""")
            
            return list(target_mapping.values())
    
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_output_dir = sys.argv[1]
    else:
        print("Usage: python diagnose_variables.py <job_output_dir>")
        sys.exit(1)
    
    diagnose_output_variables(job_output_dir)
    target_vars = fix_preprocessor_targets(job_output_dir)
    
    if target_vars:
        print(f"\n✓ Found {len(target_vars)} suitable target variables")
    else:
        print("\n✗ Could not determine suitable target variables")
