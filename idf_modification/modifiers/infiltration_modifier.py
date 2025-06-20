"""
Air infiltration and leakage modifications.

This module handles modifications to air infiltration and leakage modifications.
"""
"""
Infiltration Modifier - Handles infiltration objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class InfiltrationModifier(BaseModifier):
    """Modifier for infiltration-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize infiltration parameter definitions"""
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
                field_name='Flow Rate per Floor Area',
                field_index=5,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.01,
                performance_impact='infiltration_loads'
            ),
            'flow_per_exterior_area': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Flow Rate per Exterior Surface Area',
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
                max_value=1.0
            ),
            'temperature_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Temperature Term Coefficient',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=0.1
            ),
            'velocity_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Velocity Term Coefficient',
                field_index=10,
                data_type=float,
                min_value=0.0,
                max_value=0.5
            ),
            'velocity_squared_coefficient': ParameterDefinition(
                object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                field_name='Velocity Squared Term Coefficient',
                field_index=11,
                data_type=float,
                min_value=0.0,
                max_value=0.1
            )
        }
    
    def get_category_name(self) -> str:
        return 'infiltration'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ZONEINFILTRATION:DESIGNFLOWRATE',
            'ZONEINFILTRATION:EFFECTIVELEAKAGEAREA',
            'ZONEINFILTRATION:FLOWCOEFFICIENT',
            'SPACEINFILTRATION:DESIGNFLOWRATE',
            'SPACEINFILTRATION:EFFECTIVELEAKAGEAREA',
            'SPACEINFILTRATION:FLOWCOEFFICIENT'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['infiltration']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply infiltration-specific modifications"""
        
        if strategy == 'envelope_tightening':
            return self._apply_envelope_tightening(idf, modifiable_params)
        elif strategy == 'weatherization':
            return self._apply_weatherization(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_envelope_tightening(self, idf, modifiable_params):
        """Apply envelope tightening modifications"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEINFILTRATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check calculation method and modify appropriate field
                    calc_method = obj.Design_Flow_Rate_Calculation_Method
                    
                    # Reduce infiltration by 30-60%
                    import random
                    reduction = random.uniform(0.3, 0.6)
                    
                    modified = False
                    param_name = None
                    old_value = None
                    new_value = None
                    
                    if calc_method == 'Flow/Zone' and obj.Design_Flow_Rate:
                        old_value = float(obj.Design_Flow_Rate)
                        new_value = old_value * (1 - reduction)
                        obj.Design_Flow_Rate = new_value
                        param_name = 'design_flow_rate'
                        modified = True
                        
                    elif calc_method == 'Flow/Area':
                        # Check both possible locations
                        if obj.Flow_Rate_per_Floor_Area:
                            old_value = float(obj.Flow_Rate_per_Floor_Area)
                            new_value = old_value * (1 - reduction)
                            obj.Flow_Rate_per_Floor_Area = new_value
                            param_name = 'flow_per_zone_area'
                            modified = True
                        elif obj.Design_Flow_Rate:  # Sometimes stored in wrong field
                            old_value = float(obj.Design_Flow_Rate)
                            new_value = old_value * (1 - reduction)
                            obj.Design_Flow_Rate = new_value
                            param_name = 'flow_per_zone_area'
                            modified = True
                            
                    elif calc_method == 'AirChanges/Hour' and obj.Air_Changes_per_Hour:
                        old_value = float(obj.Air_Changes_per_Hour)
                        new_value = old_value * (1 - reduction)
                        obj.Air_Changes_per_Hour = new_value
                        param_name = 'air_changes_per_hour'
                        modified = True
                    
                    if modified:
                        from ..base_modifier import ModificationResult
                        result = ModificationResult(
                            success=True,
                            object_type='ZONEINFILTRATION:DESIGNFLOWRATE',
                            object_name=obj.Name,
                            parameter=param_name,
                            original_value=old_value,
                            new_value=new_value,
                            change_type='multiplier',
                            rule_applied='envelope_tightening',
                            validation_status='valid'
                        )
                        modifications.append(result)
                        
                        self.logger.info(f"Reduced infiltration for {obj.Name}: "
                                       f"{old_value} → {new_value} ({reduction:.0%} reduction)")
        
        return modifications
    
    def _apply_weatherization(self, idf, modifiable_params):
        """Apply weatherization improvements"""
        # Similar to envelope tightening but might also modify coefficients
        return self._apply_envelope_tightening(idf, modifiable_params)