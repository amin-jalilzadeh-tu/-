"""
Equipment Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class EquipmentModifier(BaseModifier):
    """Modifier for equipment-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize equipment parameter definitions matching parser field names"""
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
            'fuel_type': ParameterDefinition(
                object_type='FUELEQUIPMENT',
                field_name='Fuel Type',
                field_index=10,
                data_type=str,
                allowed_values=['Electricity', 'NaturalGas', 'PropaneGas', 
                               'FuelOilNo1', 'FuelOilNo2', 'Coal', 'Diesel', 
                               'Gasoline', 'OtherFuel1', 'OtherFuel2'],
                performance_impact='fuel_use'
            )
        }
    
    def get_category_name(self) -> str:
        return 'equipment'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ELECTRICEQUIPMENT',
            'FUELEQUIPMENT',
            'HOTWAREREQUIPMENT',
            'STEAMEQUIPMENT',
            'OTHEREQU IPMENT'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['equipment']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply equipment-specific modifications"""
        
        if strategy == 'efficient_equipment':
            return self._apply_efficient_equipment(parsed_objects, modifiable_params)
        elif strategy == 'energy_star':
            return self._apply_energy_star_standards(parsed_objects, modifiable_params)
        elif strategy == 'plug_load_reduction':
            return self._apply_plug_load_reduction(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_efficient_equipment(self, parsed_objects, modifiable_params):
        """Apply efficient equipment upgrades"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ELECTRICEQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce equipment power by 15-30%
                    modifications.extend(self._reduce_equipment_power_parsed(
                        obj, 0.15, 0.30, 'efficient_equipment'
                    ))
        
        return modifications
    
    def _apply_energy_star_standards(self, parsed_objects, modifiable_params):
        """Apply Energy Star equipment standards"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ELECTRICEQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Energy Star typically reduces consumption by 20-50%
                    modifications.extend(self._reduce_equipment_power_parsed(
                        obj, 0.20, 0.50, 'energy_star'
                    ))
        
        return modifications
    
    def _apply_plug_load_reduction(self, parsed_objects, modifiable_params):
        """Apply plug load reduction strategies"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ELECTRICEQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Smart power strips and controls reduce loads by 10-25%
                    modifications.extend(self._reduce_equipment_power_parsed(
                        obj, 0.10, 0.25, 'plug_load_reduction'
                    ))
                    
                    # Also adjust fractions to represent better equipment
                    for param in obj.parameters:
                        if param.field_name == 'Fraction Lost':
                            old_value = param.numeric_value or float(param.value)
                            # Reduce lost fraction by 30-50%
                            reduction = random.uniform(0.3, 0.5)
                            new_value = old_value * (1 - reduction)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'fraction_lost', old_value, new_value, 'plug_load_reduction'
                            ))
                            break
        
        return modifications
    
    def _reduce_equipment_power_parsed(self, obj, min_reduction, max_reduction, rule):
        """Helper to reduce equipment power in parsed objects"""
        modifications = []
        import random
        reduction = random.uniform(min_reduction, max_reduction)
        
        # Find the calculation method parameter (usually index 3)
        calc_method = None
        if len(obj.parameters) > 3:
            calc_method_param = obj.parameters[3]
            calc_method = calc_method_param.value
        
        # Based on calculation method, modify appropriate parameter
        if calc_method == 'EquipmentLevel':
            # Modify Design Level
            for param in obj.parameters:
                if param.field_name == 'Design Level' and param.numeric_value:
                    old_value = param.numeric_value
                    new_value = old_value * (1 - reduction)
                    
                    param.value = str(new_value)
                    param.numeric_value = new_value
                    
                    modifications.append(self._create_modification_result(
                        obj, 'design_level', old_value, new_value, rule
                    ))
                    break
                    
        elif calc_method == 'Watts/Area':
            # Modify Watts per Zone Floor Area
            for param in obj.parameters:
                if param.field_name == 'Watts per Zone Floor Area' and param.numeric_value:
                    old_value = param.numeric_value
                    new_value = old_value * (1 - reduction)
                    
                    param.value = str(new_value)
                    param.numeric_value = new_value
                    
                    modifications.append(self._create_modification_result(
                        obj, 'watts_per_area', old_value, new_value, rule
                    ))
                    break
                    
        elif calc_method == 'Watts/Person':
            # Modify Watts per Person
            for param in obj.parameters:
                if param.field_name == 'Watts per Person' and param.numeric_value:
                    old_value = param.numeric_value
                    new_value = old_value * (1 - reduction)
                    
                    param.value = str(new_value)
                    param.numeric_value = new_value
                    
                    modifications.append(self._create_modification_result(
                        obj, 'watts_per_person', old_value, new_value, rule
                    ))
                    break
        
        return modifications