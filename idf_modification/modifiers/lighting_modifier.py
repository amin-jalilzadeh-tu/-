"""
Lighting system and control modifications.

This module handles modifications to lighting system and control modifications.
"""
"""
Lighting Modifier - Handles lighting objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class LightingModifier(BaseModifier): 
    """Modifier for lighting-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize lighting parameter definitions"""
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
            'fraction_radiant': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Fraction Radiant',
                field_index=8,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            ),
            'fraction_visible': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Fraction Visible',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=1.0
            ),
            'return_air_fraction': ParameterDefinition(
                object_type='LIGHTS',
                field_name='Return Air Fraction',
                field_index=7,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            )
        }
    
    def get_category_name(self) -> str:
        return 'lighting'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'LIGHTS',
            'DAYLIGHTING:CONTROLS',
            'DAYLIGHTING:REFERENCEPOINT',
            'EXTERIORLIGHTS'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['lighting']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply lighting-specific modifications"""
        
        if strategy == 'led_retrofit':
            return self._apply_led_retrofit(idf, modifiable_params)
        elif strategy == 'occupancy_controls':
            return self._apply_occupancy_controls(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_led_retrofit(self, idf, modifiable_params):
        """Apply LED retrofit modifications"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'LIGHTS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check calculation method
                    if obj.Design_Level_Calculation_Method == 'Watts/Area':
                        current_wpf = float(obj.Watts_per_Zone_Floor_Area) if obj.Watts_per_Zone_Floor_Area else 0
                        
                        if current_wpf > 0:
                            # LED reduces by 40-60%
                            import random
                            reduction = random.uniform(0.4, 0.6)
                            new_wpf = current_wpf * (1 - reduction)
                            
                            obj.Watts_per_Zone_Floor_Area = new_wpf
                            
                            # Also update fractions for LED characteristics
                            obj.Fraction_Radiant = 0.72  # Less radiant for LED
                            obj.Fraction_Visible = 0.20  # Higher visible fraction
                            
                            modifications.append(self._create_modification_result(
                                obj, 'watts_per_area', current_wpf, new_wpf, 'led_retrofit'
                            ))
        
        return modifications
    
    def _apply_occupancy_controls(self, idf, modifiable_params):
        """Apply occupancy-based controls"""
        # This would modify schedules or add controls
        return []
    
    def _create_modification_result(self, obj, param_name, old_value, new_value, rule):
        """Helper to create modification result"""
        from ..base_modifier import ModificationResult
        
        return ModificationResult(
            success=True,
            object_type=obj.obj[0],
            object_name=obj.Name,
            parameter=param_name,
            original_value=old_value,
            new_value=new_value,
            change_type='absolute',
            rule_applied=rule,
            validation_status='valid'
        )