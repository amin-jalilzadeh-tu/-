#!/usr/bin/env python3
"""
Test baseline validation with year-agnostic matching
"""

import pandas as pd
import json
from pathlib import Path
from validation.smart_validation_wrapper import run_smart_validation

def test_baseline_with_year_agnostic():
    """Test baseline validation with year-agnostic date matching"""
    
    job_id = "025d76e7-cfdd-4c55-91fb-8a1dc14a9ef0"
    base_path = Path(f"/mnt/d/Documents/daily/E_Plus_2040_py/output/{job_id}")
    
    # Paths
    parsed_data_path = base_path / "parsed_data"
    real_data_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_parsed_format_daily_4136733.csv")
    output_path = base_path / "validation_results/baseline_year_agnostic"
    
    # Configuration with year-agnostic matching enabled
    config = {
        "target_frequency": "monthly",
        "year_agnostic_matching": True,  # Enable year-agnostic matching
        "variables_to_validate": ["Electricity", "Heating", "Cooling", "Temperature"],
        "thresholds": {
            "cvrmse": 25.0,
            "nmbe": 8.0
        }
    }
    
    print("Running baseline validation with year-agnostic matching...")
    print(f"Config: {json.dumps(config, indent=2)}")
    
    # Run validation
    results = run_smart_validation(
        parsed_data_path=str(parsed_data_path),
        real_data_path=str(real_data_path),
        config=config,
        output_path=str(output_path),
        validate_variants=False
    )
    
    print("\nChecking results...")
    
    # Check if validation results were generated
    if results and 'validation_results' in results:
        print(f"\n✓ Validation completed with {len(results['validation_results'])} results")
        for result in results['validation_results']:
            print(f"  - {result['real_variable']} → {result['sim_variable']}")
            print(f"    CVRMSE: {result['cvrmse']:.1f}%, NMBE: {result['nmbe']:.1f}%")
    else:
        print("\n✗ No validation results generated")
    
    # Check output files
    output_files = list(output_path.glob("*"))
    print(f"\nFiles created in {output_path}:")
    for file in output_files:
        print(f"  - {file.name}")
    
    # Check parquet file
    parquet_file = output_path / "validation_results.parquet"
    if parquet_file.exists():
        print(f"\n✓ SUCCESS: Parquet file generated")
        df = pd.read_parquet(parquet_file)
        print(f"  - Records: {len(df)}")
        print(f"  - Variables: {list(df['real_variable'].unique())}")
    
    return results

def check_available_sim_variables():
    """Check what variables are available in the baseline simulation data"""
    
    job_id = "025d76e7-cfdd-4c55-91fb-8a1dc14a9ef0"
    base_path = Path(f"/mnt/d/Documents/daily/E_Plus_2040_py/output/{job_id}")
    timeseries_path = base_path / "parsed_data/timeseries"
    
    print("\nChecking available simulation variables...")
    
    # Check monthly data
    monthly_file = timeseries_path / "base_all_monthly.parquet"
    if monthly_file.exists():
        df = pd.read_parquet(monthly_file)
        print(f"\nMonthly data columns: {list(df.columns[:10])}...")
        
        if 'Variable' in df.columns:
            variables = df['Variable'].unique()
            print(f"\nAvailable simulation variables ({len(variables)} total):")
            for var in sorted(variables)[:20]:
                print(f"  - {var}")
            if len(variables) > 20:
                print(f"  ... and {len(variables) - 20} more")
                
            # Check specifically for Electricity:Facility
            electricity_vars = [v for v in variables if 'electricity' in v.lower() or 'facility' in v.lower()]
            print(f"\nElectricity/Facility related variables:")
            for var in electricity_vars:
                print(f"  - {var}")

if __name__ == "__main__":
    # First check what variables are available
    check_available_sim_variables()
    
    # Then run validation with year-agnostic matching
    results = test_baseline_with_year_agnostic()