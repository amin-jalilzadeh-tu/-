"""
Configuration handling and validation for IDF modifications.

This module manages configuration settings and validates modification parameters.
"""
"""
Modification Configuration Module - Handle and validate configuration
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
import jsonschema
from dataclasses import dataclass, field
import yaml

@dataclass
class ParameterConfig:
    """Configuration for a single parameter modification"""
    method: str
    value: Optional[float] = None
    factor: Optional[float] = None
    range: Optional[List[float]] = None
    change: Optional[float] = None
    options: Optional[List[Any]] = None
    rule: Optional[str] = None

@dataclass
class CategoryConfig:
    """Configuration for a category of modifications"""
    enabled: bool = False
    strategy: str = 'default'
    parameters: Dict[str, ParameterConfig] = field(default_factory=dict)

class ModificationConfig:
    """Handle modification configuration loading and validation"""
    
    # Configuration schema for validation
    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "modification": {
                "type": "object",
                "properties": {
                    "perform_modification": {"type": "boolean"},
                    "base_idf_selection": {
                        "type": "object",
                        "properties": {
                            "method": {"type": "string", "enum": ["specific", "representative", "all"]},
                            "building_ids": {"type": "array", "items": {"type": ["string", "integer"]}}
                        }
                    },
                    "modification_strategy": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["scenarios", "sampling", "optimization"]},
                            "num_variants": {"type": "integer", "minimum": 1},
                            "seed": {"type": "integer"},
                            "sampling_method": {"type": "string"}
                        },
                        "required": ["type", "num_variants"]
                    },
                    "categories_to_modify": {"type": "object"},
                    "output_options": {
                        "type": "object",
                        "properties": {
                            "save_modified_idfs": {"type": "boolean"},
                            "track_modifications": {"type": "boolean"},
                            "generate_report": {"type": "boolean"},
                            "output_dir": {"type": "string"}
                        }
                    },
                    "post_modification": {
                        "type": "object",
                        "properties": {
                            "run_simulations": {"type": "boolean"},
                            "parse_results": {"type": "object"},
                            "compare_with_baseline": {"type": "boolean"}
                        }
                    }
                },
                "required": ["modification_strategy", "categories_to_modify", "output_options"]
            }
        }
    }
    
    def __init__(self, config_source: Union[Dict[str, Any], str, Path]):
        """
        Initialize configuration
        
        Args:
            config_source: Configuration dict, file path, or Path object
        """
        self.config = self._load_config(config_source)
        self._validate_config()
        self._set_defaults()
        
    def _load_config(self, config_source: Union[Dict[str, Any], str, Path]) -> Dict[str, Any]:
        """Load configuration from various sources"""
        if isinstance(config_source, dict):
            return config_source
            
        config_path = Path(config_source)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        # Load based on file extension
        if config_path.suffix == '.json':
            with open(config_path) as f:
                return json.load(f)
        elif config_path.suffix in ['.yaml', '.yml']:
            with open(config_path) as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")
    
    def _validate_config(self):
        """Validate configuration against schema"""
        try:
            # For now, basic validation
            # Could use jsonschema.validate(self.config, self.CONFIG_SCHEMA)
            
            if 'modification' not in self.config:
                # Try to find modification config at root level
                if 'modification_strategy' in self.config:
                    # Config is at root level, wrap it
                    self.config = {'modification': self.config}
                else:
                    raise ValueError("No modification configuration found")
                    
            mod_config = self.config['modification']
            
            # Validate required fields
            required = ['modification_strategy', 'categories_to_modify', 'output_options']
            for field in required:
                if field not in mod_config:
                    raise ValueError(f"Missing required field: {field}")
                    
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def _set_defaults(self):
        """Set default values for missing configuration options"""
        mod_config = self.config['modification']
        
        # Default output options
        if 'output_options' not in mod_config:
            mod_config['output_options'] = {}
            
        output_defaults = {
            'save_modified_idfs': True,
            'track_modifications': True,
            'generate_report': True,
            'output_dir': 'modified_idfs'
        }
        
        for key, value in output_defaults.items():
            if key not in mod_config['output_options']:
                mod_config['output_options'][key] = value
        
        # Default modification strategy
        if 'seed' not in mod_config['modification_strategy']:
            mod_config['modification_strategy']['seed'] = 42
            
        # Default post-modification
        if 'post_modification' not in mod_config:
            mod_config['post_modification'] = {
                'run_simulations': False,
                'parse_results': {
                    'parse_idf': False,
                    'parse_sql': True
                },
                'compare_with_baseline': True
            }
    
    def get_config(self) -> Dict[str, Any]:
        """Get the modification configuration section"""
        return self.config['modification']
    
    def get_category_config(self, category: str) -> Optional[CategoryConfig]:
        """Get configuration for a specific category"""
        categories = self.config['modification']['categories_to_modify']
        
        if category not in categories:
            return None
            
        cat_config = categories[category]
        
        # Convert to CategoryConfig object
        params = {}
        for param_name, param_config in cat_config.get('parameters', {}).items():
            params[param_name] = ParameterConfig(**param_config)
            
        return CategoryConfig(
            enabled=cat_config.get('enabled', False),
            strategy=cat_config.get('strategy', 'default'),
            parameters=params
        )
    
    def get_enabled_categories(self) -> List[str]:
        """Get list of enabled categories"""
        categories = self.config['modification']['categories_to_modify']
        return [cat for cat, config in categories.items() if config.get('enabled', False)]
    
    def save_config(self, output_path: Union[str, Path]):
        """Save configuration to file"""
        output_path = Path(output_path)
        
        if output_path.suffix == '.json':
            with open(output_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        elif output_path.suffix in ['.yaml', '.yml']:
            with open(output_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")
    
    def merge_config(self, override_config: Dict[str, Any]):
        """Merge override configuration with existing config"""
        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        self.config = deep_merge(self.config, override_config)
        self._validate_config()