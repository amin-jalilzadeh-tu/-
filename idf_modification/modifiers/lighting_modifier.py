"""
Lighting Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class LightingModifier(BaseModifier):
    """Modifier for lighting-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize lighting parameter definitions matching parser field names"""
        self.parameter_definitions = {
            'lighting_level': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Lighting Level',
                field_index=4,
                data_type=float,
                units='W',
                performance_impact='lighting_energy'
            ),
            'watts_per_area': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Watts per Zone Floor Area',
                field_index=5,
                data_type=float,
                units='W/m2',
                min_value=0.0,
                max_value=30.0,
                performance_impact='lighting_energy'
            ),
            'watts_per_person': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Watts per Person',
                field_index=6,
                data_type=float,
                units='W/person',
                min_value=0.0,
                max_value=200.0,
                performance_impact='lighting_energy'
            ),
            'fraction_radiant': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Fraction Radiant',
                field_index=7,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            ),
            'fraction_visible': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Fraction Visible',
                field_index=8,
                data_type=float,
                min_value=0.0,
                max_value=1.0
            ),
            'return_air_fraction': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Return Air Fraction',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            ),
            'dimmer_control': ParameterDefinition(
                object_type='DAYLIGHTING:CONTROLS',
                field_name='Lighting Control Type',
                field_index=5,
                data_type=str,
                allowed_values=['Continuous', 'Stepped', 'ContinuousOff'],
                performance_impact='lighting_control'
            ),
            'minimum_light_output': ParameterDefinition(
                object_type='DAYLIGHTING:CONTROLS',
                field_name='Minimum Light Output Fraction',
                field_index=8,
                data_type=float,
                min_value=0.0,
                max_value=0.5,
                performance_impact='lighting_control'
            )
        }
    
    def get_category_name(self) -> str:
        return 'lighting'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'LIGHTS',
            'DAYLIGHTING:CONTROLS',
            'DAYLIGHTING:DETAILED',
            'LIGHTINGDESIGNOBJECT',
            'EXTERIORLIGHTS'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['lighting']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply lighting-specific modifications"""
        
        if strategy == 'led_retrofit':
            return self._apply_led_retrofit(parsed_objects, modifiable_params)
        elif strategy == 'occupancy_sensors':
            return self._apply_occupancy_sensors(parsed_objects, modifiable_params)
        elif strategy == 'daylight_harvesting':
            return self._apply_daylight_harvesting(parsed_objects, modifiable_params)
        elif strategy == 'task_tuning':
            return self._apply_task_tuning(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_led_retrofit(self, parsed_objects, modifiable_params):
        """Apply LED retrofit improvements"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'LIGHTS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # LEDs reduce power by 50-70% compared to traditional lighting
                    reduction = random.uniform(0.5, 0.7)
                    
                    # Find calculation method (usually parameter index 3)
                    calc_method = None
                    if len(obj.parameters) > 3:
                        calc_method = obj.parameters[3].value
                    
                    # Power reduction code
                    if calc_method == 'LightingLevel':
                        for param in obj.parameters:
                            if param.field_name == 'Lighting Level' and param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                modifications.append(self._create_modification_result(
                                    obj, 'lighting_level', old_value, new_value, 'led_retrofit'
                                ))
                                break
                    
                    elif calc_method == 'Watts/Area':
                        for param in obj.parameters:
                            if param.field_name == 'Watts per Zone Floor Area' and param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                modifications.append(self._create_modification_result(
                                    obj, 'watts_per_area', old_value, new_value, 'led_retrofit'
                                ))
                                break
                    
                    elif calc_method == 'Watts/Person':
                        for param in obj.parameters:
                            if param.field_name == 'Watts per Person' and param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                modifications.append(self._create_modification_result(
                                    obj, 'watts_per_person', old_value, new_value, 'led_retrofit'
                                ))
                                break
                    
                    # Update heat fractions for LED characteristics
                    # Get current fractions first
                    current_fractions = {}
                    fraction_params = {}
                    
                    for param in obj.parameters:
                        if param.field_name == 'Fraction Radiant':
                            current_fractions['radiant'] = param.numeric_value or float(param.value or 0.37)
                            fraction_params['radiant'] = param
                        elif param.field_name == 'Fraction Visible':
                            current_fractions['visible'] = param.numeric_value or float(param.value or 0.18)
                            fraction_params['visible'] = param
                        elif param.field_name == 'Return Air Fraction':
                            current_fractions['return_air'] = param.numeric_value or float(param.value or 0.45)
                            fraction_params['return_air'] = param
                    
                    # LED typical values - these MUST sum to less than or equal to 1.0
                    # The remainder (1.0 - sum) is implicitly "Fraction Lost"
                    new_fractions = {
                        'radiant': 0.20,     # LEDs produce less radiant heat
                        'visible': 0.20,     # Similar visible light output
                        'return_air': 0.55   # More heat removed by return air
                    }
                    # Implicit fraction lost = 1.0 - 0.20 - 0.20 - 0.55 = 0.05
                    
                    # Verify the sum is valid
                    fraction_sum = sum(new_fractions.values())
                    if fraction_sum > 1.0:
                        # Scale down to ensure sum <= 1.0
                        scale = 0.95 / fraction_sum  # Leave 5% for lost
                        for key in new_fractions:
                            new_fractions[key] *= scale
                    
                    # Apply the new fractions
                    if 'radiant' in fraction_params:
                        param = fraction_params['radiant']
                        old_value = current_fractions['radiant']
                        param.value = str(new_fractions['radiant'])
                        param.numeric_value = new_fractions['radiant']
                        modifications.append(self._create_modification_result(
                            obj, 'fraction_radiant', old_value, new_fractions['radiant'], 'led_retrofit'
                        ))
                    
                    if 'visible' in fraction_params:
                        param = fraction_params['visible']
                        old_value = current_fractions['visible']
                        param.value = str(new_fractions['visible'])
                        param.numeric_value = new_fractions['visible']
                        modifications.append(self._create_modification_result(
                            obj, 'fraction_visible', old_value, new_fractions['visible'], 'led_retrofit'
                        ))
                    
                    if 'return_air' in fraction_params:
                        param = fraction_params['return_air']
                        old_value = current_fractions['return_air']
                        param.value = str(new_fractions['return_air'])
                        param.numeric_value = new_fractions['return_air']
                        modifications.append(self._create_modification_result(
                            obj, 'return_air_fraction', old_value, new_fractions['return_air'], 'led_retrofit'
                        ))
        
        return modifications
    
    def _apply_occupancy_sensors(self, parsed_objects, modifiable_params):
        """Apply occupancy sensor control"""
        modifications = []
        
        # Occupancy sensors reduce lighting by modifying schedules
        # This is a simplified approach - actual implementation would modify schedules
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'LIGHTS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Occupancy sensors can reduce lighting energy by 20-30%
                    # We'll simulate this by reducing the lighting power
                    import random
                    reduction = random.uniform(0.2, 0.3)
                    
                    for param in obj.parameters:
                        if param.field_name in ['Lighting Level', 'Watts per Zone Floor Area', 'Watts per Person']:
                            if param.numeric_value:
                                old_value = param.numeric_value
                                new_value = old_value * (1 - reduction)
                                
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                
                                param_key = self._get_param_key_from_field_name(param.field_name)
                                modifications.append(self._create_modification_result(
                                    obj, param_key, old_value, new_value, 'occupancy_sensors'
                                ))
                                break
        
        return modifications
    
    def _apply_daylight_harvesting(self, parsed_objects, modifiable_params):
        """Apply daylight harvesting controls"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'DAYLIGHTING:CONTROLS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to continuous dimming for best performance
                    for param in obj.parameters:
                        if param.field_name == 'Lighting Control Type':
                            old_value = param.value
                            new_value = 'Continuous'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'dimmer_control', old_value, new_value, 'daylight_harvesting'
                            ))
                            break
                    
                    # Set minimum light output for continuous dimming
                    for param in obj.parameters:
                        if param.field_name == 'Minimum Light Output Fraction':
                            old_value = param.numeric_value or float(param.value)
                            # Allow dimming down to 10-20%
                            import random
                            new_value = random.uniform(0.1, 0.2)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'minimum_light_output', old_value, new_value, 'daylight_harvesting'
                            ))
                            break
        
        return modifications
    
    def _apply_task_tuning(self, parsed_objects, modifiable_params):
        """Apply task tuning to reduce over-lighting"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'LIGHTS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Task tuning typically reduces lighting by 10-20%
                    import random
                    reduction = random.uniform(0.1, 0.2)
                    
                    # Find watts per area parameter
                    for param in obj.parameters:
                        if param.field_name == 'Watts per Zone Floor Area' and param.numeric_value:
                            old_value = param.numeric_value
                            new_value = old_value * (1 - reduction)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'watts_per_area', old_value, new_value, 'task_tuning'
                            ))
                            break
        
        return modifications
    
    def _get_param_key_from_field_name(self, field_name: str) -> str:
        """Convert field name to parameter key"""
        for key, param_def in self.parameter_definitions.items():
            if param_def.field_name == field_name:
                return key
        return field_name.lower().replace(' ', '_')