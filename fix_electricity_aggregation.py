#!/usr/bin/env python3
"""
Fix electricity aggregation to create monthly files with all variant values
"""

import pandas as pd
import numpy as np
from pathlib import Path

def aggregate_electricity_to_monthly(job_output_dir: str):
    """Aggregate daily electricity file to monthly with all variants"""
    
    # Paths
    comparisons_dir = Path(job_output_dir) / 'parsed_modified_results' / 'comparisons'
    daily_file = comparisons_dir / 'var_electricity_facility_na_daily_b4136733.parquet'
    monthly_file = comparisons_dir / 'var_electricity_facility_na_monthly_b4136733.parquet'
    
    print(f"Reading daily file: {daily_file}")
    
    # Read daily data
    df = pd.read_parquet(daily_file)
    print(f"Daily data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Get value columns (all base and variant columns)
    value_cols = [col for col in df.columns if col.endswith('_value')]
    print(f"Found {len(value_cols)} value columns: {value_cols[:5]}...")
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Set timestamp as index for grouping
    df = df.set_index('timestamp')
    
    # Get metadata columns
    meta_cols = ['building_id', 'Zone', 'variable_name', 'category', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    print(f"Aggregating to monthly using sum method...")
    
    # Group by month and sum (appropriate for energy data)
    agg_df = df.groupby(pd.Grouper(freq='M'))[value_cols].sum()
    
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
    
    print(f"Aggregated data shape: {result_df.shape}")
    print(f"Result columns: {result_df.columns.tolist()}")
    
    # Save the result
    result_df.to_parquet(monthly_file, index=False)
    print(f"Saved aggregated monthly file: {monthly_file}")
    
    # Also create a "from_daily" version
    monthly_from_daily_file = comparisons_dir / 'var_electricity_facility_na_monthly_from_daily_b4136733.parquet'
    result_df.to_parquet(monthly_from_daily_file, index=False)
    print(f"Saved aggregated monthly from daily file: {monthly_from_daily_file}")
    
    return result_df

if __name__ == "__main__":
    job_output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/c7312eaf-a1fc-406e-a1c8-191081756e79"
    result = aggregate_electricity_to_monthly(job_output_dir)
    print("\nDone!")