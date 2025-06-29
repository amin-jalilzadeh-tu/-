#!/usr/bin/env python3
"""
Test aggregation fixes with full year measured data
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from validation.smart_validation_wrapper import SmartValidationWrapper

def test_full_year():
    """Test with full year measured data"""
    
    # Use full year data
    output_path = "/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_data"
    real_data_path = "/mnt/d/Documents/daily/E_Plus_2040_py/data/test_validation_data/measured_data_4136733_full.csv"
    
    config = {
        'variables_to_validate': ['electricity'],
        'aggregation': {
            'target_frequency': 'daily',
            'methods': {
                'energy': 'sum',
                'temperature': 'mean'
            }
        },
        'thresholds': {
            'default': {
                'cvrmse': 30.0,
                'nmbe': 10.0
            }
        }
    }
    
    print("Testing with full year data")
    print("=" * 60)
    
    # Initialize wrapper
    wrapper = SmartValidationWrapper(
        parsed_data_path=output_path,
        real_data_path=real_data_path,
        config=config
    )
    
    # Run validation
    print("\n=== Running Full Year Validation ===")
    results = wrapper.validate_all()
    
    # Show results
    if results.get('validation_results'):
        print(f"\n✓ Validation completed: {len(results['validation_results'])} results")
        for result in results['validation_results']:
            print(f"\nBuilding: {result['building_id']}")
            print(f"Variable: {result['real_variable']} ↔ {result['sim_variable']}")
            print(f"Data points: {result['data_points']}")
            print(f"CVRMSE: {result['cvrmse']:.1f}% (threshold: {result['cvrmse_threshold']}%)")
            print(f"NMBE: {result['nmbe']:.1f}% (threshold: ±{result['nmbe_threshold']}%)")
            print(f"Pass: {'✓' if result['pass_cvrmse'] and result['pass_nmbe'] else '✗'}")
            
            if result.get('unit_conversion'):
                print(f"Unit conversion: {result['unit_conversion']}")
    else:
        print("\n✗ No validation results generated")
        
    # Test variant validation
    print("\n=== Testing Variant Validation ===")
    
    # Update path for modified results
    wrapper.parsed_data_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_modified_results")
    
    variant_results = wrapper.validate_all_variants()
    
    if variant_results.get('variant_results'):
        print(f"\n✓ Validated {len(variant_results['variant_results'])} variants")
        
        # Show summary by variant
        variant_summary = {}
        for result in variant_results['variant_results']:
            variant = result['variant_id']
            if variant not in variant_summary:
                variant_summary[variant] = {'total': 0, 'passed': 0}
            variant_summary[variant]['total'] += 1
            if result['pass_cvrmse'] and result['pass_nmbe']:
                variant_summary[variant]['passed'] += 1
        
        print("\nVariant Summary:")
        for variant, stats in sorted(variant_summary.items()):
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  Variant {variant}: {stats['passed']}/{stats['total']} passed ({pass_rate:.1f}%)")
    else:
        print("\n✗ No variant results generated")
        
    # Test aggregation to monthly
    print("\n=== Testing Monthly Aggregation ===")
    config['aggregation']['target_frequency'] = 'monthly'
    wrapper.config = wrapper.__class__.ValidationConfig(config)
    
    monthly_results = wrapper.validate_all()
    if monthly_results.get('validation_results'):
        print(f"\n✓ Monthly validation completed: {len(monthly_results['validation_results'])} results")
        result = monthly_results['validation_results'][0]
        print(f"Data points: {result['data_points']} (monthly)")
        print(f"CVRMSE: {result['cvrmse']:.1f}%")
    else:
        print("\n✗ No monthly validation results")


if __name__ == "__main__":
    test_full_year()