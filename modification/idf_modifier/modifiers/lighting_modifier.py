"""
Lighting Modifier Module - Handle lighting system modifications
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import logging

from ..base_modifier import BaseModifier, ModificationParameter


class LightingModifier(BaseModifier):
    """Modifier for lighting-related parameters"""
    
    def __init__(self, category: str = 'lighting', parsed_data_path=None):
        super().__init__(category, parsed_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Define lighting object types
        self.lighting_objects = {
            'interior_lights': ['LIGHTS'],
            'exterior_lights': ['EXTERIOR:LIGHTS'],
            'daylighting': [
                'DAYLIGHTING:CONTROLS',
                'DAYLIGHTING:REFERENCEPOINT',
                'DAYLIGHTING:DELIGHT:CONTROLS',
                'DAYLIGHTING:DELIGHT:REFERENCEPOINT'
            ]
        }
        
        # Typical lighting power densities by space type (W/m²)
        self.typical_lpd = {
            'office': {'current': 10.8, 'efficient': 6.5, 'advanced': 4.0},
            'classroom': {'current': 13.0, 'efficient': 8.5, 'advanced': 5.5},
            'retail': {'current': 16.1, 'efficient': 10.5, 'advanced': 7.0},
            'warehouse': {'current': 8.6, 'efficient': 5.5, 'advanced': 3.5},
            'residential': {'current': 7.5, 'efficient': 5.0, 'advanced': 3.0},
            'healthcare': {'current': 12.9, 'efficient': 9.0, 'advanced': 6.5},
            'hotel': {'current': 10.8, 'efficient': 7.5, 'advanced': 5.0}
        }
        
        # Parameter definitions
        self.parameter_map = self._build_parameter_map()
        
    def _build_parameter_map(self) -> Dict[str, Dict[str, Any]]:
        """Build parameter mapping for lighting objects"""
        return {
            'LIGHTS': {
                'lighting_level': {
                    'field_name': 'Lighting Level',
                    'field_index': 4,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W'
                },
                'watts_per_area': {
                    'field_name': 'Watts per Zone Floor Area',
                    'field_index': 5,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'typical_range': [3.0, 20.0],
                    'units': 'W/m²'
                },
                'watts_per_person': {
                    'field_name': 'Watts per Person',
                    'field_index': 6,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'typical_range': [50.0, 200.0],
                    'units': 'W/person'
                },
                'return_air_fraction': {
                    'field_name': 'Return Air Fraction',
                    'field_index': 7,
                    'typical_range': [0.0, 0.5],
                    'units': 'fraction'
                },
                'fraction_radiant': {
                    'field_name': 'Fraction Radiant',
                    'field_index': 8,
                    'typical_range': [0.5, 0.8],
                    'units': 'fraction'
                },
                'fraction_visible': {
                    'field_name': 'Fraction Visible',
                    'field_index': 9,
                    'typical_range': [0.1, 0.3],
                    'units': 'fraction'
                }
            },
            'EXTERIOR:LIGHTS': {
                'design_level': {
                    'field_name': 'Design Level',
                    'field_index': 3,
                    'typical_range': [100, 10000],
                    'units': 'W'
                }
            },
            'DAYLIGHTING:CONTROLS': {
                'illuminance_setpoint': {
                    'field_name': 'Illuminance Setpoint at Reference Point 1',
                    'field_index': 4,
                    'typical_range': [300, 750],
                    'units': 'lux'
                },
                'lighting_control_type': {
                    'field_name': 'Lighting Control Type',
                    'field_index': 5,
                    'options': ['Continuous', 'Stepped', 'ContinuousOff']
                },
                'minimum_light_fraction': {
                    'field_name': 'Minimum Light Output Fraction',
                    'field_index': 9,
                    'typical_range': [0.1, 0.5],
                    'units': 'fraction'
                }
            }
        }
    
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """Identify all lighting parameters in the IDF"""
        parameters = []
        
        # Interior lighting
        if 'LIGHTS' in idf.idfobjects:
            for light in idf.idfobjects['LIGHTS']:
                # Check calculation method
                calc_method_index = self.parameter_map['LIGHTS']['lighting_level']['calc_method_index']
                calc_method = light.obj[calc_method_index] if len(light.obj) > calc_method_index else None
                
                # Extract parameters based on calculation method
                if calc_method == 'Watts/Area':
                    field_def = self.parameter_map['LIGHTS']['watts_per_area']
                    current_value = light.obj[field_def['field_index']]
                    
                    if current_value and current_value != '' and float(current_value) > 0:
                        param = ModificationParameter(
                            object_type='LIGHTS',
                            object_name=light.Name,
                            field_name=field_def['field_name'],
                            field_index=field_def['field_index'],
                            current_value=float(current_value),
                            units=field_def['units'],
                            constraints={
                                'min_value': field_def['typical_range'][0],
                                'max_value': field_def['typical_range'][1]
                            }
                        )
                        param.modification_rule = calc_method
                        parameters.append(param)
                        
                elif calc_method == 'LightingLevel':
                    field_def = self.parameter_map['LIGHTS']['lighting_level']
                    current_value = light.obj[field_def['field_index']]
                    
                    if current_value and current_value != '' and float(current_value) > 0:
                        param = ModificationParameter(
                            object_type='LIGHTS',
                            object_name=light.Name,
                            field_name=field_def['field_name'],
                            field_index=field_def['field_index'],
                            current_value=float(current_value),
                            units=field_def['units']
                        )
                        param.modification_rule = calc_method
                        parameters.append(param)
                
                # Always check lighting fractions
                for fraction_type in ['return_air_fraction', 'fraction_radiant', 'fraction_visible']:
                    if fraction_type in self.parameter_map['LIGHTS']:
                        field_def = self.parameter_map['LIGHTS'][fraction_type]
                        current_value = light.obj[field_def['field_index']]
                        
                        if current_value and current_value != '':
                            param = ModificationParameter(
                                object_type='LIGHTS',
                                object_name=light.Name,
                                field_name=field_def['field_name'],
                                field_index=field_def['field_index'],
                                current_value=float(current_value),
                                units=field_def['units'],
                                constraints={
                                    'min_value': field_def['typical_range'][0],
                                    'max_value': field_def['typical_range'][1]
                                }
                            )
                            parameters.append(param)
        
        # Exterior lighting
        if 'EXTERIOR:LIGHTS' in idf.idfobjects:
            for ext_light in idf.idfobjects['EXTERIOR:LIGHTS']:
                field_def = self.parameter_map['EXTERIOR:LIGHTS']['design_level']
                current_value = ext_light.obj[field_def['field_index']]
                
                if current_value and current_value != '' and float(current_value) > 0:
                    param = ModificationParameter(
                        object_type='EXTERIOR:LIGHTS',
                        object_name=ext_light.Name,
                        field_name=field_def['field_name'],
                        field_index=field_def['field_index'],
                        current_value=float(current_value),
                        units=field_def['units'],
                        constraints={
                            'min_value': field_def['typical_range'][0],
                            'max_value': field_def['typical_range'][1]
                        }
                    )
                    parameters.append(param)
        
        # Daylighting controls
        if 'DAYLIGHTING:CONTROLS' in idf.idfobjects:
            for daylight in idf.idfobjects['DAYLIGHTING:CONTROLS']:
                # Illuminance setpoint
                field_def = self.parameter_map['DAYLIGHTING:CONTROLS']['illuminance_setpoint']
                current_value = daylight.obj[field_def['field_index']]
                
                if current_value and current_value != '':
                    param = ModificationParameter(
                        object_type='DAYLIGHTING:CONTROLS',
                        object_name=daylight.Name if hasattr(daylight, 'Name') else daylight.Zone_or_Space_Name,
                        field_name=field_def['field_name'],
                        field_index=field_def['field_index'],
                        current_value=float(current_value),
                        units=field_def['units'],
                        constraints={
                            'min_value': field_def['typical_range'][0],
                            'max_value': field_def['typical_range'][1]
                        }
                    )
                    parameters.append(param)
        
        self.logger.info(f"Identified {len(parameters)} lighting parameters")
        return parameters
    
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate modification values for lighting parameters"""
        if strategy == 'performance':
            return self._generate_performance_modifications(parameters, options)
        elif strategy == 'power_reduction':
            return self._generate_power_reduction_modifications(parameters, options)
        elif strategy == 'led_upgrade':
            return self._generate_led_upgrade_modifications(parameters, options)
        elif strategy == 'daylighting':
            return self._generate_daylighting_modifications(parameters, options)
        elif strategy == 'random':
            return self._generate_random_modifications(parameters, options)
        else:
            return self._generate_default_modifications(parameters, options)
    
    def _generate_performance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance-based modifications"""
        modification_set = {}
        
        # Get power multiplier from options
        power_mult = options.get('power', 0.8)  # 20% reduction default
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if 'watts' in param.field_name.lower() or 'lighting level' in param.field_name.lower():
                # Reduce lighting power
                new_value = self.apply_multiplier(param.current_value,
                                                power_mult,
                                                min_val=param.constraints.get('min_value', 3.0))
                modification_set[param_id] = new_value
                
            elif 'fraction_visible' in param.field_name.lower():
                # Increase visible light fraction for better efficacy
                new_value = min(param.current_value * 1.2, 0.25)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_power_reduction_modifications(self,
                                              parameters: List[ModificationParameter],
                                              options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate power reduction modifications"""
        modification_set = {}
        
        # Target reduction percentage
        reduction_target = options.get('reduction_target', 0.3)  # 30% reduction
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Watts per Zone Floor Area':
                # Apply reduction
                new_value = param.current_value * (1 - reduction_target)
                new_value = max(new_value, 3.0)  # Minimum 3 W/m²
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Lighting Level':
                # Apply reduction to absolute lighting level
                new_value = param.current_value * (1 - reduction_target)
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Design Level' and param.object_type == 'EXTERIOR:LIGHTS':
                # Reduce exterior lighting
                new_value = param.current_value * (1 - reduction_target * 0.5)  # Less aggressive
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_led_upgrade_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate LED upgrade modifications"""
        modification_set = {}
        
        # LED characteristics
        led_efficacy_improvement = 0.4  # 40% power reduction
        led_visible_fraction = 0.22  # Higher visible light fraction
        
        # Get space type for appropriate LPD
        space_type = options.get('space_type', 'office')
        target_level = options.get('target_level', 'efficient')
        
        target_lpd = self.typical_lpd.get(space_type, {}).get(target_level, 6.5)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Watts per Zone Floor Area':
                # Set to target LPD
                new_value = min(param.current_value, target_lpd)
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Lighting Level':
                # Reduce by LED efficacy improvement
                new_value = param.current_value * (1 - led_efficacy_improvement)
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Fraction Visible':
                # Update to LED characteristics
                modification_set[param_id] = led_visible_fraction
                
            elif param.field_name == 'Fraction Radiant':
                # LEDs produce less radiant heat
                modification_set[param_id] = 0.65
                
        return [modification_set]
    
    def _generate_daylighting_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate daylighting optimization modifications"""
        modification_set = {}
        
        # Daylighting parameters
        target_setpoint = options.get('illuminance_setpoint', 500)  # lux
        dimming_fraction = options.get('minimum_dimming', 0.2)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.object_type == 'DAYLIGHTING:CONTROLS':
                if 'Illuminance Setpoint' in param.field_name:
                    # Set target illuminance
                    modification_set[param_id] = target_setpoint
                elif 'Minimum Light Output Fraction' in param.field_name:
                    # Set minimum dimming level
                    modification_set[param_id] = dimming_fraction
                    
            elif param.field_name == 'Watts per Zone Floor Area':
                # Reduce lighting power assuming daylighting contribution
                daylight_factor = options.get('daylight_contribution', 0.3)
                new_value = param.current_value * (1 - daylight_factor)
                new_value = max(new_value, 3.0)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_random_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate random modifications"""
        modification_set = {}
        
        seed = options.get('seed', None)
        if seed:
            np.random.seed(seed)
            
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if 'watts' in param.field_name.lower() or 'level' in param.field_name.lower():
                # Random reduction between 10-40%
                multiplier = np.random.uniform(0.6, 0.9)
                new_value = self.apply_multiplier(param.current_value,
                                                multiplier,
                                                min_val=param.constraints.get('min_value', 3.0))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_default_modifications(self,
                                      parameters: List[ModificationParameter],
                                      options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default modification strategy - 15% power reduction"""
        modification_set = {}
        
        for param in parameters:
            if 'watts' in param.field_name.lower() or 'level' in param.field_name.lower():
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                new_value = self.apply_multiplier(param.current_value, 0.85,
                                                min_val=param.constraints.get('min_value', 3.0))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def apply_modifications(self, idf: IDF, modifications: Dict[str, Any]) -> bool:
        """Apply lighting modifications to IDF"""
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
                            for param_key, param_def in self.parameter_map.get(obj_type, {}).items():
                                if param_def.get('field_name') == field_name:
                                    field_index = param_def['field_index']
                                    
                                    # Check if this is the right calculation method
                                    if 'calc_method_index' in param_def:
                                        calc_method = obj.obj[param_def['calc_method_index']]
                                        
                                        # Skip if wrong calculation method
                                        if field_name == 'Watts per Zone Floor Area' and calc_method != 'Watts/Area':
                                            continue
                                        elif field_name == 'Lighting Level' and calc_method != 'LightingLevel':
                                            continue
                                    
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
                
        self.logger.info(f"Applied {applied_count} lighting modifications")
        return success
    
    def validate_lighting_levels(self, idf: IDF) -> Tuple[bool, List[str]]:
        """Validate lighting levels after modifications"""
        errors = []
        
        # Check interior lighting
        if 'LIGHTS' in idf.idfobjects:
            for light in idf.idfobjects['LIGHTS']:
                calc_method = light.Design_Level_Calculation_Method if hasattr(light, 'Design_Level_Calculation_Method') else None
                
                if calc_method == 'Watts/Area':
                    lpd = float(light.Watts_per_Zone_Floor_Area) if light.Watts_per_Zone_Floor_Area else 0
                    if lpd < 2.0:
                        errors.append(f"{light.Name}: LPD too low ({lpd} W/m²)")
                    elif lpd > 30.0:
                        errors.append(f"{light.Name}: LPD too high ({lpd} W/m²)")
                        
                # Check fractions sum to reasonable value
                if hasattr(light, 'Fraction_Radiant') and hasattr(light, 'Fraction_Visible'):
                    frac_rad = float(light.Fraction_Radiant) if light.Fraction_Radiant else 0
                    frac_vis = float(light.Fraction_Visible) if light.Fraction_Visible else 0
                    total_frac = frac_rad + frac_vis
                    
                    if total_frac > 1.0:
                        errors.append(f"{light.Name}: Radiant + Visible fractions > 1.0 ({total_frac})")
        
        return len(errors) == 0, errors
    
    def add_daylighting_controls(self, idf: IDF, zone_name: str, 
                                reference_point: Tuple[float, float, float] = None,
                                illuminance_setpoint: float = 500):
        """Add daylighting controls to a zone"""
        if reference_point is None:
            # Default to center of zone at 0.8m height
            reference_point = (0, 0, 0.8)
            
        # Create daylighting control
        idf.newidfobject(
            'DAYLIGHTING:CONTROLS',
            Zone_or_Space_Name=zone_name,
            Daylighting_Method='SplitFlux',
            Availability_Schedule_Name='ALWAYS_ON',
            Lighting_Control_Type='Continuous',
            Minimum_Input_Power_Fraction_for_Continuous_or_ContinuousOff_Dimming_Control=0.3,
            Minimum_Light_Output_Fraction_for_Continuous_or_ContinuousOff_Dimming_Control=0.2,
            Number_of_Stepped_Control_Steps=1,
            Probability_Lighting_will_be_Reset_When_Needed_in_Manual_Stepped_Control=1.0,
            Glare_Calculation_Daylighting_Reference_Point_Name=f'{zone_name}_DaylightRefPt1',
            Glare_Calculation_Azimuth_Angle_of_View_Direction_Clockwise_from_Zone_y_Axis=0,
            Maximum_Allowable_Discomfort_Glare_Index=22,
            DElight_Gridding_Resolution=0.2
        )
        
        # Create reference point
        idf.newidfobject(
            'DAYLIGHTING:REFERENCEPOINT',
            Name=f'{zone_name}_DaylightRefPt1',
            Zone_or_Space_Name=zone_name,
            X_Coordinate_of_Reference_Point=reference_point[0],
            Y_Coordinate_of_Reference_Point=reference_point[1],
            Z_Coordinate_of_Reference_Point=reference_point[2],
            Fraction_of_Zone_or_Space_Controlled_by_Reference_Point=1.0,
            Illuminance_Setpoint_at_Reference_Point=illuminance_setpoint
        )
        
        self.logger.info(f"Added daylighting controls to zone {zone_name}")
