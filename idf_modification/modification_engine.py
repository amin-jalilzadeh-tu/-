"""
Main orchestrator for IDF modifications.

This module coordinates the execution of various modifiers and manages the
modification workflow.
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
import numpy as np

from .base_modifier import BaseModifier, ModificationResult
from .modification_tracker import ModificationTracker
from .modification_config import ModificationConfig

# Global flag to track IDD initialization
_IDD_INITIALIZED = False

class ModificationEngine:
    """Main orchestrator for IDF modifications"""
    
    def __init__(self, project_dir, config):
        """Initialize the modification engine.
        
        Args:
            project_dir: Path to project directory
            config: Either a config dict or session_id string (for backward compatibility)
        """
        import json
        from pathlib import Path
        from datetime import datetime
        
        self.project_dir = Path(project_dir)
        self.output_dir = self.project_dir / "modified_idfs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Handle both dict config and string session_id
        if isinstance(config, str):
            # Legacy mode - config is actually session_id
            self.session_id = config
            # Try to load config from project
            config_path = self.project_dir / "combined.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                # Create minimal config
                self.config = {
                    "modifications": {
                        "enable_modifications": True,
                        "scenarios": {}
                    }
                }
            self.config_manager = ModificationConfig(self.config)
        else:
            # New mode - config is a dict
            self.config = config
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.config_manager = ModificationConfig(config)
        
        # Continue with rest of initialization...
        self.tracker = ModificationTracker()
        # (keep the rest of your existing __init__ code)
    
    def _ensure_idd_initialized(self, idd_path: str):
        """Ensure IDD is initialized only once"""
        global _IDD_INITIALIZED
        if not _IDD_INITIALIZED:
            try:
                IDF.setiddname(idd_path)
                _IDD_INITIALIZED = True
                self.logger.info(f"IDD initialized with: {idd_path}")
            except Exception as e:
                if "IDD file is set" in str(e) or "IDDAlreadySetError" in str(e.__class__.__name__):
                    _IDD_INITIALIZED = True
                    self.logger.debug("IDD was already set")
                else:
                    raise
        
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
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
        return logger
    
    # In modification_engine.py, find the _load_modifiers method and replace it with this:

    
    




    # In modification_engine.py, find the _load_modifiers method and replace it with this CORRECTED version:

    def _load_modifiers(self) -> Dict[str, BaseModifier]:
        """Dynamically load all available modifiers with flexible class name detection"""
        modifiers = {}
        
        # Get the directory containing modifiers
        modifiers_dir = Path(__file__).parent / 'modifiers'
        
        # Categories to load with their possible class name variations
        category_mappings = {
            'dhw': ['DHWModifier', 'DhwModifier', 'DomesticHotWaterModifier'],
            'equipment': ['EquipmentModifier'],
            'geometry': ['GeometryModifier'],
            'hvac': ['HVACModifier', 'HvacModifier'],
            'infiltration': ['InfiltrationModifier'],
            'lighting': ['LightingModifier'],
            'materials': ['MaterialsModifier'],
            'schedules': ['SchedulesModifier'],
            'shading': ['ShadingModifier'],
            'simulation_control': ['SimulationControlModifier', 'SimulationcontrolModifier'],
            'site_location': ['SiteLocationModifier', 'SitelocationModifier'],
            'ventilation': ['VentilationModifier']
        }
        
        for category, possible_class_names in category_mappings.items():
            try:
                # Construct module name
                module_name = f"idf_modification.modifiers.{category}_modifier"
                
                # Import module dynamically
                try:
                    module = importlib.import_module(module_name)
                except ImportError as e:
                    self.logger.warning(f"Module {module_name} not found: {e}")
                    continue
                
                # Try to find the modifier class with different naming conventions
                modifier_class = None
                actual_class_name = None
                
                # First try the provided class names
                for class_name in possible_class_names:
                    if hasattr(module, class_name):
                        modifier_class = getattr(module, class_name)
                        actual_class_name = class_name
                        break
                
                # If not found, try to find any class that inherits from BaseModifier
                if not modifier_class:
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if obj.__module__ == module_name:
                            # Check if it inherits from BaseModifier
                            try:
                                if hasattr(obj, '__bases__') and any('BaseModifier' in str(base) for base in obj.__bases__):
                                    modifier_class = obj
                                    actual_class_name = name
                                    self.logger.debug(f"Auto-detected modifier class: {name} in {module_name}")
                                    break
                            except:
                                pass
                
                if not modifier_class:
                    self.logger.error(f"No suitable modifier class found in {module_name}")
                    continue
                
                # Instantiate modifier
                category_config = self.config.get('categories_to_modify', {}).get(category, {})
                modifiers[category] = modifier_class(
                    parsed_data_path=self.parsed_data_path,
                    modification_config=category_config,
                    logger=self.logger
                )
                
                self.logger.info(f"Loaded modifier: {actual_class_name} for category '{category}'")
                
            except Exception as e:
                self.logger.error(f"Failed to load modifier {category}: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
        
        # Log summary
        if modifiers:
            self.logger.info(f"Successfully loaded {len(modifiers)} modifiers: {list(modifiers.keys())}")
        else:
            self.logger.warning("No modifiers were loaded successfully")
        
        return modifiers









    def can_proceed_with_modifications(self) -> Tuple[bool, str]:
        """
        Check if all prerequisites are met for modifications
        
        Returns:
            Tuple of (can_proceed, error_message)
        """
        # Check parsed data exists
        if not self.parsed_data_path.exists():
            return False, f"Parsed data directory not found: {self.parsed_data_path}"
        
        # Check if parsed data has content
        parquet_files = list(self.parsed_data_path.glob("*.parquet"))
        if not parquet_files:
            return False, "No parsed data files found"
        
        # Check if modifiers are loaded
        if not self.modifiers:
            return False, "No modifiers loaded"
        
        # Check if at least one category is enabled
        enabled_categories = [
            cat for cat, config in self.config.get('categories_to_modify', {}).items()
            if config.get('enabled', False)
        ]
        
        if not enabled_categories:
            return False, "No modification categories are enabled"
        
        self.logger.info(f"Prerequisites check passed. Enabled categories: {enabled_categories}")
        return True, ""
    
    def generate_modifications(self, 
                             base_idf_path: Union[str, Path],
                             building_id: Optional[str] = None,
                             epw_path: Optional[Union[str, Path]] = None) -> List[Path]:
        """
        Generate modified IDF files from base IDF
        
        Args:
            base_idf_path: Path to base IDF file
            building_id: Building identifier
            epw_path: Optional path to EPW weather file
            
        Returns:
            List of paths to generated IDF files
        """
        base_idf_path = Path(base_idf_path)
        
        if not base_idf_path.exists():
            self.logger.error(f"Base IDF file not found: {base_idf_path}")
            return []
        
        if not building_id:
            # Extract from filename
            building_id = base_idf_path.stem.split('_')[1] if '_' in base_idf_path.stem else 'unknown'
            
        self.logger.info(f"Starting modifications for building {building_id}")
        self.logger.info(f"Base IDF: {base_idf_path.name}")
        if epw_path:
            self.logger.info(f"EPW file: {Path(epw_path).name}")
        
        # Create output directory for this building
        building_output_dir = self.output_base_path / f"building_{building_id}" / self.session_id
        building_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tracking
        self.tracker.start_session(self.session_id, building_id, str(base_idf_path))
        
        # Set IDD file path
        idd_path = self.config.get('iddfile', 'EnergyPlus/Energy+.idd')
        if not Path(idd_path).is_absolute():
            # Check if it's relative to current working directory
            if Path(idd_path).exists():
                idd_path = str(Path(idd_path).resolve())
            else:
                # Try relative to project path
                project_idd = self.project_path / idd_path
                if project_idd.exists():
                    idd_path = str(project_idd.resolve())
                else:
                    self.logger.error(f"IDD file not found at: {idd_path} or {project_idd}")
                    raise FileNotFoundError(f"IDD file not found: {idd_path}")

        # Use the safe IDD initialization
        self._ensure_idd_initialized(idd_path)
        
        # Generate variants
        strategy = self.config['modification_strategy']['type']
        num_variants = self.config['modification_strategy']['num_variants']
        
        self.logger.info(f"Generating {num_variants} variants using strategy: {strategy}")
        
        generated_files = []
        
        if strategy == 'scenarios':
            generated_files = self._generate_scenario_variants(
                base_idf_path, building_id, building_output_dir, num_variants, epw_path
            )
        elif strategy == 'sampling':
            generated_files = self._generate_sampling_variants(
                base_idf_path, building_id, building_output_dir, num_variants, epw_path
            )
        elif strategy == 'optimization':
            generated_files = self._generate_optimization_variants(
                base_idf_path, building_id, building_output_dir, num_variants, epw_path
            )
        else:
            self.logger.error(f"Unknown strategy: {strategy}")
        
        # Log summary
        self.logger.info(f"Generated {len(generated_files)} variants for building {building_id}")
        
        # Save session summary
        self.tracker.save_session_summary(building_output_dir)
        
        return generated_files
    
    def _generate_scenario_variants(self,
                                  base_idf_path: Path,
                                  building_id: str,
                                  output_dir: Path,
                                  num_variants: int,
                                  epw_path: Optional[Path] = None) -> List[Path]:
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
                scenario['modifications'],
                epw_path
            )
            
            if variant_path:
                generated_files.append(variant_path)
                
        return generated_files
    
    def _generate_sampling_variants(self,
                                  base_idf_path: Path,
                                  building_id: str,
                                  output_dir: Path,
                                  num_variants: int,
                                  epw_path: Optional[Path] = None) -> List[Path]:
        """Generate variants using parameter sampling"""
        generated_files = []
        
        # Get sampling method
        sampling_method = self.config['modification_strategy'].get('sampling_method', 'uniform')
        
        # Set random seed for reproducibility
        np.random.seed(self.config['modification_strategy'].get('seed', 42))
        
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
                param_values,
                epw_path
            )
            
            if variant_path:
                generated_files.append(variant_path)
                
        return generated_files
    
    def _generate_optimization_variants(self,
                                      base_idf_path: Path,
                                      building_id: str,
                                      output_dir: Path,
                                      num_variants: int,
                                      epw_path: Optional[Path] = None) -> List[Path]:
        """Generate variants for optimization objectives"""
        generated_files = []
        
        # Define optimization objectives
        objectives = self.config['modification_strategy'].get('objectives', ['energy'])
        
        for i in range(num_variants):
            variant_id = f"opt_{i:03d}"
            
            self.logger.info(f"Generating optimization variant {variant_id}")
            
            # Generate parameter values based on objectives
            param_values = self._generate_optimization_sample(objectives, i, num_variants)
            
            # Create variant
            variant_path = self._create_variant(
                base_idf_path,
                building_id,
                variant_id,
                output_dir,
                param_values,
                epw_path
            )
            
            if variant_path:
                generated_files.append(variant_path)
                
        return generated_files
    
    def _create_variant(self,
                       base_idf_path: Path,
                       building_id: str,
                       variant_id: str,
                       output_dir: Path,
                       modifications_override: Optional[Dict] = None,
                       epw_path: Optional[Path] = None) -> Optional[Path]:
        """Create a single IDF variant"""
        try:
            # Load IDF with better error handling
            try:
                if epw_path:
                    idf = IDF(str(base_idf_path), str(epw_path))
                else:
                    idf = IDF(str(base_idf_path))
            except Exception as e:
                self.logger.error(f"Failed to load base IDF {base_idf_path}: {e}")
                return None
            
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
                    self.logger.debug(f"Applying {category} modifications")
                    
                    # Override config if needed
                    if modifications_override and category in modifications_override:
                        modifier.config = modifications_override[category]
                    
                    # Identify modifiable parameters
                    modifiable = modifier.identify_modifiable_parameters(idf)
                    
                    if not modifiable:
                        self.logger.warning(f"No modifiable parameters found for {category}")
                        continue
                    
                    # Apply modifications
                    modifications = modifier.apply_modifications(
                        idf,
                        modifiable,
                        strategy=self.config['modification_strategy']['type']
                    )
                    
                    all_modifications.extend(modifications)
                    
                    # Track modifications
                    for mod in modifications:
                        self.tracker.add_modification(variant_id, mod)
            
            # Log modification summary
            self._log_modification_summary(all_modifications)
            
            # Validate modified IDF
            validation_results = self._validate_idf(idf)
            
            if validation_results['valid']:
                # Save modified IDF
                variant_filename = f"{building_id}_{variant_id}.idf"
                variant_path = output_dir / variant_filename
                idf.save(str(variant_path))
                
                self.logger.info(f"Created variant: {variant_filename}")
                
                # Verify modifications
                if base_idf_path != variant_path:
                    self._verify_modifications(base_idf_path, variant_path)
                
                return variant_path
            else:
                self.logger.error(f"Variant {variant_id} failed validation: {validation_results['errors']}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create variant {variant_id}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _log_modification_summary(self, modifications: List[ModificationResult]):
        """Log a summary of modifications made"""
        if not modifications:
            self.logger.warning("No modifications were made")
            return
        
        # Group by success/failure
        successful = [m for m in modifications if m.success]
        failed = [m for m in modifications if not m.success]
        
        self.logger.info(f"Modification Summary:")
        self.logger.info(f"  - Total modifications: {len(modifications)}")
        self.logger.info(f"  - Successful: {len(successful)}")
        self.logger.info(f"  - Failed: {len(failed)}")
        
        # Log failures
        if failed:
            self.logger.warning("Failed modifications:")
            for mod in failed[:5]:  # Show first 5 failures
                self.logger.warning(f"  - {mod.object_type}.{mod.parameter}: {mod.message}")
            if len(failed) > 5:
                self.logger.warning(f"  ... and {len(failed) - 5} more failures")
        
        # Log parameter changes summary
        if successful:
            param_changes = {}
            for mod in successful:
                key = f"{mod.object_type}.{mod.parameter}"
                if key not in param_changes:
                    param_changes[key] = 0
                param_changes[key] += 1
            
            self.logger.info("Modified parameters:")
            for param, count in sorted(param_changes.items())[:10]:
                self.logger.info(f"  - {param}: {count} objects")
    
    def _verify_modifications(self, 
                             original_idf_path: Path, 
                             modified_idf_path: Path) -> bool:
        """
        Verify that the IDF was actually modified
        
        Returns:
            True if modifications were detected
        """
        try:
            # Simple check - compare file sizes
            original_size = original_idf_path.stat().st_size
            modified_size = modified_idf_path.stat().st_size
            
            if original_size == modified_size:
                self.logger.warning("Modified IDF has same size as original - modifications may have failed")
                return False
            else:
                size_diff = modified_size - original_size
                self.logger.debug(f"File size difference: {size_diff} bytes")
            
            # Could add more sophisticated checks here
            # like comparing specific object values
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify modifications: {e}")
            return False
    
    def _define_scenarios(self) -> List[Dict[str, Any]]:
        """Define modification scenarios"""
        scenarios = [
            {
                'name': 'Baseline',
                'modifications': {}
            },
            {
                'name': 'High Efficiency HVAC',
                'modifications': {
                    'hvac': {
                        'parameters': {
                            'cop': {'method': 'percentage', 'value': 20},
                            'efficiency': {'method': 'percentage', 'value': 15}
                        }
                    }
                }
            },
            {
                'name': 'Improved Envelope',
                'modifications': {
                    'materials': {
                        'parameters': {
                            'thermal_resistance': {'method': 'percentage', 'value': 30},
                            'u_factor': {'method': 'percentage', 'value': -20}
                        }
                    }
                }
            },
            {
                'name': 'Efficient Lighting',
                'modifications': {
                    'lighting': {
                        'parameters': {
                            'watts_per_zone_floor_area': {'method': 'percentage', 'value': -30}
                        }
                    }
                }
            },
            {
                'name': 'Combined Efficiency',
                'modifications': {
                    'hvac': {
                        'parameters': {
                            'cop': {'method': 'percentage', 'value': 15},
                            'efficiency': {'method': 'percentage', 'value': 10}
                        }
                    },
                    'materials': {
                        'parameters': {
                            'thermal_resistance': {'method': 'percentage', 'value': 20}
                        }
                    },
                    'lighting': {
                        'parameters': {
                            'watts_per_zone_floor_area': {'method': 'percentage', 'value': -20}
                        }
                    }
                }
            }
        ]
        
        # Load custom scenarios from config if available
        custom_scenarios = self.config.get('scenarios', [])
        if custom_scenarios:
            scenarios.extend(custom_scenarios)
            
        return scenarios
    
    def _generate_parameter_sample(self, 
                                 method: str, 
                                 index: int, 
                                 total: int) -> Dict[str, Dict[str, Any]]:
        """Generate parameter values using sampling method"""
        param_values = {}
        
        # Get parameter ranges from config
        param_ranges = self.config.get('parameter_ranges', {})
        
        if method == 'uniform':
            # Uniform random sampling
            for category, params in param_ranges.items():
                param_values[category] = {'parameters': {}}
                for param, range_config in params.items():
                    min_val = range_config.get('min', -30)
                    max_val = range_config.get('max', 30)
                    value = np.random.uniform(min_val, max_val)
                    param_values[category]['parameters'][param] = {
                        'method': 'percentage',
                        'value': value
                    }
                    
        elif method == 'latin_hypercube':
            # Latin Hypercube Sampling
            # This is simplified - real implementation would generate all samples at once
            for category, params in param_ranges.items():
                param_values[category] = {'parameters': {}}
                for param, range_config in params.items():
                    min_val = range_config.get('min', -30)
                    max_val = range_config.get('max', 30)
                    # Simple LHS approximation
                    segment = (max_val - min_val) / total
                    value = min_val + segment * index + np.random.uniform(0, segment)
                    param_values[category]['parameters'][param] = {
                        'method': 'percentage',
                        'value': value
                    }
                    
        elif method == 'sobol':
            # Sobol sequence sampling
            # Placeholder - would need proper Sobol implementation
            param_values = self._generate_parameter_sample('uniform', index, total)
            
        return param_values
    
    def _generate_optimization_sample(self,
                                    objectives: List[str],
                                    index: int,
                                    total: int) -> Dict[str, Dict[str, Any]]:
        """Generate parameter values for optimization objectives"""
        param_values = {}
        
        # Define parameter mappings for objectives
        objective_params = {
            'energy': {
                'hvac': ['cop', 'efficiency'],
                'lighting': ['watts_per_zone_floor_area'],
                'materials': ['thermal_resistance', 'u_factor']
            },
            'comfort': {
                'hvac': ['heating_setpoint', 'cooling_setpoint'],
                'ventilation': ['outdoor_air_flow_rate']
            },
            'cost': {
                'equipment': ['efficiency_vs_cost_curve'],
                'materials': ['insulation_thickness']
            }
        }
        
        # Generate values based on objectives
        for objective in objectives:
            if objective in objective_params:
                for category, params in objective_params[objective].items():
                    if category not in param_values:
                        param_values[category] = {'parameters': {}}
                    
                    for param in params:
                        # Progressive improvement with index
                        improvement = (index / total) * 30  # Up to 30% improvement
                        param_values[category]['parameters'][param] = {
                            'method': 'percentage',
                            'value': improvement if param != 'watts_per_zone_floor_area' else -improvement
                        }
                        
        return param_values
    
    def _validate_idf(self, idf: IDF) -> Dict[str, Any]:
        """Validate modified IDF"""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check required objects
            required_objects = ['Building', 'SimulationControl', 'RunPeriod']
            for obj_type in required_objects:
                if obj_type not in idf.idfobjects or not idf.idfobjects[obj_type]:
                    validation_results['valid'] = False
                    validation_results['errors'].append(f"Missing required object: {obj_type}")
            
            # Check for zones
            if 'Zone' in idf.idfobjects:
                num_zones = len(idf.idfobjects['Zone'])
                if num_zones == 0:
                    validation_results['warnings'].append("No thermal zones defined")
                else:
                    self.logger.debug(f"IDF contains {num_zones} zones")
            
            # Check for surfaces
            surface_types = ['BuildingSurface:Detailed', 'FenestrationSurface:Detailed']
            total_surfaces = 0
            for surface_type in surface_types:
                if surface_type in idf.idfobjects:
                    total_surfaces += len(idf.idfobjects[surface_type])
            
            if total_surfaces == 0:
                validation_results['warnings'].append("No surfaces defined")
            
            # Check HVAC systems
            hvac_objects = ['HVACTemplate:Zone:IdealLoadsAirSystem', 'AirLoopHVAC', 
                           'HVACTemplate:System:VRF', 'HVACTemplate:System:PackagedVAV']
            has_hvac = False
            for hvac_type in hvac_objects:
                if hvac_type in idf.idfobjects and len(idf.idfobjects[hvac_type]) > 0:
                    has_hvac = True
                    break
            
            if not has_hvac:
                validation_results['warnings'].append("No HVAC system defined")
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {str(e)}")
            
        return validation_results
    
    def generate_modification_report(self) -> Path:
        """Generate summary report of all modifications"""
        report_path = self.output_base_path / f"modification_report_{self.session_id}.json"
        
        report = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'configuration': self.config,
            'summary': self.tracker.get_summary(),
            'variants': self.tracker.get_all_variants()
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        self.logger.info(f"Generated modification report: {report_path}")
        return report_path
    
    def get_modified_idfs(self, building_id: Optional[str] = None) -> List[Path]:
        """
        Get list of all modified IDF files
        
        Args:
            building_id: Optional building ID to filter by
            
        Returns:
            List of paths to modified IDF files
        """
        pattern = f"building_{building_id}/**/*.idf" if building_id else "**/*.idf"
        return list(self.output_base_path.glob(pattern))