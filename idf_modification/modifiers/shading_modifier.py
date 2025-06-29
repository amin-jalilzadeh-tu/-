"""
Shading Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class ShadingModifier(BaseModifier):
    """Modifier for shading-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize shading parameter definitions matching parser field names"""
        self.parameter_definitions = {
            # External shading
            'shading_transmittance': ParameterDefinition(
                object_type='SHADING:SITE:DETAILED',
                field_name='Transmittance Schedule Name',
                field_index=2,
                data_type=str,
                performance_impact='solar_gains'
            ),
            'shading_reflectance': ParameterDefinition(
                object_type='SHADING:BUILDING:DETAILED',
                field_name='Reflectance Schedule Name',
                field_index=2,
                data_type=str,
                performance_impact='solar_gains'
            ),
            
            # Window shading control
            'shading_control_type': ParameterDefinition(
                object_type='WINDOWSHADINGCONTROL',
                field_name='Shading Control Type',
                field_index=2,
                data_type=str,
                allowed_values=['AlwaysOn', 'AlwaysOff', 'OnIfScheduleAllows',
                               'OnIfHighSolarOnWindow', 'OnIfHighHorizontalSolar',
                               'OnIfHighOutdoorAirTemperature', 'OnIfHighZoneAirTemperature',
                               'OnIfHighZoneCooling', 'OnNightIfLowOutdoorTempAndOffDay',
                               'OnNightIfLowInsideTempAndOffDay', 'OnNightIfHeatingAndOffDay'],
                performance_impact='shading_operation'
            ),
            'shading_setpoint': ParameterDefinition(
                object_type='WINDOWSHADINGCONTROL',
                field_name='Setpoint',
                field_index=7,
                data_type=float,
                performance_impact='shading_control'
            ),
            'slat_angle': ParameterDefinition(
                object_type='WINDOWSHADINGCONTROL',
                field_name='Slat Angle Schedule Name',
                field_index=11,
                data_type=str,
                performance_impact='solar_control'
            ),
            
            # Overhang parameters
            'overhang_projection': ParameterDefinition(
                object_type='SHADING:OVERHANG:PROJECTION',
                field_name='Height above Window or Door',
                field_index=2,
                data_type=float,
                units='m',
                min_value=0.0,
                max_value=3.0,
                performance_impact='solar_shading'
            ),
            'overhang_depth': ParameterDefinition(
                object_type='SHADING:OVERHANG',
                field_name='Depth',
                field_index=3,
                data_type=float,
                units='m',
                min_value=0.1,
                max_value=5.0,
                performance_impact='solar_shading'
            ),
            
            # Fin parameters
            'fin_projection': ParameterDefinition(
                object_type='SHADING:FIN:PROJECTION',
                field_name='Extension from Window/Door',
                field_index=3,
                data_type=float,
                units='m',
                min_value=0.1,
                max_value=3.0,
                performance_impact='solar_shading'
            )
        }
    
    def get_category_name(self) -> str:
        return 'shading'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'SHADING:SITE:DETAILED',
            'SHADING:BUILDING:DETAILED',
            'SHADING:ZONE:DETAILED',
            'SHADING:OVERHANG',
            'SHADING:OVERHANG:PROJECTION',
            'SHADING:FIN',
            'SHADING:FIN:PROJECTION',
            'WINDOWSHADINGCONTROL',
            'EXTERIORSHADE',
            'INTERIORSHADE'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['shading']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply shading-specific modifications"""
        
        if strategy == 'dynamic_shading':
            return self._apply_dynamic_shading(parsed_objects, modifiable_params)
        elif strategy == 'fixed_shading':
            return self._apply_fixed_shading(parsed_objects, modifiable_params)
        elif strategy == 'optimize_overhangs':
            return self._apply_optimize_overhangs(parsed_objects, modifiable_params)
        elif strategy == 'automated_blinds':
            return self._apply_automated_blinds(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_dynamic_shading(self, parsed_objects, modifiable_params):
        """Apply dynamic shading controls"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWSHADINGCONTROL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to solar-responsive control
                    for param in obj.parameters:
                        if hasattr(param, 'field_name') and param.field_name == 'Shading Control Type':
                            old_value = param.value
                            new_value = 'OnIfHighSolarOnWindow'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shading_control_type', old_value, new_value, 'dynamic_shading'
                            ))
                            break
                    
                    # Set appropriate setpoint (W/m2)
                    # Look for the setpoint parameter by field name
                    setpoint_param = None
                    for i, param in enumerate(obj.parameters):
                        if hasattr(param, 'field_name') and param.field_name == 'Setpoint':
                            setpoint_param = param
                            break
                    
                    # If not found by name, try by index (7th parameter)
                    if setpoint_param is None and len(obj.parameters) > 7:
                        # Check if this is likely the setpoint parameter
                        param = obj.parameters[7]
                        if hasattr(param, 'numeric_value') or (hasattr(param, 'value') and param.value.replace('.', '').replace('-', '').isdigit()):
                            setpoint_param = param
                    
                    if setpoint_param:
                        old_value = getattr(setpoint_param, 'numeric_value', None) or 300.0
                        try:
                            if old_value is None and hasattr(setpoint_param, 'value'):
                                old_value = float(setpoint_param.value)
                        except:
                            old_value = 300.0
                        
                        # Dynamic shading activates at 200-400 W/m2
                        import random
                        new_value = random.uniform(200, 400)
                        
                        setpoint_param.value = str(new_value)
                        if hasattr(setpoint_param, 'numeric_value'):
                            setpoint_param.numeric_value = new_value
                        
                        modifications.append(self._create_modification_result(
                            obj, 'shading_setpoint', old_value, new_value, 'dynamic_shading'
                        ))
        
        return modifications
    
    def _apply_fixed_shading(self, parsed_objects, modifiable_params):
        """Apply fixed shading improvements"""
        modifications = []
        
        # For fixed shading, we typically modify overhang and fin dimensions
        for obj_type, objects in modifiable_params.items():
            if 'OVERHANG' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase overhang depth for better summer shading
                    for param in obj.parameters:
                        if hasattr(param, 'field_name') and param.field_name == 'Depth' and hasattr(param, 'numeric_value') and param.numeric_value:
                            old_depth = param.numeric_value
                            # Increase by 20-40%
                            import random
                            factor = random.uniform(1.2, 1.4)
                            new_depth = min(old_depth * factor, 3.0)  # Cap at 3m
                            
                            param.value = str(new_depth)
                            param.numeric_value = new_depth
                            
                            modifications.append(self._create_modification_result(
                                obj, 'overhang_depth', old_depth, new_depth, 'fixed_shading'
                            ))
                            break
        
        return modifications
    
    def _apply_optimize_overhangs(self, parsed_objects, modifiable_params):
        """Optimize overhang dimensions for solar control"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SHADING:OVERHANG:PROJECTION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Optimize height above window
                    for param in obj.parameters:
                        if hasattr(param, 'field_name') and param.field_name == 'Height above Window or Door':
                            old_height = getattr(param, 'numeric_value', None)
                            if old_height is None and hasattr(param, 'value'):
                                try:
                                    old_height = float(param.value)
                                except:
                                    old_height = 0.2
                            
                            # Optimal height is typically 0.1-0.3m
                            new_height = random.uniform(0.1, 0.3)
                            
                            param.value = str(new_height)
                            if hasattr(param, 'numeric_value'):
                                param.numeric_value = new_height
                            
                            modifications.append(self._create_modification_result(
                                obj, 'overhang_projection', old_height, new_height, 'optimize_overhangs'
                            ))
                            break
            
            elif obj_type == 'SHADING:OVERHANG':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Optimize depth based on window height (simplified)
                    for param in obj.parameters:
                        if hasattr(param, 'field_name') and param.field_name == 'Depth':
                            old_depth = getattr(param, 'numeric_value', None)
                            if old_depth is None and hasattr(param, 'value'):
                                try:
                                    old_depth = float(param.value)
                                except:
                                    old_depth = 0.5
                            
                            # Optimal depth is typically 0.5-1.5m
                            new_depth = random.uniform(0.5, 1.5)
                            
                            param.value = str(new_depth)
                            if hasattr(param, 'numeric_value'):
                                param.numeric_value = new_depth
                            
                            modifications.append(self._create_modification_result(
                                obj, 'overhang_depth', old_depth, new_depth, 'optimize_overhangs'
                            ))
                            break
        
        return modifications
    
    def _apply_automated_blinds(self, parsed_objects, modifiable_params):
        """Apply automated blind controls"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWSHADINGCONTROL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to high zone cooling control for automated response
                    for param in obj.parameters:
                        if hasattr(param, 'field_name') and param.field_name == 'Shading Control Type':
                            old_value = param.value
                            new_value = 'OnIfHighZoneCooling'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shading_control_type', old_value, new_value, 'automated_blinds'
                            ))
                            break
                    
                    # Set cooling rate setpoint (W)
                    # Look for the setpoint parameter by field name
                    setpoint_param = None
                    for i, param in enumerate(obj.parameters):
                        if hasattr(param, 'field_name') and param.field_name == 'Setpoint':
                            setpoint_param = param
                            break
                    
                    # If not found by name, try by index (7th parameter)
                    if setpoint_param is None and len(obj.parameters) > 7:
                        # Check if this is likely the setpoint parameter
                        param = obj.parameters[7]
                        if hasattr(param, 'numeric_value') or (hasattr(param, 'value') and param.value.replace('.', '').replace('-', '').isdigit()):
                            setpoint_param = param
                    
                    if setpoint_param:
                        old_value = getattr(setpoint_param, 'numeric_value', None) or 100.0
                        try:
                            if old_value is None and hasattr(setpoint_param, 'value'):
                                old_value = float(setpoint_param.value)
                        except:
                            old_value = 100.0
                        
                        # Activate when cooling load exceeds 50-150W
                        import random
                        new_value = random.uniform(50, 150)
                        
                        setpoint_param.value = str(new_value)
                        if hasattr(setpoint_param, 'numeric_value'):
                            setpoint_param.numeric_value = new_value
                        
                        modifications.append(self._create_modification_result(
                            obj, 'shading_setpoint', old_value, new_value, 'automated_blinds'
                        ))
        
        return modifications