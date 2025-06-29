#!/usr/bin/env python3
"""Fix and test the aggregation system"""

import json
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_aggregation_fix():
    """Run the aggregation with the fixed code"""
    
    # Import the orchestrator module
    sys.path.append('/mnt/d/Documents/daily/E_Plus_2040_py')
    from orchestrator.timeseries_aggregation_step import run_timeseries_aggregation
    
    # Load config
    config_path = Path('/mnt/d/Documents/daily/E_Plus_2040_py/combined.json')
    with open(config_path) as f:
        config = json.load(f)
    
    # Get aggregation config
    aggregation_config = config['main_config']['timeseries_aggregation']
    
    # Ensure yearly is in target frequencies
    if 'yearly' not in aggregation_config['default_settings']['target_frequencies']:
        aggregation_config['default_settings']['target_frequencies'].append('yearly')
        logger.info("Added 'yearly' to target frequencies")
    
    # Find a recent job output directory
    output_dir = Path('/mnt/d/Documents/daily/E_Plus_2040_py/output')
    job_dirs = sorted(output_dir.glob('*/'), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not job_dirs:
        logger.error("No job output directories found")
        return
    
    # Use the most recent job
    job_dir = job_dirs[0]
    logger.info(f"Using job directory: {job_dir}")
    
    # Check if parsed data exists
    parsed_data_dir = job_dir / 'parsed_data'
    if not parsed_data_dir.exists():
        logger.error(f"Parsed data directory not found: {parsed_data_dir}")
        return
    
    # Run aggregation
    logger.info("Running time series aggregation...")
    results = run_timeseries_aggregation(
        aggregation_config,
        str(job_dir),
        str(parsed_data_dir),
        logger
    )
    
    logger.info(f"Aggregation results: {results}")
    
    # Check for yearly files
    check_yearly_files(parsed_data_dir, job_dir)

def check_yearly_files(parsed_data_dir, job_dir):
    """Check if yearly aggregation files were created"""
    logger.info("\n" + "="*60)
    logger.info("Checking for yearly aggregation files...")
    logger.info("="*60)
    
    # Check base yearly files
    timeseries_dir = parsed_data_dir / 'timeseries'
    if timeseries_dir.exists():
        yearly_base_files = list(timeseries_dir.glob('*yearly*.parquet'))
        logger.info(f"\nBase yearly files in {timeseries_dir}:")
        if yearly_base_files:
            for f in yearly_base_files:
                logger.info(f"  - {f.name}")
        else:
            logger.warning("  No yearly base files found!")
    
    # Check comparison yearly files
    comp_dirs = [
        parsed_data_dir / 'comparisons',
        job_dir / 'parsed_modified_results' / 'comparisons'
    ]
    
    for comp_dir in comp_dirs:
        if comp_dir.exists():
            yearly_comp_files = list(comp_dir.glob('*yearly*.parquet'))
            logger.info(f"\nComparison yearly files in {comp_dir}:")
            if yearly_comp_files:
                for f in yearly_comp_files[:10]:  # Show first 10
                    logger.info(f"  - {f.name}")
                if len(yearly_comp_files) > 10:
                    logger.info(f"  ... and {len(yearly_comp_files) - 10} more")
            else:
                logger.warning("  No yearly comparison files found!")
    
    # Verify a yearly file content
    verify_yearly_content(timeseries_dir, comp_dirs)

def verify_yearly_content(timeseries_dir, comp_dirs):
    """Verify the content of yearly aggregation files"""
    import pandas as pd
    
    logger.info("\n" + "="*60)
    logger.info("Verifying yearly file content...")
    logger.info("="*60)
    
    # Check a base yearly file
    yearly_files = list(timeseries_dir.glob('*yearly*.parquet'))
    if yearly_files:
        file_to_check = yearly_files[0]
        logger.info(f"\nChecking base file: {file_to_check.name}")
        
        try:
            df = pd.read_parquet(file_to_check)
            logger.info(f"  Shape: {df.shape}")
            
            # Check columns
            date_cols = [col for col in df.columns if str(col).startswith('20')]
            logger.info(f"  Year columns: {date_cols}")
            
            if len(date_cols) == 1:
                logger.info("  ✓ SUCCESS: Single year column found")
                
                # Show sample values
                if not df.empty:
                    row = df.iloc[0]
                    logger.info(f"  Sample data for {row['VariableName']}:")
                    logger.info(f"    Yearly value: {row[date_cols[0]]:.2e}")
            else:
                logger.error(f"  ✗ ERROR: Expected 1 year column, found {len(date_cols)}")
                
        except Exception as e:
            logger.error(f"  Error reading file: {e}")
    
    # Check a comparison yearly file
    for comp_dir in comp_dirs:
        if comp_dir.exists():
            yearly_comp = list(comp_dir.glob('*yearly*.parquet'))
            if yearly_comp:
                file_to_check = yearly_comp[0]
                logger.info(f"\nChecking comparison file: {file_to_check.name}")
                
                try:
                    df = pd.read_parquet(file_to_check)
                    logger.info(f"  Shape: {df.shape}")
                    logger.info(f"  Columns: {list(df.columns)}")
                    
                    # Check if it has proper timestamp-based structure
                    if 'timestamp' in df.columns:
                        logger.info(f"  Number of time points: {len(df)}")
                        if len(df) <= 12:  # Should have at most 12 rows for monthly->yearly or 1 for yearly
                            logger.info("  ✓ SUCCESS: Appropriate number of rows for yearly data")
                        else:
                            logger.warning(f"  ⚠ WARNING: Too many rows ({len(df)}) for yearly data")
                            
                except Exception as e:
                    logger.error(f"  Error reading file: {e}")
                
                break  # Just check one file

if __name__ == "__main__":
    run_aggregation_fix()