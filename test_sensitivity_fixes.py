#!/usr/bin/env python3
"""
Test script to verify sensitivity analysis fixes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
import numpy as np
from c_sensitivity.sensitivity_manager import SensitivityManager
from c_sensitivity.modification_analyzer import ModificationSensitivityAnalyzer
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sensitivity_analysis():
    """Test the fixed sensitivity analysis"""
    job_output_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/530c3730-4459-4e51-bcc0-7a2c09d1802a")
    
    print("\n=== Testing Sensitivity Analysis Fixes ===\n")
    
    # Test 1: Check zone data availability
    print("1. Checking zone-level data availability...")
    comparison_dir = job_output_dir / "parsed_modified_results" / "comparisons"
    zone_files = list(comparison_dir.glob("var_zone_*.parquet"))
    print(f"   Found {len(zone_files)} zone-level comparison files")
    
    if zone_files:
        # Check one file
        df = pd.read_parquet(zone_files[0])
        print(f"   Sample file shape: {df.shape}")
        if 'Zone' in df.columns:
            print(f"   Zones found: {df['Zone'].nunique()}")
    
    # Test 2: Test modification analyzer with zone data
    print("\n2. Testing modification analyzer...")
    try:
        analyzer = ModificationSensitivityAnalyzer(job_output_dir, logger)
        
        # Load modifications
        print("   Loading modifications...")
        analyzer.load_modification_tracking()
        print(f"   Loaded {len(analyzer.modification_tracking)} modifications")
        
        # Calculate output deltas
        print("   Calculating output deltas...")
        output_deltas = analyzer.calculate_output_deltas(
            output_variables=['Electricity:Facility'],
            aggregation='sum'
        )
        print(f"   Calculated {len(output_deltas)} output deltas")
        
        # Check for division by zero issues
        print("   Checking for zero parameter changes...")
        zero_changes = analyzer.modification_tracking[
            analyzer.modification_tracking['param_pct_change'].abs() < 0.01
        ]
        print(f"   Found {len(zero_changes)} modifications with <1% change (will be skipped)")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test regional sensitivity with validation
    print("\n3. Testing regional sensitivity analysis...")
    try:
        from c_sensitivity.regional_sensitivity import RegionalSensitivityAnalyzer
        from c_sensitivity.data_manager import SensitivityDataManager
        
        data_manager = SensitivityDataManager(job_output_dir, logger)
        regional_analyzer = RegionalSensitivityAnalyzer(data_manager, logger)
        
        # Create small test data
        X = pd.DataFrame({
            'param1': np.random.randn(100),
            'param2': np.random.randn(100),
            'param3': np.random.randn(100)
        })
        y = pd.DataFrame({
            'output1': np.random.randn(100),
            'output2': np.random.randn(100)
        })
        
        config = {'n_regions': 3, 'region_method': 'kmeans'}
        results = regional_analyzer.analyze(X, y, config)
        
        if results.empty:
            print("   Regional analysis returned empty results (as expected with test data)")
        else:
            print(f"   Regional analysis produced {len(results)} results")
            
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Test HTML report generation
    print("\n4. Testing HTML report generation...")
    try:
        from c_sensitivity.reporter import SensitivityReporter
        
        reporter = SensitivityReporter(logger)
        
        # Create test data
        test_results = {
            'metadata': {
                'analysis_type': 'modification',
                'n_parameters': 10,
                'n_outputs': 3
            },
            'modification': {
                'metadata': {'method': 'elasticity', 'n_variants': 19},
                'results': [
                    {
                        'parameter': 'test_param_1',
                        'sensitivity_score': 5.0,
                        'method': 'elasticity',
                        'metadata': {'category': 'test'}
                    }
                ]
            }
        }
        
        # Try to generate HTML (just test the method exists)
        html = reporter._create_modification_section(test_results['modification'])
        print("   HTML section generation successful")
        print(f"   Generated {len(html)} characters of HTML")
        
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check for synthetic data removal
    print("\n5. Verifying synthetic data removal...")
    try:
        from c_sensitivity.sensitivity_manager import SensitivityManager
        
        # Check if synthetic methods are removed
        manager = SensitivityManager(job_output_dir, logger)
        
        # Try to access removed methods (should fail)
        has_synthetic = hasattr(manager, '_create_synthetic_parameter_data')
        if has_synthetic:
            print("   WARNING: Synthetic data methods still exist!")
        else:
            print("   SUCCESS: Synthetic data methods have been removed")
            
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n=== All Tests Completed ===\n")

if __name__ == "__main__":
    test_sensitivity_analysis()