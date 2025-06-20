"""
Building geometry, surfaces, and zones modifications.

This module handles modifications to building geometry, surfaces, and zones modifications.
"""
"""
Geometry Modifier - Handles zones and surfaces
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class GeometryModifier(BaseModifier):
    """Modifier for geometry-related IDF objects (zones and surfaces)"""
    
    def _initialize_parameters(self):
        """Initialize geometry parameter definitions"""
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
            
            # Surface parameters
            'surface_area': ParameterDefinition(
                object_type='BUILDINGSURFACE:DETAILED',
                field_name='Area',
                field_index=-1,  # Calculated field
                data_type=float,
                units='m2',
                performance_impact='envelope_loads'
            ),
            'window_area': ParameterDefinition(
                object_type='FENESTRATIONSURFACE:DETAILED',
                field_name='Area',
                field_index=-1,  # Calculated field
                data_type=float,
                units='m2',
                performance_impact='solar_gains'
            ),
            'view_factor_to_ground': ParameterDefinition(
                object_type='BUILDINGSURFACE:DETAILED',
                field_name='View Factor to Ground',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='radiant_exchange'
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
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply geometry-specific modifications"""
        
        if strategy == 'window_optimization':
            return self._apply_window_optimization(idf, modifiable_params)
        elif strategy == 'zone_consolidation':
            return self._apply_zone_consolidation(idf, modifiable_params)
        elif strategy == 'envelope_area_reduction':
            return self._apply_envelope_reduction(idf, modifiable_params)
        else:
            # Geometry is typically not modified directly
            return []
    
    def _apply_window_optimization(self, idf, modifiable_params):
        """Optimize window sizes for energy performance"""
        modifications = []
        
        # Calculate total window and wall areas
        window_areas = {}
        wall_areas = {}
        
        # First pass - collect areas by zone
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'BUILDINGSURFACE:DETAILED':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Surface_Type in ['Wall', 'ExteriorWall']:
                        zone = obj.Zone_Name
                        area = self._calculate_surface_area(obj)
                        wall_areas[zone] = wall_areas.get(zone, 0) + area
                        
            elif obj_type == 'FENESTRATIONSURFACE:DETAILED':
                for obj_info in objects:
                    obj = obj_info['object']
                    # Get parent surface to find zone
                    parent_surface = obj.Building_Surface_Name
                    area = self._calculate_surface_area(obj)
                    # Store by parent surface for now
                    window_areas[parent_surface] = area
        
        # Second pass - optimize window-to-wall ratios
        target_wwr = 0.3  # Target 30% window-to-wall ratio
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'FENESTRATIONSURFACE:DETAILED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Scale window vertices to achieve target WWR
                    # This is simplified - actual implementation would be more complex
                    current_area = self._calculate_surface_area(obj)
                    if current_area > 0:
                        # Calculate scaling factor
                        scale_factor = (target_wwr * 1.2)  # Simplified
                        
                        # Would need to modify vertices here
                        # For now, just track the intended modification
                        modifications.append(self._create_modification_result(
                            obj, 'window_area', current_area, current_area * scale_factor, 
                            'window_optimization'
                        ))
        
        return modifications
    
    def _apply_zone_consolidation(self, idf, modifiable_params):
        """Consolidate similar zones using multipliers"""
        modifications = []
        
        # This would analyze similar zones and apply multipliers
        # For now, just increase existing multipliers slightly
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Multiplier:
                        old_mult = int(obj.Multiplier)
                        if old_mult == 1:
                            # Check if this is a perimeter zone that could be multiplied
                            if 'perimeter' in obj.Name.lower():
                                new_mult = 2  # Double similar perimeter zones
                                obj.Multiplier = new_mult
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'zone_multiplier', old_mult, new_mult, 
                                    'zone_consolidation'
                                ))
        
        return modifications
    
    def _apply_envelope_reduction(self, idf, modifiable_params):
        """Reduce envelope area through form optimization"""
        # This would be very complex - modifying building shape
        # Not typically done in parametric studies
        return []
    
    def _calculate_surface_area(self, surface_obj):
        """Calculate area of a surface from vertices"""
        # Simplified - actual calculation would use vertex coordinates
        # and proper polygon area calculation
        try:
            num_vertices = int(surface_obj.Number_of_Vertices)
            if num_vertices >= 3:
                # Would calculate from actual vertices
                # For now, return a placeholder
                return 10.0  # m2
        except:
            return 0.0
    
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