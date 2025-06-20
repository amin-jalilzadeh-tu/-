"""
Main Modifier Module - Coordinates all IDF modifications
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
from datetime import datetime
import importlib
import logging

from .base_modifier import ModificationScenario, ModificationParameter
from .modification_tracker import ModificationTracker
from .scenario_manager import ScenarioManager


class MainModifier:
    """Main coordinator for IDF modifications"""
    
    def __init__(self, config: Dict[str, Any], project_path: Path):
        """
        Initialize the main modifier
        
        Args:
            config: Configuration dictionary
            project_path: Path to project directory
        """
        self.config = config
        self.project_path = Path(project_path)
        self.parsed_data_path = self.project_path / "parsed_data"
        self.output_path = self.project_path / "modified_idfs"
        
        # Create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.modifiers = {}
        self.tracker = ModificationTracker(self.output_path)
        self.scenario_manager = ScenarioManager(self.output_path)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load modifiers
        self._load_modifiers()
        
    def _load_modifiers(self):
        """Dynamically load modifier modules"""
        modifier_config = self.config.get('parameter_groups', {})
        
        # Map of category to module name
        modifier_map = {
            'hvac': 'hvac_modifier.HVACModifier',
            'lighting': 'lighting_modifier.LightingModifier',
            'envelope': 'envelope_modifier.EnvelopeModifier',
            'infiltration': 'infiltration_modifier.InfiltrationModifier',
            'equipment': 'equipment_modifier.EquipmentModifier',
            'setpoints': 'setpoint_modifier.SetpointModifier',
            'dhw': 'dhw_modifier.DHWModifier'
        }
        
        for category, module_path in modifier_map.items():
            if modifier_config.get(category, {}).get('enabled', False):
                try:
                    module_name, class_name = module_path.rsplit('.', 1)
                    module = importlib.import_module(f'.modifiers.{module_name}', package='idf_modifier')
                    modifier_class = getattr(module, class_name)
                    self.modifiers[category] = modifier_class(category, self.parsed_data_path)
                    self.logger.info(f"Loaded modifier: {category}")
                except Exception as e:
                    self.logger.warning(f"Could not load modifier {category}: {e}")
    
    def modify_building(self, 
                       base_idf_path: Path,
                       building_id: str,
                       output_dir: Optional[Path] = None) -> List[Path]:
        """
        Generate modified IDF files for a building
        
        Args:
            base_idf_path: Path to base IDF file
            building_id: Building identifier
            output_dir: Optional output directory override
            
        Returns:
            List of generated IDF file paths
        """
        self.logger.info(f"Starting modification for building {building_id}")
        
        # Setup output directory
        if output_dir is None:
            output_dir = self.output_path / building_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load base IDF
        idf = IDF(str(base_idf_path))
        
        # Phase 1: Identify all modifiable parameters
        all_parameters = self._identify_parameters(idf, building_id)
        self.logger.info(f"Identified {len(all_parameters)} modifiable parameters")
        
        # Phase 2: Generate modification scenarios
        scenarios = self._generate_scenarios(all_parameters, building_id)
        self.logger.info(f"Generated {len(scenarios)} modification scenarios")
        
        # Phase 3: Apply modifications and generate IDFs
        generated_files = []
        
        for i, scenario in enumerate(scenarios):
            scenario_path = output_dir / f"{building_id}_scenario_{i:03d}.idf"
            
            # Copy base IDF
            scenario_idf = IDF(str(base_idf_path))
            
            # Apply modifications
            success = self._apply_scenario(scenario_idf, scenario)
            
            if success:
                # Save modified IDF
                scenario_idf.saveas(str(scenario_path))
                generated_files.append(scenario_path)
                
                # Track modifications
                self.tracker.track_scenario(building_id, scenario, scenario_path)
                
                self.logger.info(f"Generated scenario {i}: {scenario_path.name}")
            else:
                self.logger.error(f"Failed to apply scenario {i}")
        
        # Save summary
        self._save_modification_summary(building_id, scenarios, generated_files)
        
        return generated_files
    
    def _identify_parameters(self, idf: IDF, building_id: str) -> Dict[str, List[ModificationParameter]]:
        """Identify all modifiable parameters across categories"""
        all_parameters = {}
        
        for category, modifier in self.modifiers.items():
            try:
                parameters = modifier.identify_parameters(idf, building_id)
                if parameters:
                    all_parameters[category] = parameters
                    self.logger.debug(f"{category}: Found {len(parameters)} parameters")
            except Exception as e:
                self.logger.error(f"Error identifying {category} parameters: {e}")
                
        return all_parameters
    
    def _generate_scenarios(self, 
                          all_parameters: Dict[str, List[ModificationParameter]],
                          building_id: str) -> List[ModificationScenario]:
        """Generate modification scenarios based on configuration"""
        scenarios = []
        scenario_config = self.config.get('scenarios', {})
        
        # Get scenario generation method
        method = scenario_config.get('method', 'factorial')
        count = scenario_config.get('count', 10)
        
        if method == 'factorial':
            scenarios = self._generate_factorial_scenarios(all_parameters, count)
        elif method == 'random':
            scenarios = self._generate_random_scenarios(all_parameters, count)
        elif method == 'optimization':
            scenarios = self._generate_optimization_scenarios(all_parameters, count)
        elif method == 'custom':
            scenarios = self._generate_custom_scenarios(all_parameters, building_id)
        else:
            # Default: performance levels
            scenarios = self._generate_performance_scenarios(all_parameters)
            
        return scenarios
    
    def _generate_performance_scenarios(self, 
                                      all_parameters: Dict[str, List[ModificationParameter]]) -> List[ModificationScenario]:
        """Generate scenarios based on performance improvement levels"""
        scenarios = []
        
        # Define performance levels
        performance_levels = {
            'baseline': {
                'name': 'Baseline',
                'description': 'No modifications',
                'multipliers': {}
            },
            'basic': {
                'name': 'Basic Improvements',
                'description': 'Code minimum improvements',
                'multipliers': {
                    'hvac': {'efficiency': 1.1},
                    'lighting': {'power': 0.9},
                    'infiltration': {'rate': 0.8}
                }
            },
            'moderate': {
                'name': 'Moderate Improvements',
                'description': 'Cost-effective improvements',
                'multipliers': {
                    'hvac': {'efficiency': 1.25},
                    'lighting': {'power': 0.7},
                    'infiltration': {'rate': 0.6},
                    'envelope': {'insulation': 1.5}
                }
            },
            'advanced': {
                'name': 'Advanced Improvements',
                'description': 'High-performance building',
                'multipliers': {
                    'hvac': {'efficiency': 1.5},
                    'lighting': {'power': 0.5},
                    'infiltration': {'rate': 0.3},
                    'envelope': {'insulation': 2.0}
                }
            }
        }
        
        for level_id, level_config in performance_levels.items():
            scenario = ModificationScenario(
                scenario_id=f"perf_{level_id}",
                scenario_name=level_config['name'],
                description=level_config['description']
            )
            
            # Apply multipliers to parameters
            for category, parameters in all_parameters.items():
                if category in level_config.get('multipliers', {}):
                    modifier = self.modifiers[category]
                    modifications = modifier.generate_modifications(
                        parameters,
                        strategy='performance',
                        options=level_config['multipliers'][category]
                    )
                    
                    # Add to scenario
                    for mod_set in modifications:
                        for param_id, new_value in mod_set.items():
                            # Find parameter
                            for param in parameters:
                                if modifier.create_parameter_id(param.object_type, 
                                                              param.object_name, 
                                                              param.field_name) == param_id:
                                    param.new_value = new_value
                                    scenario.parameters.append(param)
                                    
            scenarios.append(scenario)
            
        return scenarios
    
    def _generate_factorial_scenarios(self, 
                                    all_parameters: Dict[str, List[ModificationParameter]],
                                    max_scenarios: int) -> List[ModificationScenario]:
        """Generate factorial design scenarios"""
        scenarios = []
        
        # Select key parameters for factorial design
        key_params = self._select_key_parameters(all_parameters, max_factors=5)
        
        # Generate factorial combinations
        levels = 3  # Low, medium, high
        combinations = self._generate_factorial_combinations(key_params, levels)
        
        # Limit to max scenarios
        if len(combinations) > max_scenarios:
            # Random sample
            indices = np.random.choice(len(combinations), max_scenarios, replace=False)
            combinations = [combinations[i] for i in indices]
        
        for i, combo in enumerate(combinations):
            scenario = ModificationScenario(
                scenario_id=f"factorial_{i:03d}",
                scenario_name=f"Factorial Design {i+1}",
                description="Factorial design scenario"
            )
            
            for param, value in combo.items():
                param.new_value = value
                scenario.parameters.append(param)
                
            scenarios.append(scenario)
            
        return scenarios
    
    def _generate_random_scenarios(self,
                                 all_parameters: Dict[str, List[ModificationParameter]],
                                 count: int) -> List[ModificationScenario]:
        """Generate random scenarios"""
        scenarios = []
        
        for i in range(count):
            scenario = ModificationScenario(
                scenario_id=f"random_{i:03d}",
                scenario_name=f"Random Scenario {i+1}",
                description="Randomly generated scenario"
            )
            
            # Randomly modify parameters from each category
            for category, parameters in all_parameters.items():
                modifier = self.modifiers[category]
                
                # Randomly select parameters to modify
                n_params = min(len(parameters), np.random.poisson(3))
                if n_params > 0:
                    selected_params = np.random.choice(parameters, n_params, replace=False)
                    
                    # Generate random modifications
                    modifications = modifier.generate_modifications(
                        list(selected_params),
                        strategy='random',
                        options={'seed': i}
                    )
                    
                    # Add to scenario
                    for mod_set in modifications:
                        for param_id, new_value in mod_set.items():
                            for param in selected_params:
                                if modifier.create_parameter_id(param.object_type,
                                                              param.object_name,
                                                              param.field_name) == param_id:
                                    param.new_value = new_value
                                    scenario.parameters.append(param)
                                    
            scenarios.append(scenario)
            
        return scenarios
    
    def _apply_scenario(self, idf: IDF, scenario: ModificationScenario) -> bool:
        """Apply a scenario to an IDF"""
        # Group parameters by category
        params_by_category = {}
        for param in scenario.parameters:
            category = self._get_parameter_category(param)
            if category not in params_by_category:
                params_by_category[category] = {}
            
            param_id = self._create_full_parameter_id(param)
            params_by_category[category][param_id] = param.new_value
        
        # Apply modifications using appropriate modifiers
        success = True
        for category, modifications in params_by_category.items():
            if category in self.modifiers:
                try:
                    modifier = self.modifiers[category]
                    if not modifier.apply_modifications(idf, modifications):
                        success = False
                        self.logger.error(f"Failed to apply {category} modifications")
                except Exception as e:
                    self.logger.error(f"Error applying {category} modifications: {e}")
                    success = False
                    
        return success
    
    def _get_parameter_category(self, param: ModificationParameter) -> str:
        """Determine category from parameter"""
        # Map object types to categories
        category_map = {
            'LIGHTS': 'lighting',
            'ELECTRICEQUIPMENT': 'equipment',
            'COIL:COOLING': 'hvac',
            'COIL:HEATING': 'hvac',
            'FAN': 'hvac',
            'MATERIAL': 'envelope',
            'CONSTRUCTION': 'envelope',
            'ZONEINFILTRATION': 'infiltration',
            'THERMOSTATSETPOINT': 'setpoints',
            'WATERHEATER': 'dhw'
        }
        
        for prefix, category in category_map.items():
            if param.object_type.startswith(prefix):
                return category
                
        return 'other'
    
    def _create_full_parameter_id(self, param: ModificationParameter) -> str:
        """Create full parameter ID"""
        return f"{param.object_type}::{param.object_name}::{param.field_name}"
    
    def _save_modification_summary(self, 
                                 building_id: str,
                                 scenarios: List[ModificationScenario],
                                 generated_files: List[Path]):
        """Save summary of modifications"""
        summary = {
            'building_id': building_id,
            'timestamp': datetime.now().isoformat(),
            'base_idf': str(self.config.get('base_idf_path', '')),
            'scenarios_generated': len(scenarios),
            'files_created': len(generated_files),
            'scenarios': []
        }
        
        for scenario, filepath in zip(scenarios, generated_files):
            scenario_summary = {
                'scenario_id': scenario.scenario_id,
                'scenario_name': scenario.scenario_name,
                'description': scenario.description,
                'file_path': str(filepath),
                'parameters_modified': len(scenario.parameters),
                'categories_modified': list(set(self._get_parameter_category(p) 
                                              for p in scenario.parameters))
            }
            summary['scenarios'].append(scenario_summary)
        
        # Save as JSON
        summary_path = self.output_path / building_id / 'modification_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
            
        # Save as DataFrame
        df_records = []
        for scenario in scenarios:
            for param in scenario.parameters:
                df_records.append({
                    'building_id': building_id,
                    'scenario_id': scenario.scenario_id,
                    'scenario_name': scenario.scenario_name,
                    'category': self._get_parameter_category(param),
                    'object_type': param.object_type,
                    'object_name': param.object_name,
                    'field_name': param.field_name,
                    'original_value': param.current_value,
                    'new_value': param.new_value,
                    'units': param.units
                })
                
        if df_records:
            df = pd.DataFrame(df_records)
            df.to_parquet(self.output_path / building_id / 'modifications.parquet', index=False)
            
    def _select_key_parameters(self, 
                             all_parameters: Dict[str, List[ModificationParameter]],
                             max_factors: int = 5) -> List[ModificationParameter]:
        """Select key parameters for factorial design"""
        # Priority parameters for each category
        priority_params = {
            'hvac': ['cop', 'efficiency', 'capacity'],
            'lighting': ['watts_per_zone_floor_area', 'lighting_level'],
            'infiltration': ['air_changes_per_hour', 'flow_rate'],
            'envelope': ['conductivity', 'thickness'],
            'setpoints': ['heating_setpoint', 'cooling_setpoint']
        }
        
        selected = []
        for category, params in all_parameters.items():
            if category in priority_params:
                for param in params:
                    for priority in priority_params[category]:
                        if priority in param.field_name.lower():
                            selected.append(param)
                            if len(selected) >= max_factors:
                                return selected
                                
        return selected[:max_factors]
    
    def _generate_factorial_combinations(self, 
                                       parameters: List[ModificationParameter],
                                       levels: int = 3) -> List[Dict[ModificationParameter, float]]:
        """Generate factorial combinations"""
        import itertools
        
        # Generate levels for each parameter
        param_levels = {}
        for param in parameters:
            if isinstance(param.current_value, (int, float)):
                # Numeric parameter
                if param.constraints:
                    min_val = param.constraints.get('min_value', param.current_value * 0.5)
                    max_val = param.constraints.get('max_value', param.current_value * 1.5)
                else:
                    min_val = param.current_value * 0.5
                    max_val = param.current_value * 1.5
                    
                param_levels[param] = np.linspace(min_val, max_val, levels)
            else:
                # Non-numeric, keep current value
                param_levels[param] = [param.current_value]
        
        # Generate all combinations
        combinations = []
        for combo in itertools.product(*param_levels.values()):
            combinations.append(dict(zip(param_levels.keys(), combo)))
            
        return combinations
    
    def _generate_custom_scenarios(self,
                                 all_parameters: Dict[str, List[ModificationParameter]],
                                 building_id: str) -> List[ModificationScenario]:
        """Generate custom scenarios from configuration"""
        scenarios = []
        
        # Load custom scenario definitions
        custom_scenarios = self.config.get('custom_scenarios', [])
        
        for i, custom_def in enumerate(custom_scenarios):
            scenario = ModificationScenario(
                scenario_id=f"custom_{i:03d}",
                scenario_name=custom_def.get('name', f'Custom Scenario {i+1}'),
                description=custom_def.get('description', '')
            )
            
            # Apply custom modifications
            for category, mods in custom_def.get('modifications', {}).items():
                if category in all_parameters:
                    for param in all_parameters[category]:
                        # Check if this parameter should be modified
                        for field_pattern, value in mods.items():
                            if field_pattern in param.field_name.lower():
                                param.new_value = value
                                scenario.parameters.append(param)
                                
            scenarios.append(scenario)
            
        return scenarios
    
    def _generate_optimization_scenarios(self,
                                       all_parameters: Dict[str, List[ModificationParameter]],
                                       count: int) -> List[ModificationScenario]:
        """Generate scenarios for optimization studies"""
        # This would integrate with optimization algorithms
        # For now, return Latin Hypercube samples
        return self._generate_lhs_scenarios(all_parameters, count)
    
    def _generate_lhs_scenarios(self,
                              all_parameters: Dict[str, List[ModificationParameter]],
                              count: int) -> List[ModificationScenario]:
        """Generate Latin Hypercube Sample scenarios"""
        from scipy.stats import qmc
        
        scenarios = []
        
        # Collect all numeric parameters
        numeric_params = []
        param_bounds = []
        
        for category, params in all_parameters.items():
            for param in params:
                if isinstance(param.current_value, (int, float)):
                    numeric_params.append(param)
                    # Get bounds
                    if param.constraints:
                        min_val = param.constraints.get('min_value', param.current_value * 0.5)
                        max_val = param.constraints.get('max_value', param.current_value * 1.5)
                    else:
                        min_val = param.current_value * 0.5
                        max_val = param.current_value * 1.5
                    param_bounds.append([min_val, max_val])
        
        if numeric_params:
            # Generate LHS samples
            sampler = qmc.LatinHypercube(d=len(numeric_params))
            samples = sampler.random(n=count)
            
            # Scale samples to bounds
            scaled_samples = qmc.scale(samples, 
                                     [b[0] for b in param_bounds],
                                     [b[1] for b in param_bounds])
            
            # Create scenarios
            for i, sample in enumerate(scaled_samples):
                scenario = ModificationScenario(
                    scenario_id=f"lhs_{i:03d}",
                    scenario_name=f"LHS Sample {i+1}",
                    description="Latin Hypercube Sample"
                )
                
                for param, value in zip(numeric_params, sample):
                    param_copy = ModificationParameter(
                        object_type=param.object_type,
                        object_name=param.object_name,
                        field_name=param.field_name,
                        field_index=param.field_index,
                        current_value=param.current_value,
                        new_value=value,
                        units=param.units
                    )
                    scenario.parameters.append(param_copy)
                    
                scenarios.append(scenario)
                
        return scenarios
