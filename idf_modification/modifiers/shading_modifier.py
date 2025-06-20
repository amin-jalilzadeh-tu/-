"""
Shading device and control modifications.

This module handles modifications to shading device and control modifications.
"""
"""
Shading Modifier - Handles shading and window control objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class ShadingModifier(BaseModifier):
    """Modifier for shading-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize shading parameter definitions"""
        self.parameter_definitions = {
            # Window shading control
            'shading_setpoint': ParameterDefinition(
                object_type='WINDOWSHADINGCONTROL',
                field_name='Setpoint',
                field_index=7,
                data_type=float,
                units='W/m2 or C',
                performance_impact='solar_control'
            ),
            'shading_setpoint2': ParameterDefinition(
                object_type='WINDOWSHADINGCONTROL',
                field_name='Setpoint 2',
                field_index=14,
                data_type=float,
                units='W/m2 or C',
                performance_impact='solar_control'
            ),
            
            # Blind properties
            'slat_width': ParameterDefinition(
                object_type='WINDOWMATERIAL:BLIND',
                field_name='Slat Width',
                field_index=2,
                data_type=float,
                units='m',
                min_value=0.01,
                max_value=0.1,
                performance_impact='blind_performance'
            ),
            'slat_angle': ParameterDefinition(
                object_type='WINDOWMATERIAL:BLIND',
                field_name='Slat Angle',
                field_index=5,
                data_type=float,
                units='degrees',
                min_value=0,
                max_value=180,
                performance_impact='solar_control'
            ),
            'slat_beam_solar_reflectance': ParameterDefinition(
                object_type='WINDOWMATERIAL:BLIND',
                field_name='Front Side Slat Beam Solar Reflectance',
                field_index=8,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='solar_reflection'
            ),
            'blind_to_glass_distance': ParameterDefinition(
                object_type='WINDOWMATERIAL:BLIND',
                field_name='Blind to Glass Distance',
                field_index=22,
                data_type=float,
                units='m',
                min_value=0.01,
                max_value=0.3,
                performance_impact='blind_performance'
            ),
            
            # Overhang/fin dimensions
            'overhang_projection': ParameterDefinition(
                object_type='SHADING:OVERHANG:PROJECTION',
                field_name='Depth',
                field_index=3,
                data_type=float,
                units='m',
                min_value=0.1,
                max_value=3.0,
                performance_impact='solar_shading'
            ),
            'fin_projection': ParameterDefinition(
                object_type='SHADING:FIN:PROJECTION',
                field_name='Depth',
                field_index=3,
                data_type=float,
                units='m',
                min_value=0.1,
                max_value=2.0,
                performance_impact='solar_shading'
            )
        }
    
    def get_category_name(self) -> str:
        return 'shading'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'WINDOWSHADINGCONTROL',
            'SHADING:SITE',
            'SHADING:SITE:DETAILED',
            'SHADING:BUILDING',
            'SHADING:BUILDING:DETAILED',
            'SHADING:ZONE',
            'SHADING:ZONE:DETAILED',
            'SHADING:OVERHANG',
            'SHADING:OVERHANG:PROJECTION',
            'SHADING:FIN',
            'SHADING:FIN:PROJECTION',
            'WINDOWMATERIAL:BLIND',
            'WINDOWMATERIAL:SCREEN',
            'WINDOWMATERIAL:SHADE'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['shading']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply shading-specific modifications"""
        
        if strategy == 'dynamic_shading':
            return self._apply_dynamic_shading(idf, modifiable_params)
        elif strategy == 'fixed_shading_optimization':
            return self._apply_fixed_shading_optimization(idf, modifiable_params)
        elif strategy == 'blind_optimization':
            return self._apply_blind_optimization(idf, modifiable_params)
        elif strategy == 'solar_control':
            return self._apply_solar_control(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_dynamic_shading(self, idf, modifiable_params):
        """Optimize dynamic shading controls"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWSHADINGCONTROL':
                for obj_info in objects:
                    obj = obj_info['object']
                    control_type = obj.Shading_Control_Type
                    
                    # Optimize setpoints based on control type
                    if control_type == 'OnIfHighSolarOnWindow':
                        if obj.Setpoint:
                            old_setpoint = float(obj.Setpoint)
                            # Lower setpoint for more aggressive shading
                            new_setpoint = old_setpoint * 0.7  # 30% reduction
                            obj.Setpoint = new_setpoint
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shading_setpoint', old_setpoint, new_setpoint,
                                'aggressive_solar_control'
                            ))
                            
                    elif control_type == 'OnIfHighZoneAirTemperature':
                        if obj.Setpoint:
                            old_setpoint = float(obj.Setpoint)
                            # Lower temperature threshold
                            new_setpoint = old_setpoint - 1.0  # 1°C lower
                            obj.Setpoint = new_setpoint
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shading_setpoint', old_setpoint, new_setpoint,
                                'temperature_based_control'
                            ))
        
        return modifications
    
    def _apply_fixed_shading_optimization(self, idf, modifiable_params):
        """Optimize fixed shading devices"""
        modifications = []
        
        # Optimize overhangs
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SHADING:OVERHANG:PROJECTION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Depth:
                        old_depth = float(obj.Depth)
                        # Increase overhang depth for better summer shading
                        new_depth = min(old_depth * 1.3, 2.0)  # 30% increase, max 2m
                        obj.Depth = new_depth
                        
                        modifications.append(self._create_modification_result(
                            obj, 'overhang_projection', old_depth, new_depth,
                            'enhanced_overhang'
                        ))
                        
            elif obj_type == 'SHADING:FIN:PROJECTION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Depth:
                        old_depth = float(obj.Depth)
                        # Moderate fin increase
                        new_depth = min(old_depth * 1.2, 1.5)  # 20% increase, max 1.5m
                        obj.Depth = new_depth
                        
                        modifications.append(self._create_modification_result(
                            obj, 'fin_projection', old_depth, new_depth,
                            'enhanced_fin'
                        ))
        
        return modifications
    
    def _apply_blind_optimization(self, idf, modifiable_params):
        """Optimize blind properties"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWMATERIAL:BLIND':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Optimize slat angle for better control
                    if obj.Slat_Angle:
                        old_angle = float(obj.Slat_Angle)
                        # Set to 45 degrees for balanced performance
                        new_angle = 45.0
                        obj.Slat_Angle = new_angle
                        
                        modifications.append(self._create_modification_result(
                            obj, 'slat_angle', old_angle, new_angle,
                            'optimal_slat_angle'
                        ))
                    
                    # Increase reflectance for better solar rejection
                    if obj.Front_Side_Slat_Beam_Solar_Reflectance:
                        old_refl = float(obj.Front_Side_Slat_Beam_Solar_Reflectance)
                        new_refl = min(old_refl * 1.3, 0.8)  # 30% increase, max 0.8
                        obj.Front_Side_Slat_Beam_Solar_Reflectance = new_refl
                        obj.Back_Side_Slat_Beam_Solar_Reflectance = new_refl
                        
                        modifications.append(self._create_modification_result(
                            obj, 'slat_beam_solar_reflectance', old_refl, new_refl,
                            'high_reflectance_slats'
                        ))
                    
                    # Optimize blind-to-glass distance
                    if obj.Blind_to_Glass_Distance:
                        old_dist = float(obj.Blind_to_Glass_Distance)
                        # Optimal distance for convection
                        new_dist = 0.05  # 5cm
                        obj.Blind_to_Glass_Distance = new_dist
                        
                        modifications.append(self._create_modification_result(
                            obj, 'blind_to_glass_distance', old_dist, new_dist,
                            'optimal_air_gap'
                        ))
        
        return modifications
    
    def _apply_solar_control(self, idf, modifiable_params):
        """Apply comprehensive solar control strategy"""
        modifications = []
        
        # Combine multiple strategies
        modifications.extend(self._apply_dynamic_shading(idf, modifiable_params))
        modifications.extend(self._apply_blind_optimization(idf, modifiable_params))
        
        # Add specific solar control for screens
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWMATERIAL:SCREEN':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce screen transmittance
                    if hasattr(obj, 'Diffuse_Solar_Transmittance'):
                        old_trans = float(obj.Diffuse_Solar_Transmittance)
                        new_trans = old_trans * 0.7  # 30% reduction
                        obj.Diffuse_Solar_Transmittance = new_trans
                        
                        modifications.append(self._create_modification_result(
                            obj, 'screen_transmittance', old_trans, new_trans,
                            'solar_screen'
                        ))
        
        return modifications
    
    def _create_modification_result(self, obj, param_name, old_value, new_value, rule):
        """Helper to create modification result"""
        from ..base_modifier import ModificationResult
        
        return ModificationResult(
            success=True,
            object_type=obj.obj[0],
            object_name=obj.Name if hasattr(obj, 'Name') else str(obj),
            parameter=param_name,
            original_value=old_value,
            new_value=new_value,
            change_type='absolute',
            rule_applied=rule,
            validation_status='valid'
        )