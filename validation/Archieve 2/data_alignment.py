"""
data_alignment.py - Smart data alignment with unit conversion and format detection
Handles alignment between real and simulated data with automatic conversions
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
import re
from datetime import datetime

from validation.validation_config import ValidationConfig

logger = logging.getLogger(__name__)


class DataAligner:
    """Handles intelligent data alignment between real and simulated datasets"""
    
    def __init__(self, config: ValidationConfig):
        """
        Initialize with validation configuration
        
        Args:
            config: ValidationConfig instance
        """
        self.config = config
        self._unit_patterns = self._compile_unit_patterns()
        
    def _compile_unit_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for extracting units from variable names"""
        return {
            'brackets': re.compile(r'\[([^\]]+)\]'),  # [kWh]
            'parentheses': re.compile(r'\(([^)]+)\)(?!.*\()'),  # (kWh) - last parentheses
            'suffix': re.compile(r'_([a-zA-Z]+)$'),  # _kWh
        }
    
    def detect_format(self, df: pd.DataFrame) -> str:
        """
        Detect data format (wide vs long)
        
        Args:
            df: Input dataframe
            
        Returns:
            'wide' or 'long'
        """
        # Check for standard column names
        has_datetime = any(col in df.columns for col in ['DateTime', 'Date', 'Timestamp'])
        has_value = 'Value' in df.columns
        has_variable = any(col in df.columns for col in ['VariableName', 'Variable'])
        
        if has_datetime and has_value:
            logger.info("Detected long format data")
            return 'long'
        
        # Check if columns look like dates
        non_id_cols = [col for col in df.columns if col not in ['BuildingID', 'VariableName', 'Variable', 'Zone']]
        date_like_cols = 0
        
        for col in non_id_cols[:10]:  # Check first 10 columns
            if self._looks_like_date(str(col)):
                date_like_cols += 1
        
        if date_like_cols > 5:
            logger.info("Detected wide format data")
            return 'wide'
        
        # Default to long if uncertain
        return 'long'
    
    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date"""
        date_patterns = [
            r'^\d{1,2}/\d{1,2}$',  # MM/DD or M/D
            r'^\d{1,2}/\d{1,2}/\d{2,4}$',  # MM/DD/YYYY
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{1,2}-\d{1,2}-\d{2,4}$',  # DD-MM-YYYY
        ]
        
        return any(re.match(pattern, text) for pattern in date_patterns)
    
    def extract_units(self, variable_name: str) -> Optional[str]:
        """
        Extract units from variable name
        
        Args:
            variable_name: Variable name potentially containing units
            
        Returns:
            Extracted unit string or None
        """
        # Try different patterns
        for pattern_name, pattern in self._unit_patterns.items():
            match = pattern.search(variable_name)
            if match:
                unit = match.group(1)
                # Clean up unit (remove frequency indicators)
                unit = unit.split('(')[0].strip()
                return unit
        
        # Check for common unit suffixes
        var_lower = variable_name.lower()
        if var_lower.endswith('_kwh'):
            return 'kWh'
        elif var_lower.endswith('_mj'):
            return 'MJ'
        elif var_lower.endswith('_kw'):
            return 'kW'
        
        return None
    
    def detect_variable_type(self, variable_name: str) -> str:
        """
        Detect variable type from name
        
        Args:
            variable_name: Variable name
            
        Returns:
            Variable type (energy, power, temperature, etc.)
        """
        var_lower = variable_name.lower()
        
        # Energy indicators
        if any(word in var_lower for word in ['energy', 'consumption', 'kwh', 'mj', 'joule']):
            return 'energy'
        
        # Power indicators
        elif any(word in var_lower for word in ['power', 'demand', 'rate', 'kw', 'watt']):
            return 'power'
        
        # Temperature indicators
        elif any(word in var_lower for word in ['temperature', 'temp', 'celsius', 'fahrenheit']):
            return 'temperature'
        
        # Default
        else:
            return 'other'
    
    def apply_unit_conversion(self, df: pd.DataFrame, variable_name: str, 
                            from_unit: str, to_unit: str) -> pd.DataFrame:
        """
        Apply unit conversion to dataframe values
        
        Args:
            df: Dataframe with values to convert
            variable_name: Name of variable being converted
            from_unit: Source unit
            to_unit: Target unit
            
        Returns:
            Dataframe with converted values
        """
        if from_unit == to_unit:
            return df
        
        var_type = self.detect_variable_type(variable_name)
        
        if var_type == 'temperature':
            # Temperature conversion needs special handling
            logger.info(f"Converting temperature from {from_unit} to {to_unit}")
            
            # Find value columns
            value_cols = self._get_value_columns(df)
            
            for col in value_cols:
                df[col] = df[col].apply(
                    lambda x: self.config.convert_temperature(x, from_unit, to_unit) 
                    if pd.notna(x) else x
                )
        else:
            # Energy/Power conversion
            factor = self.config.get_unit_converter(from_unit, to_unit, var_type)
            
            if factor != 1.0:
                logger.info(f"Converting {variable_name} from {from_unit} to {to_unit} (factor: {factor})")
                
                # Find value columns
                value_cols = self._get_value_columns(df)
                
                for col in value_cols:
                    df[col] = df[col] * factor
        
        return df
    
    def _get_value_columns(self, df: pd.DataFrame) -> List[str]:
        """Get columns containing values (not IDs or names)"""
        exclude_cols = ['BuildingID', 'VariableName', 'Variable', 'Zone', 'ZoneName', 
                       'DateTime', 'Date', 'Timestamp', 'Units', 'Quality', 'Flag']
        
        value_cols = []
        for col in df.columns:
            if col not in exclude_cols:
                # Check if column contains numeric data
                if pd.api.types.is_numeric_dtype(df[col]):
                    value_cols.append(col)
                elif df[col].dtype == 'object':
                    # Try to convert to numeric
                    try:
                        pd.to_numeric(df[col], errors='coerce')
                        value_cols.append(col)
                    except:
                        pass
        
        return value_cols
    
    def standardize_variable_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize variable names using configuration mappings
        
        Args:
            df: Dataframe with VariableName column
            
        Returns:
            Dataframe with standardized variable names
        """
        if 'VariableName' not in df.columns and 'Variable' in df.columns:
            df = df.rename(columns={'Variable': 'VariableName'})
        
        if 'VariableName' in df.columns:
            # Apply mappings
            df['VariableName'] = df['VariableName'].apply(
                lambda x: self.config.get_variable_mapping(x)
            )
        
        return df
    
    def aggregate_zones_to_building(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate zone-level data to building level
        
        Args:
            df: Dataframe with zone-level data
            
        Returns:
            Building-level aggregated dataframe
        """
        if 'Zone' not in df.columns and 'ZoneName' not in df.columns:
            # Already building level
            return df
        
        zone_col = 'Zone' if 'Zone' in df.columns else 'ZoneName'
        
        # Group by building and variable
        group_cols = ['BuildingID']
        if 'VariableName' in df.columns:
            group_cols.append('VariableName')
        
        # Determine aggregation method for each variable
        if 'VariableName' in df.columns:
            # Create a custom aggregation function for each variable
            agg_funcs = {}
            value_cols = self._get_value_columns(df)
            
            for col in value_cols:
                agg_funcs[col] = 'sum'  # Default to sum
            
            # Group and aggregate
            agg_df = df.groupby(group_cols).agg(agg_funcs).reset_index()
            
            # If we need weighted average for temperature
            temp_vars = df[df['VariableName'].str.contains('Temperature', case=False, na=False)]
            if not temp_vars.empty:
                # This would require zone areas - for now just average
                logger.warning("Temperature aggregation using simple average (zone areas not available)")
                temp_groups = temp_vars.groupby(group_cols)[value_cols].mean().reset_index()
                
                # Update the aggregated dataframe
                for idx, row in temp_groups.iterrows():
                    mask = (agg_df['BuildingID'] == row['BuildingID'])
                    if 'VariableName' in group_cols:
                        mask &= (agg_df['VariableName'] == row['VariableName'])
                    
                    if mask.any():
                        for col in value_cols:
                            agg_df.loc[mask, col] = row[col]
        else:
            # No variable name column, aggregate all numeric columns
            value_cols = self._get_value_columns(df)
            agg_df = df.groupby('BuildingID')[value_cols].sum().reset_index()
        
        logger.info(f"Aggregated {len(df)} zone-level rows to {len(agg_df)} building-level rows")
        
        return agg_df
    
    def align_data(self, real_df: pd.DataFrame, sim_df: pd.DataFrame,
                   real_units: Optional[Dict[str, str]] = None,
                   sim_units: Optional[Dict[str, str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align real and simulated data with unit conversions
        
        Args:
            real_df: Real data dataframe
            sim_df: Simulated data dataframe
            real_units: Dictionary of units for real data variables
            sim_units: Dictionary of units for simulated data variables
            
        Returns:
            Tuple of (aligned_real_df, aligned_sim_df)
        """
        logger.info("Starting data alignment process")
        
        # Detect formats
        real_format = self.detect_format(real_df)
        sim_format = self.detect_format(sim_df)
        
        logger.info(f"Real data format: {real_format}, Sim data format: {sim_format}")
        
        # Make copies to avoid modifying originals
        real_aligned = real_df.copy()
        sim_aligned = sim_df.copy()
        
        # Standardize variable names
        real_aligned = self.standardize_variable_names(real_aligned)
        sim_aligned = self.standardize_variable_names(sim_aligned)
        
        # Handle unit conversions
        if 'VariableName' in real_aligned.columns:
            for var_name in real_aligned['VariableName'].unique():
                # Determine units
                real_unit = None
                sim_unit = None
                
                # Check provided units
                if real_units and var_name in real_units:
                    real_unit = real_units[var_name]
                else:
                    # Try to extract from variable name
                    real_unit = self.extract_units(var_name)
                
                # For sim, check mapped variable name
                mapped_var = self.config.get_variable_mapping(var_name)
                if sim_units and mapped_var in sim_units:
                    sim_unit = sim_units[mapped_var]
                else:
                    sim_unit = self.extract_units(mapped_var)
                
                # Default units from config
                var_type = self.detect_variable_type(var_name)
                if not real_unit:
                    real_unit = self.config.config['units'].get(var_type, 'J' if var_type == 'energy' else 'W')
                if not sim_unit:
                    sim_unit = 'J' if var_type == 'energy' else 'W'
                
                # Apply conversions if needed
                if real_unit != sim_unit:
                    logger.info(f"Unit mismatch for {var_name}: Real={real_unit}, Sim={sim_unit}")
                    
                    # Convert real data to simulation units
                    real_subset = real_aligned[real_aligned['VariableName'] == var_name].copy()
                    if not real_subset.empty:
                        converted = self.apply_unit_conversion(real_subset, var_name, real_unit, sim_unit)
                        real_aligned.loc[real_aligned['VariableName'] == var_name] = converted
        
        # Aggregate zones if needed
        if self.config.should_aggregate_zones():
            if 'Zone' in sim_aligned.columns or 'ZoneName' in sim_aligned.columns:
                logger.info("Aggregating zone-level simulation data to building level")
                sim_aligned = self.aggregate_zones_to_building(sim_aligned)
        
        # Ensure consistent data types for building IDs
        if 'BuildingID' in real_aligned.columns:
            real_aligned['BuildingID'] = real_aligned['BuildingID'].astype(str)
        if 'BuildingID' in sim_aligned.columns:
            sim_aligned['BuildingID'] = sim_aligned['BuildingID'].astype(str)
        
        # Log final stats
        logger.info(f"Aligned data - Real: {len(real_aligned)} rows, Sim: {len(sim_aligned)} rows")
        
        return real_aligned, sim_aligned
    
    def extract_common_dates(self, real_df: pd.DataFrame, sim_df: pd.DataFrame) -> List[str]:
        """
        Extract common dates between datasets
        
        Args:
            real_df: Real data dataframe (wide format)
            sim_df: Simulated data dataframe (wide format)
            
        Returns:
            List of common date columns
        """
        # Get date columns (exclude ID and name columns)
        exclude_cols = ['BuildingID', 'VariableName', 'Variable', 'Zone', 'Units']
        
        real_dates = [col for col in real_df.columns if col not in exclude_cols]
        sim_dates = [col for col in sim_df.columns if col not in exclude_cols]
        
        # Find exact matches first
        common = list(set(real_dates) & set(sim_dates))
        
        if not common:
            # Try fuzzy matching
            logger.info("No exact date matches, trying fuzzy matching")
            common = self._fuzzy_match_dates(real_dates, sim_dates)
        
        # Sort dates
        common = sorted(common, key=lambda x: self._parse_date_column(x))
        
        logger.info(f"Found {len(common)} common dates between datasets")
        
        return common
    
    def _fuzzy_match_dates(self, real_dates: List[str], sim_dates: List[str]) -> List[str]:
        """Fuzzy match date columns"""
        matched = []
        
        for real_date in real_dates:
            # Try different transformations
            real_normalized = real_date.replace('/', '-').replace(' ', '')
            
            for sim_date in sim_dates:
                sim_normalized = sim_date.replace('/', '-').replace(' ', '')
                
                if real_normalized == sim_normalized:
                    matched.append(real_date)
                    break
                
                # Try parsing and comparing
                try:
                    real_parsed = self._parse_date_column(real_date)
                    sim_parsed = self._parse_date_column(sim_date)
                    
                    if real_parsed == sim_parsed:
                        matched.append(real_date)
                        break
                except:
                    continue
        
        return matched
    
    def _parse_date_column(self, date_str: str) -> datetime:
        """Parse date column name to datetime"""
        for date_format in self.config.get_date_formats():
            try:
                return datetime.strptime(date_str, date_format)
            except:
                continue
        
        # Try pandas parser as fallback
        try:
            return pd.to_datetime(date_str)
        except:
            # Return as-is if can't parse
            return date_str