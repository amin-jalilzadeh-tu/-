# validation_config_simple.py
"""
Simple configuration handler for validation - replaces the complex ValidationConfig
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_validation_config(config_path: Optional[str] = None, 
                          config_dict: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Load validation configuration from file or dictionary
    
    Args:
        config_path: Path to JSON configuration file
        config_dict: Configuration dictionary
        
    Returns:
        Configuration dictionary with defaults
    """
    # Default configuration
    default_config = {
        'variables_to_validate': [],  # Empty means validate all
        'aggregation': {
            'target_frequency': 'daily',
            'methods': {
                'energy': 'sum',
                'temperature': 'mean',
                'power': 'mean'
            }
        },
        'thresholds': {
            'default': {
                'cvrmse': 30.0,
                'nmbe': 10.0
            },
            'by_variable': {}
        },
        'logging': {
            'level': 'INFO',
            'show_mappings': True,
            'show_aggregations': True,
            'show_unit_conversions': True
        }
    }
    
    # Load from file if provided
    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path, 'r') as f:
                file_config = json.load(f)
                # Merge with defaults
                config = deep_merge(default_config, file_config)
        else:
            config = default_config
    else:
        config = default_config
    
    # Override with dictionary if provided
    if config_dict:
        config = deep_merge(config, config_dict)
    
    return config


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result
    