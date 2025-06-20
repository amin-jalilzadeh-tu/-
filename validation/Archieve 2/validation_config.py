"""
validation_config.py - Central configuration handling for validation
Handles unit conversions, variable mappings, and validation settings
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ValidationConfig:
    """Handles all configuration for the validation process"""
    
    # Default unit conversion factors to Joules
    ENERGY_CONVERSIONS = {
        'J': 1.0,
        'kJ': 1000.0,
        'MJ': 1000000.0,
        'GJ': 1000000000.0,
        'Wh': 3600.0,
        'kWh': 3600000.0,
        'MWh': 3600000000.0,
        'BTU': 1055.06,
        'kBTU': 1055060.0,
        'MMBTU': 1055060000.0,
        'therm': 105480000.0,
        'cal': 4.184,
        'kcal': 4184.0,
    }
    
    # Power conversion factors to Watts
    POWER_CONVERSIONS = {
        'W': 1.0,
        'kW': 1000.0,
        'MW': 1000000.0,
        'hp': 745.7,
        'BTU/h': 0.293071,
        'ton': 3516.85,  # refrigeration ton
    }
    
    # Temperature conversions (handled separately due to offsets)
    TEMP_CONVERSIONS = {
        'C': {'to_C': lambda x: x},
        'F': {'to_C': lambda x: (x - 32) * 5/9},
        'K': {'to_C': lambda x: x - 273.15},
        'R': {'to_C': lambda x: (x - 491.67) * 5/9}
    }
    
    # Default date formats to try
    DEFAULT_DATE_FORMATS = [
        '%m/%d',           # 01/31
        '%-m/%-d',         # 1/31 (Unix)
        '%m/%d/%Y',        # 01/31/2020
        '%-m/%-d/%Y',      # 1/31/2020
        '%Y-%m-%d',        # 2020-01-31
        '%Y-%m-%d %H:%M:%S',  # 2020-01-31 13:00:00
        '%m/%d/%Y %H:%M',  # 01/31/2020 13:00
        '%d/%m/%Y',        # 31/01/2020 (European)
        '%d-%m-%Y',        # 31-01-2020
    ]
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None, config_dict: Optional[Dict] = None):
        """
        Initialize configuration from file or dictionary
        
        Args:
            config_path: Path to configuration JSON file
            config_dict: Configuration dictionary (overrides file)
        """
        self.config = self._load_default_config()
        
        # Load from file if provided
        if config_path:
            file_config = self._load_config_file(config_path)
            self._merge_configs(self.config, file_config)
        
        # Override with dictionary if provided
        if config_dict:
            self._merge_configs(self.config, config_dict)
            
        # Validate configuration
        self._validate_config()
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'real_data': {
                'format': 'auto',  # auto, csv, parquet, wide, long
                'encoding': 'utf-8',
                'date_parsing': {
                    'formats': self.DEFAULT_DATE_FORMATS.copy(),
                    'dayfirst': False,
                    'yearfirst': False,
                    'infer_datetime_format': True
                }
            },
            'units': {
                'energy': 'J',
                'power': 'W',
                'temperature': 'C'
            },
            'variable_mappings': {},
            'building_mappings': {},
            'thresholds': {
                'cvrmse': 30.0,
                'nmbe': 10.0,
                'by_variable': {}
            },
            'aggregation': {
                'zones_to_building': True,
                'time_aggregation': 'auto',
                'spatial_method': {
                    'energy': 'sum',
                    'power': 'sum',
                    'temperature': 'weighted_average',
                    'rate': 'average'
                }
            },
            'data_filtering': {
                'remove_outliers': False,
                'outlier_method': 'zscore',
                'outlier_threshold': 4.0,
                'min_data_points': 0.9,  # 90% data completeness required
                'interpolate_gaps': False,
                'max_gap_size': 24  # hours
            },
            'analysis_options': {
                'data_frequency': 'daily',
                'timezone': 'UTC',
                'handle_dst': True,
                'seasonal_analysis': False,
                'peak_analysis': False
            }
        }
    
    def _load_config_file(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Configuration file not found: {path}")
            return {}
            
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            return {}
    
    def _merge_configs(self, base: Dict, override: Dict) -> None:
        """Deep merge override config into base config"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
    
    def _validate_config(self) -> None:
        """Validate configuration values"""
        # Check thresholds
        if self.config['thresholds']['cvrmse'] <= 0:
            raise ValueError("CVRMSE threshold must be positive")
        if self.config['thresholds']['nmbe'] <= 0:
            raise ValueError("NMBE threshold must be positive")
            
        # Check data completeness threshold
        if not 0 < self.config['data_filtering']['min_data_points'] <= 1:
            raise ValueError("min_data_points must be between 0 and 1")
    
    def get_unit_converter(self, from_unit: str, to_unit: str, variable_type: str = 'energy') -> float:
        """
        Get conversion factor between units
        
        Args:
            from_unit: Source unit
            to_unit: Target unit
            variable_type: Type of variable (energy, power, temperature)
            
        Returns:
            Conversion factor (multiply by this to convert)
        """
        # Clean unit strings
        from_unit = from_unit.strip()
        to_unit = to_unit.strip()
        
        # Same unit, no conversion
        if from_unit == to_unit:
            return 1.0
        
        # Get appropriate conversion dictionary
        if variable_type == 'energy':
            conversions = self.ENERGY_CONVERSIONS
        elif variable_type == 'power':
            conversions = self.POWER_CONVERSIONS
        else:
            logger.warning(f"Unknown variable type: {variable_type}")
            return 1.0
        
        # Check if units are recognized
        if from_unit not in conversions:
            logger.warning(f"Unknown {variable_type} unit: {from_unit}")
            return 1.0
        if to_unit not in conversions:
            logger.warning(f"Unknown {variable_type} unit: {to_unit}")
            return 1.0
        
        # Calculate conversion factor
        # Convert to base unit (J or W) then to target
        to_base = conversions[from_unit]
        from_base = conversions[to_unit]
        
        return to_base / from_base
    
    def convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert temperature value between units
        
        Args:
            value: Temperature value
            from_unit: Source unit (C, F, K, R)
            to_unit: Target unit
            
        Returns:
            Converted temperature value
        """
        if from_unit == to_unit:
            return value
            
        # Convert to Celsius first
        if from_unit in self.TEMP_CONVERSIONS:
            celsius = self.TEMP_CONVERSIONS[from_unit]['to_C'](value)
        else:
            logger.warning(f"Unknown temperature unit: {from_unit}")
            return value
        
        # Convert from Celsius to target
        if to_unit == 'C':
            return celsius
        elif to_unit == 'F':
            return celsius * 9/5 + 32
        elif to_unit == 'K':
            return celsius + 273.15
        elif to_unit == 'R':
            return (celsius + 273.15) * 9/5
        else:
            logger.warning(f"Unknown temperature unit: {to_unit}")
            return value
    
    def get_variable_mapping(self, real_var_name: str) -> str:
        """
        Get simulation variable name for a real data variable
        
        Args:
            real_var_name: Variable name from real data
            
        Returns:
            Mapped simulation variable name
        """
        # Check explicit mappings first
        if real_var_name in self.config['variable_mappings']:
            return self.config['variable_mappings'][real_var_name]
        
        # Try to find a match in reverse mappings
        for sim_var, real_var in self.config['variable_mappings'].items():
            if real_var == real_var_name:
                return sim_var
        
        # Return original if no mapping found
        return real_var_name
    
    def get_building_mapping(self, real_building_id: Union[str, int]) -> List[Union[str, int]]:
        """
        Get simulation building IDs for a real building ID
        
        Args:
            real_building_id: Building ID from real data
            
        Returns:
            List of simulation building IDs
        """
        # Convert to string for lookup
        real_id_str = str(real_building_id)
        
        if real_id_str in self.config['building_mappings']:
            mapped = self.config['building_mappings'][real_id_str]
            # Ensure it's a list
            if isinstance(mapped, list):
                return mapped
            else:
                return [mapped]
        
        # No mapping, assume same ID
        return [real_building_id]
    
    def get_date_formats(self) -> List[str]:
        """Get list of date formats to try"""
        return self.config['real_data']['date_parsing']['formats']
    
    def add_date_format(self, format_string: str) -> None:
        """Add a date format to try"""
        if format_string not in self.config['real_data']['date_parsing']['formats']:
            self.config['real_data']['date_parsing']['formats'].insert(0, format_string)
    
    def should_aggregate_zones(self) -> bool:
        """Check if zone-level data should be aggregated to building level"""
        return self.config['aggregation']['zones_to_building']
    
    def get_aggregation_method(self, variable_type: str) -> str:
        """
        Get aggregation method for a variable type
        
        Args:
            variable_type: Type of variable (energy, power, temperature, etc.)
            
        Returns:
            Aggregation method (sum, average, weighted_average)
        """
        methods = self.config['aggregation']['spatial_method']
        
        # Check if variable type is explicitly defined
        if variable_type in methods:
            return methods[variable_type]
        
        # Guess based on variable name patterns
        var_lower = variable_type.lower()
        if any(word in var_lower for word in ['energy', 'consumption']):
            return methods.get('energy', 'sum')
        elif any(word in var_lower for word in ['power', 'demand', 'rate']):
            return methods.get('power', 'sum')
        elif any(word in var_lower for word in ['temperature', 'temp']):
            return methods.get('temperature', 'weighted_average')
        else:
            return methods.get('rate', 'average')
    
    def get_threshold(self, metric: str, variable_name: Optional[str] = None) -> float:
        """
        Get threshold value for a metric
        
        Args:
            metric: Metric name (cvrmse, nmbe)
            variable_name: Optional variable name for specific thresholds
            
        Returns:
            Threshold value
        """
        # Check variable-specific threshold first
        if variable_name and variable_name in self.config['thresholds'].get('by_variable', {}):
            var_thresholds = self.config['thresholds']['by_variable'][variable_name]
            if metric in var_thresholds:
                return var_thresholds[metric]
        
        # Return default threshold
        return self.config['thresholds'].get(metric, 30.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self.config.copy()
    
    def save(self, path: Union[str, Path]) -> None:
        """Save configuration to JSON file"""
        path = Path(path)
        with open(path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def __str__(self) -> str:
        """String representation"""
        return json.dumps(self.config, indent=2)


# Convenience function for loading configuration
def load_validation_config(config_path: Optional[Union[str, Path]] = None, 
                          config_dict: Optional[Dict] = None) -> ValidationConfig:
    """
    Load validation configuration
    
    Args:
        config_path: Path to configuration file
        config_dict: Configuration dictionary
        
    Returns:
        ValidationConfig instance
    """
    return ValidationConfig(config_path, config_dict)