#!/usr/bin/env python3
"""
Create hourly measured data for building 4136733
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_hourly_data():
    """Create hourly measured data from daily data"""
    
    # Read the daily data
    daily_file = "data/test_validation_data/measured_data_energyplus_format_4136733.csv"
    df_daily = pd.read_csv(daily_file)
    
    print(f"Daily data shape: {df_daily.shape}")
    
    # Create hourly data
    hourly_data = []
    
    for _, row in df_daily.iterrows():
        date = pd.to_datetime(row['DateTime'])
        building_id = row['building_id']
        variable = row['Variable']
        daily_value = row['Value']
        units = row['Units']
        
        # Convert variable name to hourly format
        if '[J](Daily)' in variable:
            hourly_var = variable.replace('[J](Daily)', '[J](Hourly)')
        else:
            hourly_var = variable  # Keep as is for temperature, etc.
        
        # Create 24 hourly records for each day
        for hour in range(24):
            hour_time = date + timedelta(hours=hour)
            
            # Distribute values based on variable type
            if 'Energy' in variable or 'Electricity' in variable:
                # Energy: distribute with typical daily profile
                # Define hourly factors
                if 9 <= hour <= 17:
                    hour_factor = 1.5  # Higher during work hours (9 hours)
                elif 6 <= hour <= 8 or 18 <= hour <= 21:
                    hour_factor = 1.2  # Medium during morning/evening (7 hours)
                else:
                    hour_factor = 0.5  # Lower at night (8 hours)
                
                # Calculate normalization factor
                # 9 hours * 1.5 + 7 hours * 1.2 + 8 hours * 0.5 = 13.5 + 8.4 + 4.0 = 25.9
                total_factor = 9 * 1.5 + 7 * 1.2 + 8 * 0.5  # = 25.9
                
                # Calculate hourly value
                hourly_value = daily_value * (hour_factor / total_factor)
            
            elif 'Temperature' in variable:
                # Temperature: add hourly variation
                base_temp = daily_value
                # Cooler at night, warmer during day
                temp_variation = 3 * np.sin((hour - 6) * np.pi / 12) if 6 <= hour <= 18 else -2
                hourly_value = base_temp + temp_variation
            
            else:
                # Default: divide evenly
                hourly_value = daily_value / 24
            
            hourly_data.append({
                'building_id': building_id,
                'DateTime': hour_time.strftime('%Y-%m-%d %H:%M:%S'),
                'Variable': hourly_var,
                'Value': hourly_value,
                'Units': units
            })
    
    # Create DataFrame
    df_hourly = pd.DataFrame(hourly_data)
    
    print(f"\nHourly data shape: {df_hourly.shape}")
    print(f"Variables: {df_hourly['Variable'].unique()}")
    
    # Save full hourly data
    output_file = "data/test_validation_data/measured_data_energyplus_format_4136733_hourly.csv"
    df_hourly.to_csv(output_file, index=False)
    print(f"\nSaved to {output_file}")
    
    # Save a smaller test file (first week)
    test_df = df_hourly[pd.to_datetime(df_hourly['DateTime']) < '2013-01-08']
    test_file = "data/test_validation_data/measured_data_4136733_hourly_test.csv"
    test_df.to_csv(test_file, index=False)
    print(f"Saved test data to {test_file} ({len(test_df)} records)")
    
    # Verify energy totals match
    print("\nVerifying energy totals for January 1st:")
    jan1_daily = df_daily[(df_daily['DateTime'] == '2013-01-01') & 
                          (df_daily['Variable'] == 'Electricity:Facility [J](Daily)')]['Value'].iloc[0]
    jan1_hourly_sum = df_hourly[(pd.to_datetime(df_hourly['DateTime']).dt.date == pd.to_datetime('2013-01-01').date()) & 
                                 (df_hourly['Variable'] == 'Electricity:Facility [J](Hourly)')]['Value'].sum()
    print(f"  Daily value: {jan1_daily:,.0f} J")
    print(f"  Hourly sum: {jan1_hourly_sum:,.0f} J")
    print(f"  Difference: {abs(jan1_daily - jan1_hourly_sum):,.0f} J ({abs(jan1_daily - jan1_hourly_sum)/jan1_daily*100:.2f}%)")


if __name__ == "__main__":
    create_hourly_data()