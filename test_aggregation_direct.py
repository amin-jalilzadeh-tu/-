#!/usr/bin/env python3
"""
Test aggregation directly without imports
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
from collections import defaultdict

def detect_frequency_from_columns(df):
    """Detect frequency from date column names"""
    # Get all potential date columns
    date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}', str(col))]
    
    if not date_cols:
        # Try monthly format (YYYY-MM)
        date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}$', str(col))]
        if date_cols:
            return 'monthly'
        return 'unknown'
    
    # If we have at least 2 date columns, check the interval
    if len(date_cols) >= 2:
        try:
            # Parse first two dates
            date1 = pd.to_datetime(date_cols[0])
            date2 = pd.to_datetime(date_cols[1])
            diff = (date2 - date1).days
            
            if diff == 1:
                return 'daily'
            elif 28 <= diff <= 31:
                return 'monthly'
            elif diff == 7:
                return 'weekly'
            elif diff == 365 or diff == 366:
                return 'yearly'
        except:
            pass
    
    # Check format patterns
    if len(date_cols[0]) == 10:  # YYYY-MM-DD
        return 'daily'
    
    return 'unknown'


def aggregate_wide_to_monthly(df):
    """Aggregate wide format daily data to monthly"""
    # Get metadata columns
    meta_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Get date columns
    date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}$', str(col))]
    
    if not date_cols:
        print("No daily date columns found")
        return df
    
    # Group columns by month
    month_groups = defaultdict(list)
    for col in date_cols:
        month_key = col[:7]  # YYYY-MM
        month_groups[month_key].append(col)
    
    # Create result dataframe
    result_df = df[meta_cols].copy()
    
    # Aggregate each row
    for idx, row in df.iterrows():
        var_name = row.get('VariableName', '')
        
        # Determine aggregation method
        if 'energy' in var_name.lower() or 'consumption' in var_name.lower():
            agg_method = 'sum'
        elif 'temperature' in var_name.lower() or 'humidity' in var_name.lower():
            agg_method = 'mean'
        else:
            agg_method = 'mean'
        
        # Aggregate each month
        for month, day_cols in month_groups.items():
            values = row[day_cols].values
            # Remove NaN values
            values = values[~pd.isna(values)]
            
            if len(values) > 0:
                if agg_method == 'sum':
                    result_df.loc[idx, month] = np.sum(values)
                else:
                    result_df.loc[idx, month] = np.mean(values)
            else:
                result_df.loc[idx, month] = np.nan
    
    return result_df


def test_aggregation():
    """Test aggregation on real data"""
    print("Testing Direct Aggregation")
    print("=" * 60)
    
    # Test with base data
    base_file = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_data/timeseries/base_all_daily.parquet")
    
    if base_file.exists():
        print(f"\nReading: {base_file.name}")
        df = pd.read_parquet(base_file)
        
        print(f"Shape: {df.shape}")
        print(f"Columns: {len(df.columns)} total")
        meta_cols = [col for col in df.columns if not re.match(r'\d{4}-\d{2}', str(col))]
        print(f"Metadata columns: {meta_cols}")
        
        # Detect frequency
        freq = detect_frequency_from_columns(df)
        print(f"Detected frequency: {freq}")
        
        # Get date columns
        date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}$', str(col))]
        print(f"Date columns: {len(date_cols)} ({date_cols[0]} to {date_cols[-1]})")
        
        # Test aggregation
        print(f"\nAggregating {freq} to monthly...")
        monthly_df = aggregate_wide_to_monthly(df)
        
        # Check results
        month_cols = [col for col in monthly_df.columns if re.match(r'\d{4}-\d{2}$', str(col))]
        print(f"Result shape: {monthly_df.shape}")
        print(f"Month columns: {len(month_cols)} ({month_cols[0]} to {month_cols[-1]})")
        
        # Save test output
        output_file = base_file.parent / "base_all_monthly_test.parquet"
        monthly_df.to_parquet(output_file, index=False)
        print(f"\nSaved test output to: {output_file.name}")
        
        # Check values
        print(f"\nSample values for {df['VariableName'].iloc[0]}:")
        print(f"Daily sum (Jan): {df[date_cols[:31]].iloc[0].sum():.2f}")
        print(f"Monthly value (Jan): {monthly_df[month_cols[0]].iloc[0]:.2f}")
        
    else:
        print(f"File not found: {base_file}")
    
    # Test with comparison data
    comp_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_modified_results/comparisons")
    if comp_dir.exists():
        daily_files = list(comp_dir.glob('*_daily_*.parquet'))
        if daily_files:
            print(f"\n\nTesting comparison file aggregation...")
            comp_file = daily_files[0]
            print(f"Reading: {comp_file.name}")
            
            comp_df = pd.read_parquet(comp_file)
            print(f"Shape: {comp_df.shape}")
            print(f"Columns: {comp_df.columns.tolist()}")
            
            if 'timestamp' in comp_df.columns:
                # This is long format
                print("Format: Long (timestamps as rows)")
                # Check if can aggregate
                comp_df['timestamp'] = pd.to_datetime(comp_df['timestamp'], unit='ms')
                print(f"Date range: {comp_df['timestamp'].min()} to {comp_df['timestamp'].max()}")


if __name__ == "__main__":
    test_aggregation()