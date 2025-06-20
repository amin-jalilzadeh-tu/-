"""
Generate modification scenarios for IDF files.

This module creates various modification scenarios based on performance goals
and constraints.
"""
"""
Scenario Generator - Generate modification scenarios for IDF files
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import pandas as pd
from scipy.stats import qmc  # For Latin Hypercube Sampling
import random
import itertools

@dataclass
class Scenario:
    """Represents a single modification scenario"""
    id: str
    name: str
    description: str
    strategy: str
    modifications: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ParameterRange:
    """Defines parameter modification range"""
    parameter: str
    min_value: float
    max_value: float
    distribution: str = 'uniform'
    discrete_values: Optional[List[Any]] = None

class ScenarioGenerator:
    """Generate modification scenarios for parametric analysis"""
    
    # Predefined scenario templates
    SCENARIO_TEMPLATES = {
        'baseline': {
            'name': 'Baseline',
            'description': 'No modifications - reference case',
            'modifications': {}
        },
        'code_minimum': {
            'name': 'Code Minimum',
            'description': 'Meet minimum energy code requirements',
            'modifications': {
                'materials': {
                    'strategy': 'code_compliance',
                    'parameters': {
                        'thermal_resistance': {'method': 'absolute', 'value': 'code'},
                        'u_factor': {'method': 'absolute', 'value': 'code'}
                    }
                },
                'hvac': {
                    'strategy': 'code_compliance',
                    'parameters': {
                        'cop': {'method': 'absolute', 'value': 3.0},
                        'efficiency': {'method': 'absolute', 'value': 0.8}
                    }
                }
            }
        },
        'high_performance_envelope': {
            'name': 'High Performance Envelope',
            'description': 'Enhanced insulation and air tightness',
            'modifications': {
                'materials': {
                    'strategy': 'super_insulation',
                    'parameters': {
                        'conductivity': {'method': 'multiplier', 'factor': 0.5},
                        'thickness': {'method': 'multiplier', 'factor': 1.5}
                    }
                },
                'infiltration': {
                    'strategy': 'envelope_tightening',
                    'parameters': {
                        'flow_rate': {'method': 'multiplier', 'factor': 0.3}
                    }
                }
            }
        },
        'efficient_hvac': {
            'name': 'Efficient HVAC',
            'description': 'High efficiency HVAC equipment',
            'modifications': {
                'hvac': {
                    'strategy': 'efficiency_improvement',
                    'parameters': {
                        'cop': {'method': 'multiplier', 'range': [1.3, 1.5]},
                        'efficiency': {'method': 'multiplier', 'range': [1.2, 1.3]}
                    }
                }
            }
        },
        'reduced_loads': {
            'name': 'Reduced Internal Loads',
            'description': 'Efficient lighting and equipment',
            'modifications': {
                'lighting': {
                    'strategy': 'led_retrofit',
                    'parameters': {
                        'watts_per_area': {'method': 'multiplier', 'factor': 0.5}
                    }
                },
                'equipment': {
                    'strategy': 'energy_star',
                    'parameters': {
                        'watts_per_area': {'method': 'multiplier', 'factor': 0.7}
                    }
                }
            }
        },
        'passive_strategies': {
            'name': 'Passive Design Strategies',
            'description': 'Natural ventilation and daylighting',
            'modifications': {
                'ventilation': {
                    'strategy': 'natural_ventilation',
                    'parameters': {
                        'opening_area_fraction': {'method': 'multiplier', 'factor': 1.5}
                    }
                },
                'shading': {
                    'strategy': 'dynamic_shading',
                    'parameters': {
                        'shading_setpoint': {'method': 'multiplier', 'factor': 0.7}
                    }
                }
            }
        },
        'net_zero_ready': {
            'name': 'Net Zero Ready',
            'description': 'Comprehensive high performance building',
            'modifications': {
                'materials': {
                    'strategy': 'super_insulation',
                    'parameters': {
                        'conductivity': {'method': 'multiplier', 'factor': 0.3}
                    }
                },
                'infiltration': {
                    'strategy': 'envelope_tightening',
                    'parameters': {
                        'flow_rate': {'method': 'multiplier', 'factor': 0.2}
                    }
                },
                'hvac': {
                    'strategy': 'efficiency_improvement',
                    'parameters': {
                        'cop': {'method': 'multiplier', 'factor': 1.6}
                    }
                },
                'lighting': {
                    'strategy': 'led_retrofit',
                    'parameters': {
                        'watts_per_area': {'method': 'multiplier', 'factor': 0.3}
                    }
                },
                'equipment': {
                    'strategy': 'energy_star',
                    'parameters': {
                        'watts_per_area': {'method': 'multiplier', 'factor': 0.5}
                    }
                }
            }
        }
    }
    
    def __init__(self, parameter_registry: Optional[Dict[str, Any]] = None):
        """
        Initialize scenario generator
        
        Args:
            parameter_registry: Registry of modifiable parameters
        """
        self.parameter_registry = parameter_registry or {}
        self.random_state = None
    
    def set_random_seed(self, seed: int):
        """Set random seed for reproducibility"""
        self.random_state = seed
        random.seed(seed)
        np.random.seed(seed)
    
    def generate_predefined_scenarios(self, 
                                    scenario_names: Optional[List[str]] = None) -> List[Scenario]:
        """
        Generate scenarios from predefined templates
        
        Args:
            scenario_names: List of scenario names to generate, or None for all
            
        Returns:
            List of Scenario objects
        """
        if scenario_names is None:
            scenario_names = list(self.SCENARIO_TEMPLATES.keys())
        
        scenarios = []
        for i, name in enumerate(scenario_names):
            if name in self.SCENARIO_TEMPLATES:
                template = self.SCENARIO_TEMPLATES[name]
                scenario = Scenario(
                    id=f"scenario_{i:03d}",
                    name=template['name'],
                    description=template['description'],
                    strategy='predefined',
                    modifications=template['modifications'],
                    metadata={'template': name}
                )
                scenarios.append(scenario)
        
        return scenarios
    
    def generate_parametric_scenarios(self,
                                    parameters: Dict[str, List[ParameterRange]],
                                    num_scenarios: int,
                                    method: str = 'latin_hypercube') -> List[Scenario]:
        """
        Generate scenarios using parametric sampling
        
        Args:
            parameters: Dictionary of category -> parameter ranges
            num_scenarios: Number of scenarios to generate
            method: Sampling method ('uniform', 'latin_hypercube', 'sobol', 'factorial')
            
        Returns:
            List of Scenario objects
        """
        # Flatten parameters for sampling
        flat_params = []
        param_map = []
        
        for category, param_list in parameters.items():
            for param_range in param_list:
                flat_params.append(param_range)
                param_map.append((category, param_range.parameter))
        
        # Generate samples
        if method == 'uniform':
            samples = self._uniform_sampling(flat_params, num_scenarios)
        elif method == 'latin_hypercube':
            samples = self._latin_hypercube_sampling(flat_params, num_scenarios)
        elif method == 'sobol':
            samples = self._sobol_sampling(flat_params, num_scenarios)
        elif method == 'factorial':
            samples = self._factorial_sampling(flat_params, num_scenarios)
        else:
            raise ValueError(f"Unknown sampling method: {method}")
        
        # Create scenarios from samples
        scenarios = []
        for i, sample in enumerate(samples):
            modifications = {}
            
            for j, (category, param_name) in enumerate(param_map):
                if category not in modifications:
                    modifications[category] = {
                        'enabled': True,
                        'strategy': 'parametric_analysis',
                        'parameters': {}
                    }
                
                modifications[category]['parameters'][param_name] = {
                    'method': 'absolute',
                    'value': sample[j]
                }
            
            scenario = Scenario(
                id=f"sample_{i:03d}",
                name=f"Parametric Sample {i+1}",
                description=f"Generated using {method} sampling",
                strategy='parametric',
                modifications=modifications,
                metadata={
                    'sampling_method': method,
                    'sample_index': i,
                    'parameter_values': dict(zip([f"{cat}.{param}" for cat, param in param_map], sample))
                }
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def generate_optimization_scenarios(self,
                                      objectives: List[str],
                                      constraints: Optional[Dict[str, Any]] = None,
                                      num_scenarios: int = 10) -> List[Scenario]:
        """
        Generate scenarios for optimization objectives
        
        Args:
            objectives: List of optimization objectives ('energy', 'comfort', 'cost')
            constraints: Optional constraints on modifications
            num_scenarios: Number of scenarios to generate
            
        Returns:
            List of Scenario objects
        """
        scenarios = []
        
        # Define objective-based modifications
        objective_mods = {
            'energy': {
                'materials': {'strategy': 'super_insulation'},
                'hvac': {'strategy': 'efficiency_improvement'},
                'lighting': {'strategy': 'led_retrofit'},
                'equipment': {'strategy': 'energy_star'}
            },
            'comfort': {
                'hvac': {'strategy': 'setpoint_optimization'},
                'ventilation': {'strategy': 'natural_ventilation'},
                'shading': {'strategy': 'dynamic_shading'}
            },
            'cost': {
                'hvac': {'strategy': 'capacity_optimization'},
                'lighting': {'strategy': 'occupancy_controls'},
                'equipment': {'strategy': 'schedule_optimization'}
            },
            'resilience': {
                'materials': {'strategy': 'thermal_mass_increase'},
                'shading': {'strategy': 'fixed_shading_optimization'},
                'site_location': {'strategy': 'extreme_weather'}
            }
        }
        
        # Generate scenarios with different weights on objectives
        weights = self._generate_weights(len(objectives), num_scenarios)
        
        for i, weight_set in enumerate(weights):
            modifications = {}
            
            # Combine modifications based on weighted objectives
            for j, objective in enumerate(objectives):
                if objective in objective_mods and weight_set[j] > 0.1:
                    for category, strategy in objective_mods[objective].items():
                        if category not in modifications:
                            modifications[category] = {
                                'enabled': True,
                                'strategy': strategy['strategy'],
                                'parameters': self._get_strategy_parameters(
                                    category, 
                                    strategy['strategy'], 
                                    weight_set[j]
                                )
                            }
            
            scenario = Scenario(
                id=f"opt_{i:03d}",
                name=f"Optimization Scenario {i+1}",
                description=f"Optimizing for: {', '.join(objectives)}",
                strategy='optimization',
                modifications=modifications,
                metadata={
                    'objectives': objectives,
                    'weights': dict(zip(objectives, weight_set)),
                    'constraints': constraints
                }
            )
            scenarios.append(scenario)
        
        return scenarios
    
    def generate_sensitivity_scenarios(self,
                                     base_scenario: Scenario,
                                     parameters: List[Tuple[str, str]],
                                     variations: List[float] = [-20, -10, 0, 10, 20]) -> List[Scenario]:
        """
        Generate scenarios for sensitivity analysis
        
        Args:
            base_scenario: Base scenario to vary from
            parameters: List of (category, parameter) tuples to vary
            variations: Percentage variations to apply
            
        Returns:
            List of Scenario objects
        """
        scenarios = []
        scenario_idx = 0
        
        # One-at-a-time sensitivity analysis
        for category, param in parameters:
            for variation in variations:
                # Copy base modifications
                modifications = json.loads(json.dumps(base_scenario.modifications))
                
                # Apply variation
                if category not in modifications:
                    modifications[category] = {
                        'enabled': True,
                        'parameters': {}
                    }
                
                modifications[category]['parameters'][param] = {
                    'method': 'percentage',
                    'change': variation
                }
                
                scenario = Scenario(
                    id=f"sens_{scenario_idx:03d}",
                    name=f"Sensitivity: {category}.{param} {variation:+d}%",
                    description=f"Sensitivity analysis varying {param}",
                    strategy='sensitivity',
                    modifications=modifications,
                    metadata={
                        'base_scenario': base_scenario.id,
                        'varied_parameter': f"{category}.{param}",
                        'variation': variation
                    }
                )
                scenarios.append(scenario)
                scenario_idx += 1
        
        return scenarios
    
    def generate_retrofit_scenarios(self,
                                  building_age: str,
                                  climate_zone: str,
                                  budget_levels: List[str] = ['low', 'medium', 'high']) -> List[Scenario]:
        """
        Generate retrofit scenarios based on building characteristics
        
        Args:
            building_age: Age category ('pre-1980', '1980-2000', 'post-2000')
            climate_zone: ASHRAE climate zone
            budget_levels: List of budget levels to consider
            
        Returns:
            List of Scenario objects
        """
        scenarios = []
        
        # Define retrofit packages by age and budget
        retrofit_packages = {
            'pre-1980': {
                'low': {
                    'infiltration': {'strategy': 'weatherization'},
                    'lighting': {'strategy': 'occupancy_controls'}
                },
                'medium': {
                    'infiltration': {'strategy': 'envelope_tightening'},
                    'materials': {'strategy': 'roof_insulation'},
                    'lighting': {'strategy': 'led_retrofit'},
                    'hvac': {'strategy': 'setpoint_optimization'}
                },
                'high': {
                    'infiltration': {'strategy': 'envelope_tightening'},
                    'materials': {'strategy': 'super_insulation'},
                    'lighting': {'strategy': 'led_retrofit'},
                    'hvac': {'strategy': 'high_efficiency_replacement'},
                    'dhw': {'strategy': 'heat_pump_water_heater'}
                }
            },
            '1980-2000': {
                'low': {
                    'lighting': {'strategy': 'led_retrofit'},
                    'equipment': {'strategy': 'plug_load_reduction'}
                },
                'medium': {
                    'lighting': {'strategy': 'led_retrofit'},
                    'equipment': {'strategy': 'energy_star'},
                    'hvac': {'strategy': 'efficiency_improvement'},
                    'ventilation': {'strategy': 'demand_controlled_ventilation'}
                },
                'high': {
                    'materials': {'strategy': 'high_performance_windows'},
                    'lighting': {'strategy': 'led_retrofit'},
                    'equipment': {'strategy': 'energy_star'},
                    'hvac': {'strategy': 'high_efficiency_replacement'},
                    'ventilation': {'strategy': 'energy_recovery'}
                }
            },
            'post-2000': {
                'low': {
                    'schedules': {'strategy': 'occupancy_optimization'},
                    'hvac': {'strategy': 'setpoint_optimization'}
                },
                'medium': {
                    'lighting': {'strategy': 'daylight_dimming'},
                    'equipment': {'strategy': 'energy_star'},
                    'hvac': {'strategy': 'efficiency_improvement'},
                    'shading': {'strategy': 'dynamic_shading'}
                },
                'high': {
                    'materials': {'strategy': 'high_performance_windows'},
                    'hvac': {'strategy': 'efficiency_improvement'},
                    'ventilation': {'strategy': 'natural_ventilation'},
                    'dhw': {'strategy': 'heat_pump_water_heater'},
                    'shading': {'strategy': 'dynamic_shading'}
                }
            }
        }
        
        # Get appropriate retrofit package
        age_packages = retrofit_packages.get(building_age, retrofit_packages['1980-2000'])
        
        for i, budget in enumerate(budget_levels):
            if budget in age_packages:
                modifications = {}
                
                for category, strategy_info in age_packages[budget].items():
                    modifications[category] = {
                        'enabled': True,
                        'strategy': strategy_info['strategy'],
                        'parameters': self._get_default_parameters(category, strategy_info['strategy'])
                    }
                
                scenario = Scenario(
                    id=f"retrofit_{i:03d}",
                    name=f"{budget.title()} Budget Retrofit",
                    description=f"Retrofit package for {building_age} building with {budget} budget",
                    strategy='retrofit',
                    modifications=modifications,
                    metadata={
                        'building_age': building_age,
                        'climate_zone': climate_zone,
                        'budget_level': budget,
                        'estimated_savings': self._estimate_savings(modifications)
                    }
                )
                scenarios.append(scenario)
        
        return scenarios
    
    def _uniform_sampling(self, parameters: List[ParameterRange], n_samples: int) -> List[List[float]]:
        """Generate uniform random samples"""
        samples = []
        
        for _ in range(n_samples):
            sample = []
            for param in parameters:
                if param.discrete_values:
                    value = random.choice(param.discrete_values)
                else:
                    value = random.uniform(param.min_value, param.max_value)
                sample.append(value)
            samples.append(sample)
        
        return samples
    
    def _latin_hypercube_sampling(self, parameters: List[ParameterRange], n_samples: int) -> List[List[float]]:
        """Generate Latin Hypercube samples"""
        n_params = len(parameters)
        
        # Generate LHS samples in [0, 1]
        sampler = qmc.LatinHypercube(d=n_params, seed=self.random_state)
        unit_samples = sampler.random(n=n_samples)
        
        # Scale to parameter ranges
        samples = []
        for unit_sample in unit_samples:
            sample = []
            for i, param in enumerate(parameters):
                if param.discrete_values:
                    # Map to discrete values
                    idx = int(unit_sample[i] * len(param.discrete_values))
                    idx = min(idx, len(param.discrete_values) - 1)
                    value = param.discrete_values[idx]
                else:
                    # Scale to continuous range
                    value = param.min_value + unit_sample[i] * (param.max_value - param.min_value)
                sample.append(value)
            samples.append(sample)
        
        return samples
    
    def _sobol_sampling(self, parameters: List[ParameterRange], n_samples: int) -> List[List[float]]:
        """Generate Sobol sequence samples"""
        n_params = len(parameters)
        
        # Generate Sobol samples in [0, 1]
        sampler = qmc.Sobol(d=n_params, seed=self.random_state)
        unit_samples = sampler.random(n=n_samples)
        
        # Scale to parameter ranges (same as LHS)
        samples = []
        for unit_sample in unit_samples:
            sample = []
            for i, param in enumerate(parameters):
                if param.discrete_values:
                    idx = int(unit_sample[i] * len(param.discrete_values))
                    idx = min(idx, len(param.discrete_values) - 1)
                    value = param.discrete_values[idx]
                else:
                    value = param.min_value + unit_sample[i] * (param.max_value - param.min_value)
                sample.append(value)
            samples.append(sample)
        
        return samples
    
    def _factorial_sampling(self, parameters: List[ParameterRange], n_samples: int) -> List[List[float]]:
        """Generate factorial design samples"""
        # For each parameter, use 3 levels (min, mid, max)
        levels = []
        for param in parameters:
            if param.discrete_values:
                if len(param.discrete_values) <= 3:
                    levels.append(param.discrete_values)
                else:
                    # Take first, middle, last
                    n = len(param.discrete_values)
                    levels.append([param.discrete_values[0], 
                                 param.discrete_values[n//2], 
                                 param.discrete_values[-1]])
            else:
                mid = (param.min_value + param.max_value) / 2
                levels.append([param.min_value, mid, param.max_value])
        
        # Generate full factorial
        all_combinations = list(itertools.product(*levels))
        
        # If too many combinations, sample randomly
        if len(all_combinations) > n_samples:
            samples = random.sample(all_combinations, n_samples)
        else:
            samples = all_combinations
            # Repeat to reach n_samples
            while len(samples) < n_samples:
                samples.extend(all_combinations[:n_samples - len(samples)])
        
        return [list(s) for s in samples]
    
    def _generate_weights(self, n_objectives: int, n_samples: int) -> List[List[float]]:
        """Generate weight combinations for multi-objective optimization"""
        if n_objectives == 1:
            return [[1.0]] * n_samples
        
        # Use Dirichlet distribution to generate weights that sum to 1
        weights = np.random.dirichlet(np.ones(n_objectives), n_samples)
        return weights.tolist()
    
    def _get_strategy_parameters(self, category: str, strategy: str, weight: float) -> Dict[str, Any]:
        """Get parameters for a specific strategy with given weight"""
        # Define strategy-specific parameters
        # Weight affects the aggressiveness of the modification
        
        base_params = {
            'super_insulation': {
                'conductivity': {'method': 'multiplier', 'factor': 0.3 + 0.4 * (1 - weight)},
                'thickness': {'method': 'multiplier', 'factor': 1.2 + 0.3 * weight}
            },
            'efficiency_improvement': {
                'cop': {'method': 'multiplier', 'factor': 1.1 + 0.4 * weight},
                'efficiency': {'method': 'multiplier', 'factor': 1.1 + 0.2 * weight}
            },
            'led_retrofit': {
                'watts_per_area': {'method': 'multiplier', 'factor': 0.7 - 0.4 * weight}
            }
        }
        
        return base_params.get(strategy, {})
    
    def _get_default_parameters(self, category: str, strategy: str) -> Dict[str, Any]:
        """Get default parameters for a strategy"""
        defaults = {
            'envelope_tightening': {
                'flow_rate': {'method': 'multiplier', 'factor': 0.5}
            },
            'super_insulation': {
                'conductivity': {'method': 'multiplier', 'factor': 0.5}
            },
            'led_retrofit': {
                'watts_per_area': {'method': 'multiplier', 'factor': 0.5}
            },
            'efficiency_improvement': {
                'cop': {'method': 'multiplier', 'factor': 1.3}
            }
        }
        
        return defaults.get(strategy, {})
    
    def _estimate_savings(self, modifications: Dict[str, Any]) -> Dict[str, float]:
        """Estimate energy savings from modifications"""
        # Simplified estimation - would be more complex in practice
        savings = {
            'heating': 0,
            'cooling': 0,
            'lighting': 0,
            'equipment': 0,
            'total': 0
        }
        
        # Estimate based on modification categories
        if 'materials' in modifications:
            savings['heating'] += 15
            savings['cooling'] += 10
            
        if 'infiltration' in modifications:
            savings['heating'] += 10
            savings['cooling'] += 5
            
        if 'hvac' in modifications:
            savings['heating'] += 20
            savings['cooling'] += 20
            
        if 'lighting' in modifications:
            savings['lighting'] += 40
            
        if 'equipment' in modifications:
            savings['equipment'] += 20
        
        savings['total'] = sum(v for k, v in savings.items() if k != 'total') / 4
        
        return savings
    
    def save_scenarios(self, scenarios: List[Scenario], output_path: Union[str, Path]):
        """Save scenarios to JSON file"""
        output_path = Path(output_path)
        
        scenarios_data = []
        for scenario in scenarios:
            scenarios_data.append({
                'id': scenario.id,
                'name': scenario.name,
                'description': scenario.description,
                'strategy': scenario.strategy,
                'modifications': scenario.modifications,
                'metadata': scenario.metadata
            })
        
        with open(output_path, 'w') as f:
            json.dump(scenarios_data, f, indent=2)
    
    def load_scenarios(self, input_path: Union[str, Path]) -> List[Scenario]:
        """Load scenarios from JSON file"""
        input_path = Path(input_path)
        
        with open(input_path) as f:
            scenarios_data = json.load(f)
        
        scenarios = []
        for data in scenarios_data:
            scenario = Scenario(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                strategy=data['strategy'],
                modifications=data['modifications'],
                metadata=data.get('metadata', {})
            )
            scenarios.append(scenario)
        
        return scenarios