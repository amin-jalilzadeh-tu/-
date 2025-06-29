#!/usr/bin/env python3
"""
Inspect parquet file formats to understand wide vs long formats
"""
import pandas as pd
from pathlib import Path
import sys

def inspect_parquet_file(file_path: Path, label: str):
    """Inspect a parquet file and show its structure"""
    print(f"\n{'='*80}")
    print(f"INSPECTING: {label}")
    print(f"File: {file_path.name}")
    print(f"Path: {file_path}")
    print('='*80)
    
    try:
        # Read the file
        df = pd.read_parquet(file_path)
        
        print(f"\nShape: {df.shape[0]} rows x {df.shape[1]} columns")
        print(f"\nColumns ({len(df.columns)}):")
        for i, col in enumerate(df.columns):
            print(f"  [{i:3d}] {col}")
            
        print(f"\nData types:")
        print(df.dtypes)
        
        # Show first few rows
        print(f"\nFirst 5 rows:")
        print(df.head())
        
        # Show unique values for key columns if they exist
        key_cols = ['building_id', 'variant_id', 'variable_name', 'VariableName', 
                   'Zone', 'category', 'Units', 'ReportingFrequency']
        
        print(f"\nUnique values in key columns:")
        for col in key_cols:
            if col in df.columns:
                unique_vals = df[col].nunique()
                print(f"  {col}: {unique_vals} unique values")
                if unique_vals <= 10:
                    print(f"    Values: {df[col].unique()}")
        
        # Check for date columns
        date_cols = [col for col in df.columns if 
                    any(pattern in str(col) for pattern in ['20', 'timestamp', 'DateTime', 'date'])]
        
        if date_cols:
            print(f"\nDate-related columns found: {len(date_cols)}")
            print(f"  First few: {date_cols[:10]}")
            
        # Check if it's wide format (many date columns)
        numeric_date_cols = [col for col in df.columns if 
                           col not in key_cols and df[col].dtype in ['float64', 'int64']]
        
        if len(numeric_date_cols) > 20:
            print(f"\nLikely WIDE FORMAT - {len(numeric_date_cols)} numeric columns that could be dates")
        else:
            print(f"\nLikely LONG FORMAT - only {len(numeric_date_cols)} numeric columns")
            
    except Exception as e:
        print(f"ERROR reading file: {e}")
        

def main():
    """Main function to inspect different file types"""
    
    # Base directory
    base_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py")
    
    # Files to inspect
    files_to_check = [
        # Wide format examples
        (base_dir / "output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/timeseries/base_all_daily.parquet", 
         "BASE WIDE FORMAT - Daily"),
        
        (base_dir / "output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_data/timeseries/base_all_monthly.parquet",
         "BASE WIDE FORMAT - Monthly"),
        
        # Long format examples  
        (base_dir / "output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_modified_results/comparisons/var_electricity_facility_na_daily_b4136733.parquet",
         "COMPARISON LONG FORMAT - Daily"),
        
        (base_dir / "output/85e39910-c928-4383-b9b0-be2b945e2b48/parsed_modified_results/comparisons/var_cooling_energytransfer_na_monthly_b4136733.parquet",
         "COMPARISON LONG FORMAT - Monthly"),
         
        # Other potential formats
        (base_dir / "_output_example/6f912613-913d-40ea-ba14-eff7e6dc097f/parsed_data/sql_results/timeseries/hourly/hvac_2013.parquet",
         "SQL RESULTS FORMAT - Hourly")
    ]
    
    for file_path, label in files_to_check:
        if file_path.exists():
            inspect_parquet_file(file_path, label)
        else:
            print(f"\nFile not found: {file_path}")
            

if __name__ == "__main__":
    main()