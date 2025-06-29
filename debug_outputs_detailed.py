#!/usr/bin/env python3
"""
Debug outputs in detail
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor
from c_surrogate.surrogate_data_preprocessor import SurrogateDataPreprocessor
import logging

logging.basicConfig(level=logging.DEBUG)

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

# Now test aggregate outputs manually
print("Testing _aggregate_comparison_outputs manually...")
output_matrix = preprocessor._aggregate_comparison_outputs(aligned_data)
print(f"Output matrix shape: {output_matrix.shape}")
if not output_matrix.empty:
    print(f"Output matrix columns: {list(output_matrix.columns)}")
    print(f"First row:")
    print(output_matrix.iloc[0])