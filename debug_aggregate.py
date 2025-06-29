#!/usr/bin/env python3
"""
Debug aggregate outputs
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor

job_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/38eb2e7b-709d-43ec-9635-18a7288d7540")

# Extract data
extractor = SurrogateDataExtractor(job_dir)
extracted_data = extractor.extract_all()

# Check what's in the parameter matrix after preprocessing
config = {
    'aggregation_level': 'building',
    'use_sensitivity_filter': True,
    'target_variables': [
        'heating_energytransfer_na',
        'cooling_energytransfer_na'
    ]
}

preprocessor = SurrogateDataPreprocessor(extracted_data, config)
aligned_data = preprocessor.align_parameters_with_outputs()
aligned_data = preprocessor.filter_by_sensitivity(aligned_data)
param_matrix = preprocessor.create_parameter_matrix(aligned_data)

print("Param matrix variant_id values:")
print(param_matrix['variant_id'].unique())

# Try aggregate outputs with debug
comparison_outputs = extracted_data.get('comparison_outputs', {})
target_variables = config['target_variables']

print("\nChecking target variables:")
for target_var in target_variables:
    print(f"\n{target_var}:")
    if target_var in comparison_outputs:
        df = comparison_outputs[target_var]
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {list(df.columns)}")
        
        # Check for variant_0_value column
        if 'variant_0_value' in df.columns:
            print(f"  variant_0_value exists: {df['variant_0_value'].notna().sum()} non-null values")
        else:
            print("  No variant_0_value column found")