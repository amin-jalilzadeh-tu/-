"""
Main orchestrator for IDF modifications.

This module coordinates the execution of various modifiers and manages the
modification workflow.
"""
"""
Modification Engine - Main orchestrator for IDF modifications
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
from eppy.modeleditor import IDF
import shutil
from datetime import datetime
import importlib
import inspect

from .base_modifier import BaseModifier, ModificationResult
from .modification_tracker import ModificationTracker
from .modification_config import ModificationConfig

class ModificationEngine:
    """Main orchestrator for IDF modifications"""
    
    def __init__(self, 
                 project_path: Union[str, Path],
                 config: Union[Dict[str, Any], str, Path],
                 logger: Optional[logging.Logger] = None):
        """
        Initialize modification engine
        
        Args:
            project_path: Path to project directory
            config: Configuration dict or path to config file
            logger: Logger instance
        """
        self.project_path = Path(project_path)
        self.logger = logger or self._setup_logger()
        
        # Load configuration
        self.config_manager = ModificationConfig(config)
        self.config = self.config_manager.get_config()
        
        # Initialize paths
        self.parsed_data_path = self.project_path / 'parsed_data'
        self.output_base_path = self.project_path / self.config['output_options']['output_dir']
        self.output_base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize tracker
        self.tracker = ModificationTracker(self.output_base_path)
        
        # Load modifiers dynamically
        self.modifiers = self._load_modifiers()
        
        # Track modification sessions
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger with file and console handlers"""
        logger = logging.getLogger('ModificationEngine')
        logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # File handler
        log_dir = self.project_path / 'logs'
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / f'modification_{datetime.now():%Y%m%d_%H%M%S}.log')
        fh.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
        return logger
    
    def _load_modifiers(self) -> Dict[str, BaseModifier]:
        """Dynamically load all modifier classes"""
        modifiers = {}
        modifiers_path = Path(__file__).parent / 'modifiers'
        
        # Get categories to modify from config
        categories_config = self.config.get('categories_to_modify', {})
        
        # Import all modifier modules
        for file_path in modifiers_path.glob('*_modifier.py'):
            if file_path.name == '__init__.py':
                continue
                
            module_name = file_path.stem
            category_name = module_name.replace('_modifier', '')
            
            try:
                # Import module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find modifier class
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseModifier) and 
                        obj != BaseModifier):
                        # Instantiate modifier
                        modifier_config = categories_config.get(category_name, {})
                        modifier = obj(
                            self.parsed_data_path,
                            modifier_config,
                            self.logger
                        )
                        modifiers[category_name] = modifier
                        self.logger.info(f"Loaded modifier: {name}")
                        break
                        
            except Exception as e:
                self.logger.error(f"Failed to load modifier {module_name}: {e}")
                
        return modifiers
    
    def generate_modifications(self, 
                             base_idf_path: Union[str, Path],
                             building_id: Optional[str] = None) -> List[Path]:
        """
        Generate modified IDF files from base IDF
        
        Args:
            base_idf_path: Path to base IDF file
            building_id: Building identifier
            
        Returns:
            List of paths to generated IDF files
        """
        base_idf_path = Path(base_idf_path)
        
        if not building_id:
            # Extract from filename
            building_id = base_idf_path.stem.split('_')[1] if '_' in base_idf_path.stem else 'unknown'
            
        self.logger.info(f"Starting modifications for building {building_id}")
        
        # Create output directory for this building
        building_output_dir = self.output_base_path / f"building_{building_id}" / self.session_id
        building_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tracking
        self.tracker.start_session(self.session_id, building_id, str(base_idf_path))
        
        # Load base IDF
        IDF.setiddname(self.config.get('iddfile', 'Energy+.idd'))
        
        # Generate variants
        strategy = self.config['modification_strategy']['type']
        num_variants = self.config['modification_strategy']['num_variants']
        
        generated_files = []
        
        if strategy == 'scenarios':
            generated_files = self._generate_scenario_variants(
                base_idf_path, building_id, building_output_dir, num_variants
            )
        elif strategy == 'sampling':
            generated_files = self._generate_sampling_variants(
                base_idf_path, building_id, building_output_dir, num_variants
            )
        elif strategy == 'optimization':
            generated_files = self._generate_optimization_variants(
                base_idf_path, building_id, building_output_dir, num_variants
            )
        else:
            self.logger.error(f"Unknown strategy: {strategy}")
            
        # Save session summary
        self.tracker.save_session_summary(building_output_dir)
        
        return generated_files
    
    def _generate_scenario_variants(self,
                                  base_idf_path: Path,
                                  building_id: str,
                                  output_dir: Path,
                                  num_variants: int) -> List[Path]:
        """Generate variants based on predefined scenarios"""
        generated_files = []
        
        # Define scenarios (can be loaded from config)
        scenarios = self._define_scenarios()
        
        for i in range(min(num_variants, len(scenarios))):
            scenario = scenarios[i]
            variant_id = f"scenario_{i:03d}"
            
            self.logger.info(f"Generating variant {variant_id}: {scenario['name']}")
            
            # Create variant
            variant_path = self._create_variant(
                base_idf_path,
                building_id,
                variant_id,
                output_dir,
                scenario['modifications']
            )
            
            if variant_path:
                generated_files.append(variant_path)
                
        return generated_files
    
    def _generate_sampling_variants(self,
                                  base_idf_path: Path,
                                  building_id: str,
                                  output_dir: Path,
                                  num_variants: int) -> List[Path]:
        """Generate variants using parameter sampling"""
        generated_files = []
        
        # Get sampling method
        sampling_method = self.config['modification_strategy'].get('sampling_method', 'uniform')
        
        for i in range(num_variants):
            variant_id = f"sample_{i:03d}"
            
            self.logger.info(f"Generating variant {variant_id} using {sampling_method} sampling")
            
            # Generate parameter values
            param_values = self._generate_parameter_sample(sampling_method, i, num_variants)
            
            # Create variant
            variant_path = self._create_variant(
                base_idf_path,
                building_id,
                variant_id,
                output_dir,
                param_values
            )
            
            if variant_path:
                generated_files.append(variant_path)
                
        return generated_files
    
    def _create_variant(self,
                       base_idf_path: Path,
                       building_id: str,
                       variant_id: str,
                       output_dir: Path,
                       modifications_override: Optional[Dict] = None) -> Optional[Path]:
        """Create a single IDF variant"""
        try:
            # Load IDF
            idf = IDF(str(base_idf_path))
            
            # Track variant
            self.tracker.start_variant(variant_id)
            
            # Load current values for all modifiers
            for category, modifier in self.modifiers.items():
                if self.config['categories_to_modify'].get(category, {}).get('enabled', False):
                    modifier.load_current_values(building_id)
            
            # Apply modifications
            all_modifications = []
            
            for category, modifier in self.modifiers.items():
                category_config = self.config['categories_to_modify'].get(category, {})
                
                if category_config.get('enabled', False):
                    # Override config if needed
                    if modifications_override and category in modifications_override:
                        modifier.config = modifications_override[category]
                    
                    # Identify modifiable parameters
                    modifiable = modifier.identify_modifiable_parameters(idf)
                    
                    # Apply modifications
                    modifications = modifier.apply_modifications(
                        idf,
                        modifiable,
                        category_config.get('strategy', 'default')
                    )
                    
                    # Validate
                    modifications = modifier.validate_modifications(idf, modifications)
                    
                    all_modifications.extend(modifications)
                    
                    # Track
                    self.tracker.track_modifications(category, modifications)
            
            # Save variant
            variant_filename = f"{base_idf_path.stem}_{variant_id}.idf"
            variant_path = output_dir / variant_filename
            idf.saveas(str(variant_path))
            
            # Track variant completion
            self.tracker.complete_variant(variant_id, str(variant_path), all_modifications)
            
            self.logger.info(f"Created variant: {variant_path}")
            return variant_path
            
        except Exception as e:
            self.logger.error(f"Failed to create variant {variant_id}: {e}")
            self.tracker.fail_variant(variant_id, str(e))
            return None
    
    def _define_scenarios(self) -> List[Dict[str, Any]]:
        """Define modification scenarios"""
        # Can be loaded from config or defined here
        scenarios = [
            {
                'name': 'baseline',
                'description': 'No modifications',
                'modifications': {}
            },
            {
                'name': 'efficient_hvac',
                'description': 'Improve HVAC efficiency',
                'modifications': {
                    'hvac': {
                        'enabled': True,
                        'parameters': {
                            'cop': {'method': 'multiplier', 'factor': 1.3},
                            'efficiency': {'method': 'multiplier', 'factor': 1.2}
                        }
                    }
                }
            },
            {
                'name': 'tight_envelope',
                'description': 'Reduce infiltration and improve insulation',
                'modifications': {
                    'infiltration': {
                        'enabled': True,
                        'parameters': {
                            'flow_rate': {'method': 'multiplier', 'factor': 0.5}
                        }
                    },
                    'materials': {
                        'enabled': True,
                        'parameters': {
                            'conductivity': {'method': 'multiplier', 'factor': 0.7}
                        }
                    }
                }
            },
            {
                'name': 'efficient_lighting',
                'description': 'Reduce lighting power density',
                'modifications': {
                    'lighting': {
                        'enabled': True,
                        'parameters': {
                            'watts_per_area': {'method': 'multiplier', 'factor': 0.6}
                        }
                    }
                }
            },
            {
                'name': 'comprehensive',
                'description': 'All efficiency improvements',
                'modifications': {
                    'hvac': {
                        'enabled': True,
                        'parameters': {
                            'cop': {'method': 'multiplier', 'factor': 1.4}
                        }
                    },
                    'infiltration': {
                        'enabled': True,
                        'parameters': {
                            'flow_rate': {'method': 'multiplier', 'factor': 0.4}
                        }
                    },
                    'lighting': {
                        'enabled': True,
                        'parameters': {
                            'watts_per_area': {'method': 'multiplier', 'factor': 0.5}
                        }
                    }
                }
            }
        ]
        
        return scenarios
    
    def _generate_parameter_sample(self, 
                                 method: str, 
                                 sample_idx: int,
                                 total_samples: int) -> Dict[str, Any]:
        """Generate parameter values for sampling"""
        # Implementation depends on sampling method
        # This is a placeholder for uniform random sampling
        import random
        
        if method == 'uniform':
            sample_config = {}
            
            for category, cat_config in self.config['categories_to_modify'].items():
                if cat_config.get('enabled', False):
                    sample_config[category] = {
                        'enabled': True,
                        'parameters': {}
                    }
                    
                    for param, param_config in cat_config.get('parameters', {}).items():
                        if param_config.get('method') == 'range':
                            value = random.uniform(*param_config['range'])
                            sample_config[category]['parameters'][param] = {
                                'method': 'absolute',
                                'value': value
                            }
                            
        elif method == 'latin_hypercube':
            # Implement LHS sampling
            pass
            
        elif method == 'sobol':
            # Implement Sobol sequences
            pass
            
        return sample_config
    
    def generate_modification_report(self, output_path: Optional[Path] = None) -> Path:
        """Generate comprehensive modification report"""
        if not output_path:
            output_path = self.output_base_path / f"modification_report_{self.session_id}.html"
            
        report = self.tracker.generate_report()
        
        # Save report
        with open(output_path, 'w') as f:
            f.write(report)
            
        self.logger.info(f"Generated modification report: {output_path}")
        return output_path
    
    def get_modified_files(self, building_id: Optional[str] = None) -> List[Path]:
        """Get list of all modified IDF files"""
        if building_id:
            pattern = f"building_{building_id}/**/*.idf"
        else:
            pattern = "**/*.idf"
            
        return list(self.output_base_path.glob(pattern))
    
    def cleanup_old_sessions(self, keep_last_n: int = 5):
        """Clean up old modification sessions"""
        # Get all session directories
        sessions = []
        for building_dir in self.output_base_path.iterdir():
            if building_dir.is_dir() and building_dir.name.startswith('building_'):
                for session_dir in building_dir.iterdir():
                    if session_dir.is_dir():
                        sessions.append(session_dir)
        
        # Sort by modification time
        sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove old sessions
        for session_dir in sessions[keep_last_n:]:
            shutil.rmtree(session_dir)
            self.logger.info(f"Removed old session: {session_dir}")