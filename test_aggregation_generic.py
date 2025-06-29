#!/usr/bin/env python3
"""
Test generic aggregation function
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import re

# Add the current directory to the path
sys.path.append('.')

def test_aggregation_logic():
    """Test the aggregation logic with the fixed regex"""
    
    job_output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/c7312eaf-a1fc-406e-a1c8-191081756e79"
    comparisons_dir = Path(job_output_dir) / 'parsed_modified_results' / 'comparisons'
    
    print("Testing file discovery with fixed regex...")
    
    # Test file discovery
    files_by_freq = {}
    
    for file in comparisons_dir.glob('var_*.parquet'):
        if '_from_' not in file.stem:  # Original files only
            # Use the fixed regex pattern
            match = re.match(r'var_(.+)_([^_]+)_([^_]+)_b(\d+)\.parquet', file.name)
            if match:
                var_name_part, unit, freq, building_id = match.groups()
                print(f"Found: {file.name}")
                print(f"  Variable: {var_name_part}")
                print(f"  Unit: {unit}")
                print(f"  Frequency: {freq}")
                print(f"  Building: {building_id}")
                
                if freq not in files_by_freq:
                    files_by_freq[freq] = []
                files_by_freq[freq].append(file)
                print()
    
    print(f"Files by frequency:")
    for freq, files in files_by_freq.items():
        print(f"  {freq}: {len(files)} files")
        for file in files:
            print(f"    - {file.name}")
    
    return files_by_freq

def aggregate_daily_to_monthly_generic(input_file: Path, output_file: Path):
    """Generic function to aggregate any daily comparison file to monthly"""
    
    print(f"Aggregating {input_file.name} to monthly...")
    
    # Read daily data
    df = pd.read_parquet(input_file)
    print(f"  Input shape: {df.shape}")
    
    # Get value columns (all base and variant columns)
    value_cols = [col for col in df.columns if col.endswith('_value')]
    print(f"  Found {len(value_cols)} value columns")
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Set timestamp as index for grouping
    df = df.set_index('timestamp')
    
    # Get metadata columns
    meta_cols = ['building_id', 'Zone', 'variable_name', 'category', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Group by month and sum (appropriate for energy data)
    agg_df = df.groupby(pd.Grouper(freq='ME'))[value_cols].sum()  # Use 'ME' instead of deprecated 'M'
    
    # Reset index
    agg_df = agg_df.reset_index()
    
    # Convert back to milliseconds timestamp
    agg_df['timestamp'] = agg_df['timestamp'].astype('int64') // 10**6
    
    # Add back metadata (take first value since they should be consistent)
    for col in meta_cols:
        if col in df.columns:
            agg_df[col] = df[col].iloc[0]
    
    # Reorder columns to match original structure
    first_cols = ['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units']
    first_cols = [col for col in first_cols if col in agg_df.columns]
    other_cols = [col for col in agg_df.columns if col not in first_cols]
    
    result_df = agg_df[first_cols + other_cols]
    
    print(f"  Output shape: {result_df.shape}")
    
    # Save the result
    result_df.to_parquet(output_file, index=False)
    print(f"  Saved: {output_file.name}")
    
    return result_df

if __name__ == "__main__":
    # Test the file discovery
    files_by_freq = test_aggregation_logic()
    
    # Test aggregation on the electricity file if it exists
    if 'daily' in files_by_freq:
        for daily_file in files_by_freq['daily']:
            if 'electricity' in daily_file.name:
                # Parse filename to create output filename
                match = re.match(r'var_(.+)_([^_]+)_([^_]+)_b(\d+)\.parquet', daily_file.name)
                if match:
                    var_name_part, unit, source_freq, building_id = match.groups()
                    output_file = daily_file.parent / f"var_{var_name_part}_{unit}_monthly_from_{source_freq}_b{building_id}.parquet"
                    
                    print(f"\nTesting aggregation:")
                    print(f"Input: {daily_file}")
                    print(f"Output: {output_file}")
                    
                    # Only proceed if output doesn't exist or we want to overwrite
                    if not output_file.exists():
                        try:
                            result = aggregate_daily_to_monthly_generic(daily_file, output_file)
                            print("Aggregation successful!")
                        except Exception as e:
                            print(f"Aggregation failed: {e}")
                    else:
                        print("Output file already exists, skipping...")
                break