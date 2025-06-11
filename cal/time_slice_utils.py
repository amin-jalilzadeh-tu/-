"""
time_slice_utils.py

Utilities for filtering simulation results by time slices (months, hours, weekdays/weekends)
for more granular sensitivity analysis.

Author: Your Team
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def parse_time_columns(df_results: pd.DataFrame) -> pd.DataFrame:
    """
    Parse date/time information from E+ output columns.
    Adds columns: Year, Month, Day, Hour, DayOfWeek, IsWeekend
    
    Assumes columns like "01/01  01:00:00", "01/01  02:00:00", etc.
    """
    # Get all day columns (those that match the E+ date/time format)
    day_cols = [col for col in df_results.columns if '/' in col and ':' in col]
    
    if not day_cols:
        logger.warning("No time columns found in results DataFrame")
        return df_results
    
    # Create a mapping of column to datetime info
    time_info = []
    for col in day_cols:
        try:
            # Parse "MM/DD  HH:MM:SS" format
            parts = col.split()
            if len(parts) >= 2:
                date_part = parts[0]  # "01/01"
                time_part = parts[1]  # "01:00:00"
                
                month, day = date_part.split('/')
                hour = int(time_part.split(':')[0])
                
                # Assume current year or a default year
                dt = datetime(2024, int(month), int(day), hour)
                
                time_info.append({
                    'column': col,
                    'month': int(month),
                    'day': int(day),
                    'hour': hour,
                    'day_of_week': dt.weekday(),  # 0=Monday, 6=Sunday
                    'is_weekend': dt.weekday() >= 5
                })
        except Exception as e:
            logger.debug(f"Could not parse time column {col}: {e}")
            continue
    
    return pd.DataFrame(time_info)


def filter_results_by_time_slice(
    df_results: pd.DataFrame,
    time_slice_config: Dict[str, Any]
) -> pd.DataFrame:
    """
    Filter simulation results based on time slice configuration.
    
    Args:
        df_results: Results DataFrame with E+ time columns
        time_slice_config: Dict with time filtering options:
            {
                "months": [1, 7, 12],  # January, July, December
                "hours": [14, 15, 16],  # 2-4 PM
                "weekdays_only": True,
                "weekends_only": False,
                "specific_days": [(1, 15), (7, 4)]  # Jan 15, July 4
            }
    
    Returns:
        Filtered DataFrame with only the specified time slices
    """
    # Parse time information from columns
    time_df = parse_time_columns(df_results)
    
    if time_df.empty:
        return df_results
    
    # Start with all columns
    selected_cols = set(time_df['column'].tolist())
    
    # Filter by months
    if "months" in time_slice_config:
        months = time_slice_config["months"]
        selected_cols &= set(time_df[time_df['month'].isin(months)]['column'])
    
    # Filter by hours
    if "hours" in time_slice_config:
        hours = time_slice_config["hours"]
        selected_cols &= set(time_df[time_df['hour'].isin(hours)]['column'])
    
    # Filter by weekdays/weekends
    if time_slice_config.get("weekdays_only", False):
        selected_cols &= set(time_df[~time_df['is_weekend']]['column'])
    elif time_slice_config.get("weekends_only", False):
        selected_cols &= set(time_df[time_df['is_weekend']]['column'])
    
    # Filter by specific days
    if "specific_days" in time_slice_config:
        specific_day_cols = []
        for month, day in time_slice_config["specific_days"]:
            day_cols = time_df[(time_df['month'] == month) & 
                              (time_df['day'] == day)]['column'].tolist()
            specific_day_cols.extend(day_cols)
        selected_cols &= set(specific_day_cols)
    
    # Keep non-time columns (BuildingID, VariableName, etc.)
    non_time_cols = [col for col in df_results.columns if col not in time_df['column'].tolist()]
    final_cols = non_time_cols + list(selected_cols)
    
    return df_results[final_cols]


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
        variable_name: Variable to analyze (e.g., "Cooling:EnergyTransfer [J](Hourly)")
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
    time_df = parse_time_columns(df_results)
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
    Can be customized based on location/climate.
    """
    return {
        "winter": [12, 1, 2],
        "spring": [3, 4, 5],
        "summer": [6, 7, 8],
        "fall": [9, 10, 11],
        "heating_season": [11, 12, 1, 2, 3],  # Extended heating
        "cooling_season": [5, 6, 7, 8, 9],    # Extended cooling
        "shoulder_months": [4, 10]             # Transition months
    }


def apply_predefined_slice(
    df_results: pd.DataFrame,
    slice_name: str
) -> pd.DataFrame:
    """
    Apply a predefined time slice configuration.
    
    Available slices:
    - "peak_cooling_months": July, August
    - "peak_heating_months": January, February  
    - "afternoon_peak": 2-6 PM on weekdays
    - "morning_startup": 6-9 AM on weekdays
    - "weekend_base": All weekend hours
    - "summer_afternoons": June-August, 12-6 PM
    - "winter_mornings": Dec-Feb, 6-10 AM
    """
    predefined_slices = {
        "peak_cooling_months": {
            "months": [7, 8]
        },
        "peak_heating_months": {
            "months": [1, 2]
        },
        "afternoon_peak": {
            "hours": [14, 15, 16, 17, 18],
            "weekdays_only": True
        },
        "morning_startup": {
            "hours": [6, 7, 8, 9],
            "weekdays_only": True
        },
        "weekend_base": {
            "weekends_only": True
        },
        "summer_afternoons": {
            "months": [6, 7, 8],
            "hours": [12, 13, 14, 15, 16, 17, 18]
        },
        "winter_mornings": {
            "months": [12, 1, 2],
            "hours": [6, 7, 8, 9, 10]
        }
    }
    
    if slice_name not in predefined_slices:
        logger.warning(f"Unknown predefined slice: {slice_name}")
        return df_results
    
    return filter_results_by_time_slice(df_results, predefined_slices[slice_name])


def aggregate_by_time_pattern(
    df_results: pd.DataFrame,
    pattern: str = "hourly_profile"
) -> pd.DataFrame:
    """
    Aggregate results by time patterns for analysis.
    
    Patterns:
    - "hourly_profile": Average by hour of day
    - "monthly_profile": Sum by month
    - "day_type": Separate weekday vs weekend
    """
    time_df = parse_time_columns(df_results)
    
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
                    'MeanValue': hour_mean.mean()
                })
        
        return pd.DataFrame(agg_data)
    
    # Add other patterns as needed
    
    return df_results