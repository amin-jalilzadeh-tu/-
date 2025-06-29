#!/usr/bin/env python3
"""
Debug script to understand the data structure
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

# Check modifications_wide columns
print("modifications_wide columns:")
print(list(extracted_data['modifications_wide'].columns))
print("\nFirst few rows:")
print(extracted_data['modifications_wide'].head())

# Initialize preprocessor
config = {
    'aggregation_level': 'building',
    'use_sensitivity_filter': False,  # Disable for now
    'normalize_features': True,
    'target_variables': [
        'Electricity:Facility [J](Hourly)',
        'Heating:EnergyTransfer [J](Hourly)', 
        'Cooling:EnergyTransfer [J](Hourly)'
    ]
}

preprocessor = SurrogateDataPreprocessor(extracted_data, config)

# Try to align
aligned_data = preprocessor.align_parameters_with_outputs()
print("\nAligned data columns:")
print(list(aligned_data.columns))