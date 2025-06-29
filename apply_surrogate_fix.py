#!/usr/bin/env python3
"""
Quick fix script for surrogate modeling issues.
This script directly modifies the problematic methods.
"""

import os
import sys
from pathlib import Path

def fix_surrogate_data_extractor():
    """Apply fixes to surrogate_data_extractor.py"""
    
    file_path = Path("c_surrogate/surrogate_data_extractor.py")
    
    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return False
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Update get_summary_statistics method
    old_code1 = """        for key, data in self.data.items():
            if data is not None and not data.empty:
                summary['data_sources'][key] = {
                    'type': 'dataframe',
                    'rows': len(data),
                    'columns': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
                }"""
    
    new_code1 = """        for key, data in self.data.items():
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
            elif isinstance(data, pd.DataFrame) and not data.empty:
                summary['data_sources'][key] = {
                    'type': 'dataframe',
                    'rows': len(data),
                    'columns': len(data.columns),
                    'memory_usage_mb': data.memory_usage(deep=True).sum() / 1024 / 1024
                }"""
    
    # Fix 2: Update extract_all method's tracker section
    old_code2 = """            # Export data quality reports
            for name, df in self.data.items():
                if df is not None and not df.empty:
                    quality_report = self.tracker.generate_data_quality_report(df, name)
                    quality_path = self.tracker.dirs["extraction"] / f"quality_{name}.json"
                    with open(quality_path, "w") as f:
                        json.dump(quality_report, f, indent=2)"""
    
    new_code2 = """            # Export data quality reports
            for name, data in self.data.items():
                # Only generate quality reports for DataFrames
                if isinstance(data, pd.DataFrame) and not data.empty:
                    quality_report = self.tracker.generate_data_quality_report(data, name)
                    quality_path = self.tracker.dirs["extraction"] / f"quality_{name}.json"
                    with open(quality_path, "w") as f:
                        json.dump(quality_report, f, indent=2)
                elif isinstance(data, dict) and data:
                    # For dictionaries, log summary info
                    logger.info(f"[Extractor] {name} contains {len(data)} entries (dictionary)")"""
    
    # Apply fixes
    content = content.replace(old_code1, new_code1)
    content = content.replace(old_code2, new_code2)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")
    return True


def add_target_variable_to_config():
    """Add target_variable to surrogate config if missing"""
    
    # Common config locations
    config_paths = [
        "user_configs/*/main_config.json",
        "configs/main_config.json",
        "config.json"
    ]
    
    import glob
    import json
    
    for pattern in config_paths:
        for config_file in glob.glob(pattern):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Check if surrogate config exists and needs target_variable
                if 'surrogate' in config and 'target_variable' not in config['surrogate']:
                    config['surrogate']['target_variable'] = [
                        'electricity_facility_na_yearly_from_monthly',
                        'heating_energytransfer_na_yearly_from_monthly',
                        'cooling_energytransfer_na_yearly_from_monthly'
                    ]
                    
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    print(f"Added target_variable to {config_file}")
                    
            except Exception as e:
                print(f"Could not process {config_file}: {e}")


def main():
    """Main function"""
    print("Applying surrogate modeling fixes...")
    
    # Fix the extractor
    if fix_surrogate_data_extractor():
        print("✓ Fixed surrogate_data_extractor.py")
    else:
        print("✗ Failed to fix surrogate_data_extractor.py")
    
    # Add target variables to config
    add_target_variable_to_config()
    
    print("\nFixes applied!")
    print("\nIf running in Docker, you may need to:")
    print("1. Copy the fixed files to the container:")
    print("   docker cp c_surrogate/surrogate_data_extractor.py <container>:/usr/src/app/c_surrogate/")
    print("2. Or rebuild the Docker image")
    print("3. Or mount the local directory as a volume")


if __name__ == "__main__":
    main()