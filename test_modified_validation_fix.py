#!/usr/bin/env python3
"""
Test the modified validation to ensure parquet files are generated
"""

import pandas as pd
import json
from pathlib import Path
from validation.smart_validation_wrapper import run_smart_validation

def test_modified_validation():
    """Test modified validation with fixed parquet generation"""
    
    job_id = "b139a061-d967-47a5-b850-ff8bd3d351ae"
    base_path = Path(f"/mnt/d/Documents/daily/E_Plus_2040_py/output/{job_id}")
    
    # Paths
    parsed_data_path = base_path / "parsed_modified_results"
    real_data_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_parsed_format_daily_4136733.csv")
    output_path = base_path / "validation_results/modified_test"
    
    # Configuration
    config = {
        "target_frequency": "daily",
        "thresholds": {
            "cvrmse": 25.0,
            "nmbe": 8.0
        }
    }
    
    print("Running modified validation with variant support...")
    
    # Run validation with validate_variants=True
    results = run_smart_validation(
        parsed_data_path=str(parsed_data_path),
        real_data_path=str(real_data_path),
        config=config,
        output_path=str(output_path),
        validate_variants=True
    )
    
    print("\nChecking output files...")
    
    # Check what files were created
    output_files = list(output_path.glob("*"))
    print(f"\nFiles created in {output_path}:")
    for file in output_files:
        print(f"  - {file.name}")
        if file.suffix == '.parquet':
            df = pd.read_parquet(file)
            print(f"    Shape: {df.shape}")
            print(f"    Columns: {list(df.columns)}")
    
    # Check if parquet file was created
    parquet_file = output_path / "validation_results.parquet"
    if parquet_file.exists():
        print(f"\n✓ SUCCESS: Parquet file generated at {parquet_file}")
        df = pd.read_parquet(parquet_file)
        print(f"  - Records: {len(df)}")
        print(f"  - Configurations: {df['config_name'].unique() if 'config_name' in df.columns else 'N/A'}")
    else:
        print(f"\n✗ FAILED: No parquet file found at {parquet_file}")
    
    return results

if __name__ == "__main__":
    results = test_modified_validation()