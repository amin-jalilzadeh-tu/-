#!/usr/bin/env python3
"""Check the structure and content of parquet files in sensitivity results."""

import pandas as pd
import os
from pathlib import Path

# Define the path to sensitivity results
sensitivity_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/c7312eaf-a1fc-406e-a1c8-191081756e79/sensitivity_results")

# List all parquet files
parquet_files = [
    "modification_sensitivity_results_peak_months_cooling.parquet",
    "sensitivity_for_surrogate.parquet",
    "threshold_analysis_results.parquet",
    "uncertainty_analysis_results.parquet"
]

print("=" * 80)
print("PARQUET FILE ANALYSIS")
print("=" * 80)

for parquet_file in parquet_files:
    file_path = sensitivity_dir / parquet_file
    if file_path.exists():
        print(f"\n{'='*60}")
        print(f"File: {parquet_file}")
        print(f"{'='*60}")
        
        try:
            # Read the parquet file
            df = pd.read_parquet(file_path)
            
            print(f"\nShape: {df.shape}")
            print(f"Columns ({len(df.columns)}): {list(df.columns)}")
            
            # Show data types
            print("\nData Types:")
            print(df.dtypes)
            
            # Show first few rows
            print(f"\nFirst 3 rows:")
            print(df.head(3))
            
            # Check for duplicates
            duplicates = df.duplicated().sum()
            print(f"\nDuplicate rows: {duplicates}")
            
            # Check for null values
            null_counts = df.isnull().sum()
            if null_counts.any():
                print("\nNull values per column:")
                print(null_counts[null_counts > 0])
            else:
                print("\nNo null values found")
                
            # For sensitivity results, check unique values in key columns
            if 'parameter' in df.columns:
                print(f"\nUnique parameters: {df['parameter'].nunique()}")
                print("Sample parameters:")
                print(df['parameter'].unique()[:5])
                
            if 'sensitivity_score' in df.columns:
                print(f"\nSensitivity score range: {df['sensitivity_score'].min():.4f} to {df['sensitivity_score'].max():.4f}")
                
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"\nFile not found: {parquet_file}")

print("\n" + "=" * 80)