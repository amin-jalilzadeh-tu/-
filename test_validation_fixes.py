#!/usr/bin/env python3
"""Test the validation fixes"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from validation.smart_validation_wrapper import SmartValidationWrapper

# Test configuration
config = {
    'target_frequency': 'daily',
    'variables_to_validate': ['Electricity', 'Heating', 'Cooling'],
    'show_mappings': True,
    'cvrmse_threshold': 30,
    'nmbe_threshold': 10
}

# Paths
parsed_data_path = '/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a/parsed_modified_results'
real_data_path = '/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_parsed_format_daily_4136733.csv'

print("Testing validation fixes...")
print("="*60)

# Create validator
validator = SmartValidationWrapper(parsed_data_path, real_data_path, config)

# Test normalization function
print("\n1. Testing variable name normalization:")
test_vars = [
    "Electricity:Facility [J](Hourly)",
    "Zone Air System Sensible Heating Energy",
    "Zone Air System Sensible Cooling Energy",
    "electricity_facility",
    "heating_energytransfer",
    "cooling_energytransfer"
]

for var in test_vars:
    normalized = validator._normalize_variable_name(var)
    print(f"  {var:45} -> {normalized}")

# Test discovery
print("\n2. Testing data discovery:")
discovery = validator.discover_available_data()
print(f"  Found {len(discovery.get('comparison_files', {}))} comparison files")
if discovery.get('comparison_files'):
    # Show first few files
    for name, info in list(discovery['comparison_files'].items())[:3]:
        print(f"    - {info['variable']} ({info['frequency']})")

# Test loading comparison data
print("\n3. Testing comparison data loading:")
from validation.smart_validation_wrapper import pd
if discovery.get('comparison_files'):
    # Load one file to check variable names
    first_file = list(discovery['comparison_files'].values())[0]
    df = pd.read_parquet(first_file['file'])
    print(f"  Loaded {first_file['file'].split('/')[-1]}")
    print(f"  Variable name in file: {df['variable_name'].iloc[0] if 'variable_name' in df.columns else 'N/A'}")

# Test variable mapping
print("\n4. Testing variable mapping:")
real_vars = [
    "Electricity:Facility [J](Hourly)",
    "Zone Air System Sensible Heating Energy", 
    "Zone Air System Sensible Cooling Energy"
]
sim_vars = [
    "Electricity:Facility",
    "Heating:EnergyTransfer",
    "Cooling:EnergyTransfer"
]

mappings = validator.create_variable_mappings(real_vars, sim_vars)
print(f"  Created {len(mappings)} mappings:")
for mapping in mappings:
    print(f"    {mapping.real_var:45} -> {mapping.sim_var:30} (confidence: {mapping.confidence:.2f}, type: {mapping.match_type})")

print("\n" + "="*60)
print("Test complete!")