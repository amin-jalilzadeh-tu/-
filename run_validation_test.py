#!/usr/bin/env python3
"""Run validation with the fixes"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from validation.smart_validation_wrapper import run_smart_validation

# Configuration
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
output_path = '/mnt/d/Documents/daily/E_Plus_2040_py/validation_test_output'

print("Running validation with fixes...")
print("="*60)

# Run validation
results = run_smart_validation(
    parsed_data_path=parsed_data_path,
    real_data_path=real_data_path,
    config=config,
    output_path=output_path,
    validate_variants=True  # Test variant validation
)

print("\n" + "="*60)
print("Validation completed!")

# Print summary
if results and 'summary' in results:
    summary = results['summary']
    if 'status' in summary:
        print(f"Status: {summary['status']}")
    else:
        print(f"Configurations validated: {summary.get('configurations_validated', 0)}")
        print(f"Best configuration: {summary.get('best_configuration', 'Unknown')}")
        print(f"Best CVRMSE: {summary.get('best_cvrmse', 'N/A')}%")