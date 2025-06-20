"""
Infiltration Modifier Module - Handle infiltration and ventilation modifications
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import logging

from ..base_modifier import BaseModifier, ModificationParameter


class InfiltrationModifier(BaseModifier):
    """Modifier for infiltration and ventilation parameters"""
    
    def __init__(self, category: str = 'infiltration', parsed_data_path=None):
        super().__init__(category, parsed_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Define infiltration/ventilation object types
        self.infiltration_objects = {
            'infiltration': [
                'ZONEINFILTRATION:DESIGNFLOWRATE',
                'ZONEINFILTRATION:EFFECTIVELEAKAGEAREA',
                'ZONEINFILTRATION:FLOWCOEFFICIENT'
            ],
            'ventilation': [
                'ZONEVENTILATION:DESIGNFLOWRATE',
                'ZONEVENTILATION:WINDANDSTACKDRIVENFLOW',
                'DESIGNSPECIFICATION:OUTDOORAIR'
            ],
            'mixing': [
                'ZONEMIXING',
                'ZONECROSSMIXING'
            ]
        }
        
        # Typical infiltration rates by building type
        self.typical_rates = {
            'tight': {
                'ach': 0.1,  # Air changes per hour
                'flow_per_area': 0.00025,  # m³/s-m²
                'description': 'Very tight construction (Passive House level)'
            },
            'good': {
                'ach': 0.3,
                'flow_per_area': 0.00075,
                'description': 'Good modern construction'
            },
            'average': {
                'ach': 0.5,
                'flow_per_area': 0.00125,
                'description': 'Average construction'
            },
            'poor': {
                'ach': 1.0,
                'flow_per_area': 0.0025,
                'description': 'Poor or old construction'
            }
        }
        
        # Parameter definitions
        self.parameter_map = self._build_parameter_map()
        
    def _build_parameter_map(self) -> Dict[str, Dict[str, Any]]:
        """Build parameter mapping for infiltration objects"""
        return {
            'ZONEINFILTRATION:DESIGNFLOWRATE': {
                'design_flow_rate': {
                    'field_name': 'Design Flow Rate',
                    'field_index': 4,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'm³/s',
                    'typical_range': [0.0001, 0.1]
                },
                'flow_per_area': {
                    'field_name': 'Flow Rate per Floor Area',
                    'field_index': 5,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'm³/s-m²',
                    'typical_range': [0.0001, 0.005]
                },
                'flow_per_exterior_area': {
                    'field_name': 'Flow Rate per Exterior Surface Area',
                    'field_index': 6,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'm³/s-m²',
                    'typical_range': [0.00001, 0.001]
                },
                'air_changes': {
                    'field_name': 'Air Changes per Hour',
                    'field_index': 7,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'ACH',
                    'typical_range': [0.05, 2.0]
                },
                'constant_coefficient': {
                    'field_name': 'Constant Term Coefficient',
                    'field_index': 8,
                    'units': 'dimensionless',
                    'typical_range': [0.0, 1.0]
                },
                'temperature_coefficient': {
                    'field_name': 'Temperature Term Coefficient',
                    'field_index': 9,
                    'units': 'dimensionless',
                    'typical_range': [0.0, 0.04]
                },
                'velocity_coefficient': {
                    'field_name': 'Velocity Term Coefficient',
                    'field_index': 10,
                    'units': 'dimensionless',
                    'typical_range': [0.0, 0.3]
                },
                'velocity_squared_coefficient': {
                    'field_name': 'Velocity Squared Term Coefficient',
                    'field_index': 11,
                    'units': 'dimensionless',
                    'typical_range': [0.0, 0.3]
                }
            },
            'ZONEVENTILATION:DESIGNFLOWRATE': {
                'design_flow_rate': {
                    'field_name': 'Design Flow Rate',
                    'field_index': 4,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'm³/s',
                    'typical_range': [0.001, 1.0]
                },
                'flow_rate_per_area': {
                    'field_name': 'Flow Rate per Zone Floor Area',
                    'field_index': 5,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'm³/s-m²',
                    'typical_range': [0.0001, 0.01]
                },
                'flow_rate_per_person': {
                    'field_name': 'Flow Rate per Person',
                    'field_index': 6,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'm³/s-person',
                    'typical_range': [0.001, 0.02]
                },
                'air_changes': {
                    'field_name': 'Air Changes per Hour',
                    'field_index': 7,
                    'calc_method_field': 'Design Flow Rate Calculation Method',
                    'calc_method_index': 3,
                    'units': 'ACH',
                    'typical_range': [0.5, 10.0]
                },
                'fan_pressure_rise': {
                    'field_name': 'Fan Pressure Rise',
                    'field_index': 9,
                    'units': 'Pa',
                    'typical_range': [0.0, 300.0]
                },
                'fan_efficiency': {
                    'field_name': 'Fan Total Efficiency',
                    'field_index': 10,
                    'units': 'fraction',
                    'typical_range': [0.5, 0.9]
                }
            },
            'DESIGNSPECIFICATION:OUTDOORAIR': {
                'outdoor_air_per_person': {
                    'field_name': 'Outdoor Air Flow per Person',
                    'field_index': 2,
                    'units': 'm³/s-person',
                    'typical_range': [0.0, 0.02]
                },
                'outdoor_air_per_area': {
                    'field_name': 'Outdoor Air Flow per Zone Floor Area',
                    'field_index': 3,
                    'units': 'm³/s-m²',
                    'typical_range': [0.0, 0.003]
                },
                'outdoor_air_per_zone': {
                    'field_name': 'Outdoor Air Flow per Zone',
                    'field_index': 4,
                    'units': 'm³/s',
                    'typical_range': [0.0, 1.0]
                },
                'outdoor_air_ach': {
                    'field_name': 'Outdoor Air Flow Air Changes per Hour',
                    'field_index': 5,
                    'units': 'ACH',
                    'typical_range': [0.0, 10.0]
                }
            }
        }
    
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """Identify all infiltration/ventilation parameters in the IDF"""
        parameters = []
        
        # Process infiltration objects
        for inf_type in self.infiltration_objects['infiltration']:
            if inf_type in idf.idfobjects:
                for inf_obj in idf.idfobjects[inf_type]:
                    # Skip if schedule is OFF
                    if hasattr(inf_obj, 'Schedule_Name') and inf_obj.Schedule_Name == 'OFF':
                        continue
                    
                    if inf_type in self.parameter_map:
                        # Get calculation method for flow rate objects
                        if inf_type == 'ZONEINFILTRATION:DESIGNFLOWRATE':
                            calc_method = inf_obj.obj[3] if len(inf_obj.obj) > 3 else None
                            
                            # Extract appropriate parameter based on calc method
                            if calc_method == 'Flow/Zone':
                                param_def = self.parameter_map[inf_type]['design_flow_rate']
                            elif calc_method == 'Flow/Area':
                                param_def = self.parameter_map[inf_type]['flow_per_area']
                            elif calc_method == 'Flow/ExteriorArea':
                                param_def = self.parameter_map[inf_type]['flow_per_exterior_area']
                            elif calc_method == 'AirChanges/Hour':
                                param_def = self.parameter_map[inf_type]['air_changes']
                            else:
                                continue
                            
                            # Extract value
                            field_index = param_def['field_index']
                            if len(inf_obj.obj) > field_index:
                                current_value = inf_obj.obj[field_index]
                                
                                # Special handling for Flow/Area in wrong field (from your paste.txt)
                                if calc_method == 'Flow/Area' and field_index == 5 and not current_value:
                                    # Check if value is in Design Flow Rate field
                                    if len(inf_obj.obj) > 4 and inf_obj.obj[4]:
                                        current_value = inf_obj.obj[4]
                                        field_index = 4
                                
                                if current_value and current_value != '' and float(current_value) > 0:
                                    param = ModificationParameter(
                                        object_type=inf_type,
                                        object_name=inf_obj.Name,
                                        field_name=param_def['field_name'],
                                        field_index=field_index,
                                        current_value=float(current_value),
                                        units=param_def['units'],
                                        constraints={
                                            'min_value': param_def['typical_range'][0],
                                            'max_value': param_def['typical_range'][1],
                                            'calc_method': calc_method
                                        }
                                    )
                                    parameters.append(param)
                        
                        # Always extract coefficients if present
                        for coef_type in ['constant_coefficient', 'temperature_coefficient', 
                                        'velocity_coefficient', 'velocity_squared_coefficient']:
                            if coef_type in self.parameter_map[inf_type]:
                                param_def = self.parameter_map[inf_type][coef_type]
                                field_index = param_def['field_index']
                                if len(inf_obj.obj) > field_index:
                                    current_value = inf_obj.obj[field_index]
                                    if current_value and current_value != '':
                                        param = ModificationParameter(
                                            object_type=inf_type,
                                            object_name=inf_obj.Name,
                                            field_name=param_def['field_name'],
                                            field_index=field_index,
                                            current_value=float(current_value),
                                            units=param_def['units'],
                                            constraints={
                                                'min_value': param_def['typical_range'][0],
                                                'max_value': param_def['typical_range'][1]
                                            }
                                        )
                                        parameters.append(param)
        
        # Process ventilation objects
        for vent_type in self.infiltration_objects['ventilation']:
            if vent_type in idf.idfobjects:
                for vent_obj in idf.idfobjects[vent_type]:
                    if vent_type in self.parameter_map:
                        param_defs = self.parameter_map[vent_type]
                        
                        for param_key, param_def in param_defs.items():
                            field_index = param_def['field_index']
                            if len(vent_obj.obj) > field_index:
                                current_value = vent_obj.obj[field_index]
                                
                                if current_value and current_value != '' and current_value != 'autosize':
                                    try:
                                        param = ModificationParameter(
                                            object_type=vent_type,
                                            object_name=vent_obj.Name if hasattr(vent_obj, 'Name') else f"{vent_type}_{id(vent_obj)}",
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
                                    except ValueError:
                                        pass
        
        self.logger.info(f"Identified {len(parameters)} infiltration/ventilation parameters")
        return parameters
    
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate modification values for infiltration parameters"""
        if strategy == 'performance':
            return self._generate_performance_modifications(parameters, options)
        elif strategy == 'air_sealing':
            return self._generate_air_sealing_modifications(parameters, options)
        elif strategy == 'ventilation_optimization':
            return self._generate_ventilation_modifications(parameters, options)
        elif strategy == 'passive_house':
            return self._generate_passive_house_modifications(parameters, options)
        elif strategy == 'random':
            return self._generate_random_modifications(parameters, options)
        else:
            return self._generate_default_modifications(parameters, options)
    
    def _generate_performance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance-based infiltration modifications"""
        modification_set = {}
        
        # Get rate multiplier
        rate_mult = options.get('rate', 0.6)  # 40% reduction default
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            # Reduce infiltration rates
            if any(keyword in param.field_name.lower() for keyword in 
                   ['flow rate', 'air changes', 'flow per']):
                new_value = self.apply_multiplier(param.current_value,
                                                rate_mult,
                                                min_val=param.constraints['min_value'])
                modification_set[param_id] = new_value
                
            # Adjust coefficients
            elif 'coefficient' in param.field_name.lower():
                # Reduce coefficients proportionally
                new_value = self.apply_multiplier(param.current_value,
                                                rate_mult,
                                                min_val=0.0)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_air_sealing_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate air sealing modifications"""
        modification_set = {}
        
        # Target performance level
        target_level = options.get('target_level', 'good')
        target_rates = self.typical_rates.get(target_level, self.typical_rates['good'])
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Air Changes per Hour':
                # Set to target ACH
                if param.current_value > target_rates['ach']:
                    modification_set[param_id] = target_rates['ach']
                    
            elif param.field_name == 'Flow Rate per Floor Area':
                # Set to target flow per area
                if param.current_value > target_rates['flow_per_area']:
                    modification_set[param_id] = target_rates['flow_per_area']
                    
            elif 'coefficient' in param.field_name.lower():
                # Reduce all coefficients for tighter building
                reduction = 0.5 if target_level == 'tight' else 0.7
                new_value = param.current_value * reduction
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_ventilation_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ventilation optimization modifications"""
        modification_set = {}
        
        # Ventilation strategy
        demand_control = options.get('demand_control_ventilation', True)
        heat_recovery = options.get('heat_recovery', True)
        
        for param in parameters:
            if param.object_type.startswith('ZONEVENTILATION'):
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                if demand_control and 'flow' in param.field_name.lower():
                    # Reduce base ventilation rate (assuming DCV will modulate)
                    new_value = param.current_value * 0.7
                    modification_set[param_id] = new_value
                    
                elif param.field_name == 'Fan Total Efficiency':
                    # Improve fan efficiency
                    new_value = min(param.current_value * 1.2, 0.85)
                    modification_set[param_id] = new_value
                    
                elif param.field_name == 'Fan Pressure Rise':
                    # Reduce pressure rise if heat recovery added
                    if heat_recovery:
                        new_value = param.current_value * 1.2  # Account for HRV pressure drop
                        modification_set[param_id] = new_value
                        
        return [modification_set]
    
    def _generate_passive_house_modifications(self,
                                            parameters: List[ModificationParameter],
                                            options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Passive House level modifications"""
        modification_set = {}
        
        # Passive House infiltration target: 0.6 ACH @ 50 Pa
        # Approximate to ~0.1 ACH under normal conditions
        target_ach = 0.1
        target_flow_area = 0.00025  # m³/s-m²
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.object_type.startswith('ZONEINFILTRATION'):
                if param.field_name == 'Air Changes per Hour':
                    modification_set[param_id] = target_ach
                    
                elif param.field_name == 'Flow Rate per Floor Area':
                    modification_set[param_id] = target_flow_area
                    
                elif param.field_name == 'Design Flow Rate':
                    # Reduce by 80%
                    new_value = param.current_value * 0.2
                    modification_set[param_id] = new_value
                    
                elif 'coefficient' in param.field_name.lower():
                    # Very low coefficients for tight building
                    if 'constant' in param.field_name.lower():
                        modification_set[param_id] = 0.05
                    else:
                        modification_set[param_id] = 0.01
                        
        return [modification_set]
    
    def _generate_random_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate random infiltration modifications"""
        modification_set = {}
        
        seed = options.get('seed', None)
        if seed:
            np.random.seed(seed)
            
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            # Random reduction between 20-60%
            if any(keyword in param.field_name.lower() for keyword in 
                   ['flow', 'air changes', 'coefficient']):
                multiplier = np.random.uniform(0.4, 0.8)
                new_value = self.apply_multiplier(param.current_value,
                                                multiplier,
                                                min_val=param.constraints.get('min_value', 0))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_default_modifications(self,
                                      parameters: List[ModificationParameter],
                                      options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default infiltration modifications - 30% reduction"""
        modification_set = {}
        
        for param in parameters:
            if any(keyword in param.field_name.lower() for keyword in 
                   ['flow', 'air changes', 'coefficient']):
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                new_value = self.apply_multiplier(param.current_value, 0.7,
                                                min_val=param.constraints.get('min_value', 0))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def apply_modifications(self, idf: IDF, modifications: Dict[str, Any]) -> bool:
        """Apply infiltration modifications to IDF"""
        success = True
        applied_count = 0
        
        for param_id, new_value in modifications.items():
            try:
                # Parse parameter ID
                obj_type, obj_name, field_name = self.parse_parameter_id(param_id)
                
                # Find and modify object
                if obj_type in idf.idfobjects:
                    for obj in idf.idfobjects[obj_type]:
                        if hasattr(obj, 'Name') and obj.Name == obj_name:
                            # Find field index
                            if obj_type in self.parameter_map:
                                # Special handling for flow rate calculation methods
                                if obj_type == 'ZONEINFILTRATION:DESIGNFLOWRATE':
                                    calc_method = obj.Design_Flow_Rate_Calculation_Method
                                    
                                    # Find the right parameter definition
                                    param_def = None
                                    for key, pdef in self.parameter_map[obj_type].items():
                                        if pdef['field_name'] == field_name:
                                            param_def = pdef
                                            break
                                    
                                    if param_def:
                                        field_index = param_def['field_index']
                                        
                                        # Special case for Flow/Area in wrong field
                                        if (calc_method == 'Flow/Area' and 
                                            field_name == 'Flow Rate per Floor Area' and
                                            field_index == 5 and
                                            not obj.obj[5] and
                                            obj.obj[4]):  # Value in wrong field
                                            field_index = 4
                                        
                                        # Apply modification
                                        old_value = obj.obj[field_index]
                                        obj.obj[field_index] = new_value
                                        
                                        self.logger.debug(f"Modified {obj_type} {obj_name} "
                                                        f"{field_name}: {old_value} → {new_value}")
                                        applied_count += 1
                                else:
                                    # Normal parameter modification
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
                
        self.logger.info(f"Applied {applied_count} infiltration modifications")
        return success
    
    def validate_infiltration_rates(self, idf: IDF) -> Tuple[bool, List[str]]:
        """Validate infiltration rates after modifications"""
        errors = []
        
        # Check infiltration objects
        for inf_obj in idf.idfobjects.get('ZONEINFILTRATION:DESIGNFLOWRATE', []):
            calc_method = inf_obj.Design_Flow_Rate_Calculation_Method if hasattr(inf_obj, 'Design_Flow_Rate_Calculation_Method') else None
            
            if calc_method == 'AirChanges/Hour':
                ach = float(inf_obj.Air_Changes_per_Hour) if inf_obj.Air_Changes_per_Hour else 0
                if ach < 0:
                    errors.append(f"{inf_obj.Name}: Negative ACH ({ach})")
                elif ach > 5.0:
                    errors.append(f"{inf_obj.Name}: Very high ACH ({ach})")
                    
            elif calc_method == 'Flow/Area':
                # Check both possible field locations
                flow = float(inf_obj.Flow_Rate_per_Floor_Area) if inf_obj.Flow_Rate_per_Floor_Area else 0
                if flow == 0 and inf_obj.Design_Flow_Rate:
                    flow = float(inf_obj.Design_Flow_Rate)
                    
                if flow < 0:
                    errors.append(f"{inf_obj.Name}: Negative flow rate ({flow} m³/s-m²)")
                elif flow > 0.01:
                    errors.append(f"{inf_obj.Name}: Very high flow rate ({flow} m³/s-m²)")
        
        # Check coefficients sum to reasonable value
        for inf_obj in idf.idfobjects.get('ZONEINFILTRATION:DESIGNFLOWRATE', []):
            const_coef = float(inf_obj.Constant_Term_Coefficient) if hasattr(inf_obj, 'Constant_Term_Coefficient') and inf_obj.Constant_Term_Coefficient else 0
            temp_coef = float(inf_obj.Temperature_Term_Coefficient) if hasattr(inf_obj, 'Temperature_Term_Coefficient') and inf_obj.Temperature_Term_Coefficient else 0
            vel_coef = float(inf_obj.Velocity_Term_Coefficient) if hasattr(inf_obj, 'Velocity_Term_Coefficient') and inf_obj.Velocity_Term_Coefficient else 0
            vel2_coef = float(inf_obj.Velocity_Squared_Term_Coefficient) if hasattr(inf_obj, 'Velocity_Squared_Term_Coefficient') and inf_obj.Velocity_Squared_Term_Coefficient else 0
            
            total_coef = const_coef + temp_coef + vel_coef + vel2_coef
            if total_coef == 0:
                errors.append(f"{inf_obj.Name}: All coefficients are zero")
            elif total_coef > 2.0:
                errors.append(f"{inf_obj.Name}: Coefficient sum too high ({total_coef})")
        
        return len(errors) == 0, errors
    
    def calculate_effective_infiltration(self, idf: IDF, zone_name: str) -> Optional[float]:
        """Calculate effective infiltration rate for a zone in ACH"""
        total_ach = 0.0
        
        # Find zone volume
        zone_volume = None
        for zone in idf.idfobjects.get('ZONE', []):
            if zone.Name == zone_name:
                zone_volume = float(zone.Volume) if zone.Volume and zone.Volume != 'autocalculate' else None
                break
                
        if not zone_volume:
            return None
            
        # Sum all infiltration sources
        for inf_obj in idf.idfobjects.get('ZONEINFILTRATION:DESIGNFLOWRATE', []):
            if inf_obj.Zone_or_ZoneList_or_Space_or_SpaceList_Name == zone_name:
                calc_method = inf_obj.Design_Flow_Rate_Calculation_Method
                
                if calc_method == 'AirChanges/Hour':
                    ach = float(inf_obj.Air_Changes_per_Hour) if inf_obj.Air_Changes_per_Hour else 0
                    total_ach += ach
                    
                elif calc_method == 'Flow/Zone':
                    flow = float(inf_obj.Design_Flow_Rate) if inf_obj.Design_Flow_Rate else 0
                    # Convert m³/s to ACH
                    ach = (flow * 3600) / zone_volume
                    total_ach += ach
                    
        return total_ach
