#!/usr/bin/env python3
"""
Update building ID in measured_data_parsed_format_daily.csv from 4136737 to 4136733
"""

import pandas as pd

def update_parsed_format():
    """Update building ID in parsed format file"""
    
    input_file = "data/test_validation_data/measured_data_parsed_format_daily.csv"
    output_file = "data/test_validation_data/measured_data_parsed_format_daily_4136733.csv"
    
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    print(f"Original shape: {df.shape}")
    print(f"Original buildings: {df['building_id'].unique()}")
    
    # Filter to building 4136737 and change to 4136733
    df_filtered = df[df['building_id'] == 4136737].copy()
    df_filtered['building_id'] = 4136733
    
    print(f"\nFiltered shape: {df_filtered.shape}")
    print(f"New building ID: {df_filtered['building_id'].unique()}")
    
    # Save
    df_filtered.to_csv(output_file, index=False)
    print(f"\nSaved to {output_file}")
    
    # Update combined.json to use the new file
    import json
    
    combined_file = "combined.json"
    print(f"\nUpdating {combined_file}...")
    
    with open(combined_file, 'r') as f:
        config = json.load(f)
    
    # Update the real_data_path
    old_path = "data/test_validation_data/measured_data_parsed_format_daily.csv"
    new_path = "data/test_validation_data/measured_data_parsed_format_daily_4136733.csv"
    
    if 'validation' in config and 'stages' in config['validation']:
        if 'baseline' in config['validation']['stages']:
            config['validation']['stages']['baseline']['config']['real_data_path'] = new_path
            print(f"Updated baseline real_data_path to: {new_path}")
        
        if 'modified' in config['validation']['stages']:
            config['validation']['stages']['modified']['config']['real_data_path'] = new_path
            print(f"Updated modified real_data_path to: {new_path}")
    
    # Save updated config
    with open(combined_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\nUpdated {combined_file}")


if __name__ == "__main__":
    update_parsed_format()