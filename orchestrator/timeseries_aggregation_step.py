"""
orchestrator/post_processing/timeseries_aggregation_step.py

Time Series Aggregation Post-Processing Step
Handles aggregation and selection of parsed time series data for both base and modified results
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
import logging
import re
from collections import defaultdict


class TimeSeriesAggregator:
    """Handle time series aggregation with configurable rules"""
    
    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.aggregation_rules = self._build_aggregation_rules()
        
    def _build_aggregation_rules(self) -> Dict[str, str]:
        """Build aggregation rules from configuration"""
        rules = {}
        
        # Get rules from config
        rule_config = self.config.get('aggregation_rules', {})
        
        # Process pattern-based rules
        for rule in rule_config.get('by_pattern', []):
            patterns = rule['pattern'] if isinstance(rule['pattern'], list) else [rule['pattern']]
            method = rule['method']
            
            for pattern in patterns:
                rules[pattern.lower()] = method
        
        # Add variable-specific rules
        for var, method in rule_config.get('by_variable', {}).items():
            rules[var] = method
        
        # Add default
        rules['default'] = rule_config.get('default_method', 'mean')
        
        return rules
    
    def determine_aggregation_method(self, variable_name: str, from_freq: str = None, to_freq: str = None) -> str:
        """Determine aggregation method for a variable"""
        # Check variable-specific overrides first
        for override in self.config.get('variable_overrides', []):
            if override['variable'] == variable_name:
                methods = override.get('aggregation_methods', {})
                freq_key = f"{from_freq}_to_{to_freq}"
                if freq_key in methods:
                    return methods[freq_key]
        
        # Check exact variable match
        if variable_name in self.aggregation_rules:
            return self.aggregation_rules[variable_name]
        
        var_lower = variable_name.lower()
        
        # Check pattern rules
        for pattern, method in self.aggregation_rules.items():
            if pattern != 'default' and pattern in var_lower:
                return method
        
        return self.aggregation_rules['default']


def detect_frequency_from_columns(df: pd.DataFrame) -> str:
    """Detect frequency from date column names"""
    # Get all potential date columns
    date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}-\d{2}', str(col))]
    
    if not date_cols:
        # Try monthly format (YYYY-MM)
        date_cols = [col for col in df.columns if re.match(r'\d{4}-\d{2}$', str(col))]
        if date_cols:
            return 'monthly'
        return 'unknown'
    
    # If we have at least 2 date columns, check the interval
    if len(date_cols) >= 2:
        try:
            # Parse first two dates
            date1 = pd.to_datetime(date_cols[0])
            date2 = pd.to_datetime(date_cols[1])
            diff = (date2 - date1).days
            
            if diff == 1:
                return 'daily'
            elif 28 <= diff <= 31:
                return 'monthly'
            elif diff == 7:
                return 'weekly'
            elif diff == 365 or diff == 366:
                return 'yearly'
        except:
            pass
    
    # Check format patterns
    if len(date_cols[0]) == 10:  # YYYY-MM-DD
        return 'daily'
    elif '_' in str(date_cols[0]) and re.match(r'\d{4}-\d{2}-\d{2}_\d{2}', str(date_cols[0])):
        return 'hourly'
    
    return 'unknown'


def aggregate_base_columns(df: pd.DataFrame, from_freq: str, to_freq: str, 
                          aggregator: TimeSeriesAggregator) -> pd.DataFrame:
    """Aggregate base data columns directly without reshaping"""
    if from_freq == to_freq:
        return df
    
    # Check if this is already aggregated data with the wrong name
    detected_freq = detect_frequency_from_columns(df)
    if detected_freq == to_freq:
        aggregator.logger.info(f"    Data already at {to_freq} frequency, no aggregation needed")
        return df
    
    # Get metadata columns (non-date columns)
    meta_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Get date columns
    if from_freq == 'hourly':
        date_pattern = r'\d{4}-\d{2}-\d{2}_\d{2}'
    elif from_freq == 'daily':
        date_pattern = r'\d{4}-\d{2}-\d{2}$'
    else:
        return df
    
    date_cols = [col for col in df.columns if re.match(date_pattern, str(col))]
    
    if not date_cols:
        return df
    
    # Group columns by target period
    grouped_cols = defaultdict(list)
    
    if from_freq == 'daily' and to_freq == 'monthly':
        for col in date_cols:
            month_key = col[:7]  # YYYY-MM
            grouped_cols[month_key].append(col)
    
    elif from_freq == 'hourly' and to_freq == 'daily':
        for col in date_cols:
            day_key = col[:10]  # YYYY-MM-DD
            grouped_cols[day_key].append(col)
    
    elif from_freq == 'monthly' and to_freq == 'yearly':
        for col in date_cols:
            year_key = col[:4]  # YYYY
            grouped_cols[year_key].append(col)
    
    else:
        return df
    
    # Create new dataframe with aggregated columns
    result_df = df[meta_cols].copy()
    
    # Process each row
    for idx, row in df.iterrows():
        var_name = row.get('VariableName', '')
        agg_method = aggregator.determine_aggregation_method(var_name, from_freq, to_freq)
        
        # Aggregate each time group
        for new_col, source_cols in grouped_cols.items():
            values = row[source_cols].values
            # Remove NaN values
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


def aggregate_comparison_data(df: pd.DataFrame, from_freq: str, to_freq: str, 
                            aggregator: TimeSeriesAggregator) -> pd.DataFrame:
    """Aggregate comparison data maintaining the base/variant structure"""
    # Frequency mapping
    freq_map = {
        'hourly': 'H',
        'daily': 'D', 
        'monthly': 'M',
        'yearly': 'Y'
    }
    
    if from_freq not in freq_map or to_freq not in freq_map:
        return pd.DataFrame()
    
    # Check if valid aggregation
    freq_order = ['timestep', 'hourly', 'daily', 'monthly', 'yearly']
    if freq_order.index(from_freq) >= freq_order.index(to_freq):
        return pd.DataFrame()
    
    df = df.copy()
    
    # Convert timestamp from milliseconds to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Get aggregation method
    var_name = df['variable_name'].iloc[0] if 'variable_name' in df.columns else ''
    agg_method = aggregator.determine_aggregation_method(var_name, from_freq, to_freq)
    
    # Set timestamp as index
    df = df.set_index('timestamp')
    
    # Get value columns (base_value, variant_X_value)
    value_cols = [col for col in df.columns if col.endswith('_value')]
    
    # Get metadata columns to preserve
    meta_cols = ['building_id', 'Zone', 'variable_name', 'category', 'Units']
    meta_cols = [col for col in meta_cols if col in df.columns]
    
    # Group and aggregate
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
    
    # Reset index
    agg_df = agg_df.reset_index()
    
    # Convert back to milliseconds timestamp
    agg_df['timestamp'] = agg_df['timestamp'].astype('int64') // 10**6
    
    # Add back metadata (take first value since they should be consistent)
    for col in meta_cols:
        if col in df.columns:
            agg_df[col] = df[col].iloc[0]
    
    # Reorder columns to match original structure
    first_cols = ['timestamp', 'building_id', 'Zone', 'variable_name', 'category', 'Units']
    first_cols = [col for col in first_cols if col in agg_df.columns]
    other_cols = [col for col in agg_df.columns if col not in first_cols]
    
    return agg_df[first_cols + other_cols]


def should_process_variable(variable_name: str, selection_config: dict) -> bool:
    """Check if a variable should be processed based on selection criteria"""
    mode = selection_config.get('mode', 'all')
    
    if mode == 'all':
        return True
    
    # Check specific variables
    if 'variables' in selection_config:
        if mode == 'include':
            return variable_name in selection_config['variables']
        else:  # exclude
            return variable_name not in selection_config['variables']
    
    # Check patterns
    if 'patterns' in selection_config:
        for pattern in selection_config['patterns']:
            pattern_regex = pattern.replace('*', '.*')
            if re.match(pattern_regex, variable_name, re.IGNORECASE):
                return mode == 'include'
    
    # Check categories - would need to be passed in or determined from variable
    
    # Default behavior
    return mode == 'exclude'


def process_base_aggregation(base_file: Path, from_freq: str, to_freq: str,
                           config: dict, aggregator: TimeSeriesAggregator, 
                           logger: logging.Logger) -> Optional[Path]:
    """Process aggregation for a base file"""
    # Check if target already exists
    if from_freq == to_freq:
        logger.debug(f"  Source and target frequencies match ({from_freq}), skipping")
        return None
    
    # Create output filename
    if 'selected' in base_file.stem:
        output_file = base_file.parent / f"base_selected_{to_freq}_from_{from_freq}.parquet"
    else:
        output_file = base_file.parent / f"base_all_{to_freq}_from_{from_freq}.parquet"
    
    # Skip if already exists and skip_existing is True
    if output_file.exists() and config.get('default_settings', {}).get('skip_existing', True):
        logger.info(f"  Skipping existing: {output_file.name}")
        return None
    
    # Read and process
    logger.info(f"  Aggregating {from_freq} → {to_freq}")
    df = pd.read_parquet(base_file)
    
    # Apply variable selection if needed
    selection_config = config.get('variable_selection', {})
    if selection_config.get('mode') != 'all':
        # Filter rows based on VariableName
        df = df[df['VariableName'].apply(lambda x: should_process_variable(x, selection_config))]
        
        if df.empty:
            logger.warning(f"  No variables selected for aggregation")
            return None
    
    # Aggregate
    aggregated_df = aggregate_base_columns(df, from_freq, to_freq, aggregator)
    
    if not aggregated_df.empty:
        aggregated_df.to_parquet(output_file, index=False)
        logger.info(f"  Created: {output_file.name}")
        return output_file
    
    return None


def process_comparison_aggregation(comp_file: Path, from_freq: str, to_freq: str,
                                 config: dict, aggregator: TimeSeriesAggregator,
                                 logger: logging.Logger) -> Optional[Path]:
    """Process aggregation for a comparison file"""
    # Extract info from filename
    match = re.match(r'var_(.+?)_(.+?)_(.+?)_b(\d+)\.parquet', comp_file.name)
    if not match:
        return None
    
    var_name_part, unit, source_freq, building_id = match.groups()
    
    if source_freq != from_freq:
        return None
    
    # Read first row to get actual variable name
    df_sample = pd.read_parquet(comp_file, columns=['variable_name'])
    if df_sample.empty:
        return None
    
    actual_var_name = df_sample['variable_name'].iloc[0]
    
    # Check if should process
    selection_config = config.get('variable_selection', {})
    if not should_process_variable(actual_var_name, selection_config):
        logger.debug(f"  Skipping {actual_var_name} based on selection criteria")
        return None
    
    # Create output filename
    output_file = comp_file.parent / f"var_{var_name_part}_{unit}_{to_freq}_from_{from_freq}_b{building_id}.parquet"
    
    # Skip if already exists
    if output_file.exists() and config.get('default_settings', {}).get('skip_existing', True):
        return None
    
    # Read and aggregate
    df = pd.read_parquet(comp_file)
    aggregated_df = aggregate_comparison_data(df, from_freq, to_freq, aggregator)
    
    if not aggregated_df.empty:
        aggregated_df.to_parquet(output_file, index=False)
        logger.info(f"  Created: {output_file.name}")
        return output_file
    
    return None


def run_timeseries_aggregation(
    aggregation_cfg: dict,
    job_output_dir: str,
    parsed_data_dir: str,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Run time series aggregation on parsed data
    
    Args:
        aggregation_cfg: Configuration from combined.json
        job_output_dir: Job output directory
        parsed_data_dir: Directory containing parsed data
        logger: Logger instance
        
    Returns:
        Summary of aggregation results
    """
    logger.info("[INFO] Starting time series aggregation post-processing...")
    
    # Initialize aggregator
    aggregator = TimeSeriesAggregator(aggregation_cfg, logger)
    
    # Get target frequencies
    target_frequencies = aggregation_cfg.get('default_settings', {}).get('target_frequencies', ['daily', 'monthly'])
    
    # Results tracking
    results = {
        'success': True,
        'base_files_created': 0,
        'comparison_files_created': 0,
        'variables_processed': 0,
        'frequencies_created': [],
        'errors': []
    }
    
    # Define frequency hierarchy
    freq_hierarchy = ['hourly', 'daily', 'monthly', 'yearly']
    
    # Process base data
    if aggregation_cfg.get('input_options', {}).get('use_base_data', True):
        logger.info("\n[INFO] Processing base data aggregations...")
        
        timeseries_dir = Path(parsed_data_dir) / 'timeseries'
        if timeseries_dir.exists():
            # Find existing base files
            base_files = {}
            for file in timeseries_dir.glob('base_*.parquet'):
                if '_from_' not in file.stem:  # Original files only
                    # Detect frequency
                    if '_hourly' in file.stem:
                        base_files['hourly'] = file
                    elif '_daily' in file.stem:
                        base_files['daily'] = file
                    elif '_monthly' in file.stem:
                        base_files['monthly'] = file
                    else:
                        # Detect from columns
                        try:
                            # Read a small sample to detect frequency
                            df_sample = pd.read_parquet(file)
                            freq = detect_frequency_from_columns(df_sample)
                            if freq != 'unknown':
                                base_files[freq] = file
                                logger.info(f"  Detected {freq} frequency in {file.name}")
                        except Exception as e:
                            logger.warning(f"  Failed to detect frequency in {file.name}: {e}")
            
            # Log available base files
            logger.info(f"  Found base files: {list(base_files.keys())}")
            
            # Create aggregations
            for i, source_freq in enumerate(freq_hierarchy):
                if source_freq in base_files:
                    logger.info(f"\n  Processing {source_freq} base data...")
                    for target_freq in target_frequencies:
                        target_idx = freq_hierarchy.index(target_freq) if target_freq in freq_hierarchy else -1
                        if target_idx > i:
                            logger.info(f"    Aggregating {source_freq} → {target_freq}")
                            output_file = process_base_aggregation(
                                base_files[source_freq], source_freq, target_freq,
                                aggregation_cfg, aggregator, logger
                            )
                            
                            if output_file:
                                results['base_files_created'] += 1
                                if target_freq not in results['frequencies_created']:
                                    results['frequencies_created'].append(target_freq)
                        elif target_idx == i:
                            logger.debug(f"    Skipping {target_freq} (same as source)")
                        else:
                            logger.debug(f"    Cannot aggregate {source_freq} → {target_freq}")
    
    # Process comparison data
    if aggregation_cfg.get('input_options', {}).get('use_variant_data', True):
        logger.info("\n[INFO] Processing comparison data aggregations...")
        
        # Check both parsed_data and parsed_modified_results
        comparison_dirs = []
        
        parsed_comp_dir = Path(parsed_data_dir) / 'comparisons'
        if parsed_comp_dir.exists():
            comparison_dirs.append(parsed_comp_dir)
        
        modified_dir = Path(job_output_dir) / 'parsed_modified_results' / 'comparisons'
        if modified_dir.exists():
            comparison_dirs.append(modified_dir)
        
        for comp_dir in comparison_dirs:
            logger.info(f"\n[INFO] Processing comparisons in: {comp_dir}")
            
            # Group files by frequency
            files_by_freq = defaultdict(list)
            
            for file in comp_dir.glob('var_*.parquet'):
                if '_from_' not in file.stem:  # Original files only
                    match = re.match(r'var_(.+?)_(.+?)_(.+?)_b(\d+)\.parquet', file.name)
                    if match:
                        _, _, freq, _ = match.groups()
                        files_by_freq[freq].append(file)
            
            # Process aggregations
            for source_freq, files in files_by_freq.items():
                if source_freq in freq_hierarchy:
                    source_idx = freq_hierarchy.index(source_freq)
                    
                    for target_freq in target_frequencies:
                        if freq_hierarchy.index(target_freq) > source_idx:
                            logger.info(f"\n  Aggregating {len(files)} {source_freq} files to {target_freq}")
                            
                            for comp_file in files:
                                output_file = process_comparison_aggregation(
                                    comp_file, source_freq, target_freq,
                                    aggregation_cfg, aggregator, logger
                                )
                                
                                if output_file:
                                    results['comparison_files_created'] += 1
                                    if target_freq not in results['frequencies_created']:
                                        results['frequencies_created'].append(target_freq)
    
    # Create summary
    total_files = results['base_files_created'] + results['comparison_files_created']
    
    logger.info(f"\n[SUCCESS] Time series aggregation completed:")
    logger.info(f"  - Base files created: {results['base_files_created']}")
    logger.info(f"  - Comparison files created: {results['comparison_files_created']}")
    logger.info(f"  - Total files created: {total_files}")
    logger.info(f"  - Frequencies available: {results['frequencies_created']}")
    
    return {
        'success': True,
        'variables_processed': results['variables_processed'],
        'frequencies_created': results['frequencies_created'],
        'output_dir': parsed_data_dir,
        'files_created': total_files,
        'base_data_processed': results['base_files_created'] > 0,
        'comparison_data_processed': results['comparison_files_created'] > 0
    }