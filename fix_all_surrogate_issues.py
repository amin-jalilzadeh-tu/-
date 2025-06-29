#!/usr/bin/env python3
"""
Comprehensive fix for all surrogate modeling issues.
This script fixes the type checking issues in multiple files.
"""

import os
import re
from pathlib import Path

def fix_file(file_path, fixes):
    """Apply fixes to a file."""
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found")
        return False
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    for old_pattern, new_pattern in fixes:
        content = content.replace(old_pattern, new_pattern)
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {file_path}")
        return True
    else:
        print(f"- No changes needed in {file_path}")
        return False

def main():
    """Apply all fixes."""
    print("Applying comprehensive surrogate modeling fixes...\n")
    
    # Fix 1: surrogate_data_extractor.py - get_summary_statistics method
    fixes_extractor = [
        (
            """            if data is not None and not data.empty:
                summary['data_sources'][key] = {
                    'type': 'dataframe',
                    'rows': len(data),
                    'columns': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
                }""",
            """            # Handle dictionaries (like comparison_outputs)
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
                }"""
        ),
        (
            """                if df is not None and not df.empty:
                    quality_report = self.tracker.generate_data_quality_report(df, name)""",
            """                if isinstance(df, pd.DataFrame) and not df.empty:
                    quality_report = self.tracker.generate_data_quality_report(df, name)"""
        )
    ]
    
    # Fix 2: surrogate_pipeline_tracker.py - export_input_data method
    fixes_tracker = [
        (
            """        for name, df in data_dict.items():
            if df is not None and not df.empty:""",
            """        for name, data in data_dict.items():
            # Handle DataFrames
            if hasattr(data, 'empty') and not data.empty:
                df = data"""
        ),
        (
            """            if df is not None and not df.empty:
                # Save parquet
                file_path = step_dir / f"{name}.parquet"
                df.to_parquet(file_path, index=False)""",
            """            # Handle DataFrames
            if hasattr(data, 'empty') and not data.empty:
                df = data
                # Save parquet
                file_path = step_dir / f"{name}.parquet"
                df.to_parquet(file_path, index=False)"""
        )
    ]
    
    # Alternative fix for tracker if above doesn't work
    fixes_tracker_alt = [
        (
            """            if df is not None and not df.empty:""",
            """            if isinstance(df, pd.DataFrame) and not df.empty:"""
        )
    ]
    
    # Apply fixes
    fix_file('c_surrogate/surrogate_data_extractor.py', fixes_extractor)
    fix_file('c_surrogate/surrogate_pipeline_tracker.py', fixes_tracker)
    
    # Try alternative fix if needed
    fix_file('c_surrogate/surrogate_pipeline_tracker.py', fixes_tracker_alt)
    
    print("\n" + "="*60)
    print("DOCKER DEPLOYMENT INSTRUCTIONS:")
    print("="*60)
    print("\n1. Copy fixed files to Docker container:")
    print("   docker cp c_surrogate/surrogate_data_extractor.py <container>:/usr/src/app/c_surrogate/")
    print("   docker cp c_surrogate/surrogate_pipeline_tracker.py <container>:/usr/src/app/c_surrogate/")
    print("   docker cp c_surrogate/surrogate_data_consolidator.py <container>:/usr/src/app/c_surrogate/")
    print("   docker cp c_surrogate/surrogate_data_preprocessor.py <container>:/usr/src/app/c_surrogate/")
    print("   docker cp c_surrogate/unified_surrogate.py <container>:/usr/src/app/c_surrogate/")
    
    print("\n2. Or rebuild the Docker image:")
    print("   docker-compose build")
    print("   docker-compose up -d")
    
    print("\n3. Add target_variable to your config if missing:")
    print('   "surrogate": {')
    print('       "enabled": true,')
    print('       "target_variable": [')
    print('           "electricity_facility_na_yearly_from_monthly",')
    print('           "heating_energytransfer_na_yearly_from_monthly",')
    print('           "cooling_energytransfer_na_yearly_from_monthly"')
    print('       ]')
    print('   }')

if __name__ == "__main__":
    main()