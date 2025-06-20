"""
Equipment and appliance modifications.

This module handles modifications to equipment and appliance modifications.
"""
"""
Equipment Modifier - Handles electrical and other equipment
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class EquipmentModifier(BaseModifier):
    """Modifier for equipment-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize equipment parameter definitions"""
        self.parameter_definitions = {
            'design_level': ParameterDefinition(
                object_type='ELECTRICEQUIPMENT',
                field_name='Design Level',
                field_index=4,
                data_type=float,
                units='W',
                performance_impact='plug_loads'
            ),
            'watts_per_area': ParameterDefinition(
                object_type='ELECTRICEQUIPMENT',
                field_name='Watts per Zone Floor Area',
                field_index=5,
                data_type=float,
                units='W/m2',
                min_value=0.0,
                max_value=50.0,
                performance_impact='plug_loads'
            ),
            'watts_per_person': ParameterDefinition(
                object_type='ELECTRICEQUIPMENT',
                field_name='Watts per Person',
                field_index=6,
                data_type=float,
                units='W/person',
                min_value=0.0,
                max_value=500.0,
                performance_impact='plug_loads'
            ),
            'fraction_latent': ParameterDefinition(
                object_type='ELECTRICEQUIPMENT',
                field_name='Fraction Latent',
                field_index=7,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            ),
            'fraction_radiant': ParameterDefinition(
                object_type='ELECTRICEQUIPMENT',
                field_name='Fraction Radiant',
                field_index=8,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            ),
            'fraction_lost': ParameterDefinition(
                object_type='ELECTRICEQUIPMENT',
                field_name='Fraction Lost',
                field_index=9,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='zone_loads'
            ),
            'gas_design_level': ParameterDefinition(
                object_type='GASEQUIPMENT',
                field_name='Design Level',
                field_index=4,
                data_type=float,
                units='W',
                performance_impact='gas_loads'
            ),
            'exterior_design_level': ParameterDefinition(
                object_type='EXTERIOREQUIPMENT',
                field_name='Design Level',
                field_index=2,
                data_type=float,
                units='W',
                performance_impact='exterior_loads'
            )
        }
    
    def get_category_name(self) -> str:
        return 'equipment'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ELECTRICEQUIPMENT',
            'GASEQUIPMENT',
            'HOTWATEREQUIPMENT',
            'STEAMEQUIPMENT',
            'OTHEREQUIPMENT',
            'EXTERIOREQUIPMENT',
            'EXTERIOR:LIGHTS',
            'REFRIGERATION:SYSTEM',
            'REFRIGERATION:COMPRESSORRACK'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['equipment']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply equipment-specific modifications"""
        
        if strategy == 'energy_star':
            return self._apply_energy_star_equipment(idf, modifiable_params)
        elif strategy == 'plug_load_reduction':
            return self._apply_plug_load_reduction(idf, modifiable_params)
        elif strategy == 'schedule_optimization':
            return self._apply_schedule_optimization(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_energy_star_equipment(self, idf, modifiable_params):
        """Upgrade to Energy Star equipment"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ELECTRICEQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check calculation method
                    calc_method = obj.Design_Level_Calculation_Method
                    
                    # Reduce equipment power by 20-35% for Energy Star
                    import random
                    reduction = random.uniform(0.20, 0.35)
                    
                    if calc_method == 'EquipmentLevel' and obj.Design_Level:
                        old_level = float(obj.Design_Level)
                        new_level = old_level * (1 - reduction)
                        obj.Design_Level = new_level
                        param_name = 'design_level'
                        
                        modifications.append(self._create_modification_result(
                            obj, param_name, old_level, new_level, 'energy_star_upgrade'
                        ))
                        
                    elif calc_method == 'Watts/Area' and obj.Watts_per_Zone_Floor_Area:
                        old_wpf = float(obj.Watts_per_Zone_Floor_Area)
                        new_wpf = old_wpf * (1 - reduction)
                        obj.Watts_per_Zone_Floor_Area = new_wpf
                        param_name = 'watts_per_area'
                        
                        modifications.append(self._create_modification_result(
                            obj, param_name, old_wpf, new_wpf, 'energy_star_upgrade'
                        ))
                        
                    elif calc_method == 'Watts/Person' and obj.Watts_per_Person:
                        old_wpp = float(obj.Watts_per_Person)
                        new_wpp = old_wpp * (1 - reduction)
                        obj.Watts_per_Person = new_wpp
                        param_name = 'watts_per_person'
                        
                        modifications.append(self._create_modification_result(
                            obj, param_name, old_wpp, new_wpp, 'energy_star_upgrade'
                        ))
        
        return modifications
    
    def _apply_plug_load_reduction(self, idf, modifiable_params):
        """Apply plug load reduction strategies"""
        modifications = []
        
        # Reduce both power and adjust load fractions
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ELECTRICEQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce plug loads
                    modifications.extend(self._reduce_equipment_power(obj, 0.15, 0.25, 'plug_load_management'))
                    
                    # Also adjust fractions for more efficient equipment
                    if obj.Fraction_Lost:
                        old_lost = float(obj.Fraction_Lost)
                        # Reduce losses by 50%
                        new_lost = old_lost * 0.5
                        obj.Fraction_Lost = new_lost
                        
                        # Redistribute to radiant
                        if obj.Fraction_Radiant:
                            old_radiant = float(obj.Fraction_Radiant)
                            obj.Fraction_Radiant = old_radiant + (old_lost - new_lost)
                        
                        modifications.append(self._create_modification_result(
                            obj, 'fraction_lost', old_lost, new_lost, 'efficient_equipment'
                        ))
        
        return modifications
    
    def _apply_schedule_optimization(self, idf, modifiable_params):
        """Optimize equipment schedules"""
        # This would modify schedules, not equipment values directly
        # For now, return empty - schedule modification is handled separately
        return []
    
    def _reduce_equipment_power(self, obj, min_reduction, max_reduction, rule):
        """Helper to reduce equipment power"""
        modifications = []
        import random
        reduction = random.uniform(min_reduction, max_reduction)
        
        calc_method = obj.Design_Level_Calculation_Method
        
        if calc_method == 'EquipmentLevel' and obj.Design_Level:
            old_value = float(obj.Design_Level)
            new_value = old_value * (1 - reduction)
            obj.Design_Level = new_value
            modifications.append(self._create_modification_result(
                obj, 'design_level', old_value, new_value, rule
            ))
            
        elif calc_method == 'Watts/Area' and obj.Watts_per_Zone_Floor_Area:
            old_value = float(obj.Watts_per_Zone_Floor_Area)
            new_value = old_value * (1 - reduction)
            obj.Watts_per_Zone_Floor_Area = new_value
            modifications.append(self._create_modification_result(
                obj, 'watts_per_area', old_value, new_value, rule
            ))
            
        elif calc_method == 'Watts/Person' and obj.Watts_per_Person:
            old_value = float(obj.Watts_per_Person)
            new_value = old_value * (1 - reduction)
            obj.Watts_per_Person = new_value
            modifications.append(self._create_modification_result(
                obj, 'watts_per_person', old_value, new_value, rule
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