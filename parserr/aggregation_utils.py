"""
Aggregation Utilities Module
Handles smart aggregation of timeseries data respecting original frequencies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
import logging


class SmartAggregator:
    """Smart aggregation that respects variable types and original frequencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define aggregation rules by variable pattern
        self.aggregation_rules = {
            'sum': ['Energy', 'Consumption', 'Total', 'Volume'],
            'mean': ['Temperature', 'Rate', 'Power', 'Humidity', 'Pressure', 
                    'Setpoint', 'Fraction', 'Coefficient'],
            'max': ['Peak', 'Maximum'],
            'min': ['Minimum'],
            'last': ['Status', 'Mode', 'State']
        }
    
    def determine_aggregation_method(self, variable_name: str) -> str:
        """
        Determine aggregation method based on variable name
        
        Args:
            variable_name: Name of the variable
            
        Returns:
            Aggregation method ('sum', 'mean', 'max', 'min', 'last')
        """
        var_lower = variable_name.lower()
        
        # Check each rule
        for method, patterns in self.aggregation_rules.items():
            for pattern in patterns:
                if pattern.lower() in var_lower:
                    return method
        
        # Default to mean for unknown variables
        return 'mean'
    
    def can_aggregate(self, from_freq: str, to_freq: str) -> bool:
        """
        Check if aggregation from one frequency to another is valid
        
        Args:
            from_freq: Source frequency
            to_freq: Target frequency
            
        Returns:
            True if aggregation is valid
        """
        # Define frequency hierarchy
        freq_hierarchy = {
            'timestep': 0,
            'hourly': 1,
            'daily': 2,
            'monthly': 3,
            'yearly': 4
        }
        
        from_level = freq_hierarchy.get(from_freq.lower(), -1)
        to_level = freq_hierarchy.get(to_freq.lower(), -1)
        
        # Can only aggregate to higher level (larger time period)
        return from_level < to_level and from_level >= 0 and to_level >= 0
    
    def aggregate_by_variable(self, df: pd.DataFrame,
                            from_freq: str,
                            to_freq: str,
                            value_col: str = 'Value',
                            time_col: str = 'DateTime',
                            group_cols: List[str] = None) -> pd.DataFrame:
        """
        Aggregate data respecting variable types
        
        Args:
            df: Input dataframe
            from_freq: Source frequency
            to_freq: Target frequency
            value_col: Column containing values
            time_col: Column containing timestamps
            group_cols: Additional grouping columns
            
        Returns:
            Aggregated dataframe
        """
        # Check if aggregation is valid
        if not self.can_aggregate(from_freq, to_freq):
            self.logger.warning(f"Cannot aggregate from {from_freq} to {to_freq}")
            return df
        
        # Default group columns
        if group_cols is None:
            group_cols = ['building_id', 'variant_id', 'Variable', 'Zone']
        
        # Filter to existing columns
        group_cols = [col for col in group_cols if col in df.columns]
        
        # Ensure datetime
        df[time_col] = pd.to_datetime(df[time_col])
        
        # Map frequency to pandas frequency
        freq_map = {
            'hourly': 'H',
            'daily': 'D',
            'monthly': 'M',
            'yearly': 'Y'
        }
        
        pandas_freq = freq_map.get(to_freq.lower(), 'D')
        
        # Group by variable to apply different aggregation methods
        aggregated_dfs = []
        
        for variable in df['Variable'].unique():
            var_df = df[df['Variable'] == variable].copy()
            
            # Determine aggregation method
            agg_method = self.determine_aggregation_method(variable)
            
            # Set index for resampling
            var_df = var_df.set_index(time_col)
            
            # Group and resample
            if group_cols:
                grouped = var_df.groupby(group_cols)[value_col]
                
                if agg_method == 'sum':
                    resampled = grouped.resample(pandas_freq).sum()
                elif agg_method == 'mean':
                    resampled = grouped.resample(pandas_freq).mean()
                elif agg_method == 'max':
                    resampled = grouped.resample(pandas_freq).max()
                elif agg_method == 'min':
                    resampled = grouped.resample(pandas_freq).min()
                else:  # last
                    resampled = grouped.resample(pandas_freq).last()
            else:
                # No grouping
                if agg_method == 'sum':
                    resampled = var_df[value_col].resample(pandas_freq).sum()
                elif agg_method == 'mean':
                    resampled = var_df[value_col].resample(pandas_freq).mean()
                elif agg_method == 'max':
                    resampled = var_df[value_col].resample(pandas_freq).max()
                elif agg_method == 'min':
                    resampled = var_df[value_col].resample(pandas_freq).min()
                else:  # last
                    resampled = var_df[value_col].resample(pandas_freq).last()
            
            # Reset index
            resampled_df = resampled.reset_index()
            
            # Add metadata back
            if 'Units' in var_df.columns:
                resampled_df['Units'] = var_df['Units'].iloc[0]
            if 'category' in var_df.columns:
                resampled_df['category'] = var_df['category'].iloc[0]
            
            resampled_df['aggregation_method'] = agg_method
            resampled_df['source_frequency'] = from_freq
            
            aggregated_dfs.append(resampled_df)
        
        # Combine all aggregated data
        if aggregated_dfs:
            result = pd.concat(aggregated_dfs, ignore_index=True)
            return result
        else:
            return pd.DataFrame()
    
    def create_aggregation_pipeline(self, df: pd.DataFrame,
                                  original_freq: str,
                                  target_freqs: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Create multiple aggregation levels from original data
        
        Args:
            df: Original dataframe
            original_freq: Original frequency of data
            target_freqs: List of target frequencies (default: hourly, daily, monthly)
            
        Returns:
            Dictionary of frequency -> aggregated dataframe
        """
        if target_freqs is None:
            target_freqs = ['hourly', 'daily', 'monthly']
        
        results = {}
        current_df = df.copy()
        current_freq = original_freq
        
        # Process each target frequency in order
        freq_order = ['timestep', 'hourly', 'daily', 'monthly', 'yearly']
        
        for target_freq in freq_order:
            if target_freq in target_freqs:
                if self.can_aggregate(current_freq, target_freq):
                    # Aggregate to this level
                    aggregated = self.aggregate_by_variable(
                        current_df, 
                        current_freq, 
                        target_freq
                    )
                    results[target_freq] = aggregated
                    
                    # Update current data for next level
                    current_df = aggregated
                    current_freq = target_freq
        
        return results
    
    def respect_original_frequency(self, df: pd.DataFrame,
                                 reporting_freq_col: str = 'ReportingFrequency') -> Dict[str, pd.DataFrame]:
        """
        Split data by original reporting frequency
        
        Args:
            df: Input dataframe with mixed frequencies
            reporting_freq_col: Column containing reporting frequency
            
        Returns:
            Dictionary of frequency -> dataframe
        """
        freq_mapping = {
            'Timestep': 'timestep',
            'Hourly': 'hourly', 
            'Daily': 'daily',
            'Monthly': 'monthly',
            'RunPeriod': 'runperiod',
            'Annual': 'yearly'
        }
        
        frequency_dfs = {}
        
        if reporting_freq_col in df.columns:
            for orig_freq, mapped_freq in freq_mapping.items():
                freq_df = df[df[reporting_freq_col] == orig_freq].copy()
                if not freq_df.empty:
                    frequency_dfs[mapped_freq] = freq_df
                    self.logger.info(f"Found {len(freq_df)} rows with {mapped_freq} frequency")
        else:
            # If no frequency column, assume all data is same frequency
            frequency_dfs['unknown'] = df
        
        return frequency_dfs
    
    def aggregate_mixed_frequencies(self, df: pd.DataFrame,
                                  target_freq: str = 'daily') -> pd.DataFrame:
        """
        Aggregate data with mixed original frequencies to target frequency
        
        Args:
            df: Input dataframe with mixed frequencies
            target_freq: Target frequency
            
        Returns:
            Aggregated dataframe
        """
        # First split by original frequency
        freq_dfs = self.respect_original_frequency(df)
        
        aggregated_results = []
        
        for source_freq, freq_df in freq_dfs.items():
            if source_freq == target_freq:
                # Already at target frequency, no aggregation needed
                aggregated_results.append(freq_df)
            elif self.can_aggregate(source_freq, target_freq):
                # Aggregate to target
                aggregated = self.aggregate_by_variable(
                    freq_df,
                    source_freq,
                    target_freq
                )
                aggregated_results.append(aggregated)
            else:
                # Cannot aggregate (e.g., monthly to daily)
                self.logger.warning(
                    f"Skipping {len(freq_df)} rows at {source_freq} frequency "
                    f"(cannot aggregate to {target_freq})"
                )
        
        # Combine results
        if aggregated_results:
            return pd.concat(aggregated_results, ignore_index=True)
        else:
            return pd.DataFrame()


def calculate_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate derived metrics from aggregated data
    
    Args:
        df: Aggregated dataframe
        
    Returns:
        Dataframe with additional derived metrics
    """
    df_copy = df.copy()
    
    # Example: Calculate COP from heating/cooling energy and electricity
    if 'Zone Air System Sensible Heating Energy' in df['Variable'].values and \
       'Heating:Electricity' in df['Variable'].values:
        
        # This would need more complex logic to properly match zones and times
        pass
    
    # Example: Calculate total site energy
    energy_vars = df[df['Variable'].str.contains('Energy', na=False)]
    if not energy_vars.empty:
        # Group by time and sum all energy
        pass
    
    return df_copy


def validate_aggregation(original_df: pd.DataFrame, 
                        aggregated_df: pd.DataFrame,
                        tolerance: float = 0.01) -> Dict[str, any]:
    """
    Validate aggregation results
    
    Args:
        original_df: Original data
        aggregated_df: Aggregated data
        tolerance: Tolerance for comparison
        
    Returns:
        Validation results
    """
    validation_results = {
        'valid': True,
        'issues': [],
        'statistics': {}
    }
    
    # Check row counts
    validation_results['statistics']['original_rows'] = len(original_df)
    validation_results['statistics']['aggregated_rows'] = len(aggregated_df)
    
    # For energy variables, check if totals match
    if 'Variable' in original_df.columns and 'Value' in original_df.columns:
        energy_vars = original_df[original_df['Variable'].str.contains('Energy', na=False)]
        
        for var in energy_vars['Variable'].unique():
            original_sum = original_df[original_df['Variable'] == var]['Value'].sum()
            
            if var in aggregated_df['Variable'].values:
                aggregated_sum = aggregated_df[aggregated_df['Variable'] == var]['Value'].sum()
                
                diff_pct = abs(original_sum - aggregated_sum) / original_sum if original_sum != 0 else 0
                
                if diff_pct > tolerance:
                    validation_results['valid'] = False
                    validation_results['issues'].append({
                        'variable': var,
                        'original_sum': original_sum,
                        'aggregated_sum': aggregated_sum,
                        'difference_pct': diff_pct
                    })
    
    return validation_results