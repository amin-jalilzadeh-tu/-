#!/usr/bin/env python3
"""
Test aggregation fixes with real data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from validation.smart_validation_wrapper import SmartValidationWrapper

def test_with_real_data():
    """Test with actual output data"""
    
    # Use the real output path provided by user - point to parsed_data directory
    output_path = "/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_data"
    real_data_path = "/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_4136733.csv"
    
    config = {
        'variables_to_validate': ['electricity'],
        'aggregation': {
            'target_frequency': 'daily',
            'methods': {
                'energy': 'sum',
                'temperature': 'mean'
            }
        },
        'logging': {
            'level': 'INFO',
            'show_mappings': True,
            'show_aggregations': True,
            'show_unit_conversions': True
        }
    }
    
    print("Testing with real data from:", output_path)
    print("=" * 60)
    
    # Initialize wrapper
    wrapper = SmartValidationWrapper(
        parsed_data_path=output_path,
        real_data_path=real_data_path,
        config=config
    )
    
    # Test discovery
    print("\n=== Discovery Phase ===")
    discovery = wrapper.discover_available_data()
    
    print(f"\nBase datasets found: {len(discovery.get('base_datasets', {}))}")
    for name, info in discovery.get('base_datasets', {}).items():
        print(f"  - {name}: {info.get('frequency', 'unknown')} frequency, {info.get('format', 'unknown')} format")
    
    print(f"\nComparison files found: {len(discovery.get('comparison_files', {}))}")
    for var, files in discovery.get('comparison_files', {}).items():
        print(f"  - {var}: {len(files)} files")
        for file_info in files[:2]:  # Show first 2
            print(f"    * {file_info['filename']} ({file_info.get('frequency', 'unknown')})")
    
    # Test loading
    print("\n=== Loading Phase ===")
    sim_data = wrapper.load_simulation_data(discovery)
    print(f"Loaded {len(sim_data)} rows of simulation data")
    
    if not sim_data.empty:
        print(f"Columns: {list(sim_data.columns)}")
        print(f"Variables: {sim_data['Variable'].unique() if 'Variable' in sim_data.columns else 'N/A'}")
        
        # Check if frequency was preserved
        if '_source_frequency' in sim_data.columns:
            print(f"Source frequencies: {sim_data['_source_frequency'].unique()}")
    
    # Test validation
    print("\n=== Validation Phase ===")
    try:
        results = wrapper.validate_all()
        
        if results.get('validation_results'):
            print(f"\nValidation completed: {len(results['validation_results'])} results")
            for result in results['validation_results']:
                print(f"  {result['real_variable']} ↔ {result['sim_variable']}")
                print(f"    CVRMSE: {result['cvrmse']:.1f}% (threshold: {result['cvrmse_threshold']}%)")
                print(f"    NMBE: {result['nmbe']:.1f}% (threshold: ±{result['nmbe_threshold']}%)")
                print(f"    Pass: {'✓' if result['pass_cvrmse'] and result['pass_nmbe'] else '✗'}")
        else:
            print("No validation results generated")
            
    except Exception as e:
        print(f"Validation error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_with_real_data()