#!/usr/bin/env python3
"""
Find electricity keys with variants
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
print("Electricity-related keys:")
for key in sorted(comparison_outputs.keys()):
    if 'electricity' in key or 'facility' in key:
        df = comparison_outputs[key]
        variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
        print(f"  {key}: shape={df.shape}, variant_cols={len(variant_cols)}")
        if variant_cols:
            print(f"    Example variant columns: {variant_cols[:3]}")

# Check metadata
metadata = extracted_data.get('comparison_metadata')
if metadata is not None:
    print("\nElectricity files from metadata:")
    elec_files = metadata[metadata['variable'].str.contains('electricity', case=False)]
    for _, row in elec_files.iterrows():
        print(f"  {row['variable']}_{row['aggregation']}_{row['time_period']}: n_records={row['n_records']}")