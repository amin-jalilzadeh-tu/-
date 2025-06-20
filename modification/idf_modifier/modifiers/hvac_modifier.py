"""
HVAC Modifier Module - Handle HVAC system modifications
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import logging

from ..base_modifier import BaseModifier, ModificationParameter


class HVACModifier(BaseModifier):
    """Modifier for HVAC-related parameters"""
    
    def __init__(self, category: str = 'hvac', parsed_data_path=None):
        super().__init__(category, parsed_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Define HVAC object types
        self.hvac_objects = {
            'cooling_coils': [
                'COIL:COOLING:DX:SINGLESPEED',
                'COIL:COOLING:DX:TWOSPEED',
                'COIL:COOLING:DX:VARIABLESPEED',
                'COIL:COOLING:WATER',
                'COILSYSTEM:COOLING:DX'
            ],
            'heating_coils': [
                'COIL:HEATING:ELECTRIC',
                'COIL:HEATING:FUEL',
                'COIL:HEATING:GAS',
                'COIL:HEATING:WATER',
                'COIL:HEATING:STEAM'
            ],
            'fans': [
                'FAN:CONSTANTVOLUME',
                'FAN:VARIABLEVOLUME',
                'FAN:ONOFF',
                'FAN:SYSTEMMODEL'
            ],
            'pumps': [
                'PUMP:CONSTANTSPEED',
                'PUMP:VARIABLESPEED',
                'HEADEREDPUMPS:CONSTANTSPEED',
                'HEADEREDPUMPS:VARIABLESPEED'
            ],
            'chillers': [
                'CHILLER:ELECTRIC:EIR',
                'CHILLER:ELECTRIC:REFORMULATEDEIR',
                'CHILLER:ABSORPTION',
                'CHILLER:ABSORPTIONINDIRECT'
            ],
            'boilers': [
                'BOILER:HOTWATER',
                'BOILER:STEAM'
            ],
            'ideal_loads': [
                'ZONEHVAC:IDEALLOADSAIRSYSTEM'
            ]
        }
        
        # Parameter definitions for each object type
        self.parameter_map = self._build_parameter_map()
        
    def _build_parameter_map(self) -> Dict[str, Dict[str, Any]]:
        """Build comprehensive parameter mapping"""
        return {
            'COIL:COOLING:DX:SINGLESPEED': {
                'cop': {
                    'field_name': 'Gross Rated COP',
                    'field_index': 8,
                    'typical_range': [2.5, 5.0],
                    'improvement_potential': 1.5
                },
                'capacity': {
                    'field_name': 'Gross Rated Total Cooling Capacity',
                    'field_index': 4,
                    'typical_range': [1000, 100000],
                    'units': 'W'
                },
                'airflow': {
                    'field_name': 'Rated Air Flow Rate',
                    'field_index': 5,
                    'typical_range': [0.001, 10],
                    'units': 'm3/s'
                }
            },
            'COIL:HEATING:ELECTRIC': {
                'efficiency': {
                    'field_name': 'Efficiency',
                    'field_index': 2,
                    'typical_range': [0.8, 1.0],
                    'improvement_potential': 1.0
                },
                'capacity': {
                    'field_name': 'Nominal Capacity',
                    'field_index': 3,
                    'typical_range': [1000, 100000],
                    'units': 'W'
                }
            },
            'FAN:VARIABLEVOLUME': {
                'efficiency': {
                    'field_name': 'Fan Total Efficiency',
                    'field_index': 6,
                    'typical_range': [0.5, 0.9],
                    'improvement_potential': 1.3
                },
                'pressure': {
                    'field_name': 'Pressure Rise',
                    'field_index': 4,
                    'typical_range': [100, 1500],
                    'units': 'Pa'
                },
                'flow_rate': {
                    'field_name': 'Maximum Flow Rate',
                    'field_index': 5,
                    'typical_range': [0.01, 50],
                    'units': 'm3/s'
                }
            },
            'PUMP:VARIABLESPEED': {
                'head': {
                    'field_name': 'Rated Pump Head',
                    'field_index': 6,
                    'typical_range': [10000, 300000],
                    'units': 'Pa'
                },
                'power': {
                    'field_name': 'Rated Power Consumption',
                    'field_index': 7,
                    'typical_range': [50, 50000],
                    'units': 'W'
                },
                'efficiency': {
                    'field_name': 'Motor Efficiency',
                    'field_index': 8,
                    'typical_range': [0.7, 0.95],
                    'improvement_potential': 1.2
                }
            },
            'ZONEHVAC:IDEALLOADSAIRSYSTEM': {
                'max_heating_capacity': {
                    'field_name': 'Maximum Sensible Heating Capacity',
                    'field_index': 11,
                    'typical_range': [1000, 100000],
                    'units': 'W'
                },
                'max_cooling_capacity': {
                    'field_name': 'Maximum Total Cooling Capacity',
                    'field_index': 14,
                    'typical_range': [1000, 100000],
                    'units': 'W'
                },
                'heat_recovery': {
                    'field_name': 'Sensible Heat Recovery Effectiveness',
                    'field_index': 25,
                    'typical_range': [0.0, 0.9],
                    'improvement_potential': 'absolute'
                }
            }
        }
    
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """Identify all HVAC parameters in the IDF"""
        parameters = []
        
        # Load parsed data if available
        parsed_data = self.load_parsed_data(building_id) if self.parsed_data_path else None
        
        # Iterate through all HVAC object types
        for category, object_types in self.hvac_objects.items():
            for obj_type in object_types:
                if obj_type in idf.idfobjects:
                    objects = idf.idfobjects[obj_type]
                    
                    for obj in objects:
                        # Get parameters for this object type
                        if obj_type in self.parameter_map:
                            param_defs = self.parameter_map[obj_type]
                            
                            for param_key, param_def in param_defs.items():
                                try:
                                    # Get current value
                                    field_index = param_def['field_index']
                                    current_value = obj.obj[field_index]
                                    
                                    if current_value and current_value != 'autosize':
                                        # Create parameter
                                        param = ModificationParameter(
                                            object_type=obj_type,
                                            object_name=obj.Name if hasattr(obj, 'Name') else f"{obj_type}_{id(obj)}",
                                            field_name=param_def['field_name'],
                                            field_index=field_index,
                                            current_value=float(current_value),
                                            units=param_def.get('units', ''),
                                            constraints={
                                                'min_value': param_def['typical_range'][0],
                                                'max_value': param_def['typical_range'][1]
                                            }
                                        )
                                        
                                        parameters.append(param)
                                        
                                except Exception as e:
                                    self.logger.debug(f"Could not extract {param_key} from {obj_type}: {e}")
        
        self.logger.info(f"Identified {len(parameters)} HVAC parameters")
        return parameters
    
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate modification values for HVAC parameters"""
        modifications = []
        
        if strategy == 'performance':
            modifications = self._generate_performance_modifications(parameters, options)
        elif strategy == 'efficiency_improvement':
            modifications = self._generate_efficiency_modifications(parameters, options)
        elif strategy == 'capacity_adjustment':
            modifications = self._generate_capacity_modifications(parameters, options)
        elif strategy == 'random':
            modifications = self._generate_random_modifications(parameters, options)
        else:
            # Default strategy
            modifications = self._generate_default_modifications(parameters, options)
            
        return modifications
    
    def _generate_performance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance-based modifications"""
        modification_set = {}
        
        # Get multipliers from options
        efficiency_mult = options.get('efficiency', 1.1)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type, 
                                              param.object_name, 
                                              param.field_name)
            
            # Apply different strategies based on parameter type
            if 'cop' in param.field_name.lower():
                # Improve COP
                new_value = self.apply_multiplier(param.current_value, 
                                                efficiency_mult,
                                                min_val=param.constraints.get('min_value'),
                                                max_val=param.constraints.get('max_value'))
                modification_set[param_id] = new_value
                
            elif 'efficiency' in param.field_name.lower():
                # Improve efficiency
                new_value = self.apply_multiplier(param.current_value,
                                                efficiency_mult,
                                                min_val=param.constraints.get('min_value'),
                                                max_val=1.0)  # Cap at 100% efficiency
                modification_set[param_id] = new_value
                
            elif 'heat recovery' in param.field_name.lower():
                # Add heat recovery if not present
                if param.current_value == 0:
                    modification_set[param_id] = 0.7  # 70% heat recovery
                else:
                    # Improve existing heat recovery
                    new_value = min(param.current_value * 1.2, 0.9)
                    modification_set[param_id] = new_value
                    
        return [modification_set]
    
    def _generate_efficiency_modifications(self,
                                         parameters: List[ModificationParameter],
                                         options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate efficiency-focused modifications"""
        modification_set = {}
        
        # Target efficiency levels
        target_cop = options.get('target_cop', 4.0)
        target_fan_efficiency = options.get('target_fan_efficiency', 0.8)
        target_pump_efficiency = options.get('target_pump_efficiency', 0.85)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if 'cop' in param.field_name.lower():
                # Move towards target COP
                if param.current_value < target_cop:
                    new_value = min(target_cop, param.current_value * 1.3)
                    modification_set[param_id] = new_value
                    
            elif 'fan' in param.object_type.lower() and 'efficiency' in param.field_name.lower():
                # Improve fan efficiency
                if param.current_value < target_fan_efficiency:
                    new_value = min(target_fan_efficiency, param.current_value * 1.2)
                    modification_set[param_id] = new_value
                    
            elif 'pump' in param.object_type.lower() and 'efficiency' in param.field_name.lower():
                # Improve pump efficiency
                if param.current_value < target_pump_efficiency:
                    new_value = min(target_pump_efficiency, param.current_value * 1.15)
                    modification_set[param_id] = new_value
                    
        return [modification_set]
    
    def _generate_capacity_modifications(self,
                                       parameters: List[ModificationParameter],
                                       options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate capacity adjustment modifications"""
        modification_set = {}
        
        # Capacity multiplier
        capacity_mult = options.get('capacity_multiplier', 1.0)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if 'capacity' in param.field_name.lower():
                # Adjust capacity
                new_value = param.current_value * capacity_mult
                modification_set[param_id] = new_value
                
            elif 'flow' in param.field_name.lower() and 'rate' in param.field_name.lower():
                # Adjust flow rates proportionally
                new_value = param.current_value * capacity_mult
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_random_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate random modifications within bounds"""
        modification_set = {}
        
        seed = options.get('seed', None)
        if seed:
            np.random.seed(seed)
            
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            # Random within ±30% of current value
            multiplier = np.random.uniform(0.7, 1.3)
            new_value = self.apply_multiplier(param.current_value,
                                            multiplier,
                                            min_val=param.constraints.get('min_value'),
                                            max_val=param.constraints.get('max_value'))
            modification_set[param_id] = new_value
            
        return [modification_set]
    
    def _generate_default_modifications(self,
                                      parameters: List[ModificationParameter],
                                      options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default modification strategy"""
        modification_set = {}
        
        # Simple 10% improvement for efficiency parameters
        for param in parameters:
            if 'efficiency' in param.field_name.lower() or 'cop' in param.field_name.lower():
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                new_value = self.apply_multiplier(param.current_value, 1.1,
                                                min_val=param.constraints.get('min_value'),
                                                max_val=param.constraints.get('max_value'))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def apply_modifications(self, idf: IDF, modifications: Dict[str, Any]) -> bool:
        """Apply HVAC modifications to IDF"""
        success = True
        applied_count = 0
        
        for param_id, new_value in modifications.items():
            try:
                # Parse parameter ID
                obj_type, obj_name, field_name = self.parse_parameter_id(param_id)
                
                # Find object in IDF
                if obj_type in idf.idfobjects:
                    objects = idf.idfobjects[obj_type]
                    
                    for obj in objects:
                        # Match by name or check all if name not available
                        if (hasattr(obj, 'Name') and obj.Name == obj_name) or \
                           (not hasattr(obj, 'Name') and f"{obj_type}_{id(obj)}" == obj_name):
                            
                            # Find field index
                            if obj_type in self.parameter_map:
                                for param_key, param_def in self.parameter_map[obj_type].items():
                                    if param_def['field_name'] == field_name:
                                        field_index = param_def['field_index']
                                        
                                        # Apply modification
                                        old_value = obj.obj[field_index]
                                        obj.obj[field_index] = new_value
                                        
                                        self.logger.debug(f"Modified {obj_type} {obj_name} "
                                                        f"{field_name}: {old_value} → {new_value}")
                                        applied_count += 1
                                        break
                            break
                            
            except Exception as e:
                self.logger.error(f"Error applying modification {param_id}: {e}")
                success = False
                
        self.logger.info(f"Applied {applied_count} HVAC modifications")
        return success
    
    def validate_hvac_system(self, idf: IDF) -> Tuple[bool, List[str]]:
        """Validate HVAC system after modifications"""
        errors = []
        
        # Check cooling coil COPs are reasonable
        for obj_type in self.hvac_objects['cooling_coils']:
            if obj_type in idf.idfobjects:
                for obj in idf.idfobjects[obj_type]:
                    if hasattr(obj, 'Gross_Rated_COP'):
                        cop = float(obj.Gross_Rated_COP) if obj.Gross_Rated_COP else 0
                        if cop < 2.0:
                            errors.append(f"{obj.Name}: COP too low ({cop})")
                        elif cop > 7.0:
                            errors.append(f"{obj.Name}: COP unrealistically high ({cop})")
        
        # Check fan efficiencies
        for obj_type in self.hvac_objects['fans']:
            if obj_type in idf.idfobjects:
                for obj in idf.idfobjects[obj_type]:
                    if hasattr(obj, 'Fan_Total_Efficiency'):
                        eff = float(obj.Fan_Total_Efficiency) if obj.Fan_Total_Efficiency else 0
                        if eff < 0.3:
                            errors.append(f"{obj.Name}: Fan efficiency too low ({eff})")
                        elif eff > 0.95:
                            errors.append(f"{obj.Name}: Fan efficiency too high ({eff})")
        
        return len(errors) == 0, errors
