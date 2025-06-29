#!/usr/bin/env python3
"""
Update building IDs in measured data from 4136737/4136738 to 4136733
"""

import pandas as pd
import sys

def update_building_ids():
    """Update building IDs to match simulation data"""
    
    # Read the original file
    input_file = "data/test_validation_data/measured_data_energyplus_format.csv"
    output_file = "data/test_validation_data/measured_data_energyplus_format_4136733.csv"
    
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    print(f"Original shape: {df.shape}")
    print(f"Original buildings: {df['building_id'].unique()}")
    
    # Filter to only keep data from building 4136737 (as representative)
    # and change its ID to 4136733
    df_filtered = df[df['building_id'] == 4136737].copy()
    df_filtered['building_id'] = 4136733
    
    print(f"\nFiltered shape: {df_filtered.shape}")
    print(f"New building ID: {df_filtered['building_id'].unique()}")
    
    # Check variables
    print(f"\nVariables in data:")
    for var in df_filtered['Variable'].unique():
        count = len(df_filtered[df_filtered['Variable'] == var])
        print(f"  - {var}: {count} records")
    
    # Save the updated file
    df_filtered.to_csv(output_file, index=False)
    print(f"\nSaved to {output_file}")
    
    # Also create a smaller test file with just January data
    jan_data = df_filtered[pd.to_datetime(df_filtered['DateTime']).dt.month == 1]
    test_file = "data/test_validation_data/measured_data_4136733_jan.csv"
    jan_data.to_csv(test_file, index=False)
    print(f"Saved January test data to {test_file} ({len(jan_data)} records)")
    
    return output_file


if __name__ == "__main__":
    update_building_ids()