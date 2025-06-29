#!/usr/bin/env python3
"""Standalone script to run aggregation without full imports"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from collections import defaultdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Copy the essential functions
class TimeSeriesAggregator:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.aggregation_rules = self._build_aggregation_rules()
        
    def _build_aggregation_rules(self):
        rules = {}
        rule_config = self.config.get('aggregation_rules', {})
        
        for rule in rule_config.get('by_pattern', []):
            patterns = rule['pattern'] if isinstance(rule['pattern'], list) else [rule['pattern']]
            method = rule['method']
            for pattern in patterns:
                rules[pattern.lower()] = method
        
        for var, method in rule_config.get('by_variable', {}).items():
            rules[var] = method
        
        rules['default'] = rule_config.get('default_method', 'mean')
        return rules
    
    def determine_aggregation_method(self, variable_name, from_freq=None, to_freq=None):
        if variable_name in self.aggregation_rules:
            return self.aggregation_rules[variable_name]
        
        var_lower = variable_name.lower()
        for pattern, method in self.aggregation_rules.items():
            if pattern != 'default' and pattern in var_lower:
                return method
        
        return self.aggregation_rules['default']

def aggregate_base_columns(df, from_freq, to_freq, aggregator):
    """Fixed version of aggregate_base_columns"""
    if from_freq == to_freq:
        return df
    
    meta_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Get date columns based on frequency
    if from_freq == 'hourly':
        date_pattern = r'\d{4}-\d{2}-\d{2}_\d{2}'
    elif from_freq == 'daily':
        date_pattern = r'\d{4}-\d{2}-\d{2}$'
    elif from_freq == 'monthly':
        date_pattern = r'\d{4}-\d{2}$'
    else:
        return df
    
    date_cols = [col for col in df.columns if re.match(date_pattern, str(col))]
    
    if not date_cols:
        return df
    
    grouped_cols = defaultdict(list)
    
    # Group columns by target period
    if from_freq == 'daily' and to_freq == 'yearly':
        for col in date_cols:
            year_key = col[:4]  # YYYY
            grouped_cols[year_key].append(col)
    elif from_freq == 'daily' and to_freq == 'monthly':
        for col in date_cols:
            month_key = col[:7]  # YYYY-MM
            grouped_cols[month_key].append(col)
    elif from_freq == 'monthly' and to_freq == 'yearly':
        for col in date_cols:
            year_key = col[:4]  # YYYY
            grouped_cols[year_key].append(col)
    elif from_freq == 'hourly' and to_freq == 'daily':
        for col in date_cols:
            day_key = col[:10]  # YYYY-MM-DD
            grouped_cols[day_key].append(col)
    else:
        return df
    
    result_df = df[meta_cols].copy()
    
    # Process each row
    for idx, row in df.iterrows():
        var_name = row.get('VariableName', '')
        agg_method = aggregator.determine_aggregation_method(var_name, from_freq, to_freq)
        
        # Aggregate each time group
        for new_col, source_cols in grouped_cols.items():
            values = row[source_cols].values
            values = values[~pd.isna(values)]
            
            if len(values) > 0:
                if agg_method == 'sum':
                    result_df.loc[idx, new_col] = np.sum(values)
                elif agg_method == 'mean':
                    result_df.loc[idx, new_col] = np.mean(values)
                elif agg_method == 'max':
                    result_df.loc[idx, new_col] = np.max(values)
                elif agg_method == 'min':
                    result_df.loc[idx, new_col] = np.min(values)
                else:
                    result_df.loc[idx, new_col] = np.mean(values)
            else:
                result_df.loc[idx, new_col] = np.nan
    
    return result_df

def aggregate_comparison_data(df, from_freq, to_freq, aggregator):
    """Aggregate comparison data"""
    freq_map = {
        'hourly': 'H',
        'daily': 'D', 
        'monthly': 'M',
        'yearly': 'Y'
    }
    
    if from_freq not in freq_map or to_freq not in freq_map:
        return pd.DataFrame()
    
    freq_order = ['timestep', 'hourly', 'daily', 'monthly', 'yearly']
    if freq_order.index(from_freq) >= freq_order.index(to_freq):
        return pd.DataFrame()
    
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    var_name = df['variable_name'].iloc[0] if 'variable_name' in df.columns else ''
    agg_method = aggregator.determine_aggregation_method(var_name, from_freq, to_freq)
    
    df = df.set_index('timestamp')
    value_cols = [col for col in df.columns if col.endswith('_value')]
    meta_cols = ['building_id', 'Zone', 'variable_name', 'category', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Aggregate
    if agg_method == 'sum':
        agg_df = df.groupby(pd.Grouper(freq=freq_map[to_freq]))[value_cols].sum()
    elif agg_method == 'mean':
        agg_df = df.groupby(pd.Grouper(freq=freq_map[to_freq]))[value_cols].mean()
    elif agg_method == 'max':
        agg_df = df.groupby(pd.Grouper(freq=freq_map[to_freq]))[value_cols].max()
    elif agg_method == 'min':
        agg_df = df.groupby(pd.Grouper(freq=freq_map[to_freq]))[value_cols].min()
    else:
        agg_df = df.groupby(pd.Grouper(freq=freq_map[to_freq]))[value_cols].mean()
    
    agg_df = agg_df.reset_index()
    agg_df['timestamp'] = agg_df['timestamp'].astype('int64') // 10**6
    
    for col in meta_cols:
        if col in df.columns:
            agg_df[col] = df[col].iloc[0]
    
    first_cols = ['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units']
    first_cols = [col for col in first_cols if col in agg_df.columns]
    other_cols = [col for col in agg_df.columns if col not in first_cols]
    
    return agg_df[first_cols + other_cols]

def main():
    """Main aggregation runner"""
    # Load config
    with open('combined.json') as f:
        config = json.load(f)
    
    agg_config = config['main_config']['timeseries_aggregation']
    
    # Create aggregator
    aggregator = TimeSeriesAggregator(agg_config, logger)
    
    # Find output directory
    output_dir = Path('output')
    
    # Check if a specific job directory is provided as argument
    import sys
    if len(sys.argv) > 1:
        job_dir = output_dir / sys.argv[1]
        if not job_dir.exists():
            logger.error(f"Specified job directory not found: {job_dir}")
            return
        logger.info(f"Using specified job directory: {job_dir}")
    else:
        # Find directories with parsed_data subdirectory
        job_dirs = []
        for d in output_dir.iterdir():
            if d.is_dir() and (d / 'parsed_data').exists():
                job_dirs.append(d)
        
        if not job_dirs:
            logger.error("No job directories with parsed_data found")
            return
        
        # Sort by modification time
        job_dirs = sorted(job_dirs, key=lambda x: x.stat().st_mtime, reverse=True)
        job_dir = job_dirs[0]
        logger.info(f"Using job directory: {job_dir}")
    
    # Process base files
    timeseries_dir = job_dir / 'parsed_data' / 'timeseries'
    if timeseries_dir.exists():
        logger.info("\n" + "="*60)
        logger.info("Processing BASE aggregations")
        logger.info("="*60)
        
        # Daily to yearly
        daily_files = list(timeseries_dir.glob('base_*_daily.parquet'))
        for daily_file in daily_files:
            if '_from_' not in daily_file.stem:
                logger.info(f"\nProcessing: {daily_file.name}")
                
                df = pd.read_parquet(daily_file)
                logger.info(f"  Input shape: {df.shape}")
                
                # Create yearly aggregation
                yearly_df = aggregate_base_columns(df, 'daily', 'yearly', aggregator)
                
                # Save
                output_name = daily_file.stem.replace('_daily', '_yearly_from_daily') + '.parquet'
                output_path = timeseries_dir / output_name
                yearly_df.to_parquet(output_path, index=False)
                
                logger.info(f"  Output shape: {yearly_df.shape}")
                logger.info(f"  Saved to: {output_name}")
                
                # Verify
                year_cols = [col for col in yearly_df.columns if str(col).startswith('20')]
                logger.info(f"  Year columns: {year_cols}")
        
        # Monthly to yearly
        monthly_files = list(timeseries_dir.glob('base_*_monthly.parquet'))
        for monthly_file in monthly_files:
            if '_from_' not in monthly_file.stem:
                logger.info(f"\nProcessing: {monthly_file.name}")
                
                df = pd.read_parquet(monthly_file)
                logger.info(f"  Input shape: {df.shape}")
                
                # Create yearly aggregation
                yearly_df = aggregate_base_columns(df, 'monthly', 'yearly', aggregator)
                
                # Save
                output_name = monthly_file.stem.replace('_monthly', '_yearly_from_monthly') + '.parquet'
                output_path = timeseries_dir / output_name
                yearly_df.to_parquet(output_path, index=False)
                
                logger.info(f"  Output shape: {yearly_df.shape}")
                logger.info(f"  Saved to: {output_name}")
    
    # Process comparison files
    comp_dirs = [
        job_dir / 'parsed_data' / 'comparisons',
        job_dir / 'parsed_modified_results' / 'comparisons'
    ]
    
    for comp_dir in comp_dirs:
        if comp_dir.exists():
            logger.info("\n" + "="*60)
            logger.info(f"Processing COMPARISON aggregations in {comp_dir}")
            logger.info("="*60)
            
            # Monthly to yearly
            monthly_comps = list(comp_dir.glob('var_*_monthly_b*.parquet'))
            for comp_file in monthly_comps[:5]:  # Process first 5 as example
                if '_from_' not in comp_file.stem:
                    logger.info(f"\nProcessing: {comp_file.name}")
                    
                    # Extract info from filename
                    match = re.match(r'var_(.+?)_(.+?)_(.+?)_b(\d+)\.parquet', comp_file.name)
                    if match:
                        var_name, unit, freq, building_id = match.groups()
                        
                        df = pd.read_parquet(comp_file)
                        logger.info(f"  Input shape: {df.shape}")
                        
                        # Create yearly aggregation
                        yearly_df = aggregate_comparison_data(df, 'monthly', 'yearly', aggregator)
                        
                        if not yearly_df.empty:
                            # Save
                            output_name = f"var_{var_name}_{unit}_yearly_from_monthly_b{building_id}.parquet"
                            output_path = comp_dir / output_name
                            yearly_df.to_parquet(output_path, index=False)
                            
                            logger.info(f"  Output shape: {yearly_df.shape}")
                            logger.info(f"  Saved to: {output_name}")
                        else:
                            logger.warning(f"  Failed to aggregate")
    
    logger.info("\n" + "="*60)
    logger.info("Aggregation complete!")
    logger.info("="*60)

if __name__ == "__main__":
    main()