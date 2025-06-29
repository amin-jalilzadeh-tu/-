#!/usr/bin/env python3
"""Script to examine parquet files structure"""

import sys
import json

try:
    import pandas as pd
    import pyarrow.parquet as pq
except ImportError:
    print("Error: pandas or pyarrow not installed")
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "pyarrow"])
    import pandas as pd
    import pyarrow.parquet as pq

def examine_parquet(file_path):
    """Examine a parquet file and return its structure"""
    print(f"\n{'='*80}")
    print(f"Examining: {file_path}")
    print('='*80)
    
    try:
        # Read the parquet file
        df = pd.read_parquet(file_path)
        
        # Basic info
        print(f"\nShape: {df.shape} (rows: {df.shape[0]}, columns: {df.shape[1]})")
        
        # Column names and types
        print("\nColumns and types:")
        for col, dtype in df.dtypes.items():
            print(f"  - {col}: {dtype}")
        
        # Sample data
        print("\nFirst 3 rows:")
        print(df.head(3).to_string())
        
        # Check for datetime columns
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        if datetime_cols:
            print(f"\nDatetime columns: {datetime_cols}")
        
        # Check for numeric columns
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        if numeric_cols:
            print(f"\nNumeric columns: {numeric_cols}")
        
        # Memory usage
        print(f"\nMemory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
    except Exception as e:
        print(f"Error reading file: {str(e)}")

# Files to examine
files_to_examine = [
    "/mnt/d/Documents/daily/E_Plus_2040_py/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/timeseries/base_all_daily.parquet",
    "/mnt/d/Documents/daily/E_Plus_2040_py/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/relationships/zone_mappings.parquet",
    "/mnt/d/Documents/daily/E_Plus_2040_py/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/relationships/equipment_assignments.parquet",
    "/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_hourly.parquet",
    "/mnt/d/Documents/daily/E_Plus_2040_py/output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/metadata/building_registry.parquet",
]

if __name__ == "__main__":
    for file_path in files_to_examine:
        examine_parquet(file_path)