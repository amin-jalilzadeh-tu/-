#!/usr/bin/env python3
"""
Debug comparison output keys
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
comparison_outputs = extracted_data.get('comparison_outputs', {})
print("All comparison output keys:")
for key in sorted(comparison_outputs.keys()):
    df = comparison_outputs[key]
    has_variants = any(col.startswith('variant_') and col.endswith('_value') for col in df.columns)
    print(f"  {key}: has_variant_cols={has_variants}, shape={df.shape}")