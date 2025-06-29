#!/usr/bin/env python3
"""Script to inspect the structure of modification tracking parquet files."""

import pandas as pd
import os

# Define the file paths
parquet_files = [
    "/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/modified_idfs/modifications_detail_wide_20250629_030549.parquet",
    "/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/modified_idfs/modifications_detail_long_20250629_030549.parquet"
]

for file_path in parquet_files:
    if os.path.exists(file_path):
        print(f"\n{'='*80}")
        print(f"Inspecting: {os.path.basename(file_path)}")
        print(f"{'='*80}")
        
        # Load the parquet file
        df = pd.read_parquet(file_path)
        
        # Display basic information
        print(f"\nShape: {df.shape}")
        print(f"\nColumn names:")
        for i, col in enumerate(df.columns):
            print(f"  {i+1}. {col}")
        
        print(f"\nData types:")
        print(df.dtypes)
        
        print(f"\nFirst 5 rows:")
        print(df.head())
        
        # Check for columns that might be equivalent to 'field_name'
        potential_field_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['field', 'param', 'name', 'variable'])]
        if potential_field_columns:
            print(f"\nPotential 'field_name' equivalent columns:")
            for col in potential_field_columns:
                print(f"  - {col}")
                print(f"    Sample values: {df[col].dropna().unique()[:5].tolist()}")
    else:
        print(f"\nFile not found: {file_path}")