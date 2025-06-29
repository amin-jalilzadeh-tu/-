#!/usr/bin/env python3
"""Check aggregation output to diagnose issues"""

import pandas as pd
import json
from pathlib import Path

# Find a yearly aggregation file
yearly_file = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/parsed_data/timeseries/base_all_yearly_from_daily.parquet")

if yearly_file.exists():
    print(f"Reading: {yearly_file}")
    df = pd.read_parquet(yearly_file)
    
    print(f"\nShape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")
    
    # Show first few rows
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())
    
    # Check date columns
    date_cols = [col for col in df.columns if isinstance(col, str) and (col.startswith('20') or col.startswith('19'))]
    print(f"\nDate columns found: {date_cols[:10]}")  # Show first 10
    
    # Check if these are daily or yearly
    if len(date_cols) > 1:
        print(f"\nNumber of date columns: {len(date_cols)}")
        if len(date_cols) > 12:
            print("ERROR: Found more than 12 date columns in yearly data - appears to be daily data!")
        else:
            print("Looks like proper yearly data")

# Now check a comparison file
print("\n" + "="*80 + "\n")

# Find comparison files  
comp_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/e686dc76-9ae0-4317-8297-71142bd06e27/parsed_modified_results/comparisons")
if comp_dir.exists():
    comp_files = list(comp_dir.glob("var_*.parquet"))
    if comp_files:
        # Read first comparison file
        comp_file = comp_files[0]
        print(f"Reading comparison: {comp_file.name}")
        df_comp = pd.read_parquet(comp_file)
        
        print(f"\nShape: {df_comp.shape}")
        print(f"\nColumns: {list(df_comp.columns)}")
        
        print("\nFirst 5 rows:")
        print(df_comp.head(5).to_string())
        
        # Check timestamp format
        if 'timestamp' in df_comp.columns:
            # Convert timestamp to datetime
            df_comp['datetime'] = pd.to_datetime(df_comp['timestamp'], unit='ms')
            print(f"\nTimestamp range: {df_comp['datetime'].min()} to {df_comp['datetime'].max()}")
            
            # Check frequency
            if len(df_comp) > 1:
                time_diff = (df_comp['datetime'].iloc[1] - df_comp['datetime'].iloc[0]).total_seconds()
                if time_diff < 3600:
                    print(f"Frequency appears to be sub-hourly ({time_diff} seconds)")
                elif time_diff < 86400:
                    print(f"Frequency appears to be hourly")
                elif time_diff < 86400 * 7:
                    print(f"Frequency appears to be daily")
                elif time_diff < 86400 * 35:
                    print(f"Frequency appears to be monthly")
                else:
                    print(f"Frequency appears to be yearly")