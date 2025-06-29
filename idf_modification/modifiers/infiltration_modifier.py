"""
Infiltration Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class InfiltrationModifier(BaseModifier):
    """Modifier for infiltration-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize infiltration parameter definitions matching parser field names"""
        self.parameter_definitions = {
            'design_flow_rate': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Design Flow Rate',
                field_index=4,
                data_type=float,
                units='m3/s',
                performance_impact='infiltration_loads'
            ),
            'flow_per_zone_area': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Flow per Zone Floor Area',
                field_index=5,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.01,
                performance_impact='infiltration_loads'
            ),
            'flow_per_exterior_area': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Flow per Exterior Surface Area',
                field_index=6,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.01,
                performance_impact='infiltration_loads'
            ),
            'air_changes_per_hour': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Air Changes per Hour',
                field_index=7,
                data_type=float,
                units='1/hr',
                min_value=0.0,
                max_value=5.0,
                performance_impact='infiltration_loads'
            ),
            'constant_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Constant Term Coefficient',
                field_index=8,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='infiltration_model'
            ),
            'temperature_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Temperature Term Coefficient',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=0.05,
                performance_impact='infiltration_model'
            ),
            'velocity_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Velocity Term Coefficient',
                field_index=10,
                data_type=float,
                min_value=0.0,
                max_value=0.5,
                performance_impact='infiltration_model'
            ),
            'velocity_squared_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Velocity Squared Term Coefficient',
                field_index=11,
                data_type=float,
                min_value=0.0,
                max_value=0.1,
                performance_impact='infiltration_model'
            )
        }
    
    def get_category_name(self) -> str:
        return 'infiltration'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ZONEINFILTRATION:DESIGNFLOWRATE',
            'ZONEINFILTRATION:EFFECTIVELEAKAGEAREA',
            'ZONEINFILTRATION:FLOWCOEFFICIENT'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['infiltration']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply infiltration-specific modifications"""
        
        if strategy == 'air_sealing':
            return self._apply_air_sealing(parsed_objects, modifiable_params)
        elif strategy == 'tight_construction':
            return self._apply_tight_construction(parsed_objects, modifiable_params)
        elif strategy == 'passive_house':
            return self._apply_passive_house_standard(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_air_sealing(self, parsed_objects, modifiable_params):
        """Apply air sealing improvements"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEINFILTRATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce infiltration rates by 20-40%
                    # Reduce infiltration rates by 20-40%
                    reduction = random.uniform(0.2, 0.4)

                    # FIX: Ensure we don't reduce to zero or negative
                    # Keep at least 10% of original value
                    min_reduction = 0.9  # Maximum 90% reduction
                    reduction = min(reduction, min_reduction)
                    
                    # Find calculation method (usually parameter index 3)
                    calc_method = None
                    if len(obj.parameters) > 3:
                        calc_method = obj.parameters[3].value
                    
                    if calc_method == 'Flow/Zone':
                        # Modify Design Flow Rate
                        for param in obj.parameters:
                            if param.field_name == 'Design Flow Rate' and param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'design_flow_rate', old_value, new_value, 'air_sealing'
                                ))
                                break
                    
                    elif calc_method == 'Flow/Area':
                        # Modify Flow per Zone Floor Area
                        for param in obj.parameters:
                            if param.field_name == 'Flow per Zone Floor Area' and param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'flow_per_zone_area', old_value, new_value, 'air_sealing'
                                ))
                                break
                    
                    elif calc_method == 'AirChanges/Hour':
                        # Modify Air Changes per Hour
                        for param in obj.parameters:
                            if param.field_name == 'Air Changes per Hour' and param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'air_changes_per_hour', old_value, new_value, 'air_sealing'
                                ))
                                break
        
        return modifications
    
    def _apply_tight_construction(self, parsed_objects, modifiable_params):
        """Apply tight construction standards"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEINFILTRATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Tight construction targets specific ACH values
                    for param in obj.parameters:
                        if param.field_name == 'Air Changes per Hour':
                            old_value = param.numeric_value or float(param.value)
                            # Tight construction: 0.1-0.3 ACH
                            import random
                            new_value = random.uniform(0.1, 0.3)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'air_changes_per_hour', old_value, new_value, 'tight_construction'
                            ))
                            break
                    
                    # Also adjust coefficients for tighter building
                    for param in obj.parameters:
                        if param.field_name == 'Constant Term Coefficient':
                            old_value = param.numeric_value or float(param.value)
                            # Reduce constant term for tighter building
                            new_value = old_value * 0.5
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'constant_coefficient', old_value, new_value, 'tight_construction'
                            ))
                            break
        
        return modifications
    
    def _apply_passive_house_standard(self, parsed_objects, modifiable_params):
        """Apply Passive House infiltration standards"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEINFILTRATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Passive House standard: 0.6 ACH at 50 Pa
                    # This translates to about 0.05 ACH under normal conditions
                    for param in obj.parameters:
                        if param.field_name == 'Air Changes per Hour':
                            old_value = param.numeric_value or float(param.value)
                            new_value = 0.05  # Passive House standard
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'air_changes_per_hour', old_value, new_value, 'passive_house'
                            ))
                            break
                    
                    # Set very low coefficients for passive house
                    coefficient_updates = {
                        'Constant Term Coefficient': 0.1,
                        'Temperature Term Coefficient': 0.001,
                        'Velocity Term Coefficient': 0.001,
                        'Velocity Squared Term Coefficient': 0.0001
                    }
                    
                    for param in obj.parameters:
                        if param.field_name in coefficient_updates:
                            old_value = param.numeric_value or float(param.value)
                            new_value = coefficient_updates[param.field_name]
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            param_key = self._get_param_key_from_field_name(param.field_name)
                            modifications.append(self._create_modification_result(
                                obj, param_key, old_value, new_value, 'passive_house'
                            ))
        
        return modifications
    
    def _get_param_key_from_field_name(self, field_name: str) -> str:
        """Convert field name to parameter key"""
        for key, param_def in self.parameter_definitions.items():
            if param_def.field_name == field_name:
                return key
        return field_name.lower().replace(' ', '_')