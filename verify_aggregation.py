#!/usr/bin/env python3
"""
Verify aggregation calculations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re

def verify_aggregation():
    """Verify the aggregation calculations"""
    base_file = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_data/timeseries/base_all_daily.parquet")
    monthly_file = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_data/timeseries/base_all_monthly.parquet")
    
    print("Verifying Aggregation Calculations")
    print("=" * 60)
    
    # Read daily data
    daily_df = pd.read_parquet(base_file)
    print(f"\nDaily data shape: {daily_df.shape}")
    
    # Read existing monthly data
    if monthly_file.exists():
        monthly_df = pd.read_parquet(monthly_file)
        print(f"Monthly data shape: {monthly_df.shape}")
        
        # Get January columns
        jan_daily_cols = [col for col in daily_df.columns if str(col).startswith('2013-01-')]
        jan_monthly_col = '2013-01'
        
        print(f"\nJanuary daily columns: {len(jan_daily_cols)}")
        
        # Check first row (Electricity:Facility)
        if daily_df['VariableName'].iloc[0] == 'Electricity:Facility':
            print(f"\nElectricity:Facility for building {daily_df['building_id'].iloc[0]}:")
            
            # Daily values
            jan_daily_values = daily_df[jan_daily_cols].iloc[0].values
            print(f"Daily values (first 5): {jan_daily_values[:5]}")
            print(f"Daily sum: {np.sum(jan_daily_values):,.0f} J")
            print(f"Daily mean: {np.mean(jan_daily_values):,.0f} J")
            
            # Monthly value
            if jan_monthly_col in monthly_df.columns:
                monthly_val = monthly_df[monthly_df['VariableName'] == 'Electricity:Facility'][jan_monthly_col].iloc[0]
                print(f"Monthly value: {monthly_val:,.0f} J")
                
                # Check if it's sum or mean
                if abs(monthly_val - np.sum(jan_daily_values)) < 1:
                    print("→ Monthly is SUM of daily (correct for energy)")
                elif abs(monthly_val - np.mean(jan_daily_values)) < 1:
                    print("→ Monthly is MEAN of daily (incorrect for energy)")
            
        # Check temperature variable if exists
        temp_vars = daily_df[daily_df['VariableName'].str.contains('Temperature', na=False)]
        if not temp_vars.empty:
            print(f"\n{temp_vars['VariableName'].iloc[0]}:")
            temp_daily = temp_vars[jan_daily_cols].iloc[0].values
            print(f"Daily mean: {np.mean(temp_daily):.2f}")
            
            if jan_monthly_col in monthly_df.columns:
                temp_monthly = monthly_df[monthly_df['VariableName'] == temp_vars['VariableName'].iloc[0]]
                if not temp_monthly.empty:
                    monthly_val = temp_monthly[jan_monthly_col].iloc[0]
                    print(f"Monthly value: {monthly_val:.2f}")
                    
                    if abs(monthly_val - np.mean(temp_daily)) < 0.1:
                        print("→ Monthly is MEAN of daily (correct for temperature)")
    
    # Check comparison data aggregation
    print("\n\nChecking comparison data...")
    comp_file = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_modified_results/comparisons/var_electricity_facility_na_daily_b4136733.parquet")
    
    if comp_file.exists():
        comp_df = pd.read_parquet(comp_file)
        comp_df['timestamp'] = pd.to_datetime(comp_df['timestamp'], unit='ms')
        
        # Get January data
        jan_data = comp_df[comp_df['timestamp'].dt.month == 1]
        print(f"\nJanuary daily records: {len(jan_data)}")
        print(f"Base value sum: {jan_data['base_value'].sum():,.0f} J")
        print(f"Base value mean: {jan_data['base_value'].mean():,.0f} J")
        
        # Compare with wide format
        print(f"\nComparing formats:")
        print(f"Wide format (base_all_daily) Jan sum: {np.sum(jan_daily_values):,.0f} J")
        print(f"Long format (comparison) Jan sum: {jan_data['base_value'].sum():,.0f} J")
        print(f"Difference: {abs(np.sum(jan_daily_values) - jan_data['base_value'].sum()):,.0f} J")


if __name__ == "__main__":
    verify_aggregation()