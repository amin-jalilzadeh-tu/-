#!/usr/bin/env python3
"""
Manual baseline validation fix script
"""

import pandas as pd
import json
from pathlib import Path
from validation.smart_validation_wrapper import SmartValidationWrapper

def run_fixed_baseline_validation():
    """Run baseline validation with fixed data loading"""
    
    job_id = "b139a061-d967-47a5-b850-ff8bd3d351ae"
    base_path = Path(f"/mnt/d/Documents/daily/E_Plus_2040_py/output/{job_id}")
    
    # Paths
    parsed_data_path = base_path / "parsed_data"
    real_data_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_parsed_format_daily_4136733.csv")
    output_path = base_path / "validation_results/baseline_fixed"
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Configuration
    config = {
        "target_frequency": "daily",
        "thresholds": {
            "cvrmse": 25.0,
            "nmbe": 8.0
        }
    }
    
    # Create validator
    validator = SmartValidationWrapper(str(parsed_data_path), str(real_data_path), config)
    
    # Manually load baseline data
    print("Loading baseline data...")
    daily_path = parsed_data_path / "timeseries/base_all_daily.parquet"
    if daily_path.exists():
        df = pd.read_parquet(daily_path)
        print(f"Loaded wide format data: {df.shape}")
        
        # Convert to long format
        df_long = validator._convert_wide_to_long(df)
        print(f"Converted to long format: {df_long.shape}")
        
        # Save converted data for inspection
        df_long.to_parquet(output_path / "baseline_data_long.parquet")
        print(f"Saved converted data to {output_path / 'baseline_data_long.parquet'}")
    
    # Run validation
    print("\nRunning validation...")
    results = validator.validate_all()
    
    # Save results
    if results.get('validation_results'):
        val_df = pd.DataFrame(results['validation_results'])
        val_df.to_csv(output_path / 'validation_results.csv', index=False)
        val_df.to_parquet(output_path / 'validation_results.parquet', index=False)
        print(f"Saved validation results: {len(val_df)} records")
    
    # Save summary
    with open(output_path / 'validation_summary.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    
    # Print summary
    if 'summary' in results:
        summary = results['summary']
        print("\nValidation Summary:")
        print(f"- Pass rate: {summary.get('pass_rate', 0):.1f}%")
        print(f"- Buildings validated: {summary.get('buildings_validated', 0)}")
        print(f"- Variables validated: {summary.get('variables_validated', 0)}")

if __name__ == "__main__":
    run_fixed_baseline_validation()
