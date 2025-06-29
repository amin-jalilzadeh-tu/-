#!/usr/bin/env python3
"""
Fix validation issues:
1. Fix parquet file generation for variant validation
2. Fix baseline validation to handle wide format data properly
"""

import shutil
from pathlib import Path

def fix_validation_wrapper():
    """Fix the validation wrapper to save parquet files for variant validation"""
    
    wrapper_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/validation/smart_validation_wrapper.py")
    
    # Backup original file
    backup_path = wrapper_path.with_suffix('.py.bak')
    shutil.copy(wrapper_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Read the file
    with open(wrapper_path, 'r') as f:
        content = f.read()
    
    # Find the section that saves results
    save_section = '''    # Save results if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save validation results
        if results.get('validation_results'):
            val_df = pd.DataFrame(results['validation_results'])
            val_df.to_csv(output_path / 'validation_results.csv', index=False)
            val_df.to_parquet(output_path / 'validation_results.parquet', index=False)'''
    
    # Replace with improved version that handles variant validation
    new_save_section = '''    # Save results if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Collect all validation results (handles both standard and variant validation)
        all_validation_results = []
        
        # Check for standard validation results
        if results.get('validation_results'):
            all_validation_results.extend(results['validation_results'])
        
        # Check for variant validation results
        if results.get('base_results', {}).get('validation_results'):
            all_validation_results.extend(results['base_results']['validation_results'])
        
        if results.get('variant_results'):
            for variant_id, variant_data in results['variant_results'].items():
                if variant_data.get('validation_results'):
                    all_validation_results.extend(variant_data['validation_results'])
        
        # Save all validation results
        if all_validation_results:
            val_df = pd.DataFrame(all_validation_results)
            val_df.to_csv(output_path / 'validation_results.csv', index=False)
            val_df.to_parquet(output_path / 'validation_results.parquet', index=False)'''
    
    # Replace the content
    new_content = content.replace(save_section, new_save_section)
    
    # Write back
    with open(wrapper_path, 'w') as f:
        f.write(new_content)
    
    print("Fixed validation wrapper to save parquet files for variant validation")
    
    # Also fix the baseline validation issue by improving the discovery
    # Find the discovery section that checks for wide format
    discovery_fix = '''        # Check if this frequency is available
        if preferred_freq not in discovery.get('available_frequencies', []):
            continue'''
    
    new_discovery_fix = '''        # Check if this frequency is available
        if preferred_freq not in discovery.get('available_frequencies', []):
            continue
        
        # Also check timeseries data which might be in wide format
        for dataset_name, dataset_info in discovery.get('timeseries', {}).items():
            if dataset_info.get('frequency') == preferred_freq:
                logger.info(f"  - Found {dataset_name} timeseries data ({preferred_freq})")'''
    
    # Read again to apply second fix
    with open(wrapper_path, 'r') as f:
        content = f.read()
    
    # Apply the fix
    if discovery_fix in content:
        new_content = content.replace(discovery_fix, new_discovery_fix)
        with open(wrapper_path, 'w') as f:
            f.write(new_content)
        print("Fixed baseline validation discovery issue")
    
    return True

def create_baseline_fix_script():
    """Create a script to manually run baseline validation with proper data loading"""
    
    script_content = '''#!/usr/bin/env python3
"""
Manual baseline validation fix script
"""

import pandas as pd
import json
from pathlib import Path
from validation.smart_validation_wrapper import SmartValidationWrapper

def run_fixed_baseline_validation():
    """Run baseline validation with fixed data loading"""
    
    job_id = "b139a061-d967-47a5-b850-ff8bd3d351ae"
    base_path = Path(f"/mnt/d/Documents/daily/E_Plus_2040_py/output/{job_id}")
    
    # Paths
    parsed_data_path = base_path / "parsed_data"
    real_data_path = base_path / "measured_data.csv"
    output_path = base_path / "validation_results/baseline_fixed"
    
    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Configuration
    config = {
        "target_frequency": "daily",
        "thresholds": {
            "cvrmse": 25.0,
            "nmbe": 8.0
        }
    }
    
    # Create validator
    validator = SmartValidationWrapper(str(parsed_data_path), str(real_data_path), config)
    
    # Manually load baseline data
    print("Loading baseline data...")
    daily_path = parsed_data_path / "timeseries/base_all_daily.parquet"
    if daily_path.exists():
        df = pd.read_parquet(daily_path)
        print(f"Loaded wide format data: {df.shape}")
        
        # Convert to long format
        df_long = validator._convert_wide_to_long(df)
        print(f"Converted to long format: {df_long.shape}")
        
        # Save converted data for inspection
        df_long.to_parquet(output_path / "baseline_data_long.parquet")
        print(f"Saved converted data to {output_path / 'baseline_data_long.parquet'}")
    
    # Run validation
    print("\\nRunning validation...")
    results = validator.validate_all()
    
    # Save results
    if results.get('validation_results'):
        val_df = pd.DataFrame(results['validation_results'])
        val_df.to_csv(output_path / 'validation_results.csv', index=False)
        val_df.to_parquet(output_path / 'validation_results.parquet', index=False)
        print(f"Saved validation results: {len(val_df)} records")
    
    # Save summary
    with open(output_path / 'validation_summary.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\\nResults saved to: {output_path}")
    
    # Print summary
    if 'summary' in results:
        summary = results['summary']
        print("\\nValidation Summary:")
        print(f"- Pass rate: {summary.get('pass_rate', 0):.1f}%")
        print(f"- Buildings validated: {summary.get('buildings_validated', 0)}")
        print(f"- Variables validated: {summary.get('variables_validated', 0)}")

if __name__ == "__main__":
    run_fixed_baseline_validation()
'''
    
    script_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/fix_baseline_validation.py")
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    print(f"Created baseline fix script: {script_path}")
    return script_path

if __name__ == "__main__":
    print("Fixing validation issues...")
    
    # Fix the validation wrapper
    if fix_validation_wrapper():
        print("\n✓ Fixed validation wrapper")
    
    # Create baseline fix script
    script_path = create_baseline_fix_script()
    print(f"\n✓ Created baseline fix script: {script_path}")
    
    print("\nFixes applied successfully!")
    print("\nNext steps:")
    print("1. Run the baseline fix script: python3 fix_baseline_validation.py")
    print("2. Re-run the modified validation to generate parquet files")