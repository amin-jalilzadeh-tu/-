"""
c_surrogate/time_slice_utils.py

Enhanced utilities for filtering simulation results by time slices.
Now integrated with the new data extraction pipeline and supports
direct DataFrame operations from parquet files.

Author: Your Team
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TimeSliceManager:
    """
    Enhanced time slice manager that works with the new data pipeline.
    """
    
    def __init__(self, time_slice_config: Dict[str, Any] = None):
        """
        Initialize the time slice manager.
        
        Args:
            time_slice_config: Configuration for time slicing
        """
        self.config = time_slice_config or {}
        self.time_info_cache = {}
        
    def apply_time_slice_to_dataframe(self, 
                                    df: pd.DataFrame, 
                                    slice_config: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Apply time slicing to a DataFrame with E+ time columns or DateTime column.
        
        Args:
            df: DataFrame with time data
            slice_config: Override configuration
            
        Returns:
            Filtered DataFrame
        """
        config = slice_config or self.config
        
        if not config.get('enabled', False):
            return df
        
        # Detect time format
        if 'DateTime' in df.columns:
            return self._filter_by_datetime_column(df, config)
        else:
            # Look for E+ style columns
            time_cols = self._detect_time_columns(df)
            if time_cols:
                return self._filter_by_time_columns(df, config, time_cols)
        
        logger.warning("No time columns detected, returning original DataFrame")
        return df
    
    def _filter_by_datetime_column(self, 
                                 df: pd.DataFrame, 
                                 config: Dict[str, Any]) -> pd.DataFrame:
        """Filter DataFrame with DateTime column."""
        # Ensure DateTime is datetime type
        if not pd.api.types.is_datetime64_any_dtype(df['DateTime']):
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create time features
        df['Month'] = df['DateTime'].dt.month
        df['Hour'] = df['DateTime'].dt.hour
        df['DayOfWeek'] = df['DateTime'].dt.dayofweek
        df['IsWeekend'] = df['DayOfWeek'] >= 5
        
        # Apply filters
        mask = pd.Series(True, index=df.index)
        
        slice_type = config.get('slice_type', 'none')
        
        if slice_type == 'peak_months':
            season = config.get('season', 'both')
            if season == 'cooling':
                months = config.get('peak_cooling_months', [6, 7, 8])
                mask &= df['Month'].isin(months)
            elif season == 'heating':
                months = config.get('peak_heating_months', [12, 1, 2])
                mask &= df['Month'].isin(months)
            elif season == 'both':
                cooling_months = config.get('peak_cooling_months', [6, 7, 8])
                heating_months = config.get('peak_heating_months', [12, 1, 2])
                mask &= df['Month'].isin(cooling_months + heating_months)
        
        elif slice_type == 'time_of_day':
            hours = config.get('peak_hours', [14, 15, 16, 17])
            if isinstance(config.get('peak_hours_range'), dict):
                start = config['peak_hours_range']['start']
                end = config['peak_hours_range']['end']
                hours = list(range(start, end + 1))
            mask &= df['Hour'].isin(hours)
        
        elif slice_type == 'day_of_week':
            if config.get('analyze_weekends', True):
                mask &= df['IsWeekend']
            else:
                mask &= ~df['IsWeekend']
        
        elif slice_type == 'combined':
            filters = config.get('combined_filters', {})
            if 'months' in filters:
                mask &= df['Month'].isin(filters['months'])
            if 'hours' in filters:
                mask &= df['Hour'].isin(filters['hours'])
            if 'day_of_week' in filters:
                if filters['day_of_week'] == 'weekdays':
                    mask &= ~df['IsWeekend']
                elif filters['day_of_week'] == 'weekends':
                    mask &= df['IsWeekend']
        
        elif slice_type == 'custom':
            if 'start_date' in config and 'end_date' in config:
                start = pd.to_datetime(config['start_date'])
                end = pd.to_datetime(config['end_date'])
                mask &= (df['DateTime'] >= start) & (df['DateTime'] <= end)
        
        # Clean up temporary columns
        temp_cols = ['Month', 'Hour', 'DayOfWeek', 'IsWeekend']
        df_filtered = df[mask].copy()
        df_filtered = df_filtered.drop(columns=[col for col in temp_cols if col in df_filtered.columns])
        
        logger.info(f"Time slice filtering: {len(df)} -> {len(df_filtered)} rows")
        
        return df_filtered
    
    def _detect_time_columns(self, df: pd.DataFrame) -> List[str]:
        """Detect E+ style time columns."""
        return [col for col in df.columns if '/' in str(col) and ':' in str(col)]
    
    def _filter_by_time_columns(self, 
                              df: pd.DataFrame, 
                              config: Dict[str, Any],
                              time_cols: List[str]) -> pd.DataFrame:
        """Filter by E+ style time columns."""
        # Parse time information if not cached
        cache_key = f"{id(df)}_{len(time_cols)}"
        if cache_key not in self.time_info_cache:
            self.time_info_cache[cache_key] = parse_time_columns_enhanced(df, time_cols)
        
        time_info = self.time_info_cache[cache_key]
        
        if time_info.empty:
            return df
        
        # Filter based on configuration
        selected_cols = filter_columns_by_config(time_info, config)
        
        # Keep non-time columns
        non_time_cols = [col for col in df.columns if col not in time_cols]
        final_cols = non_time_cols + selected_cols
        
        return df[final_cols]


def parse_time_columns_enhanced(df: pd.DataFrame, time_cols: List[str] = None) -> pd.DataFrame:
    """
    Enhanced parsing of E+ time columns with better error handling.
    
    Args:
        df: DataFrame with E+ time columns
        time_cols: List of time columns to parse (auto-detect if None)
        
    Returns:
        DataFrame with parsed time information
    """
    if time_cols is None:
        time_cols = [col for col in df.columns if '/' in str(col) and ':' in str(col)]
    
    if not time_cols:
        logger.warning("No time columns found in DataFrame")
        return pd.DataFrame()
    
    time_info = []
    
    for col in time_cols:
        try:
            # Handle different E+ output formats
            # Format 1: "MM/DD  HH:MM:SS"
            # Format 2: "MM/DD HH:MM:SS"
            # Format 3: "MM/DD  HH:MM"
            
            col_str = str(col).strip()
            
            # Split by multiple spaces first, then single space
            parts = col_str.split('  ')
            if len(parts) == 1:
                parts = col_str.split(' ')
            
            if len(parts) >= 2:
                date_part = parts[0].strip()
                time_part = parts[1].strip()
                
                # Parse date
                if '/' in date_part:
                    month, day = date_part.split('/')
                    month = int(month)
                    day = int(day)
                else:
                    continue
                
                # Parse time
                if ':' in time_part:
                    time_components = time_part.split(':')
                    hour = int(time_components[0])
                    minute = int(time_components[1]) if len(time_components) > 1 else 0
                else:
                    continue
                
                # Create datetime for day of week calculation
                # Use a leap year to handle Feb 29
                dt = datetime(2024, month, day, hour, minute)
                
                time_info.append({
                    'column': col,
                    'month': month,
                    'day': day,
                    'hour': hour,
                    'minute': minute,
                    'day_of_week': dt.weekday(),
                    'is_weekend': dt.weekday() >= 5,
                    'is_peak_cooling': month in [6, 7, 8],
                    'is_peak_heating': month in [12, 1, 2],
                    'is_peak_hour': hour in [14, 15, 16, 17],
                    'is_business_hour': 8 <= hour <= 17 and dt.weekday() < 5
                })
                
        except Exception as e:
            logger.debug(f"Could not parse time column {col}: {e}")
            continue
    
    return pd.DataFrame(time_info)


def filter_columns_by_config(time_df: pd.DataFrame, config: Dict[str, Any]) -> List[str]:
    """
    Filter time columns based on configuration.
    
    Args:
        time_df: DataFrame with parsed time information
        config: Time slice configuration
        
    Returns:
        List of column names that match the filter criteria
    """
    if time_df.empty:
        return []
    
    # Start with all columns
    mask = pd.Series(True, index=time_df.index)
    
    slice_type = config.get('slice_type', 'none')
    
    if slice_type == 'peak_months':
        season = config.get('season', 'both')
        if season == 'cooling':
            mask &= time_df['is_peak_cooling']
        elif season == 'heating':
            mask &= time_df['is_peak_heating']
        elif season == 'both':
            mask &= time_df['is_peak_cooling'] | time_df['is_peak_heating']
    
    elif slice_type == 'time_of_day':
        hours = config.get('peak_hours', [14, 15, 16, 17])
        if isinstance(config.get('peak_hours_range'), dict):
            start = config['peak_hours_range']['start']
            end = config['peak_hours_range']['end']
            hours = list(range(start, end + 1))
        mask &= time_df['hour'].isin(hours)
    
    elif slice_type == 'day_of_week':
        if config.get('analyze_weekends', True):
            mask &= time_df['is_weekend']
        else:
            mask &= ~time_df['is_weekend']
    
    elif slice_type == 'combined':
        filters = config.get('combined_filters', {})
        if 'months' in filters:
            mask &= time_df['month'].isin(filters['months'])
        if 'hours' in filters:
            mask &= time_df['hour'].isin(filters['hours'])
        if 'day_of_week' in filters:
            if filters['day_of_week'] == 'weekdays':
                mask &= ~time_df['is_weekend']
            elif filters['day_of_week'] == 'weekends':
                mask &= time_df['is_weekend']
    
    elif slice_type == 'custom':
        # Custom filters
        if 'months' in config:
            mask &= time_df['month'].isin(config['months'])
        if 'hours' in config:
            mask &= time_df['hour'].isin(config['hours'])
        if 'weekdays_only' in config and config['weekdays_only']:
            mask &= ~time_df['is_weekend']
        if 'weekends_only' in config and config['weekends_only']:
            mask &= time_df['is_weekend']
        if 'specific_days' in config:
            day_mask = pd.Series(False, index=time_df.index)
            for month, day in config['specific_days']:
                day_mask |= (time_df['month'] == month) & (time_df['day'] == day)
            mask &= day_mask
    
    return time_df[mask]['column'].tolist()


def aggregate_time_sliced_data(
    df: pd.DataFrame,
    time_slice_config: Dict[str, Any],
    aggregation_method: str = 'sum',
    group_by: List[str] = None
) -> pd.DataFrame:
    """
    Aggregate data after time slicing.
    
    Args:
        df: DataFrame with time-sliced data
        time_slice_config: Time slice configuration
        aggregation_method: How to aggregate ('sum', 'mean', 'max', etc.)
        group_by: Columns to group by before aggregation
        
    Returns:
        Aggregated DataFrame
    """
    # Apply time slicing first
    manager = TimeSliceManager(time_slice_config)
    df_sliced = manager.apply_time_slice_to_dataframe(df)
    
    if df_sliced.empty:
        logger.warning("Time slicing resulted in empty DataFrame")
        return pd.DataFrame()
    
    # Determine grouping columns
    if group_by is None:
        # Auto-detect grouping columns
        group_by = []
        for col in ['building_id', 'Zone', 'Variable', 'VariableName']:
            if col in df_sliced.columns:
                group_by.append(col)
    
    if not group_by:
        logger.warning("No grouping columns found")
        return df_sliced
    
    # Get numeric columns
    numeric_cols = df_sliced.select_dtypes(include=[np.number]).columns.tolist()
    value_cols = [col for col in numeric_cols if col not in group_by]
    
    if not value_cols:
        logger.warning("No numeric columns to aggregate")
        return df_sliced
    
    # Aggregate
    agg_funcs = {}
    for col in value_cols:
        if aggregation_method == 'sum':
            agg_funcs[col] = 'sum'
        elif aggregation_method == 'mean':
            agg_funcs[col] = 'mean'
        elif aggregation_method == 'max':
            agg_funcs[col] = 'max'
        elif aggregation_method == 'min':
            agg_funcs[col] = 'min'
        elif aggregation_method == 'std':
            agg_funcs[col] = 'std'
        else:
            agg_funcs[col] = aggregation_method
    
    result = df_sliced.groupby(group_by).agg(agg_funcs).reset_index()
    
    # Add metadata about the time slice
    result['time_slice_type'] = time_slice_config.get('slice_type', 'none')
    result['aggregation_method'] = aggregation_method
    
    return result


def compare_time_slices(
    df: pd.DataFrame,
    time_slice_comparisons: List[Dict[str, Any]],
    target_variable: str = 'Value',
    comparison_metrics: List[str] = None
) -> pd.DataFrame:
    """
    Compare results across multiple time slices.
    
    Args:
        df: Base DataFrame
        time_slice_comparisons: List of time slice configurations to compare
        target_variable: Variable to compare
        comparison_metrics: Metrics to calculate ['mean', 'sum', 'peak', 'std']
        
    Returns:
        DataFrame with comparison results
    """
    if comparison_metrics is None:
        comparison_metrics = ['mean', 'sum', 'peak', 'std']
    
    comparison_results = []
    
    for slice_config in time_slice_comparisons:
        if not slice_config.get('enabled', True):
            continue
        
        # Apply time slice
        manager = TimeSliceManager(slice_config)
        df_sliced = manager.apply_time_slice_to_dataframe(df)
        
        if df_sliced.empty:
            continue
        
        # Calculate metrics
        result = {
            'slice_name': slice_config.get('name', 'unnamed'),
            'slice_type': slice_config.get('slice_type', 'custom'),
            'description': slice_config.get('description', ''),
            'n_datapoints': len(df_sliced)
        }
        
        if target_variable in df_sliced.columns:
            values = df_sliced[target_variable]
            
            if 'mean' in comparison_metrics:
                result['mean'] = values.mean()
            if 'sum' in comparison_metrics:
                result['sum'] = values.sum()
            if 'peak' in comparison_metrics:
                result['peak'] = values.max()
            if 'std' in comparison_metrics:
                result['std'] = values.std()
            if 'min' in comparison_metrics:
                result['min'] = values.min()
            if 'percentile_95' in comparison_metrics:
                result['percentile_95'] = values.quantile(0.95)
        
        comparison_results.append(result)
    
    return pd.DataFrame(comparison_results)


def create_time_slice_report(
    base_data: pd.DataFrame,
    modified_data: pd.DataFrame,
    time_slice_config: Dict[str, Any],
    output_variables: List[str],
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Create a comprehensive time slice analysis report.
    
    Args:
        base_data: Baseline simulation data
        modified_data: Modified simulation data
        time_slice_config: Time slicing configuration
        output_variables: Variables to analyze
        output_path: Optional path to save report
        
    Returns:
        Dictionary with analysis results
    """
    report = {
        'timestamp': datetime.now().isoformat(),
        'config': time_slice_config,
        'results': {}
    }
    
    manager = TimeSliceManager(time_slice_config)
    
    for var in output_variables:
        var_results = {
            'base': {},
            'modified': {},
            'comparison': {}
        }
        
        # Filter for variable
        base_var = base_data[base_data['Variable'] == var] if 'Variable' in base_data.columns else base_data
        mod_var = modified_data[modified_data['Variable'] == var] if 'Variable' in modified_data.columns else modified_data
        
        # Apply time slicing
        base_sliced = manager.apply_time_slice_to_dataframe(base_var)
        mod_sliced = manager.apply_time_slice_to_dataframe(mod_var)
        
        # Calculate statistics
        if not base_sliced.empty and 'Value' in base_sliced.columns:
            var_results['base'] = {
                'mean': base_sliced['Value'].mean(),
                'sum': base_sliced['Value'].sum(),
                'peak': base_sliced['Value'].max(),
                'std': base_sliced['Value'].std(),
                'n_points': len(base_sliced)
            }
        
        if not mod_sliced.empty and 'Value' in mod_sliced.columns:
            var_results['modified'] = {
                'mean': mod_sliced['Value'].mean(),
                'sum': mod_sliced['Value'].sum(),
                'peak': mod_sliced['Value'].max(),
                'std': mod_sliced['Value'].std(),
                'n_points': len(mod_sliced)
            }
        
        # Calculate differences
        if var_results['base'] and var_results['modified']:
            var_results['comparison'] = {
                'mean_change': var_results['modified']['mean'] - var_results['base']['mean'],
                'sum_change': var_results['modified']['sum'] - var_results['base']['sum'],
                'peak_change': var_results['modified']['peak'] - var_results['base']['peak'],
                'mean_change_percent': ((var_results['modified']['mean'] - var_results['base']['mean']) / 
                                      var_results['base']['mean'] * 100) if var_results['base']['mean'] != 0 else np.nan
            }
        
        report['results'][var] = var_results
    
    # Save report if path provided
    if output_path:
        import json
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
    
    return report


# Legacy functions for backward compatibility
def filter_results_by_time_slice(
    df_results: pd.DataFrame,
    time_slice_config: Dict[str, Any]
) -> pd.DataFrame:
    """
    Legacy function - redirects to new implementation.
    """
    manager = TimeSliceManager(time_slice_config)
    return manager.apply_time_slice_to_dataframe(df_results)


def parse_time_columns(df_results: pd.DataFrame) -> pd.DataFrame:
    """
    Legacy function - redirects to enhanced version.
    """
    return parse_time_columns_enhanced(df_results)


def get_peak_hours(
    df_results: pd.DataFrame,
    variable_name: str,
    n_peak_hours: int = 100,
    peak_type: str = "max"
) -> List[str]:
    """
    Identify peak hours for a specific variable.
    
    Args:
        df_results: Results DataFrame
        variable_name: Variable to analyze
        n_peak_hours: Number of peak hours to identify
        peak_type: "max" for highest values, "min" for lowest
        
    Returns:
        List of column names representing peak hours
    """
    # Filter for the specific variable
    var_data = df_results[df_results['VariableName'] == variable_name]
    
    if var_data.empty:
        logger.warning(f"Variable {variable_name} not found in results")
        return []
    
    # Get time columns
    time_df = parse_time_columns_enhanced(df_results)
    time_cols = time_df['column'].tolist()
    
    # Sum across all buildings for each time column
    time_sums = {}
    for col in time_cols:
        if col in var_data.columns:
            time_sums[col] = var_data[col].sum()
    
    # Sort and get top N
    sorted_times = sorted(time_sums.items(), 
                         key=lambda x: x[1], 
                         reverse=(peak_type == "max"))
    
    return [col for col, _ in sorted_times[:n_peak_hours]]


def get_seasonal_definitions() -> Dict[str, List[int]]:
    """
    Return standard seasonal month definitions.
    """
    return {
        "winter": [12, 1, 2],
        "spring": [3, 4, 5],
        "summer": [6, 7, 8],
        "fall": [9, 10, 11],
        "heating_season": [11, 12, 1, 2, 3],
        "cooling_season": [5, 6, 7, 8, 9],
        "shoulder_months": [4, 10]
    }


def apply_predefined_slice(
    df_results: pd.DataFrame,
    slice_name: str
) -> pd.DataFrame:
    """
    Apply a predefined time slice configuration.
    """
    predefined_slices = {
        "peak_cooling_months": {
            "slice_type": "peak_months",
            "season": "cooling",
            "enabled": True
        },
        "peak_heating_months": {
            "slice_type": "peak_months",
            "season": "heating",
            "enabled": True
        },
        "afternoon_peak": {
            "slice_type": "time_of_day",
            "peak_hours": [14, 15, 16, 17, 18],
            "enabled": True
        },
        "morning_startup": {
            "slice_type": "time_of_day",
            "peak_hours": [6, 7, 8, 9],
            "enabled": True
        },
        "weekend_base": {
            "slice_type": "day_of_week",
            "analyze_weekends": True,
            "enabled": True
        },
        "summer_afternoons": {
            "slice_type": "combined",
            "combined_filters": {
                "months": [6, 7, 8],
                "hours": [12, 13, 14, 15, 16, 17, 18]
            },
            "enabled": True
        },
        "winter_mornings": {
            "slice_type": "combined",
            "combined_filters": {
                "months": [12, 1, 2],
                "hours": [6, 7, 8, 9, 10]
            },
            "enabled": True
        }
    }
    
    if slice_name not in predefined_slices:
        logger.warning(f"Unknown predefined slice: {slice_name}")
        return df_results
    
    manager = TimeSliceManager(predefined_slices[slice_name])
    return manager.apply_time_slice_to_dataframe(df_results)


def aggregate_by_time_pattern(
    df_results: pd.DataFrame,
    pattern: str = "hourly_profile"
) -> pd.DataFrame:
    """
    Aggregate results by time patterns for analysis.
    """
    time_df = parse_time_columns_enhanced(df_results)
    
    if pattern == "hourly_profile":
        # Group columns by hour
        hour_groups = {}
        for _, row in time_df.iterrows():
            hour = row['hour']
            if hour not in hour_groups:
                hour_groups[hour] = []
            hour_groups[hour].append(row['column'])
        
        # Create aggregated DataFrame
        agg_data = []
        for hour, cols in sorted(hour_groups.items()):
            valid_cols = [c for c in cols if c in df_results.columns]
            if valid_cols:
                hour_mean = df_results[valid_cols].mean(axis=1)
                agg_data.append({
                    'Hour': hour,
                    'MeanValue': hour_mean.mean(),
                    'StdValue': hour_mean.std(),
                    'NumDataPoints': len(valid_cols)
                })
        
        return pd.DataFrame(agg_data)
    
    elif pattern == "monthly_profile":
        # Group by month
        month_groups = {}
        for _, row in time_df.iterrows():
            month = row['month']
            if month not in month_groups:
                month_groups[month] = []
            month_groups[month].append(row['column'])
        
        agg_data = []
        for month, cols in sorted(month_groups.items()):
            valid_cols = [c for c in cols if c in df_results.columns]
            if valid_cols:
                month_sum = df_results[valid_cols].sum(axis=1)
                agg_data.append({
                    'Month': month,
                    'TotalValue': month_sum.sum(),
                    'MeanValue': month_sum.mean(),
                    'NumDataPoints': len(valid_cols)
                })
        
        return pd.DataFrame(agg_data)
    
    elif pattern == "day_type":
        # Separate weekday vs weekend
        weekday_cols = time_df[~time_df['is_weekend']]['column'].tolist()
        weekend_cols = time_df[time_df['is_weekend']]['column'].tolist()
        
        weekday_valid = [c for c in weekday_cols if c in df_results.columns]
        weekend_valid = [c for c in weekend_cols if c in df_results.columns]
        
        agg_data = []
        
        if weekday_valid:
            weekday_mean = df_results[weekday_valid].mean(axis=1)
            agg_data.append({
                'DayType': 'Weekday',
                'MeanValue': weekday_mean.mean(),
                'StdValue': weekday_mean.std(),
                'NumDataPoints': len(weekday_valid)
            })
        
        if weekend_valid:
            weekend_mean = df_results[weekend_valid].mean(axis=1)
            agg_data.append({
                'DayType': 'Weekend',
                'MeanValue': weekend_mean.mean(),
                'StdValue': weekend_mean.std(),
                'NumDataPoints': len(weekend_valid)
            })
        
        return pd.DataFrame(agg_data)
    
    return df_results