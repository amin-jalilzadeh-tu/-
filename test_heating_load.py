#!/usr/bin/env python3
"""Test heating variable loading specifically"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from validation.smart_validation_wrapper import SmartValidationWrapper

# Test configuration
config = {
    'target_frequency': 'daily',
    'variables_to_validate': ['Heating'],  # Only test heating
    'show_mappings': True,
    'logging': {'level': 'DEBUG'}  # Enable debug logging
}

# Paths
parsed_data_path = '/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results'
real_data_path = '/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_parsed_format_daily_4136733.csv'

print("Testing heating variable loading...")
print("="*60)

# Create validator
validator = SmartValidationWrapper(parsed_data_path, real_data_path, config)

# Test discovery
discovery = validator.discover_available_data()

# Load simulation data  
sim_df = validator._load_from_comparison_files(discovery, 'daily', variant_id=None)

print("\nLoaded simulation data:")
print(f"  Total rows: {len(sim_df)}")
print(f"  Variables: {sim_df['Variable'].unique() if not sim_df.empty else 'None'}")

# Check what heating variables are available
if not sim_df.empty:
    heating_vars = sim_df[sim_df['Variable'].str.contains('Heating', case=False, na=False)]['Variable'].unique()
    print(f"\nHeating variables found: {heating_vars}")