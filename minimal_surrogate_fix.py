#!/usr/bin/env python3
"""
Minimal fix for the surrogate modeling error.
This creates a fixed version of the problematic method.
"""

# Save this as a fixed version of get_summary_statistics
FIXED_GET_SUMMARY_STATISTICS = '''
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics of extracted data.
        """
        summary = {
            'extraction_timestamp': datetime.now().isoformat(),
            'data_sources': {}
        }
        
        for key, data in self.data.items():
            # Handle dictionaries (like comparison_outputs)
            if isinstance(data, dict):
                if data:  # non-empty dict
                    summary['data_sources'][key] = {
                        'type': 'dictionary',
                        'keys': list(data.keys()),
                        'num_entries': len(data)
                    }
                    # Add specific info for comparison_outputs
                    if key == 'comparison_outputs':
                        total_rows = sum(len(df) if hasattr(df, '__len__') else 0 for df in data.values())
                        summary['data_sources'][key]['total_rows'] = total_rows
            # Handle DataFrames
            elif hasattr(data, 'empty') and not data.empty:
                summary['data_sources'][key] = {
                    'type': 'dataframe',
                    'rows': len(data),
                    'columns': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
                }
                
                # Add specific summaries
                if key == 'modifications' and 'param_id' in data.columns:
                    summary['data_sources'][key]['unique_parameters'] = data['param_id'].nunique()
                    if 'category' in data.columns:
                        summary['data_sources'][key]['categories'] = data['category'].unique().tolist()
                elif key == 'sensitivity' and 'sensitivity_score' in data.columns:
                    summary['data_sources'][key]['high_sensitivity_params'] = len(
                        data[data['sensitivity_score'] > data['sensitivity_score'].quantile(0.75)]
                    )
        
        return summary
'''

# Instructions
print("""
DOCKER FIX INSTRUCTIONS:
========================

Since the code is running in a Docker container, you need to apply the fix there.

Option 1: Copy fixed files to container
----------------------------------------
1. First, check if our local fixes work:
   docker cp c_surrogate/surrogate_data_extractor.py <container_name>:/usr/src/app/c_surrogate/surrogate_data_extractor.py
   docker cp c_surrogate/surrogate_data_consolidator.py <container_name>:/usr/src/app/c_surrogate/surrogate_data_consolidator.py

Option 2: Apply patch inside container
--------------------------------------
1. Enter the container:
   docker exec -it <container_name> bash

2. Edit the file directly:
   vi /usr/src/app/c_surrogate/surrogate_data_extractor.py
   
3. Go to line 747 and change:
   FROM: if data is not None and not data.empty:
   TO:   if isinstance(data, pd.DataFrame) and not data.empty:

Option 3: Mount local directory
-------------------------------
1. Stop the container
2. Restart with volume mount:
   docker run -v /mnt/d/Documents/daily/E_Plus_2040_py/c_surrogate:/usr/src/app/c_surrogate ...

Option 4: Add monkey patch to orchestrator
------------------------------------------
Add this to the beginning of orchestrator/surrogate_step.py:

import types
from c_surrogate.surrogate_data_extractor import SurrogateDataExtractor

def fixed_get_summary_statistics(self):
    summary = {'extraction_timestamp': datetime.now().isoformat(), 'data_sources': {}}
    for key, data in self.data.items():
        if isinstance(data, dict) and data:
            summary['data_sources'][key] = {
                'type': 'dictionary',
                'keys': list(data.keys()),
                'num_entries': len(data)
            }
        elif hasattr(data, 'empty') and not data.empty:
            summary['data_sources'][key] = {
                'type': 'dataframe',
                'rows': len(data),
                'columns': len(data.columns),
                'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
            }
    return summary

# Apply the monkey patch
SurrogateDataExtractor.get_summary_statistics = fixed_get_summary_statistics
""")