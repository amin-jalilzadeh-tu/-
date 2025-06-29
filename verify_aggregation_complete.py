#!/usr/bin/env python3
"""Verify that aggregation is working correctly"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def verify_base_aggregation():
    """Verify base aggregation files"""
    logger.info("="*60)
    logger.info("VERIFYING BASE AGGREGATION")
    logger.info("="*60)
    
    base_dir = Path('/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/parsed_data/timeseries')
    
    # Check daily to yearly
    daily_file = base_dir / 'base_all_daily.parquet'
    yearly_file = base_dir / 'base_all_yearly_from_daily.parquet'
    
    if daily_file.exists() and yearly_file.exists():
        logger.info("\n✓ Daily to Yearly aggregation:")
        
        daily_df = pd.read_parquet(daily_file)
        yearly_df = pd.read_parquet(yearly_file)
        
        logger.info(f"  Daily shape: {daily_df.shape}")
        logger.info(f"  Yearly shape: {yearly_df.shape}")
        
        # Check columns
        daily_date_cols = [col for col in daily_df.columns if str(col).startswith('2013')]
        yearly_date_cols = [col for col in yearly_df.columns if str(col).startswith('20')]
        
        logger.info(f"  Daily date columns: {len(daily_date_cols)}")
        logger.info(f"  Yearly date columns: {yearly_date_cols}")
        
        # Verify aggregation for electricity
        elec_row_daily = daily_df[daily_df['VariableName'] == 'Electricity:Facility'].iloc[0]
        elec_row_yearly = yearly_df[yearly_df['VariableName'] == 'Electricity:Facility'].iloc[0]
        
        daily_sum = elec_row_daily[daily_date_cols].sum()
        yearly_value = elec_row_yearly['2013']
        
        logger.info(f"\n  Electricity verification:")
        logger.info(f"    Sum of daily values: {daily_sum:.2e}")
        logger.info(f"    Yearly value: {yearly_value:.2e}")
        logger.info(f"    Match: {np.isclose(daily_sum, yearly_value)}")
    else:
        logger.error("✗ Base aggregation files not found")

def verify_comparison_aggregation():
    """Verify comparison aggregation files"""
    logger.info("\n" + "="*60)
    logger.info("VERIFYING COMPARISON AGGREGATION")
    logger.info("="*60)
    
    comp_dir = Path('/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/parsed_modified_results/comparisons')
    
    # Check electricity monthly to yearly
    monthly_file = comp_dir / 'var_electricity_facility_na_monthly_b4136733.parquet'
    yearly_file = comp_dir / 'var_electricity_facility_yearly_from_monthly_b4136733.parquet'
    
    if monthly_file.exists() and yearly_file.exists():
        logger.info("\n✓ Monthly to Yearly comparison aggregation:")
        
        monthly_df = pd.read_parquet(monthly_file)
        yearly_df = pd.read_parquet(yearly_file)
        
        logger.info(f"  Monthly shape: {monthly_df.shape}")
        logger.info(f"  Yearly shape: {yearly_df.shape}")
        
        # Check that we have proper yearly aggregation
        if len(yearly_df) <= 2:  # Should have at most 2 years
            logger.info("  ✓ Correct number of yearly rows")
            
            # Verify values
            if 'base_value' in yearly_df.columns:
                yearly_base_sum = yearly_df['base_value'].sum()
                logger.info(f"  Total yearly base value: {yearly_base_sum:.2e}")
        else:
            logger.error(f"  ✗ Too many rows for yearly data: {len(yearly_df)}")
    else:
        logger.error("✗ Comparison aggregation files not found")

def check_all_aggregations():
    """Check all aggregation combinations"""
    logger.info("\n" + "="*60)
    logger.info("AGGREGATION SUMMARY")
    logger.info("="*60)
    
    base_dir = Path('/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/parsed_data/timeseries')
    comp_dir = Path('/mnt/d/Documents/daily/E_Plus_2040_py/output/f1bece00-4e3b-499b-a691-39ec0ed8a5f6/parsed_modified_results/comparisons')
    
    # Base aggregations
    logger.info("\nBase aggregations found:")
    base_aggs = {
        'Daily → Monthly': base_dir / 'base_all_monthly_from_daily.parquet',
        'Daily → Yearly': base_dir / 'base_all_yearly_from_daily.parquet',
        'Monthly → Yearly': base_dir / 'base_all_yearly_from_monthly.parquet'
    }
    
    for name, path in base_aggs.items():
        if path.exists():
            logger.info(f"  ✓ {name}: {path.name}")
        else:
            logger.info(f"  ✗ {name}: NOT FOUND")
    
    # Comparison aggregations
    logger.info("\nComparison aggregations found (sample):")
    yearly_comps = list(comp_dir.glob('*yearly*.parquet'))
    if yearly_comps:
        logger.info(f"  ✓ Found {len(yearly_comps)} yearly comparison files")
        for f in yearly_comps[:5]:
            logger.info(f"    - {f.name}")
    else:
        logger.info("  ✗ No yearly comparison files found")

if __name__ == "__main__":
    verify_base_aggregation()
    verify_comparison_aggregation()
    check_all_aggregations()
    
    logger.info("\n" + "="*60)
    logger.info("AGGREGATION VERIFICATION COMPLETE")
    logger.info("="*60)