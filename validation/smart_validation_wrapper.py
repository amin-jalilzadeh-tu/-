# smart_validation_wrapper.py
"""
Smart Validation Wrapper - Intelligently validates simulation results against measured data
With configuration support, frequency alignment, and detailed logging
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
import re
from datetime import datetime
import logging
from dataclasses import dataclass
from collections import defaultdict
import json

# Import metrics
from validation.metrics import cv_rmse, nmbe, mean_bias_error

logger = logging.getLogger(__name__)


@dataclass
class ValidationMapping:
    """Stores mapping between real and simulated data"""
    real_var: str
    sim_var: str
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'semantic', 'configured'
    aggregation_info: Optional[Dict] = None


class ValidationConfig:
    """Simple configuration handler for validation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Extract main settings
        self.variables_to_validate = config.get('variables_to_validate', [])
        self.aggregation = config.get('aggregation', {})
        self.target_frequency = self.aggregation.get('target_frequency', 'daily')
        self.aggregation_methods = self.aggregation.get('methods', {
            'energy': 'sum',
            'temperature': 'mean',
            'power': 'mean'
        })
        
        # Thresholds
        self.thresholds = config.get('thresholds', {})
        self.default_thresholds = self.thresholds.get('default', {
            'cvrmse': 30.0,
            'nmbe': 10.0
        })
        self.variable_thresholds = self.thresholds.get('by_variable', {})
        
        # Logging settings
        self.logging = config.get('logging', {})
        self.log_level = self.logging.get('level', 'INFO')
        self.show_mappings = self.logging.get('show_mappings', True)
        self.show_aggregations = self.logging.get('show_aggregations', True)
        self.show_unit_conversions = self.logging.get('show_unit_conversions', True)
    
    def get_threshold(self, metric: str, variable: str) -> float:
        """Get threshold for a specific metric and variable"""
        # Check variable-specific first
        for var_pattern, thresholds in self.variable_thresholds.items():
            if var_pattern.lower() in variable.lower():
                if metric in thresholds:
                    return thresholds[metric]
        
        # Fall back to default
        return self.default_thresholds.get(metric, 30.0)


class SmartValidationWrapper:
    """Intelligently validates simulation results against measured data"""
    
    def __init__(self, parsed_data_path: str, real_data_path: str, 
                 config: Optional[Dict[str, Any]] = None):
        self.parsed_data_path = Path(parsed_data_path)
        self.real_data_path = Path(real_data_path)
        
        # Load configuration
        self.config = ValidationConfig(config) if config else ValidationConfig({})
        
        # Set up logging
        self._setup_logging()
        
        # Variable name patterns for semantic matching
        self.variable_patterns = {
            'electricity': {
                'patterns': [
                    r'electricity.*facility',
                    r'facility.*electric',
                    r'total.*electric.*energy',
                    r'electric.*energy.*total',
                    r'electricity:facility',
                    r'total.*electricity'
                ],
                'keywords': ['electricity', 'electric', 'power', 'facility']
            },
            'heating': {
                'patterns': [
                    r'heating.*energy',
                    r'zone.*air.*system.*sensible.*heating',
                    r'sensible.*heating.*energy',
                    r'heating.*transfer',
                    r'water.*heater.*heating',
                    r'heating:energytransfer',
                    r'heating\s+energy'
                ],
                'keywords': ['heating', 'heat', 'heater']
            },
            'cooling': {
                'patterns': [
                    r'cooling.*energy',
                    r'zone.*air.*system.*sensible.*cooling',
                    r'sensible.*cooling.*energy',
                    r'cooling.*transfer',
                    r'cooling:energytransfer',
                    r'cooling\s+energy'
                ],
                'keywords': ['cooling', 'cool']
            },
            'temperature': {
                'patterns': [
                    r'zone.*mean.*air.*temperature',
                    r'zone.*air.*temperature',
                    r'mean.*temperature',
                    r'indoor.*temp',
                    r'zone.*temp',
                    r'zone\s+temperature'
                ],
                'keywords': ['temperature', 'temp']
            }
        }
        
        # Unit conversions
        self.unit_conversions = {
            ('J', 'kWh'): 1 / 3600000,
            ('kWh', 'J'): 3600000,
            ('J', 'MJ'): 1 / 1000000,
            ('MJ', 'J'): 1000000,
            ('J', 'GJ'): 1 / 1000000000,
            ('GJ', 'J'): 1000000000,
            ('kWh', 'MWh'): 1 / 1000,
            ('MWh', 'kWh'): 1000,
            ('W', 'kW'): 1 / 1000,
            ('kW', 'W'): 1000,
            ('C', 'F'): lambda x: x * 9/5 + 32,
            ('F', 'C'): lambda x: (x - 32) * 5/9,
            ('K', 'C'): lambda x: x - 273.15,
            ('C', 'K'): lambda x: x + 273.15
        }
        
        self.step_count = 0
        self.total_steps = 6
    
    def _setup_logging(self):
        """Configure logging based on config"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='[%(levelname)s] %(message)s'
        )
    
    def _log_step(self, step_name: str):
        """Log a major step in the process"""
        self.step_count += 1
        logger.info(f"\nStep {self.step_count}/{self.total_steps}: {step_name}")
    
    def discover_available_data(self) -> Dict[str, Any]:
        """Discover what data the parser actually produced"""
        self._log_step("Discovering available simulation data...")
        
        discovery = {
            'timeseries': {},
            'outputs_defined': {},
            'zones': {},
            'aggregation_needed': {},
            'available_variables': set(),
            'available_frequencies': set()
        }
        
        # Check new timeseries data structure
        ts_path = self.parsed_data_path / 'timeseries'
        
        # Also check old structure for backward compatibility
        old_ts_path = self.parsed_data_path / 'sql_results' / 'timeseries'
        
        # Try new structure first
        if ts_path.exists():
            # Check for base_all_*.parquet files
            for freq in ['hourly', 'daily', 'monthly', 'yearly']:
                file_path = ts_path / f'base_all_{freq}.parquet'
                if file_path.exists():
                    try:
                        df = pd.read_parquet(file_path)
                        if not df.empty:
                            # New format has wide structure with dates as columns
                            # Extract metadata columns
                            metadata_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
                            date_cols = [col for col in df.columns if col not in metadata_cols]
                            
                            if 'VariableName' in df.columns:
                                variables = df['VariableName'].unique().tolist()
                                discovery['available_variables'].update(variables)
                            
                            discovery['timeseries'][f'base_all_{freq}'] = {
                                'file': str(file_path),
                                'format': 'wide',  # New wide format
                                'buildings': df['building_id'].unique().tolist() if 'building_id' in df.columns else [],
                                'variables': variables if 'VariableName' in df.columns else [],
                                'zones': df['Zone'].unique().tolist() if 'Zone' in df.columns else [],
                                'date_columns': len(date_cols),
                                'frequency': freq,
                                'records': len(df),
                                'has_units': 'Units' in df.columns
                            }
                            
                            discovery['available_frequencies'].add(freq)
                            logger.info(f"  - Found base_all_{freq}: {len(df)} rows × {len(date_cols)} date columns, {len(variables)} variables")
                    except Exception as e:
                        logger.debug(f"    Error reading {file_path}: {str(e)}")
        
        # Check old structure for backward compatibility
        elif old_ts_path.exists():
            # Check hourly data
            hourly_path = old_ts_path / 'hourly'
            if hourly_path.exists():
                for file in hourly_path.glob('*.parquet'):
                    df = pd.read_parquet(file)
                    if not df.empty and 'Variable' in df.columns:
                        variables = df['Variable'].unique().tolist()
                        discovery['available_variables'].update(variables)
                        
                        discovery['timeseries'][file.stem] = {
                            'file': str(file),
                            'format': 'long',  # Old long format
                            'buildings': df['building_id'].unique().tolist() if 'building_id' in df.columns else [],
                            'variables': variables,
                            'zones': df['Zone'].unique().tolist() if 'Zone' in df.columns else [],
                            'date_range': (df['DateTime'].min(), df['DateTime'].max()) if 'DateTime' in df.columns else None,
                            'frequency': 'hourly',
                            'records': len(df),
                            'has_units': 'Units' in df.columns
                        }
                        
                        discovery['available_frequencies'].add('hourly')
                        logger.info(f"  - Found {file.stem}: {len(df):,} hourly records, {len(variables)} variables")
            
            # Check daily aggregated data
            daily_path = old_ts_path / 'aggregated' / 'daily'
            if daily_path.exists():
                for file in daily_path.glob('*.parquet'):
                    df = pd.read_parquet(file)
                    if not df.empty and 'Variable' in df.columns:
                        variables = df['Variable'].unique().tolist()
                        discovery['available_variables'].update(variables)
                        
                        discovery['timeseries'][f"{file.stem}_daily"] = {
                            'file': str(file),
                            'format': 'long',  # Old long format
                            'buildings': df['building_id'].unique().tolist() if 'building_id' in df.columns else [],
                            'variables': variables,
                            'zones': df['Zone'].unique().tolist() if 'Zone' in df.columns else [],
                            'date_range': (df['DateTime'].min(), df['DateTime'].max()) if 'DateTime' in df.columns else None,
                            'frequency': 'daily',
                            'records': len(df),
                            'has_units': 'Units' in df.columns
                        }
                        
                        discovery['available_frequencies'].add('daily')
                        logger.info(f"  - Found {file.stem}_daily: {len(df):,} daily records, {len(variables)} variables")
                        if 'Units' not in df.columns:
                            logger.info(f"    Note: No Units column in {file.stem}_daily")
        
        # Log available variables
        if discovery['available_variables']:
            logger.info(f"\n  Available simulation variables:")
            for var in sorted(discovery['available_variables'])[:10]:  # Show first 10
                logger.info(f"    * {var}")
            if len(discovery['available_variables']) > 10:
                logger.info(f"    ... and {len(discovery['available_variables']) - 10} more")
        
        # Check for comparison files (for modified results)
        comparisons_path = self.parsed_data_path / 'comparisons'
        if comparisons_path.exists():
            comparison_files = list(comparisons_path.glob('var_*.parquet'))
            if comparison_files:
                logger.info(f"\n  Found {len(comparison_files)} comparison files")
                discovery['comparison_files'] = {}
                
                for comp_file in comparison_files[:5]:  # Show first 5
                    # Parse filename: var_{variable}_{unit}_{frequency}_b{building_id}.parquet
                    parts = comp_file.stem.split('_')
                    if len(parts) >= 5:
                        variable = '_'.join(parts[1:-3])  # Handle multi-word variables
                        frequency = parts[-2]
                        building_id = parts[-1][1:]  # Remove 'b' prefix
                        
                        discovery['comparison_files'][comp_file.stem] = {
                            'file': str(comp_file),
                            'variable': variable,
                            'frequency': frequency,
                            'building_id': building_id
                        }
                        logger.debug(f"    - {comp_file.name}: {variable} ({frequency})")
                
                if len(comparison_files) > 5:
                    logger.info(f"    ... and {len(comparison_files) - 5} more")
        
        # Check zone information
        zone_file = self.parsed_data_path / 'relationships' / 'zone_mappings.parquet'
        if zone_file.exists():
            zone_df = pd.read_parquet(zone_file)
            for building_id in zone_df['building_id'].unique():
                building_zones = zone_df[zone_df['building_id'] == building_id]
                zones = building_zones['sql_zone_name'].unique().tolist()
                discovery['zones'][building_id] = zones
                
                # Check if we need aggregation
                if len(zones) > 1:
                    discovery['aggregation_needed'][building_id] = True
                    logger.debug(f"  Building {building_id} has {len(zones)} zones - will need aggregation")
        
        return discovery
    
    def load_and_parse_real_data(self) -> pd.DataFrame:
        """Load real data with flexible parsing"""
        self._log_step("Loading real/measured data...")
        
        # Load the data
        logger.info(f"  - Reading from: {self.real_data_path}")
        real_df = pd.read_csv(self.real_data_path)
        logger.info(f"  - Loaded {len(real_df):,} rows")
        
        # Check required columns
        required = ['building_id', 'DateTime', 'Variable', 'Value']
        missing = [col for col in required if col not in real_df.columns]
        
        # Handle case variations
        if missing:
            # Try case-insensitive matching
            col_mapping = {}
            for req_col in missing:
                for actual_col in real_df.columns:
                    if req_col.lower() == actual_col.lower():
                        col_mapping[actual_col] = req_col
                        break
            
            if col_mapping:
                real_df = real_df.rename(columns=col_mapping)
                logger.info(f"  - Renamed columns: {col_mapping}")
        
        # Add Units column if missing - infer from variable names
        if 'Units' not in real_df.columns:
            logger.info("  - Units column missing, inferring from variable names...")
            real_df['Units'] = real_df['Variable'].apply(self._infer_units_from_variable)
            logger.info(f"  - Added Units column with inferred values")
            
            # Log unique units inferred
            unique_units = real_df.groupby('Variable')['Units'].first()
            logger.debug("  - Inferred units:")
            for var, unit in unique_units.items():
                logger.debug(f"    {var}: {unit}")
        
        # Parse DateTime with multiple format attempts
        if 'DateTime' in real_df.columns:
            logger.info("  - Parsing datetime values...")
            
            # Try multiple formats
            datetime_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%m/%d/%Y %H:%M:%S',
                '%d/%m/%Y',
                '%d/%m/%Y %H:%M:%S',
                '%Y/%m/%d',
                '%Y/%m/%d %H:%M:%S',
            ]
            
            parsed = False
            for fmt in datetime_formats:
                try:
                    real_df['DateTime'] = pd.to_datetime(real_df['DateTime'], format=fmt)
                    parsed = True
                    logger.info(f"    Successfully parsed with format: {fmt}")
                    break
                except:
                    logger.debug(f"    Failed to parse with format: {fmt}")
                    continue
            
            if not parsed:
                # Try pandas auto-detection
                try:
                    real_df['DateTime'] = pd.to_datetime(real_df['DateTime'], infer_datetime_format=True)
                    logger.info("    Successfully parsed with pandas auto-detection")
                except Exception as e:
                    logger.error(f"    Failed to parse DateTime: {e}")
                    raise
        
        # Ensure building_id is string for consistency
        if 'building_id' in real_df.columns:
            real_df['building_id'] = real_df['building_id'].astype(str)
        
        # Detect data frequency
        if 'DateTime' in real_df.columns and len(real_df) > 1:
            time_diffs = real_df.groupby(['building_id', 'Variable'])['DateTime'].diff().dropna()
            if not time_diffs.empty:
                mode_diff = time_diffs.mode()
                if not mode_diff.empty:
                    hours = mode_diff.iloc[0].total_seconds() / 3600
                    if hours < 1.5:
                        freq = 'hourly'
                    elif hours < 25:
                        freq = 'daily'
                    else:
                        freq = 'other'
                    logger.info(f"  - Detected frequency: {freq}")
        
        # Log data summary
        buildings = real_df['building_id'].unique() if 'building_id' in real_df.columns else []
        variables = real_df['Variable'].unique() if 'Variable' in real_df.columns else []
        
        logger.info(f"  - Found {len(buildings)} buildings: {list(buildings[:5])}" + 
                   (" ..." if len(buildings) > 5 else ""))
        logger.info(f"  - Found {len(variables)} variables: {list(variables[:5])}" + 
                   (" ..." if len(variables) > 5 else ""))
        
        if 'DateTime' in real_df.columns:
            date_range = (real_df['DateTime'].min(), real_df['DateTime'].max())
            logger.info(f"  - Date range: {date_range[0]} to {date_range[1]}")
        
        return real_df
    
    def _infer_units_from_variable(self, variable_name: str) -> str:
        """Infer units from variable name"""
        var_lower = variable_name.lower()
        
        # Check for units in brackets [J], [kWh], etc.
        bracket_match = re.search(r'\[([^\]]+)\]', variable_name)
        if bracket_match:
            unit_str = bracket_match.group(1)
            # Extract just the unit part if it includes frequency like "J(Hourly)"
            unit_parts = unit_str.split('(')
            return unit_parts[0].strip()
        
        # Common patterns
        if 'temperature' in var_lower or 'temp' in var_lower:
            return 'C'
        elif 'electricity' in var_lower or 'electric' in var_lower:
            return 'J'
        elif 'energy' in var_lower:
            return 'J'
        elif 'power' in var_lower or 'demand' in var_lower:
            return 'W'
        elif 'heating' in var_lower:
            return 'J'
        elif 'cooling' in var_lower:
            return 'J'
        elif 'humidity' in var_lower:
            return '%'
        elif 'flow' in var_lower and 'rate' in var_lower:
            return 'm3/s'
        elif 'pressure' in var_lower:
            return 'Pa'
        else:
            return 'unknown'
    
    def _convert_wide_to_long(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert wide format (dates as columns) to long format (dates as rows)"""
        import re
        
        # Identify metadata columns vs date columns
        metadata_cols = ['building_id', 'variant_id', 'VariableName', 'category', 'Zone', 'Units']
        # Keep only metadata columns that exist in the dataframe
        id_vars = [col for col in metadata_cols if col in df.columns]
        
        # Find date columns (format: YYYY-MM-DD or similar)
        date_cols = []
        for col in df.columns:
            if col not in metadata_cols:
                # Check if column name looks like a date
                if re.match(r'\d{4}-\d{2}-\d{2}', str(col)):
                    date_cols.append(col)
        
        if not date_cols:
            logger.warning("No date columns found in wide format data")
            return df
        
        # Melt the dataframe
        df_long = df.melt(
            id_vars=id_vars,
            value_vars=date_cols,
            var_name='DateTime',
            value_name='Value'
        )
        
        # Convert DateTime to proper datetime
        df_long['DateTime'] = pd.to_datetime(df_long['DateTime'])
        
        # Rename VariableName to Variable for consistency
        if 'VariableName' in df_long.columns:
            df_long = df_long.rename(columns={'VariableName': 'Variable'})
        
        # Remove rows with null values
        df_long = df_long.dropna(subset=['Value'])
        
        # Sort by building, variable, and date for better organization
        sort_cols = ['building_id', 'Variable', 'DateTime']
        sort_cols = [col for col in sort_cols if col in df_long.columns]
        if sort_cols:
            df_long = df_long.sort_values(sort_cols)
        
        logger.info(f"    Converted {len(df)} wide rows to {len(df_long)} long rows")
        
        return df_long
    
    def _load_from_comparison_files(self, discovery: Dict[str, Any], target_freq: str, variant_id: Optional[str] = None) -> pd.DataFrame:
        """Load simulation data from comparison files (for modified results)
        
        Args:
            discovery: Discovery information
            target_freq: Target frequency (daily, monthly, etc.)
            variant_id: Optional variant ID to load (e.g., 'variant_0', 'variant_1', etc.)
                       If None, loads base values
        """
        comparison_data = []
        
        # Determine which column to use for values
        value_column = f'{variant_id}_value' if variant_id else 'base_value'
        
        # Priority order for loading comparison files based on target frequency
        if target_freq == 'daily':
            freq_priority = ['daily', 'monthly']  # Try daily first, fall back to monthly
        elif target_freq == 'monthly':
            freq_priority = ['monthly', 'daily']  # Try monthly first, can aggregate daily
        else:
            freq_priority = [target_freq, 'daily', 'monthly']
        
        # Track what frequency we actually loaded
        loaded_frequency = None
        
        for preferred_freq in freq_priority:
            if comparison_data:  # Already loaded data
                break
                
            for file_info in discovery['comparison_files'].values():
                if file_info['frequency'] == preferred_freq:
                    try:
                        df = pd.read_parquet(file_info['file'])
                        
                        # Check if the requested value column exists
                        if value_column not in df.columns:
                            logger.debug(f"    Column {value_column} not found in {file_info['file']}")
                            continue
                        
                        # Detect actual frequency from the data
                        actual_freq = self._detect_frequency(df, file_info['file'])
                        
                        # Transform comparison file to standard format
                        sim_df = pd.DataFrame({
                            'building_id': df['building_id'],
                            'DateTime': df['timestamp'] if 'timestamp' in df.columns else df['DateTime'],
                            'Variable': df['variable_name'] if 'variable_name' in df.columns else file_info['variable'],
                            'Value': df[value_column],
                            'Units': df['Units'] if 'Units' in df.columns else 'unknown',
                            'Zone': df['Zone'] if 'Zone' in df.columns else 'Building',
                            '_source_frequency': actual_freq  # Store actual frequency for aggregation
                        })
                        
                        # Add variant info if loading variant data
                        if variant_id:
                            sim_df['variant_id'] = variant_id
                        
                        comparison_data.append(sim_df)
                        loaded_frequency = actual_freq
                        logger.info(f"    Loaded {file_info['variable']} from comparison file ({value_column}, {actual_freq} data)")
                    except Exception as e:
                        logger.debug(f"    Error loading {file_info['file']}: {str(e)}")
        
        if comparison_data:
            combined_df = pd.concat(comparison_data, ignore_index=True)
            logger.info(f"  - Loaded {len(combined_df)} records from {len(comparison_data)} comparison files")
            if loaded_frequency and loaded_frequency != target_freq:
                logger.info(f"  - Loaded {loaded_frequency} frequency data (target was {target_freq})")
            return combined_df
        
        return pd.DataFrame()
    
    def load_simulation_data(self, discovery: Dict[str, Any]) -> pd.DataFrame:
        """Load simulation data based on target frequency"""
        self._log_step("Loading simulation data...")
        
        all_sim_data = []
        target_freq = self.config.target_frequency
        
        logger.info(f"  - Target frequency: {target_freq}")
        logger.info(f"  - Available frequencies: {sorted(discovery.get('available_frequencies', []))}")
        
        # Priority order for loading data based on target frequency
        if target_freq == 'daily':
            freq_priority = ['daily', 'hourly', 'monthly']
        elif target_freq == 'monthly':
            freq_priority = ['monthly', 'daily', 'hourly']
        elif target_freq == 'hourly':
            freq_priority = ['hourly', 'daily']
        else:
            freq_priority = ['daily', 'monthly', 'hourly']
        
        # Try to load data in priority order
        data_loaded = False
        loaded_frequency = None
        
        for preferred_freq in freq_priority:
            if data_loaded:
                break
                
            # Check if this frequency is available
            if preferred_freq not in discovery.get('available_frequencies', []):
                continue
            
            # Load all datasets with this frequency
            for dataset_name, dataset_info in discovery['timeseries'].items():
                if dataset_info.get('frequency') == preferred_freq:
                    logger.info(f"  - Loading {dataset_name} ({preferred_freq} data, {dataset_info['records']:,} records)")
                    df = pd.read_parquet(dataset_info['file'])
                    
                    if not df.empty:
                        # Check if this is wide format (new structure)
                        if dataset_info.get('format') == 'wide':
                            logger.info(f"    Converting from wide to long format")
                            df = self._convert_wide_to_long(df)
                        
                        # Add frequency info for later aggregation decisions
                        df['_source_frequency'] = preferred_freq
                        
                        # Add Units column if missing
                        if 'Units' not in df.columns and dataset_info.get('has_units') is False:
                            logger.info(f"    Adding Units column to {dataset_name}")
                            df['Units'] = df['Variable'].apply(self._infer_units_from_variable)
                        
                        all_sim_data.append(df)
                        data_loaded = True
                        loaded_frequency = preferred_freq
        
        if data_loaded:
            logger.info(f"  - Loaded {loaded_frequency} frequency data (will {'aggregate' if loaded_frequency != target_freq else 'use as-is'})")
        
        if all_sim_data:
            sim_df = pd.concat(all_sim_data, ignore_index=True)
            logger.info(f"  - Total simulation records loaded: {len(sim_df):,}")
            
            # Ensure building_id is string
            if 'building_id' in sim_df.columns:
                sim_df['building_id'] = sim_df['building_id'].astype(str)
            
            # Check for Units column
            if 'Units' not in sim_df.columns:
                logger.info("  - Units column missing from simulation data, adding...")
                sim_df['Units'] = sim_df['Variable'].apply(self._infer_units_from_variable)
            
            return sim_df
        else:
            # Try loading from comparison files if available
            if 'comparison_files' in discovery and discovery['comparison_files']:
                logger.info("  - No timeseries data found, checking comparison files...")
                return self._load_from_comparison_files(discovery, target_freq)
            else:
                logger.error("  - No simulation data found!")
                return pd.DataFrame()
    
    def align_frequencies(self, real_df: pd.DataFrame, sim_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Align data frequencies between real and simulated data"""
        self._log_step("Aligning data frequencies...")
        
        if sim_df.empty:
            return real_df, sim_df
        
        # Detect frequencies
        real_freq = self._detect_frequency(real_df)
        
        # For simulation data, check if we stored the source frequency
        if '_source_frequency' in sim_df.columns:
            sim_freq = sim_df['_source_frequency'].iloc[0] if len(sim_df) > 0 else 'unknown'
            # Remove the helper column
            sim_df = sim_df.drop('_source_frequency', axis=1)
        else:
            sim_freq = self._detect_frequency(sim_df)
        
        logger.info(f"  - Real data frequency: {real_freq}")
        logger.info(f"  - Sim data frequency: {sim_freq}")
        logger.info(f"  - Target frequency: {self.config.target_frequency}")
        
        # Align to target frequency
        target = self.config.target_frequency
        
        # Aggregate simulation data if needed
        if sim_freq != target:
            if sim_freq == 'hourly' and target == 'daily':
                logger.info("  - Aggregating hourly simulation data to daily...")
                sim_df = self._aggregate_to_daily(sim_df)
            elif sim_freq == 'monthly' and target == 'daily':
                logger.info("  - Note: Monthly data loaded for daily validation (will validate monthly averages)")
                # Don't disaggregate monthly to daily - just note it
            elif sim_freq == 'daily' and target == 'monthly':
                logger.info("  - Aggregating daily simulation data to monthly...")
                sim_df = self._aggregate_to_monthly(sim_df)
        else:
            logger.info(f"  - Simulation data already at target frequency ({target})")
        
        # Aggregate real data if needed
        if real_freq != target:
            if real_freq == 'hourly' and target == 'daily':
                logger.info("  - Aggregating hourly real data to daily...")
                real_df = self._aggregate_to_daily(real_df)
            elif real_freq == 'daily' and target == 'monthly':
                logger.info("  - Aggregating daily real data to monthly...")
                real_df = self._aggregate_to_monthly(real_df)
        else:
            logger.info(f"  - Real data already at target frequency ({target})")
        
        return real_df, sim_df
    
    def _is_date_column(self, col_name: str) -> bool:
        """Check if a column name represents a date"""
        import re
        # Check for YYYY-MM-DD format
        if re.match(r'^\d{4}-\d{2}-\d{2}$', str(col_name)):
            return True
        # Check for YYYY-MM format
        if re.match(r'^\d{4}-\d{2}$', str(col_name)):
            return True
        return False
    
    def _detect_frequency_from_columns(self, columns: List[str]) -> str:
        """Detect frequency from date column names"""
        date_cols = [col for col in columns if self._is_date_column(col)]
        
        if len(date_cols) < 2:
            return 'unknown'
        
        # Check format of first date column
        first_col = date_cols[0]
        
        # Monthly format (YYYY-MM)
        if re.match(r'^\d{4}-\d{2}$', first_col):
            return 'monthly'
        
        # Daily format (YYYY-MM-DD) - need to check spacing
        if re.match(r'^\d{4}-\d{2}-\d{2}$', first_col):
            try:
                # Parse first few dates
                dates = pd.to_datetime(date_cols[:min(10, len(date_cols))])
                # Check intervals
                intervals = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                
                # Check if all intervals are 1 day
                if all(interval == 1 for interval in intervals):
                    return 'daily'
                # Check if hourly (would have multiple entries per day)
                elif all(interval == 0 for interval in intervals[:5]):  # Same day
                    return 'hourly'
                else:
                    return 'other'
            except:
                return 'unknown'
        
        return 'unknown'
    
    def _detect_frequency_from_filename(self, filename: str) -> str:
        """Detect frequency from filename patterns"""
        filename_lower = filename.lower()
        
        if 'hourly' in filename_lower:
            return 'hourly'
        elif 'daily' in filename_lower:
            return 'daily'
        elif 'monthly' in filename_lower:
            return 'monthly'
        elif 'yearly' in filename_lower or 'annual' in filename_lower:
            return 'yearly'
        
        return 'unknown'
    
    def _detect_frequency(self, df: pd.DataFrame, filename: Optional[str] = None) -> str:
        """Detect data frequency from dataframe or filename"""
        # First try filename if provided
        if filename:
            freq = self._detect_frequency_from_filename(filename)
            if freq != 'unknown':
                return freq
        
        # Check if this is wide format (dates as columns)
        date_cols = [col for col in df.columns if self._is_date_column(col)]
        if date_cols:
            return self._detect_frequency_from_columns(df.columns)
        
        # Original logic for long format
        if 'DateTime' not in df.columns or len(df) < 2:
            return 'unknown'
        
        # Ensure DateTime is parsed
        if not pd.api.types.is_datetime64_any_dtype(df['DateTime']):
            df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Sample time differences
        sample_df = df.head(1000)  # Use sample for speed
        if 'building_id' in df.columns and 'Variable' in df.columns:
            time_diffs = sample_df.groupby(['building_id', 'Variable'])['DateTime'].diff().dropna()
        else:
            time_diffs = sample_df['DateTime'].diff().dropna()
        
        if time_diffs.empty:
            return 'unknown'
        
        # Get mode of time differences
        mode_diff = time_diffs.mode()
        if mode_diff.empty:
            return 'unknown'
        
        hours = mode_diff.iloc[0].total_seconds() / 3600
        
        if hours < 1.5:
            return 'hourly'
        elif hours < 25:
            return 'daily'
        elif hours < 35 * 24:
            return 'monthly'
        else:
            return 'other'
    
    def _aggregate_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data to daily frequency"""
        if 'DateTime' not in df.columns:
            return df
        
        # Ensure DateTime is datetime type
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create date column
        df['Date'] = df['DateTime'].dt.date
        
        # Group columns
        group_cols = ['building_id', 'Date']
        if 'Variable' in df.columns:
            group_cols.insert(1, 'Variable')
        if 'Zone' in df.columns and df['Zone'].nunique() > 1:
            group_cols.append('Zone')
        
        # Determine aggregation method
        agg_results = []
        
        if 'Variable' in df.columns:
            for var in df['Variable'].unique():
                var_df = df[df['Variable'] == var]
                
                # Determine aggregation method based on variable type
                var_lower = var.lower()
                agg_method = self._get_aggregation_method(var_lower)
                
                if self.config.show_aggregations:
                    logger.info(f"    * {var}: {len(var_df)} hourly → daily ({agg_method})")
                
                # Aggregate - handle both with and without Units column
                var_group_cols = [col for col in group_cols if col in var_df.columns]
                
                if 'Units' in var_df.columns:
                    agg_df = var_df.groupby(var_group_cols).agg({
                        'Value': agg_method,
                        'Units': 'first'
                    }).reset_index()
                else:
                    agg_df = var_df.groupby(var_group_cols).agg({
                        'Value': agg_method
                    }).reset_index()
                
                agg_results.append(agg_df)
        else:
            # No variable column, aggregate all
            agg_df = df.groupby(group_cols).agg({
                'Value': 'sum'
            }).reset_index()
            agg_results.append(agg_df)
        
        if agg_results:
            result_df = pd.concat(agg_results, ignore_index=True)
            # Convert Date back to DateTime
            result_df['DateTime'] = pd.to_datetime(result_df['Date'])
            result_df = result_df.drop('Date', axis=1)
            
            logger.info(f"  - Aggregation complete: {len(df)} → {len(result_df)} records")
            return result_df
        
        return df
    
    def _aggregate_to_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate data to monthly frequency"""
        if 'DateTime' not in df.columns:
            return df
        
        # Ensure DateTime is datetime type
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Create month column
        df['YearMonth'] = df['DateTime'].dt.to_period('M')
        
        # Group columns
        group_cols = ['building_id', 'YearMonth']
        if 'Variable' in df.columns:
            group_cols.insert(1, 'Variable')
        if 'Zone' in df.columns and df['Zone'].nunique() > 1:
            group_cols.append('Zone')
        
        # Aggregate
        agg_results = []
        
        if 'Variable' in df.columns:
            for var in df['Variable'].unique():
                var_df = df[df['Variable'] == var]
                
                # Determine aggregation method
                var_lower = var.lower()
                agg_method = self._get_aggregation_method(var_lower)
                
                logger.info(f"    * {var}: aggregating to monthly ({agg_method})")
                
                # Aggregate
                var_group_cols = [col for col in group_cols if col in var_df.columns]
                
                if 'Units' in var_df.columns:
                    agg_df = var_df.groupby(var_group_cols).agg({
                        'Value': agg_method,
                        'Units': 'first'
                    }).reset_index()
                else:
                    agg_df = var_df.groupby(var_group_cols).agg({
                        'Value': agg_method
                    }).reset_index()
                
                agg_results.append(agg_df)
        else:
            # No variable column
            agg_df = df.groupby(group_cols).agg({
                'Value': 'sum'
            }).reset_index()
            agg_results.append(agg_df)
        
        if agg_results:
            result_df = pd.concat(agg_results, ignore_index=True)
            # Convert YearMonth back to DateTime (first day of month)
            result_df['DateTime'] = pd.to_datetime(result_df['YearMonth'].astype(str))
            result_df = result_df.drop('YearMonth', axis=1)
            
            logger.info(f"  - Monthly aggregation complete: {len(df)} → {len(result_df)} records")
            return result_df
        
        return df
    
    def _get_aggregation_method(self, variable_name: str) -> str:
        """Get aggregation method for a variable"""
        var_lower = variable_name.lower()
        
        # Check configuration
        for var_type, method in self.config.aggregation_methods.items():
            if var_type in var_lower:
                return method
        
        # Default rules
        if any(word in var_lower for word in ['energy', 'consumption']):
            return 'sum'
        elif any(word in var_lower for word in ['temperature', 'temp', 'humidity']):
            return 'mean'
        elif any(word in var_lower for word in ['power', 'rate', 'demand']):
            return 'mean'
        else:
            return 'sum'
    
    def create_variable_mappings(self, real_vars: List[str], sim_vars: List[str]) -> List[ValidationMapping]:
        """Create intelligent mappings between real and simulated variables"""
        self._log_step("Creating variable mappings...")
        
        mappings = []
        
        # Filter based on configuration
        if self.config.variables_to_validate:
            logger.info(f"  - Filtering variables based on config: {self.config.variables_to_validate}")
            
            # Filter real variables
            filtered_real_vars = []
            for config_var in self.config.variables_to_validate:
                config_var_lower = config_var.lower()
                for real_var in real_vars:
                    if config_var_lower in real_var.lower():
                        filtered_real_vars.append(real_var)
            
            if filtered_real_vars:
                real_vars = list(set(filtered_real_vars))
                logger.info(f"  - Filtered to {len(real_vars)} real variables")
            else:
                logger.warning("  - No real variables match configuration filter!")
        
        # Log what we're trying to map
        logger.info(f"\n  Real variables to map:")
        for var in real_vars[:10]:
            logger.info(f"    - {var}")
        if len(real_vars) > 10:
            logger.info(f"    ... and {len(real_vars) - 10} more")
        
        # First pass: exact matches
        for real_var in real_vars:
            if real_var in sim_vars:
                mappings.append(ValidationMapping(
                    real_var=real_var,
                    sim_var=real_var,
                    confidence=1.0,
                    match_type='exact'
                ))
                if self.config.show_mappings:
                    logger.info(f"\n  ✓ Exact match: {real_var}")
        
        # Second pass: semantic matching
        unmapped_real = [v for v in real_vars if not any(m.real_var == v for m in mappings)]
        unmapped_sim = [v for v in sim_vars if not any(m.sim_var == v for m in mappings)]
        
        for real_var in unmapped_real:
            best_match = self._find_semantic_match(real_var, unmapped_sim)
            if best_match:
                mappings.append(best_match)
                unmapped_sim.remove(best_match.sim_var)
                if self.config.show_mappings:
                    logger.info(f"\n  ≈ Semantic match: {real_var} → {best_match.sim_var} "
                               f"(confidence: {best_match.confidence:.2f})")
        
        # Log unmapped variables
        final_unmapped = [v for v in real_vars if not any(m.real_var == v for m in mappings)]
        if final_unmapped:
            logger.warning(f"\n  ✗ Could not map {len(final_unmapped)} variables:")
            for var in final_unmapped[:5]:
                logger.warning(f"    - {var}")
                # Suggest possible matches
                possible_matches = self._suggest_matches(var, sim_vars)
                if possible_matches:
                    logger.info(f"      Possible matches: {', '.join(possible_matches[:3])}")
            if len(final_unmapped) > 5:
                logger.warning(f"    ... and {len(final_unmapped) - 5} more")
        
        logger.info(f"\n  Mapping summary: {len(mappings)} successful mappings")
        
        return mappings
    
    def _find_semantic_match(self, real_var: str, sim_vars: List[str]) -> Optional[ValidationMapping]:
        """Find semantic match for a variable"""
        real_var_lower = real_var.lower()
        best_match = None
        best_score = 0
        
        # Check each category
        for category, category_info in self.variable_patterns.items():
            patterns = category_info['patterns']
            keywords = category_info['keywords']
            
            # Check if real variable matches this category
            real_matches_category = any(re.search(pattern, real_var_lower) for pattern in patterns)
            if not real_matches_category:
                # Check keywords
                real_matches_category = any(keyword in real_var_lower for keyword in keywords)
            
            if real_matches_category:
                # Find simulation variables in same category
                for sim_var in sim_vars:
                    sim_var_lower = sim_var.lower()
                    
                    # Check patterns
                    sim_matches = any(re.search(pattern, sim_var_lower) for pattern in patterns)
                    if not sim_matches:
                        # Check keywords
                        sim_matches = any(keyword in sim_var_lower for keyword in keywords)
                    
                    if sim_matches:
                        confidence = self._calculate_match_confidence(real_var_lower, sim_var_lower)
                        if confidence > best_score:
                            best_score = confidence
                            best_match = ValidationMapping(
                                real_var=real_var,
                                sim_var=sim_var,
                                confidence=confidence,
                                match_type='semantic'
                            )
        
        # If no semantic match, try fuzzy matching
        if not best_match and best_score < 0.6:
            for sim_var in sim_vars:
                score = self._fuzzy_match_score(real_var_lower, sim_var.lower())
                if score > best_score and score > 0.6:
                    best_score = score
                    best_match = ValidationMapping(
                        real_var=real_var,
                        sim_var=sim_var,
                        confidence=score,
                        match_type='fuzzy'
                    )
        
        return best_match
    
    def _suggest_matches(self, real_var: str, sim_vars: List[str]) -> List[str]:
        """Suggest possible matches for an unmapped variable"""
        suggestions = []
        real_var_lower = real_var.lower()
        
        # Extract key words from real variable
        real_words = set(re.findall(r'\w+', real_var_lower))
        
        for sim_var in sim_vars:
            sim_var_lower = sim_var.lower()
            sim_words = set(re.findall(r'\w+', sim_var_lower))
            
            # Check for any common words
            common_words = real_words & sim_words
            if common_words:
                suggestions.append((sim_var, len(common_words)))
        
        # Sort by number of common words
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in suggestions]
    
    def _calculate_match_confidence(self, var1: str, var2: str) -> float:
        """Calculate confidence score for variable match"""
        # Extract words
        words1 = set(re.findall(r'\w+', var1.lower()))
        words2 = set(re.findall(r'\w+', var2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # Common words
        common = words1 & words2
        
        # Key terms that should match
        key_terms = {
            'electricity', 'heating', 'cooling', 'temperature', 'energy',
            'facility', 'zone', 'air', 'system', 'sensible', 'water',
            'heater', 'power', 'demand', 'transfer', 'total', 'mean'
        }
        
        key_matches = len(common & key_terms)
        
        # Calculate scores
        jaccard = len(common) / len(words1 | words2)
        key_score = key_matches / len(key_terms) if key_terms else 0
        
        # Weighted combination
        return 0.6 * jaccard + 0.4 * key_score
    
    def _fuzzy_match_score(self, str1: str, str2: str) -> float:
        """Simple fuzzy matching score"""
        if str1 == str2:
            return 1.0
        
        # Check containment
        if str1 in str2 or str2 in str1:
            return 0.8
        
        # Common substring ratio
        common_chars = 0
        for i in range(min(len(str1), len(str2))):
            if str1[i] == str2[i]:
                common_chars += 1
        
        return common_chars / max(len(str1), len(str2))
    
    def aggregate_zones_to_building(self, df: pd.DataFrame, variable: str, building_id: str) -> pd.DataFrame:
        """Aggregate zone-level data to building level"""
        if 'Zone' not in df.columns:
            return df
        
        # Get unique zones (excluding 'Environment')
        zones = df[df['Zone'] != 'Environment']['Zone'].unique()
        
        if len(zones) <= 1:
            return df
        
        if self.config.show_aggregations:
            logger.info(f"\n  Aggregating {len(zones)} zones for building {building_id}, variable: {variable}")
        
        # Determine aggregation method
        agg_method = self._get_aggregation_method(variable)
        
        # Group by everything except Zone, Value, and Units (if it exists)
        exclude_cols = ['Zone', 'Value']
        if 'Units' in df.columns:
            exclude_cols.append('Units')
        
        group_cols = [col for col in df.columns if col not in exclude_cols]
        
        # Build aggregation dict - only include Units if it exists
        agg_dict = {'Value': agg_method}
        if 'Units' in df.columns:
            agg_dict['Units'] = 'first'
        
        # Aggregate
        try:
            agg_df = df[df['Zone'] != 'Environment'].groupby(group_cols).agg(agg_dict).reset_index()
        except KeyError as e:
            logger.error(f"Error aggregating zones: {e}")
            logger.error(f"Available columns: {df.columns.tolist()}")
            logger.error(f"Group columns: {group_cols}")
            logger.error(f"Aggregation dict: {agg_dict}")
            raise
        
        # Add zone info
        agg_df['Zone'] = 'Building_Total'
        agg_df['zone_aggregation'] = f"{agg_method} of {len(zones)} zones"
        
        if self.config.show_aggregations:
            logger.info(f"    - Method: {agg_method}")
            logger.info(f"    - Zones: {list(zones[:5])}" + (" ..." if len(zones) > 5 else ""))
        
        return agg_df
        
    def align_and_validate_mapping(self, real_df: pd.DataFrame, sim_df: pd.DataFrame, 
                                  mapping: ValidationMapping) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Align real and simulated data for a specific variable mapping"""
        alignment_info = {
            'mapping': mapping,
            'real_count': 0,
            'sim_count': 0,
            'aligned_count': 0,
            'unit_conversion': None,
            'zone_aggregation': None,
            'issues': []
        }
        
        # Filter data for the mapped variables
        real_data = real_df[real_df['Variable'] == mapping.real_var].copy()
        sim_data = sim_df[sim_df['Variable'] == mapping.sim_var].copy()
        
        alignment_info['real_count'] = len(real_data)
        alignment_info['sim_count'] = len(sim_data)
        
        if real_data.empty:
            alignment_info['issues'].append(f"No real data found for {mapping.real_var}")
            return pd.DataFrame(), alignment_info
        
        if sim_data.empty:
            alignment_info['issues'].append(f"No simulation data found for {mapping.sim_var}")
            return pd.DataFrame(), alignment_info
        
        # Get unique buildings
        real_buildings = set(real_data['building_id'].unique())
        sim_buildings = set(sim_data['building_id'].unique())
        common_buildings = real_buildings & sim_buildings
        
        if not common_buildings:
            alignment_info['issues'].append(f"No common buildings between datasets")
            alignment_info['issues'].append(f"Real buildings: {real_buildings}")
            alignment_info['issues'].append(f"Sim buildings: {sim_buildings}")
            return pd.DataFrame(), alignment_info
        
        aligned_results = []
        
        for building_id in common_buildings:
            building_real = real_data[real_data['building_id'] == building_id]
            building_sim = sim_data[sim_data['building_id'] == building_id]
            
            # Check if zone aggregation is needed
            if 'Zone' in building_sim.columns:
                zones = building_sim[building_sim['Zone'] != 'Environment']['Zone'].unique()
                if len(zones) > 1:
                    building_sim = self.aggregate_zones_to_building(
                        building_sim, mapping.sim_var, building_id
                    )
                    alignment_info['zone_aggregation'] = f"Aggregated {len(zones)} zones"
            
            # Similarly for real data if it has zones
            if 'Zone' in building_real.columns:
                zones = building_real[building_real['Zone'] != 'Environment']['Zone'].unique()
                if len(zones) > 1:
                    building_real = self.aggregate_zones_to_building(
                        building_real, mapping.real_var, building_id
                    )
            
            # Merge on date
            building_real['Date'] = pd.to_datetime(building_real['DateTime']).dt.date
            building_sim['Date'] = pd.to_datetime(building_sim['DateTime']).dt.date
            
            # Check if Units column exists in each dataframe
            real_cols = ['building_id', 'Date', 'Value']
            sim_cols = ['building_id', 'Date', 'Value']
            real_rename = {'Value': 'Real_Value'}
            sim_rename = {'Value': 'Sim_Value'}

            if 'Units' in building_real.columns:
                real_cols.append('Units')
                real_rename['Units'] = 'Real_Units'

            if 'Units' in building_sim.columns:
                sim_cols.append('Units')
                sim_rename['Units'] = 'Sim_Units'

            merged = pd.merge(
                building_real[real_cols].rename(columns=real_rename),
                building_sim[sim_cols].rename(columns=sim_rename),
                on=['building_id', 'Date'],
                how='inner'
            )
            
            # Check for unit conversion
            if not merged.empty:
                real_unit = None
                sim_unit = None
                
                # Get units if they exist
                if 'Real_Units' in merged.columns:
                    real_unit = merged['Real_Units'].iloc[0]
                if 'Sim_Units' in merged.columns:
                    sim_unit = merged['Sim_Units'].iloc[0]
                
                # If we don't have sim units, try to infer from variable name
                if not sim_unit and mapping.sim_var:
                    # Extract unit from variable name if it's in brackets
                    unit_match = re.search(r'\[([^\]]+)\]', mapping.sim_var)
                    if unit_match:
                        unit_str = unit_match.group(1)
                        # Extract just the unit part if it includes frequency
                        unit_parts = unit_str.split('(')
                        sim_unit = unit_parts[0].strip()
                
                if real_unit and sim_unit and real_unit != sim_unit:
                    # Apply conversion
                    conversion_applied = self._apply_unit_conversion(
                        merged, 'Sim_Value', sim_unit, real_unit, mapping.sim_var
                    )
                    if conversion_applied:
                        alignment_info['unit_conversion'] = f"{sim_unit} → {real_unit}"
                    else:    
                        alignment_info['issues'].append(
                            f"Could not convert units: {sim_unit} to {real_unit} for {mapping.sim_var}"
                        )

            if not merged.empty:
                aligned_results.append(merged)
            else:
                alignment_info['issues'].append(f"No overlapping dates for building {building_id}")
        
        if aligned_results:
            final_df = pd.concat(aligned_results, ignore_index=True)
            alignment_info['aligned_count'] = len(final_df)
        else:
            final_df = pd.DataFrame()
            alignment_info['issues'].append("No data could be aligned")
        
        return final_df, alignment_info
    
    def _apply_unit_conversion(self, df: pd.DataFrame, value_col: str, 
                              from_unit: str, to_unit: str, variable_name: str) -> bool:
        """Apply unit conversion to dataframe values"""
        if not from_unit or not to_unit:
            return False
            
        if from_unit == to_unit:
            return False
        
        conversion_key = (from_unit, to_unit)
        
        if conversion_key in self.unit_conversions:
            converter = self.unit_conversions[conversion_key]
            
            if self.config.show_unit_conversions:
                logger.info(f"  Converting {variable_name}: {from_unit} → {to_unit}")
            
            if callable(converter):
                df[value_col] = df[value_col].apply(converter)
            else:
                df[value_col] = df[value_col] * converter
            
            return True
        else:
            # Try reverse conversion
            reverse_key = (to_unit, from_unit)
            if reverse_key in self.unit_conversions:
                converter = self.unit_conversions[reverse_key]
                
                if self.config.show_unit_conversions:
                    logger.info(f"  Converting {variable_name}: {from_unit} → {to_unit} (using inverse)")
                
                if callable(converter):
                    # Can't easily invert lambda functions
                    logger.warning(f"    Cannot invert conversion function for {from_unit} → {to_unit}")
                    return False
                else:
                    df[value_col] = df[value_col] / converter
                
                return True
        
        logger.warning(f"  No conversion available for {from_unit} → {to_unit}")
        return False
    
    def validate_all(self) -> Dict[str, Any]:
        """Main validation function"""
        logger.info("\n" + "="*60)
        logger.info("SMART VALIDATION STARTING")
        logger.info("="*60)
        
        results = {
            'discovery': {},
            'mappings': [],
            'validation_results': [],
            'alignment_details': [],
            'summary': {},
            'recommendations': []
        }
        
        try:
            # Step 1: Discover available data
            results['discovery'] = self.discover_available_data()
            
            # Step 2: Load real data
            real_df = self.load_and_parse_real_data()
            real_vars = real_df['Variable'].unique().tolist() if 'Variable' in real_df.columns else []
            
            # Step 3: Load simulation data
            sim_df = self.load_simulation_data(results['discovery'])
            
            if sim_df.empty:
                logger.error("No simulation data found!")
                results['summary'] = {'status': 'No simulation data found'}
                return results
            
            sim_vars = sim_df['Variable'].unique().tolist() if 'Variable' in sim_df.columns else []
            
            # Step 4: Align frequencies
            real_df, sim_df = self.align_frequencies(real_df, sim_df)
            
            # Step 5: Create variable mappings
            results['mappings'] = self.create_variable_mappings(real_vars, sim_vars)
            
            # Step 6: Validate each mapping
            self._log_step("Validating data...")
            
            for mapping in results['mappings']:
                logger.info(f"\n  Validating: {mapping.real_var} ↔ {mapping.sim_var}")
                
                try:
                    aligned_df, alignment_info = self.align_and_validate_mapping(real_df, sim_df, mapping)
                    results['alignment_details'].append(alignment_info)
                    
                    if not aligned_df.empty:
                        # Calculate metrics for each building
                        for building_id in aligned_df['building_id'].unique():
                            building_data = aligned_df[aligned_df['building_id'] == building_id]
                            
                            if len(building_data) >= 10:  # Need sufficient data points
                                # Calculate metrics
                                real_values = building_data['Real_Value'].values
                                sim_values = building_data['Sim_Value'].values
                                
                                cvrmse_val = cv_rmse(sim_values, real_values)
                                nmbe_val = nmbe(sim_values, real_values)
                                mbe_val = mean_bias_error(sim_values, real_values)
                                
                                # Get thresholds
                                cvrmse_threshold = self.config.get_threshold('cvrmse', mapping.real_var)
                                nmbe_threshold = self.config.get_threshold('nmbe', mapping.real_var)
                                
                                # Store results
                                result = {
                                    'building_id': building_id,
                                    'real_variable': mapping.real_var,
                                    'sim_variable': mapping.sim_var,
                                    'mapping_confidence': mapping.confidence,
                                    'mapping_type': mapping.match_type,
                                    'data_points': len(building_data),
                                    'cvrmse': cvrmse_val,
                                    'nmbe': nmbe_val,
                                    'mbe': mbe_val,
                                    'cvrmse_threshold': cvrmse_threshold,
                                    'nmbe_threshold': nmbe_threshold,
                                    'pass_cvrmse': cvrmse_val <= cvrmse_threshold,
                                    'pass_nmbe': abs(nmbe_val) <= nmbe_threshold,
                                    'unit_conversion': alignment_info.get('unit_conversion'),
                                    'zone_aggregation': alignment_info.get('zone_aggregation'),
                                    'issues': alignment_info.get('issues', [])
                                }
                                
                                results['validation_results'].append(result)
                                
                                # Log result
                                pass_fail = "PASS" if (result['pass_cvrmse'] and result['pass_nmbe']) else "FAIL"
                                logger.info(f"    - Building {building_id}: {pass_fail}")
                                logger.info(f"      CVRMSE: {cvrmse_val:.1f}% (threshold: {cvrmse_threshold}%)")
                                logger.info(f"      NMBE: {nmbe_val:.1f}% (threshold: ±{nmbe_threshold}%)")
                                
                                if alignment_info.get('unit_conversion'):
                                    logger.info(f"      Unit conversion: {alignment_info['unit_conversion']}")
                                if alignment_info.get('zone_aggregation'):
                                    logger.info(f"      Zone aggregation: {alignment_info['zone_aggregation']}")
                            else:
                                logger.warning(f"    - Building {building_id}: Insufficient data ({len(building_data)} points)")
                    else:
                        # Log alignment failure
                        logger.warning(f"    - Failed to align data: {alignment_info.get('issues', [])}")
                        
                except Exception as e:
                    logger.error(f"    - Error validating {mapping.real_var}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Generate summary
            results['summary'] = self._generate_summary(results)
            results['recommendations'] = self._generate_recommendations(results)
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            results['summary'] = {'status': f'Error: {str(e)}'}
        
        return results
    
    def validate_all_variants(self) -> Dict[str, Any]:
        """Validate all variants from comparison files against measured data"""
        logger.info("\n" + "="*60)
        logger.info("VARIANT VALIDATION STARTING")
        logger.info("="*60)
        
        all_results = {
            'base_results': None,
            'variant_results': {},
            'variant_comparison': {},
            'best_variant': None,
            'summary': {}
        }
        
        try:
            # Step 1: Discover available data
            discovery = self.discover_available_data()
            
            if not discovery.get('comparison_files'):
                logger.error("No comparison files found for variant validation")
                all_results['summary'] = {'status': 'No comparison files found'}
                return all_results
            
            # Step 2: Load real data once
            real_df = self.load_and_parse_real_data()
            real_vars = real_df['Variable'].unique().tolist() if 'Variable' in real_df.columns else []
            
            # Step 3: Get list of variants from first comparison file
            sample_file = next(iter(discovery['comparison_files'].values()))
            df_sample = pd.read_parquet(sample_file['file'])
            variant_columns = [col for col in df_sample.columns if col.startswith('variant_') and col.endswith('_value')]
            variant_ids = [col.replace('_value', '') for col in variant_columns]
            
            logger.info(f"\nFound {len(variant_ids)} variants to validate")
            
            # Step 4: Validate base simulation
            logger.info("\n--- Validating Base Simulation ---")
            base_sim_df = self._load_from_comparison_files(discovery, self.config.target_frequency, variant_id=None)
            
            if not base_sim_df.empty:
                # Run validation for base
                base_results = self._validate_single_configuration(real_df, base_sim_df, real_vars, "base")
                all_results['base_results'] = base_results
            
            # Step 5: Validate each variant
            for variant_id in sorted(variant_ids):
                logger.info(f"\n--- Validating {variant_id} ---")
                variant_sim_df = self._load_from_comparison_files(discovery, self.config.target_frequency, variant_id=variant_id)
                
                if not variant_sim_df.empty:
                    variant_results = self._validate_single_configuration(real_df, variant_sim_df, real_vars, variant_id)
                    all_results['variant_results'][variant_id] = variant_results
            
            # Step 6: Compare all results and find best variant
            all_results['variant_comparison'] = self._compare_variant_results(all_results)
            all_results['best_variant'] = self._find_best_variant(all_results)
            all_results['summary'] = self._generate_variant_summary(all_results)
            
        except Exception as e:
            logger.error(f"Variant validation error: {str(e)}", exc_info=True)
            all_results['summary'] = {'status': f'Error: {str(e)}'}
        
        return all_results
    
    def _validate_single_configuration(self, real_df: pd.DataFrame, sim_df: pd.DataFrame, 
                                     real_vars: List[str], config_name: str) -> Dict[str, Any]:
        """Validate a single configuration (base or variant) against real data"""
        results = {
            'config_name': config_name,
            'mappings': [],
            'validation_results': [],
            'alignment_details': [],
            'summary': {}
        }
        
        if sim_df.empty:
            results['summary'] = {'status': 'No simulation data'}
            return results
        
        sim_vars = sim_df['Variable'].unique().tolist() if 'Variable' in sim_df.columns else []
        
        # Align frequencies
        real_df_aligned, sim_df_aligned = self.align_frequencies(real_df, sim_df)
        
        # Create variable mappings
        results['mappings'] = self.create_variable_mappings(real_vars, sim_vars)
        
        # Validate each mapping
        for mapping in results['mappings']:
            try:
                aligned_df, alignment_info = self.align_and_validate_mapping(real_df_aligned, sim_df_aligned, mapping)
                results['alignment_details'].append(alignment_info)
                
                if not aligned_df.empty:
                    # Calculate metrics for each building
                    for building_id in aligned_df['building_id'].unique():
                        building_data = aligned_df[aligned_df['building_id'] == building_id]
                        
                        if len(building_data) >= 10:
                            # Calculate metrics
                            real_values = building_data['Real_Value'].values
                            sim_values = building_data['Sim_Value'].values
                            
                            cvrmse_val = cv_rmse(sim_values, real_values)
                            nmbe_val = nmbe(sim_values, real_values)
                            
                            # Get thresholds
                            cvrmse_threshold = self.config.get_threshold('cvrmse', mapping.real_var)
                            nmbe_threshold = self.config.get_threshold('nmbe', mapping.real_var)
                            
                            # Store results
                            result = {
                                'config_name': config_name,
                                'building_id': building_id,
                                'real_variable': mapping.real_var,
                                'sim_variable': mapping.sim_var,
                                'data_points': len(building_data),
                                'cvrmse': cvrmse_val,
                                'nmbe': nmbe_val,
                                'cvrmse_threshold': cvrmse_threshold,
                                'nmbe_threshold': nmbe_threshold,
                                'pass_cvrmse': cvrmse_val <= cvrmse_threshold,
                                'pass_nmbe': abs(nmbe_val) <= nmbe_threshold,
                                'pass_overall': cvrmse_val <= cvrmse_threshold and abs(nmbe_val) <= nmbe_threshold
                            }
                            
                            results['validation_results'].append(result)
                            
            except Exception as e:
                logger.error(f"Error validating {mapping.real_var} for {config_name}: {str(e)}")
        
        # Generate summary
        results['summary'] = self._generate_config_summary(results)
        
        return results
    
    def _generate_config_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary for a single configuration"""
        val_results = results['validation_results']
        
        if not val_results:
            return {'status': 'No validation results'}
        
        passed_validations = [r for r in val_results if r['pass_overall']]
        
        return {
            'total_validations': len(val_results),
            'passed_validations': len(passed_validations),
            'pass_rate': len(passed_validations) / len(val_results) * 100 if val_results else 0,
            'avg_cvrmse': sum(r['cvrmse'] for r in val_results) / len(val_results),
            'avg_nmbe': sum(r['nmbe'] for r in val_results) / len(val_results)
        }
    
    def _compare_variant_results(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare all variant results with base"""
        comparison = {}
        
        if not all_results['base_results'] or not all_results['base_results']['summary'].get('avg_cvrmse'):
            return comparison
        
        base_cvrmse = all_results['base_results']['summary']['avg_cvrmse']
        base_nmbe = all_results['base_results']['summary']['avg_nmbe']
        base_pass_rate = all_results['base_results']['summary']['pass_rate']
        
        for variant_id, variant_results in all_results['variant_results'].items():
            if variant_results['summary'].get('avg_cvrmse'):
                var_cvrmse = variant_results['summary']['avg_cvrmse']
                var_nmbe = variant_results['summary']['avg_nmbe']
                var_pass_rate = variant_results['summary']['pass_rate']
                
                comparison[variant_id] = {
                    'cvrmse_improvement': ((base_cvrmse - var_cvrmse) / base_cvrmse * 100) if base_cvrmse > 0 else 0,
                    'nmbe_improvement': ((abs(base_nmbe) - abs(var_nmbe)) / abs(base_nmbe) * 100) if base_nmbe != 0 else 0,
                    'pass_rate_improvement': var_pass_rate - base_pass_rate,
                    'absolute_metrics': {
                        'cvrmse': var_cvrmse,
                        'nmbe': var_nmbe,
                        'pass_rate': var_pass_rate
                    }
                }
        
        return comparison
    
    def _find_best_variant(self, all_results: Dict[str, Any]) -> Optional[str]:
        """Find the best performing variant"""
        if not all_results['variant_comparison']:
            return None
        
        # Score based on pass rate first, then CVRMSE
        best_variant = None
        best_score = float('-inf')
        
        for variant_id, metrics in all_results['variant_comparison'].items():
            # Score = pass_rate + (100 - cvrmse)
            score = metrics['absolute_metrics']['pass_rate'] + (100 - metrics['absolute_metrics']['cvrmse'])
            
            if score > best_score:
                best_score = score
                best_variant = variant_id
        
        return best_variant
    
    def _generate_variant_summary(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall variant validation summary"""
        summary = {
            'total_configurations': 1 + len(all_results['variant_results']),  # base + variants
            'configurations_validated': 0,
            'best_configuration': 'base',
            'best_pass_rate': 0,
            'best_cvrmse': float('inf'),
            'improvements_found': []
        }
        
        # Check base results
        if all_results['base_results'] and all_results['base_results']['summary'].get('pass_rate') is not None:
            summary['configurations_validated'] += 1
            base_pass_rate = all_results['base_results']['summary']['pass_rate']
            base_cvrmse = all_results['base_results']['summary']['avg_cvrmse']
            summary['best_pass_rate'] = base_pass_rate
            summary['best_cvrmse'] = base_cvrmse
        
        # Check variant results
        for variant_id, variant_results in all_results['variant_results'].items():
            if variant_results['summary'].get('pass_rate') is not None:
                summary['configurations_validated'] += 1
                var_pass_rate = variant_results['summary']['pass_rate']
                var_cvrmse = variant_results['summary']['avg_cvrmse']
                
                if var_pass_rate > summary['best_pass_rate'] or (var_pass_rate == summary['best_pass_rate'] and var_cvrmse < summary['best_cvrmse']):
                    summary['best_configuration'] = variant_id
                    summary['best_pass_rate'] = var_pass_rate
                    summary['best_cvrmse'] = var_cvrmse
                
                # Check for improvements
                if all_results['variant_comparison'].get(variant_id):
                    improvement = all_results['variant_comparison'][variant_id]
                    if improvement['cvrmse_improvement'] > 5 or improvement['pass_rate_improvement'] > 0:
                        summary['improvements_found'].append({
                            'variant': variant_id,
                            'cvrmse_improvement': improvement['cvrmse_improvement'],
                            'pass_rate_improvement': improvement['pass_rate_improvement']
                        })
        
        return summary
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary"""
        val_results = results['validation_results']
        
        if not val_results:
            return {'status': 'No validation results'}
        
        successful_validations = [r for r in val_results if r['data_points'] > 0]
        passed_validations = [r for r in successful_validations if r['pass_cvrmse'] and r['pass_nmbe']]
        
        summary = {
            'total_mappings': len(results['mappings']),
            'successful_validations': len(successful_validations),
            'passed_validations': len(passed_validations),
            'pass_rate': len(passed_validations) / len(successful_validations) * 100 if successful_validations else 0,
            'buildings_validated': len(set(r['building_id'] for r in successful_validations)),
            'variables_validated': len(set(r['real_variable'] for r in successful_validations)),
            'mapping_types': {
                'exact': sum(1 for m in results['mappings'] if m.match_type == 'exact'),
                'semantic': sum(1 for m in results['mappings'] if m.match_type == 'semantic'),
                'fuzzy': sum(1 for m in results['mappings'] if m.match_type == 'fuzzy')
            },
            'unit_conversions': sum(1 for r in val_results if r.get('unit_conversion')),
            'zone_aggregations': sum(1 for r in val_results if r.get('zone_aggregation')),
            'data_issues': len([r for r in val_results if r.get('issues')])
        }
        
        return summary
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check mapping quality
        low_confidence_mappings = [m for m in results['mappings'] if m.confidence < 0.7]
        if low_confidence_mappings:
            recommendations.append(
                f"Consider standardizing variable names: {len(low_confidence_mappings)} "
                f"variables have low confidence mappings"
            )
        
        # Check for missing variables
        if results['mappings'] and self.config.variables_to_validate:
            mapped_real_vars = {m.real_var for m in results['mappings']}
            requested_but_not_found = []
            for requested in self.config.variables_to_validate:
                if not any(requested.lower() in var.lower() for var in mapped_real_vars):
                    requested_but_not_found.append(requested)
            
            if requested_but_not_found:
                recommendations.append(
                    f"Could not find these requested variables: {', '.join(requested_but_not_found)}"
                )
        
        # Check for failed validations
        if results['validation_results']:
            failed = [r for r in results['validation_results'] if not (r['pass_cvrmse'] and r['pass_nmbe'])]
            if failed:
                # Group by failure reason
                cvrmse_fails = [r for r in failed if not r['pass_cvrmse']]
                nmbe_fails = [r for r in failed if not r['pass_nmbe']]
                
                if cvrmse_fails:
                    avg_cvrmse = sum(r['cvrmse'] for r in cvrmse_fails) / len(cvrmse_fails)
                    recommendations.append(
                        f"High CV(RMSE) values (avg: {avg_cvrmse:.1f}%) indicate poor model fit. "
                        f"Consider calibration."
                    )
                
                if nmbe_fails:
                    avg_nmbe = sum(abs(r['nmbe']) for r in nmbe_fails) / len(nmbe_fails)
                    recommendations.append(
                        f"High NMBE values (avg: {avg_nmbe:.1f}%) indicate systematic bias. "
                        f"Check model inputs and schedules."
                    )
        
        # Check for zone aggregation
        if results['summary'].get('zone_aggregations', 0) > 0:
            recommendations.append(
                "Consider adding building-level output variables to avoid zone aggregation uncertainties"
            )
        
        # Check for data issues
        if results['summary'].get('data_issues', 0) > 0:
            recommendations.append(
                "Some data alignment issues were encountered. Check the logs for details."
            )
        
        return recommendations


def run_smart_validation(parsed_data_path: str, real_data_path: str, 
                        config: Optional[Dict[str, Any]] = None,
                        output_path: Optional[str] = None,
                        validate_variants: bool = False) -> Dict[str, Any]:
    """Run smart validation and save results
    
    Args:
        parsed_data_path: Path to parsed simulation data
        real_data_path: Path to real/measured data
        config: Validation configuration
        output_path: Path to save results
        validate_variants: If True, validates all variants from comparison files
    """
    
    # Create validator
    validator = SmartValidationWrapper(parsed_data_path, real_data_path, config)
    
    # Run validation
    if validate_variants:
        results = validator.validate_all_variants()
        print("\n" + "="*60)
        print("VARIANT VALIDATION SUMMARY")
        print("="*60)
        
        # Print variant-specific summary
        summary = results.get('summary', {})
        if 'status' in summary:
            print(f"\nStatus: {summary['status']}")
        else:
            print(f"\nConfigurations validated: {summary.get('configurations_validated', 0)} of {summary.get('total_configurations', 0)}")
            print(f"Best configuration: {summary.get('best_configuration', 'Unknown')}")
            print(f"Best pass rate: {summary.get('best_pass_rate', 0):.1f}%")
            print(f"Best CVRMSE: {summary.get('best_cvrmse', 0):.1f}%")
            
            if summary.get('improvements_found'):
                print("\nImprovements found:")
                for imp in summary['improvements_found']:
                    print(f"  - {imp['variant']}: CVRMSE improved by {imp['cvrmse_improvement']:.1f}%")
            
            # Print detailed results for each configuration
            if results.get('base_results'):
                base_summary = results['base_results'].get('summary', {})
                print(f"\nBase results:")
                print(f"  Pass rate: {base_summary.get('pass_rate', 0):.1f}%")
                print(f"  Avg CVRMSE: {base_summary.get('avg_cvrmse', 0):.1f}%")
                print(f"  Avg NMBE: {base_summary.get('avg_nmbe', 0):.1f}%")
            
            # Show top 5 variants
            if results.get('variant_comparison'):
                sorted_variants = sorted(
                    results['variant_comparison'].items(),
                    key=lambda x: x[1]['absolute_metrics']['pass_rate'] + (100 - x[1]['absolute_metrics']['cvrmse']),
                    reverse=True
                )[:5]
                
                print("\nTop 5 variants:")
                for variant_id, metrics in sorted_variants:
                    print(f"  - {variant_id}:")
                    print(f"    Pass rate: {metrics['absolute_metrics']['pass_rate']:.1f}%")
                    print(f"    CVRMSE: {metrics['absolute_metrics']['cvrmse']:.1f}%")
                    print(f"    Improvement: {metrics['cvrmse_improvement']:.1f}%")
    else:
        results = validator.validate_all()
        print("\n" + "="*60)
        print("SMART VALIDATION SUMMARY")
        print("="*60)
    
    summary = results['summary']
    if 'status' in summary:
        print(f"\nStatus: {summary['status']}")
    else:
        print(f"\nMappings created: {summary.get('total_mappings', 0)}")
        print(f"  - Exact matches: {summary.get('mapping_types', {}).get('exact', 0)}")
        print(f"  - Semantic matches: {summary.get('mapping_types', {}).get('semantic', 0)}")
        print(f"  - Fuzzy matches: {summary.get('mapping_types', {}).get('fuzzy', 0)}")
        
        print(f"\nValidations performed: {summary.get('successful_validations', 0)}")
        print(f"Validations passed: {summary.get('passed_validations', 0)}")
        print(f"Pass rate: {summary.get('pass_rate', 0):.1f}%")
        
        print(f"\nBuildings validated: {summary.get('buildings_validated', 0)}")
        print(f"Variables validated: {summary.get('variables_validated', 0)}")
        
        if summary.get('unit_conversions', 0) > 0:
            print(f"\nUnit conversions applied: {summary['unit_conversions']}")
        if summary.get('zone_aggregations', 0) > 0:
            print(f"Zone aggregations performed: {summary['zone_aggregations']}")
        if summary.get('data_issues', 0) > 0:
            print(f"Data alignment issues encountered: {summary['data_issues']}")
    
    if results.get('recommendations'):
        print("\nRecommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    # Save results if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save validation results
        if results.get('validation_results'):
            val_df = pd.DataFrame(results['validation_results'])
            val_df.to_csv(output_path / 'validation_results.csv', index=False)
            val_df.to_parquet(output_path / 'validation_results.parquet', index=False)
        
        # Save mappings
        if results.get('mappings'):
            mappings_data = [{
                'real_variable': m.real_var,
                'sim_variable': m.sim_var,
                'confidence': m.confidence,
                'match_type': m.match_type
            } for m in results['mappings']]
            
            mappings_df = pd.DataFrame(mappings_data)
            mappings_df.to_csv(output_path / 'variable_mappings.csv', index=False)
        
        # Save summary
        with open(output_path / 'validation_summary.json', 'w') as f:
            # Convert mappings to serializable format
            results_serializable = results.copy()
            results_serializable['mappings'] = mappings_data if results.get('mappings') else []
            json.dump(results_serializable, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_path}")
    
    return results