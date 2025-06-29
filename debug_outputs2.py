#!/usr/bin/env python3
"""
Debug why outputs aren't being created
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
        'electricity_facility_na',
        'heating_energytransfer_na', 
        'cooling_energytransfer_na'
    ]
}

preprocessor = SurrogateDataPreprocessor(extracted_data, config)
aligned_data = preprocessor.align_parameters_with_outputs()
aligned_data = preprocessor.filter_by_sensitivity(aligned_data)
param_matrix = preprocessor.create_parameter_matrix(aligned_data)

print("Param matrix info:")
print(f"  Shape: {param_matrix.shape}")
print(f"  Columns: {list(param_matrix.columns)[:10]}...")
print(f"  First few rows:")
print(param_matrix.head())

# Check comparison outputs
comparison_outputs = extracted_data.get('comparison_outputs', {})
print("\nComparison outputs available:")
for key in comparison_outputs.keys():
    df = comparison_outputs[key]
    print(f"  {key}: shape={df.shape}")
    
# Check specific output
if 'electricity_facility_na' in comparison_outputs:
    df = comparison_outputs['electricity_facility_na']
    print(f"\nelectricity_facility_na columns: {list(df.columns)}")
    print(f"First row:")
    print(df.iloc[0])