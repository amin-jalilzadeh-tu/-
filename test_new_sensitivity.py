#!/usr/bin/env python3
"""
Test script to demonstrate sensitivity analysis with new data format
"""

import logging
from pathlib import Path
import pandas as pd

# Import the updated modules
from c_sensitivity.sensitivity_manager import SensitivityManager
from c_sensitivity.data_manager import SensitivityDataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def test_new_data_format():
    """Test sensitivity analysis with new comparison file format"""
    
    # Set project directory
    project_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a")
    
    # Initialize data manager
    data_manager = SensitivityDataManager(project_dir, logger)
    
    # Test loading comparison data
    logger.info("\n=== Testing New Comparison File Format ===")
    
    # Load comparison results
    results = data_manager.load_simulation_results(
        result_type='daily',
        variables=['electricity', 'heating', 'cooling'],
        load_modified=True
    )
    
    if 'comparison_data' in results:
        logger.info(f"Successfully loaded comparison data for {len(results['comparison_data'])} variables")
        
        # Show sample of comparison data
        for var_name, df in results['comparison_data'].items():
            logger.info(f"\nVariable: {var_name}")
            logger.info(f"  Shape: {df.shape}")
            logger.info(f"  Columns: {df.columns.tolist()}")
            
            # Check for variant columns
            variant_cols = [col for col in df.columns if col.startswith('variant_') and col.endswith('_value')]
            logger.info(f"  Found {len(variant_cols)} variants: {variant_cols}")
            break
    
    # Test variant sensitivity data
    logger.info("\n=== Testing Variant Sensitivity Data ===")
    
    sensitivity_data = data_manager.get_variant_sensitivity_data(frequency='daily')
    
    if not sensitivity_data.empty:
        logger.info(f"Generated sensitivity data with {len(sensitivity_data)} records")
        logger.info(f"Columns: {sensitivity_data.columns.tolist()}")
        logger.info(f"\nSample data:")
        logger.info(sensitivity_data.head())
    
    # Test sensitivity analysis with new format
    logger.info("\n=== Testing Sensitivity Analysis ===")
    
    sensitivity_manager = SensitivityManager(project_dir, logger)
    
    # Configure for modification-based analysis using new format
    config = {
        "enabled": True,
        "analysis_type": "modification_based",
        "output_variables": ["Electricity:Facility", "Heating:EnergyTransfer", "Cooling:EnergyTransfer"],
        "aggregation_method": "sum",
        "multi_level_analysis": {
            "enabled": True,
            "analyze_building_level": True,
            "analyze_zone_level": False
        },
        "result_frequency": "daily",
        "output_base_dir": str(project_dir / "sensitivity_results_new"),
        "report_formats": ["csv", "json"]
    }
    
    # Run analysis
    report_path = sensitivity_manager.run_analysis(config)
    
    if report_path:
        logger.info(f"\n=== Sensitivity Analysis Complete ===")
        logger.info(f"Report saved to: {report_path}")
        
        # Load and display results
        results_path = Path(report_path).parent / "sensitivity_results.csv"
        if results_path.exists():
            results_df = pd.read_csv(results_path)
            logger.info(f"\nTop 10 sensitive parameters:")
            top_params = results_df.nlargest(10, 'sensitivity_score')[['parameter', 'output_variable', 'sensitivity_score']]
            logger.info(top_params.to_string())
    else:
        logger.error("Sensitivity analysis failed")

def test_data_availability():
    """Check what data formats are available"""
    
    project_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a")
    
    logger.info("\n=== Checking Data Availability ===")
    
    # Check for new format
    new_format_paths = {
        "Base timeseries": project_dir / "parsed_data/timeseries",
        "Comparison files": project_dir / "parsed_modified_results/comparisons"
    }
    
    for name, path in new_format_paths.items():
        if path.exists():
            files = list(path.glob("*.parquet"))
            logger.info(f"{name}: Found {len(files)} files")
            if files and len(files) < 10:
                for f in files[:5]:
                    logger.info(f"  - {f.name}")
        else:
            logger.info(f"{name}: Not found")
    
    # Check for old format
    old_format_paths = {
        "Old base": project_dir / "parsed_data/sql_results/timeseries/aggregated",
        "Old modified": project_dir / "parsed_modified_results/sql_results/timeseries/aggregated"
    }
    
    for name, path in old_format_paths.items():
        if path.exists():
            logger.info(f"{name}: Exists")
        else:
            logger.info(f"{name}: Not found")

if __name__ == "__main__":
    # First check what data is available
    test_data_availability()
    
    # Then test the new format
    test_new_data_format()