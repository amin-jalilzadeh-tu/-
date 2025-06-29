#!/usr/bin/env python3
"""
Test the main aggregation system
"""

import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.timeseries_aggregation_step import run_timeseries_aggregation

def test_main_aggregation():
    """Test the main aggregation system with real data"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    
    # Configuration for aggregation
    aggregation_config = {
        "default_settings": {
            "target_frequencies": ["monthly", "yearly"],
            "skip_existing": False  # Force re-aggregation for testing
        },
        "aggregation_rules": {
            "by_pattern": [
                {"pattern": ["Energy", "Consumption"], "method": "sum"},
                {"pattern": ["Temperature", "Humidity"], "method": "mean"},
                {"pattern": ["Rate", "Power"], "method": "mean"}
            ],
            "default_method": "mean"
        },
        "input_options": {
            "use_base_data": True,
            "use_variant_data": True
        },
        "variable_selection": {
            "mode": "all"
        }
    }
    
    # Test paths
    job_output_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a"
    parsed_data_dir = "/mnt/d/Documents/daily/E_Plus_2040_py/output/7f5a59d5-4cde-4f21-9eb7-04d8a765453a/parsed_data"
    
    print("Testing Main Aggregation System")
    print("=" * 60)
    print(f"Parsed data directory: {parsed_data_dir}")
    print(f"Target frequencies: {aggregation_config['default_settings']['target_frequencies']}")
    print()
    
    # Run aggregation
    try:
        results = run_timeseries_aggregation(
            aggregation_cfg=aggregation_config,
            job_output_dir=job_output_dir,
            parsed_data_dir=parsed_data_dir,
            logger=logger
        )
        
        print("\n" + "=" * 60)
        print("Aggregation Results:")
        print(f"Success: {results.get('success', False)}")
        print(f"Files created: {results.get('files_created', 0)}")
        print(f"Frequencies created: {results.get('frequencies_created', [])}")
        print(f"Base data processed: {results.get('base_data_processed', False)}")
        print(f"Comparison data processed: {results.get('comparison_data_processed', False)}")
        
        # Check created files
        timeseries_dir = Path(parsed_data_dir) / 'timeseries'
        if timeseries_dir.exists():
            print(f"\nFiles in timeseries directory:")
            for file in sorted(timeseries_dir.glob('*.parquet')):
                print(f"  - {file.name}")
                
        # Check comparison files
        comp_dir = Path(job_output_dir) / 'parsed_modified_results' / 'comparisons'
        if comp_dir.exists():
            aggregated_files = list(comp_dir.glob('*_from_*.parquet'))
            if aggregated_files:
                print(f"\nAggregated comparison files created:")
                for file in sorted(aggregated_files)[:5]:  # Show first 5
                    print(f"  - {file.name}")
                if len(aggregated_files) > 5:
                    print(f"  ... and {len(aggregated_files) - 5} more")
                    
    except Exception as e:
        print(f"Error during aggregation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_main_aggregation()