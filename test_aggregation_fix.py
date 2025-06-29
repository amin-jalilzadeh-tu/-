#!/usr/bin/env python3
"""Test the aggregation fix for daily to yearly"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the aggregation module
import sys
sys.path.append('/mnt/d/Documents/daily/E_Plus_2040_py')
from orchestrator.timeseries_aggregation_step import TimeSeriesAggregator, aggregate_base_columns

def create_test_data():
    """Create test data similar to actual base data"""
    # Create date columns for a full year
    dates = pd.date_range('2013-01-01', '2013-12-31', freq='D')
    date_cols = [d.strftime('%Y-%m-%d') for d in dates]
    
    # Create test dataframe
    data = {
        'building_id': [4136733, 4136733],
        'variant_id': ['base', 'base'],
        'VariableName': ['Electricity:Facility', 'Heating:EnergyTransfer'],
        'category': ['energy_meters', 'hvac'],
        'Zone': ['Building', 'Building'],
        'Units': ['J', 'J']
    }
    
    # Add daily values
    for i, date_col in enumerate(date_cols):
        # Electricity has consistent daily usage
        data[date_col] = [6.4e6, 8.2e6]  # Daily values in Joules
    
    df = pd.DataFrame(data)
    return df, date_cols

def test_aggregation():
    """Test the aggregation functionality"""
    logger.info("Creating test data...")
    df, date_cols = create_test_data()
    
    # Create a dummy config
    config = {
        'aggregation_rules': {
            'by_pattern': [
                {
                    'pattern': ['*Energy*', '*Electricity*'],
                    'method': 'sum'
                }
            ],
            'default_method': 'mean'
        }
    }
    
    # Create aggregator
    aggregator = TimeSeriesAggregator(config, logger)
    
    # Test daily to yearly aggregation
    logger.info("\nTesting daily to yearly aggregation...")
    yearly_df = aggregate_base_columns(df, 'daily', 'yearly', aggregator)
    
    logger.info(f"Input shape: {df.shape}")
    logger.info(f"Output shape: {yearly_df.shape}")
    
    # Check columns
    yearly_cols = [col for col in yearly_df.columns if col.startswith('20')]
    logger.info(f"Yearly columns: {yearly_cols}")
    
    # Verify aggregation
    if len(yearly_cols) == 1 and yearly_cols[0] == '2013':
        logger.info("✓ SUCCESS: Yearly aggregation created single year column")
        
        # Check values
        for idx, row in yearly_df.iterrows():
            var_name = row['VariableName']
            yearly_value = row['2013']
            
            # Calculate expected value
            daily_values = df.iloc[idx][date_cols].values
            expected = np.sum(daily_values)  # Sum for energy variables
            
            logger.info(f"{var_name}:")
            logger.info(f"  Daily sum: {expected:.2e}")
            logger.info(f"  Yearly value: {yearly_value:.2e}")
            logger.info(f"  Match: {np.isclose(yearly_value, expected)}")
    else:
        logger.error(f"✗ FAILED: Expected 1 yearly column, got {len(yearly_cols)}")
        
    # Test daily to monthly aggregation
    logger.info("\nTesting daily to monthly aggregation...")
    monthly_df = aggregate_base_columns(df, 'daily', 'monthly', aggregator)
    
    monthly_cols = [col for col in monthly_df.columns if col.startswith('20')]
    logger.info(f"Monthly columns count: {len(monthly_cols)}")
    logger.info(f"First 5 monthly columns: {monthly_cols[:5]}")
    
    if len(monthly_cols) == 12:
        logger.info("✓ SUCCESS: Monthly aggregation created 12 month columns")
    else:
        logger.error(f"✗ FAILED: Expected 12 monthly columns, got {len(monthly_cols)}")

if __name__ == "__main__":
    test_aggregation()