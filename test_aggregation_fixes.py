#!/usr/bin/env python3
"""
Test script to verify aggregation fixes in the validation system
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from validation.smart_validation_wrapper import SmartValidationWrapper, ValidationConfig

def create_test_data():
    """Create test data in both wide and long formats"""
    print("Creating test data...")
    
    # Create test directory
    test_dir = Path("test_aggregation_data")
    test_dir.mkdir(exist_ok=True)
    
    # Create wide format data (like base data)
    dates = pd.date_range('2013-01-01', '2013-01-10', freq='D')
    wide_data = {
        'building_id': ['4136733'],
        'variant_id': ['base'],
        'VariableName': ['Electricity:Facility'],
        'category': ['energy'],
        'Zone': ['NA'],
        'Units': ['J']
    }
    
    # Add date columns with values
    for date in dates:
        wide_data[date.strftime('%Y-%m-%d')] = [1777.8e6]  # Convert kWh to J
    
    wide_df = pd.DataFrame(wide_data)
    wide_path = test_dir / "base_all_daily.parquet"
    wide_df.to_parquet(wide_path)
    print(f"Created wide format data: {wide_path}")
    
    # Create long format data (like comparison data)
    long_data = []
    for date in dates:
        long_data.append({
            'timestamp': date,
            'building_id': '4136733',
            'Zone': 'NA',
            'variable_name': 'Electricity:Facility',
            'category': 'energy',
            'Units': 'J',
            'base_value': 1777.8e6,
            'variant_0_value': 1777.8e6 * 0.9  # 10% reduction
        })
    
    long_df = pd.DataFrame(long_data)
    long_path = test_dir / "var_electricity_facility_na_daily_b4136733.parquet"
    long_df.to_parquet(long_path)
    print(f"Created long format data: {long_path}")
    
    # Create measured data
    measured_data = []
    for date in dates:
        measured_data.append({
            'building_id': '4136733',
            'DateTime': date.strftime('%Y-%m-%d'),
            'Variable': 'Total Electricity',
            'Value': 1800.0,  # kWh
            'Units': 'kWh'
        })
    
    measured_df = pd.DataFrame(measured_data)
    measured_path = test_dir / "measured_data.csv"
    measured_df.to_csv(measured_path, index=False)
    print(f"Created measured data: {measured_path}")
    
    return test_dir


def test_frequency_detection(wrapper):
    """Test frequency detection for both wide and long formats"""
    print("\n=== Testing Frequency Detection ===")
    
    # Test wide format frequency detection
    test_dir = Path("test_aggregation_data")
    wide_df = pd.read_parquet(test_dir / "base_all_daily.parquet")
    
    # Test the new frequency detection methods
    if hasattr(wrapper, '_detect_frequency_from_columns'):
        freq = wrapper._detect_frequency_from_columns(wide_df)
        print(f"Wide format frequency from columns: {freq}")
    
    # Test filename frequency detection
    if hasattr(wrapper, '_detect_frequency_from_filename'):
        freq = wrapper._detect_frequency_from_filename("base_all_daily.parquet")
        print(f"Frequency from filename 'base_all_daily.parquet': {freq}")
        
        freq = wrapper._detect_frequency_from_filename("var_electricity_facility_na_monthly_b4136733.parquet")
        print(f"Frequency from filename with monthly: {freq}")
    
    # Test long format frequency detection
    long_df = pd.read_parquet(test_dir / "var_electricity_facility_na_daily_b4136733.parquet")
    freq = wrapper._detect_frequency(long_df)
    print(f"Long format frequency: {freq}")


def test_data_loading(wrapper):
    """Test data loading with discovered frequencies"""
    print("\n=== Testing Data Loading ===")
    
    # First do discovery
    discovery = wrapper.discover_available_data()
    
    # Test loading with discovered data
    try:
        sim_data = wrapper.load_simulation_data(discovery)
        print(f"Loaded simulation data: {len(sim_data)} rows")
        print(f"Data columns: {list(sim_data.columns)[:10]}...")
        
        # Check if frequency was preserved
        if '_source_frequency' in sim_data.columns:
            print(f"Source frequency preserved: {sim_data['_source_frequency'].iloc[0]}")
    except Exception as e:
        print(f"Error loading data: {e}")


def test_aggregation_skip(wrapper):
    """Test that aggregation is skipped when data is already at target frequency"""
    print("\n=== Testing Aggregation Skip Logic ===")
    
    # Create daily data for both real and sim
    dates = pd.date_range('2013-01-01', '2013-01-10', freq='D')
    real_data = pd.DataFrame({
        'DateTime': dates,
        'Value': np.random.rand(len(dates)) * 1000,
        'building_id': '4136733',
        'Variable': 'Total Electricity'
    })
    
    sim_data = pd.DataFrame({
        'DateTime': dates,
        'Value': np.random.rand(len(dates)) * 1000,
        'building_id': '4136733',
        'Variable': 'Electricity:Facility',
        '_source_frequency': 'daily'  # Add source frequency
    })
    
    # Test align_frequencies
    if hasattr(wrapper, 'align_frequencies'):
        real_aligned, sim_aligned = wrapper.align_frequencies(real_data, sim_data)
        print(f"Real data after alignment: {len(real_aligned)} rows")
        print(f"Sim data after alignment: {len(sim_aligned)} rows")
        
        # Check if aggregation was skipped
        if len(real_aligned) == len(real_data) and len(sim_aligned) == len(sim_data):
            print("✓ Aggregation correctly skipped for same frequency")
        else:
            print("✗ Aggregation was performed unnecessarily")


def test_wide_to_long_conversion(wrapper):
    """Test wide to long format conversion"""
    print("\n=== Testing Wide to Long Conversion ===")
    
    test_dir = Path("test_aggregation_data")
    wide_df = pd.read_parquet(test_dir / "base_all_daily.parquet")
    
    if hasattr(wrapper, '_convert_wide_to_long'):
        long_df = wrapper._convert_wide_to_long(wide_df)
        print(f"Converted wide to long: {len(long_df)} rows")
        print(f"Long format columns: {list(long_df.columns)}")
        print(f"Sample data:\n{long_df.head()}")
    else:
        print("✗ _convert_wide_to_long method not found")


def test_full_validation_flow():
    """Test the complete validation flow with aggregation"""
    print("\n=== Testing Full Validation Flow ===")
    
    # Create config
    config = {
        'variables_to_validate': ['electricity'],
        'aggregation': {
            'target_frequency': 'daily',
            'methods': {
                'energy': 'sum',
                'temperature': 'mean'
            }
        }
    }
    
    test_dir = create_test_data()
    
    # Initialize wrapper
    wrapper = SmartValidationWrapper(
        parsed_data_path=str(test_dir),
        real_data_path=str(test_dir / "measured_data.csv"),
        config=config
    )
    
    # Run tests
    test_frequency_detection(wrapper)
    test_data_loading(wrapper)
    test_aggregation_skip(wrapper)
    test_wide_to_long_conversion(wrapper)
    
    # Try full validation
    print("\n=== Running Full Validation ===")
    try:
        results = wrapper.validate_all()
        print(f"Validation completed successfully!")
        
        # Check discovery
        if 'discovery' in results:
            print(f"Discovery found: {len(results['discovery'].get('base_datasets', {}))} base datasets")
        
        # Check validation results
        if 'validation_results' in results:
            print(f"Validation results: {len(results['validation_results'])} results")
            for result in results['validation_results']:
                print(f"  {result.get('real_variable')} - CVRMSE: {result.get('cvrmse', 0):.2f}%")
                
        # Try variant validation
        print("\n=== Running Variant Validation ===")
        variant_results = wrapper.validate_all_variants()
        if 'variant_results' in variant_results:
            print(f"Validated {len(variant_results['variant_results'])} variants")
            
    except Exception as e:
        print(f"Validation error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Testing Aggregation Fixes")
    print("=" * 50)
    test_full_validation_flow()