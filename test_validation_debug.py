#!/usr/bin/env python3
"""Debug validation mapping issues"""

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

# Create validator
validator = SmartValidationWrapper(parsed_data_path, real_data_path, config)

# Test specific mapping
real_var = "Zone Air System Sensible Heating Energy"
sim_vars = ["Heating:EnergyTransfer", "Cooling:EnergyTransfer", "Electricity:Facility"]

print("Testing semantic matching for heating variable:")
print(f"Real variable: {real_var}")
print(f"Normalized: {validator._normalize_variable_name(real_var)}")

# Try to find match
match = validator._find_semantic_match(real_var, sim_vars)
if match:
    print(f"\nFound match: {match.sim_var} (confidence: {match.confidence:.3f})")
else:
    print("\nNo match found!")

# Test confidence calculation directly
print("\nTesting confidence calculation:")
real_norm = validator._normalize_variable_name(real_var)
for sim_var in sim_vars:
    sim_norm = validator._normalize_variable_name(sim_var)
    conf = validator._calculate_match_confidence(real_norm, sim_norm)
    print(f"  {real_var} vs {sim_var}")
    print(f"    Normalized: {real_norm} vs {sim_norm}")
    print(f"    Confidence: {conf:.3f}")