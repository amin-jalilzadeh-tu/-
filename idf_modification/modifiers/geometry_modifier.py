"""
Geometry Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class GeometryModifier(BaseModifier):
    """Modifier for geometry-related IDF objects (zones and surfaces)"""
    
    def _initialize_parameters(self):
        """Initialize geometry parameter definitions matching parser field names"""
        self.parameter_definitions = {
            # Zone parameters
            'zone_multiplier': ParameterDefinition(
                object_type='ZONE',
                field_name='Multiplier',
                field_index=6,
                data_type=int,
                min_value=1,
                max_value=100,
                performance_impact='zone_loads'
            ),
            'ceiling_height': ParameterDefinition(
                object_type='ZONE',
                field_name='Ceiling Height',
                field_index=7,
                data_type=float,
                units='m',
                min_value=2.0,
                max_value=10.0,
                performance_impact='zone_volume'
            ),
            'zone_volume': ParameterDefinition(
                object_type='ZONE',
                field_name='Volume',
                field_index=8,
                data_type=float,
                units='m3',
                performance_impact='zone_loads'
            ),
            'zone_floor_area': ParameterDefinition(
                object_type='ZONE',
                field_name='Floor Area',
                field_index=9,
                data_type=float,
                units='m2',
                performance_impact='zone_loads'
            ),
            
            # Surface parameters - Note: area is calculated, not directly modifiable
            'view_factor_to_ground': ParameterDefinition(
                object_type='BUILDINGSURFACE:DETAILED',
                field_name='View Factor to Ground',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='radiant_exchange'
            ),
            
            # Window multiplier for fenestration
            'window_multiplier': ParameterDefinition(
                object_type='FENESTRATIONSURFACE:DETAILED',
                field_name='Multiplier',
                field_index=9,
                data_type=float,
                min_value=0.1,
                max_value=10.0,
                performance_impact='solar_gains'
            )
        }
    
    def get_category_name(self) -> str:
        return 'geometry'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ZONE',
            'ZONELIST',
            'BUILDINGSURFACE:DETAILED',
            'FENESTRATIONSURFACE:DETAILED',
            'GLOBALGEOMETRYRULES',
            'FLOOR:DETAILED',
            'WALL:DETAILED',
            'ROOFCEILING:DETAILED',
            'WINDOW',
            'DOOR',
            'GLAZEDDOOR'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['geometry_zones', 'geometry_surfaces']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply geometry-specific modifications"""
        
        if strategy == 'window_optimization':
            return self._apply_window_optimization(parsed_objects, modifiable_params)
        elif strategy == 'zone_volume_adjustment':
            return self._apply_zone_volume_adjustment(parsed_objects, modifiable_params)
        elif strategy == 'view_factor_optimization':
            return self._apply_view_factor_optimization(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_window_optimization(self, parsed_objects, modifiable_params):
        """Optimize window sizes for energy performance"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'FENESTRATIONSURFACE:DETAILED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Find multiplier parameter
                    for param in obj.parameters:
                        if param.field_name == 'Multiplier':
                            old_value = param.numeric_value or float(param.value or 1.0)
                            
                            # Adjust window size based on orientation
                            # This is simplified - real implementation would check orientation
                            adjustment = random.uniform(0.7, 1.3)  # -30% to +30%
                            new_value = old_value * adjustment
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'window_multiplier', old_value, new_value, 'window_optimization'
                            ))
                            break
        
        return modifications
    
    def _apply_zone_volume_adjustment(self, parsed_objects, modifiable_params):
        """Adjust zone volumes and heights"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Adjust ceiling height
                    for param in obj.parameters:
                        if param.field_name == 'Ceiling Height' and param.numeric_value:
                            old_height = param.numeric_value
                            # Increase height for better natural ventilation
                            import random
                            factor = random.uniform(1.05, 1.15)  # 5-15% increase
                            new_height = min(old_height * factor, 10.0)  # Cap at 10m
                            
                            param.value = str(new_height)
                            param.numeric_value = new_height
                            
                            modifications.append(self._create_modification_result(
                                obj, 'ceiling_height', old_height, new_height, 'zone_volume_adjustment'
                            ))
                            
                            # Also update volume if present
                            for vol_param in obj.parameters:
                                if vol_param.field_name == 'Volume' and vol_param.numeric_value:
                                    old_volume = vol_param.numeric_value
                                    # Assuming volume scales linearly with height
                                    new_volume = old_volume * (new_height / old_height)
                                    
                                    vol_param.value = str(new_volume)
                                    vol_param.numeric_value = new_volume
                                    
                                    modifications.append(self._create_modification_result(
                                        obj, 'zone_volume', old_volume, new_volume, 'zone_volume_adjustment'
                                    ))
                                    break
                            break
        
        return modifications
    
    def _apply_view_factor_optimization(self, parsed_objects, modifiable_params):
        """Optimize view factors for surfaces"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'BUILDINGSURFACE:DETAILED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an exterior surface
                    # Simplified - real implementation would check boundary condition
                    for param in obj.parameters:
                        if param.field_name == 'View Factor to Ground':
                            old_value = param.numeric_value or float(param.value or 0.5)
                            
                            # Optimize based on surface type
                            # This is simplified - real implementation would check surface type
                            import random
                            if 'ROOF' in obj.name.upper():
                                # Roofs should have low view factor to ground
                                new_value = random.uniform(0.0, 0.2)
                            elif 'FLOOR' in obj.name.upper():
                                # Floors might have higher view factor
                                new_value = random.uniform(0.7, 1.0)
                            else:
                                # Walls - moderate view factor
                                new_value = random.uniform(0.4, 0.6)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'view_factor_to_ground', old_value, new_value, 'view_factor_optimization'
                            ))
                            break
        
        return modifications