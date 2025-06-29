#!/usr/bin/env python3
"""
Debug outputs structure
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor

job_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/38eb2e7b-709d-43ec-9635-18a7288d7540")

# Extract data
extractor = SurrogateDataExtractor(job_dir)
extracted_data = extractor.extract_all()

# Check comparison outputs
print("Comparison outputs keys:")
comparison_outputs = extracted_data.get('comparison_outputs', {})
for key in sorted(comparison_outputs.keys()):
    print(f"  {key}")

# Check first comparison output structure
if comparison_outputs:
    first_key = list(comparison_outputs.keys())[0]
    first_df = comparison_outputs[first_key]
    print(f"\nExample output ({first_key}):")
    print(f"  Shape: {first_df.shape}")
    print(f"  Columns: {list(first_df.columns)}")
    print(f"  First few rows:")
    print(first_df.head())

# Check comparison metadata
print("\nComparison metadata:")
metadata = extracted_data.get('comparison_metadata', None)
if metadata is not None:
    print(f"  Shape: {metadata.shape}")
    print(f"  Columns: {list(metadata.columns)}")
    print(metadata.head(10))