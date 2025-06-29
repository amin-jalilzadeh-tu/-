"""
c_sensitivity/time_slicer.py

Time slicing utilities for sensitivity analysis.
Enables analysis on specific time periods like peak months, hours of day, or weekends.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
import logging


class TimeSlicer:
    """Handles time-based filtering of simulation data for sensitivity analysis"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Default peak months (can be overridden)
        self.default_peak_cooling_months = [6, 7, 8]  # June, July, August
        self.default_peak_heating_months = [12, 1, 2]  # December, January, February
        self.default_peak_hours = [14, 15, 16, 17]    # 2pm-5pm
        
    def slice_data(self, 
                   df: pd.DataFrame,
                   time_config: Dict[str, any],
                   datetime_col: str = 'DateTime') -> pd.DataFrame:
        """
        Apply time slicing to a DataFrame based on configuration
        
        Args:
            df: DataFrame with datetime column
            time_config: Time slicing configuration
            datetime_col: Name of datetime column
            
        Returns:
            Filtered DataFrame
        """
        if not time_config.get('enabled', False):
            return df
        
        # Ensure datetime column is datetime type
        if datetime_col in df.columns:
            df = df.copy()
            df[datetime_col] = pd.to_datetime(df[datetime_col])
        else:
            self.logger.warning(f"DateTime column '{datetime_col}' not found. Returning unfiltered data.")
            return df
        
        slice_type = time_config.get('slice_type', 'none')
        
        if slice_type == 'peak_months':
            return self._filter_peak_months(df, time_config, datetime_col)
        elif slice_type == 'time_of_day':
            return self._filter_time_of_day(df, time_config, datetime_col)
        elif slice_type == 'day_of_week':
            return self._filter_day_of_week(df, time_config, datetime_col)
        elif slice_type == 'custom':
            return self._filter_custom(df, time_config, datetime_col)
        elif slice_type == 'combined':
            return self._filter_combined(df, time_config, datetime_col)
        else:
            return df
    
    def _filter_peak_months(self, 
                           df: pd.DataFrame,
                           config: Dict,
                           datetime_col: str) -> pd.DataFrame:
        """Filter data for peak cooling or heating months"""
        season = config.get('season', 'cooling')
        
        if season == 'cooling':
            months = config.get('peak_cooling_months', self.default_peak_cooling_months)
        elif season == 'heating':
            months = config.get('peak_heating_months', self.default_peak_heating_months)
        else:
            # Both seasons
            cooling_months = config.get('peak_cooling_months', self.default_peak_cooling_months)
            heating_months = config.get('peak_heating_months', self.default_peak_heating_months)
            months = cooling_months + heating_months
        
        mask = df[datetime_col].dt.month.isin(months)
        filtered_df = df[mask].copy()
        
        self.logger.info(f"Filtered to {len(filtered_df)} records for months: {months}")
        return filtered_df
    
    def _filter_time_of_day(self,
                           df: pd.DataFrame,
                           config: Dict,
                           datetime_col: str) -> pd.DataFrame:
        """Filter data for specific hours of the day"""
        peak_hours = config.get('peak_hours', self.default_peak_hours)
        
        # Handle different hour specifications
        if isinstance(peak_hours, dict):
            # e.g., {"start": 14, "end": 17}
            start_hour = peak_hours.get('start', 14)
            end_hour = peak_hours.get('end', 17)
            mask = (df[datetime_col].dt.hour >= start_hour) & (df[datetime_col].dt.hour <= end_hour)
        else:
            # List of specific hours
            mask = df[datetime_col].dt.hour.isin(peak_hours)
        
        filtered_df = df[mask].copy()
        
        self.logger.info(f"Filtered to {len(filtered_df)} records for peak hours")
        return filtered_df
    
    def _filter_day_of_week(self,
                           df: pd.DataFrame,
                           config: Dict,
                           datetime_col: str) -> pd.DataFrame:
        """Filter for weekends or weekdays"""
        analyze_weekends = config.get('analyze_weekends', True)
        
        # Monday=0, Sunday=6
        if analyze_weekends:
            mask = df[datetime_col].dt.dayofweek.isin([5, 6])  # Saturday, Sunday
            day_type = "weekends"
        else:
            mask = df[datetime_col].dt.dayofweek.isin([0, 1, 2, 3, 4])  # Monday-Friday
            day_type = "weekdays"
        
        filtered_df = df[mask].copy()
        
        self.logger.info(f"Filtered to {len(filtered_df)} records for {day_type}")
        return filtered_df
    
    def _filter_custom(self,
                      df: pd.DataFrame,
                      config: Dict,
                      datetime_col: str) -> pd.DataFrame:
        """Apply custom date range filtering"""
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        
        if start_date:
            start_date = pd.to_datetime(start_date)
            df = df[df[datetime_col] >= start_date]
        
        if end_date:
            end_date = pd.to_datetime(end_date)
            df = df[df[datetime_col] <= end_date]
        
        self.logger.info(f"Filtered to custom date range: {len(df)} records")
        return df
    
    def _filter_combined(self,
                        df: pd.DataFrame,
                        config: Dict,
                        datetime_col: str) -> pd.DataFrame:
        """Apply multiple filters combined"""
        # Start with full dataframe
        filtered_df = df.copy()
        
        # Apply month filter if specified
        if 'months' in config:
            months = config['months']
            filtered_df = filtered_df[filtered_df[datetime_col].dt.month.isin(months)]
        
        # Apply hour filter if specified
        if 'hours' in config:
            hours = config['hours']
            filtered_df = filtered_df[filtered_df[datetime_col].dt.hour.isin(hours)]
        
        # Apply day of week filter if specified
        if 'day_of_week' in config:
            if config['day_of_week'] == 'weekends':
                filtered_df = filtered_df[filtered_df[datetime_col].dt.dayofweek.isin([5, 6])]
            elif config['day_of_week'] == 'weekdays':
                filtered_df = filtered_df[filtered_df[datetime_col].dt.dayofweek.isin([0, 1, 2, 3, 4])]
        
        self.logger.info(f"Combined filtering resulted in {len(filtered_df)} records")
        return filtered_df
    
    def get_time_slice_summary(self,
                              df: pd.DataFrame,
                              datetime_col: str = 'DateTime') -> Dict[str, any]:
        """Get summary statistics about the time coverage of a dataframe"""
        if datetime_col not in df.columns:
            return {}
        
        dt_series = pd.to_datetime(df[datetime_col])
        
        summary = {
            'start_date': dt_series.min(),
            'end_date': dt_series.max(),
            'total_records': len(df),
            'unique_months': sorted(dt_series.dt.month.unique().tolist()),
            'unique_years': sorted(dt_series.dt.year.unique().tolist()),
            'unique_hours': sorted(dt_series.dt.hour.unique().tolist()),
            'weekend_records': len(df[dt_series.dt.dayofweek.isin([5, 6])]),
            'weekday_records': len(df[dt_series.dt.dayofweek.isin([0, 1, 2, 3, 4])]),
            'hourly_distribution': dt_series.dt.hour.value_counts().to_dict(),
            'monthly_distribution': dt_series.dt.month.value_counts().to_dict()
        }
        
        return summary
    
    def suggest_peak_periods(self,
                            df: pd.DataFrame,
                            variable_col: str,
                            datetime_col: str = 'DateTime',
                            n_months: int = 3) -> Dict[str, List[int]]:
        """
        Analyze data to suggest peak heating and cooling months
        
        Args:
            df: DataFrame with energy data
            variable_col: Column containing energy values
            datetime_col: DateTime column name
            n_months: Number of peak months to identify
            
        Returns:
            Dictionary with suggested peak months
        """
        if variable_col not in df.columns:
            return {}
        
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        
        # Group by month and sum
        monthly = df.groupby(df[datetime_col].dt.month)[variable_col].sum()
        
        # Find peak months
        peak_months = monthly.nlargest(n_months).index.tolist()
        low_months = monthly.nsmallest(n_months).index.tolist()
        
        # Heuristic: if peak months are in summer, they're cooling
        # if peak months are in winter, they're heating
        summer_months = [6, 7, 8]
        winter_months = [12, 1, 2]
        
        peak_summer_count = sum(1 for m in peak_months if m in summer_months)
        peak_winter_count = sum(1 for m in peak_months if m in winter_months)
        
        if peak_summer_count > peak_winter_count:
            # Cooling dominant
            suggestions = {
                'peak_cooling_months': peak_months,
                'peak_heating_months': low_months,
                'dominant_season': 'cooling'
            }
        else:
            # Heating dominant
            suggestions = {
                'peak_heating_months': peak_months,
                'peak_cooling_months': low_months,
                'dominant_season': 'heating'
            }
        
        return suggestions
    
    def create_time_slice_report(self,
                                original_df: pd.DataFrame,
                                filtered_df: pd.DataFrame,
                                config: Dict) -> Dict[str, any]:
        """Create a report summarizing the time slicing operation"""
        report = {
            'slice_config': config,
            'original_records': len(original_df),
            'filtered_records': len(filtered_df),
            'retention_rate': len(filtered_df) / len(original_df) * 100 if len(original_df) > 0 else 0,
            'time_coverage': self.get_time_slice_summary(filtered_df)
        }
        
        return report
    
    def validate_time_slice_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """Validate time slice configuration"""
        errors = []
        
        if not isinstance(config, dict):
            errors.append("Time slice config must be a dictionary")
            return False, errors
        
        if config.get('enabled', False):
            slice_type = config.get('slice_type')
            
            if slice_type not in ['peak_months', 'time_of_day', 'day_of_week', 'custom', 'combined', None]:
                errors.append(f"Invalid slice_type: {slice_type}")
            
            if slice_type == 'peak_months':
                if 'season' in config and config['season'] not in ['cooling', 'heating', 'both']:
                    errors.append("Season must be 'cooling', 'heating', or 'both'")
            
            if slice_type == 'time_of_day':
                if 'peak_hours' in config:
                    hours = config['peak_hours']
                    if isinstance(hours, list):
                        if not all(0 <= h <= 23 for h in hours):
                            errors.append("Peak hours must be between 0 and 23")
                    elif isinstance(hours, dict):
                        if 'start' in hours and not 0 <= hours['start'] <= 23:
                            errors.append("Start hour must be between 0 and 23")
                        if 'end' in hours and not 0 <= hours['end'] <= 23:
                            errors.append("End hour must be between 0 and 23")
        
        return len(errors) == 0, errors