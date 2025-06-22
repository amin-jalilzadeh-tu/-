"""
HVAC Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
import pandas as pd
from ..base_modifier import BaseModifier, ParameterDefinition

class HVACModifier(BaseModifier):
    """Modifier for HVAC-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize HVAC parameter definitions matching parser field names"""
        self.parameter_definitions = {
            # Cooling coil parameters
            'cooling_capacity': ParameterDefinition(
                object_type='COIL:COOLING:DX:SINGLESPEED',
                field_name='Gross Rated Total Cooling Capacity',
                field_index=4,  # Adjusted based on typical position
                data_type=float,
                units='W',
                min_value=1000,
                max_value=100000,
                performance_impact='cooling_energy'
            ),
            'cooling_cop': ParameterDefinition(
                object_type='COIL:COOLING:DX:SINGLESPEED',
                field_name='Rated COP',
                field_index=8,  # Adjusted based on typical position
                data_type=float,
                units='W/W',
                min_value=2.0,
                max_value=6.0,
                performance_impact='cooling_efficiency'
            ),
            
            # Heating coil parameters
            'heating_capacity': ParameterDefinition(
                object_type='COIL:HEATING:ELECTRIC',
                field_name='Nominal Capacity',
                field_index=1,  # Adjusted based on typical position
                data_type=float,
                units='W',
                min_value=1000,
                max_value=50000,
                performance_impact='heating_energy'
            ),
            'heating_efficiency': ParameterDefinition(
                object_type='COIL:HEATING:ELECTRIC',
                field_name='Efficiency',
                field_index=2,
                data_type=float,
                units='',
                min_value=0.8,
                max_value=1.0,
                performance_impact='heating_efficiency'
            ),
            
            # Fan parameters
            'fan_efficiency': ParameterDefinition(
                object_type='FAN:VARIABLEVOLUME',
                field_name='Fan Total Efficiency',
                field_index=5,
                data_type=float,
                units='',
                min_value=0.5,
                max_value=0.9,
                performance_impact='fan_energy'
            ),
            'fan_pressure_rise': ParameterDefinition(
                object_type='FAN:VARIABLEVOLUME',
                field_name='Pressure Rise',
                field_index=3,
                data_type=float,
                units='Pa',
                min_value=100,
                max_value=2000,
                performance_impact='fan_energy'
            ),
            
            # Thermostat setpoints
            'heating_setpoint': ParameterDefinition(
                object_type='THERMOSTATSETPOINT:DUALSETPOINT',
                field_name='Heating Setpoint Temperature Schedule Name',
                field_index=0,
                data_type=str,
                performance_impact='heating_energy'
            ),
            'cooling_setpoint': ParameterDefinition(
                object_type='THERMOSTATSETPOINT:DUALSETPOINT',
                field_name='Cooling Setpoint Temperature Schedule Name',
                field_index=1,
                data_type=str,
                performance_impact='cooling_energy'
            ),
            
            # Chiller parameters
            'chiller_cop': ParameterDefinition(
                object_type='CHILLER:ELECTRIC:EIR',
                field_name='Reference COP',
                field_index=2,
                data_type=float,
                units='W/W',
                min_value=3.0,
                max_value=7.0,
                performance_impact='cooling_efficiency'
            ),
            
            # Boiler parameters
            'boiler_efficiency': ParameterDefinition(
                object_type='BOILER:HOTWATER',
                field_name='Nominal Thermal Efficiency',
                field_index=4,
                data_type=float,
                units='',
                min_value=0.7,
                max_value=0.99,
                performance_impact='heating_efficiency'
            )
        }
    
    def get_category_name(self) -> str:
        return 'hvac'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'HVACTEMPLATE:SYSTEM:VAV',
            'HVACTEMPLATE:SYSTEM:PACKAGEDVAV',
            'HVACTEMPLATE:SYSTEM:UNITARY',
            'COIL:COOLING:DX:SINGLESPEED',
            'COIL:COOLING:DX:TWOSPEED',
            'COIL:COOLING:DX:VARIABLESPEED',
            'COIL:HEATING:ELECTRIC',
            'COIL:HEATING:GAS',
            'COIL:HEATING:DX:SINGLESPEED',
            'FAN:VARIABLEVOLUME',
            'FAN:CONSTANTVOLUME',
            'FAN:ONOFF',
            'PUMP:VARIABLESPEED',
            'PUMP:CONSTANTSPEED',
            'CHILLER:ELECTRIC:EIR',
            'CHILLER:ELECTRIC:REFORMULATEDEIR',
            'BOILER:HOTWATER',
            'BOILER:STEAM',
            'THERMOSTATSETPOINT:DUALSETPOINT',
            'THERMOSTATSETPOINT:SINGLEHEATING',
            'THERMOSTATSETPOINT:SINGLECOOLING',
            'AIRTERMINAL:SINGLEDUCT:VAV:REHEAT',
            'AIRTERMINAL:SINGLEDUCT:VAV:NOREHEAT',
            'ZONEHVAC:PACKAGEDTERMINALAIRCONDITIONER',
            'ZONEHVAC:PACKAGEDTERMINALHEATPUMP'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['hvac_equipment', 'hvac_systems', 'hvac_thermostats']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply HVAC-specific modifications"""
        
        if strategy == 'high_efficiency':
            return self._apply_high_efficiency_upgrades(parsed_objects, modifiable_params)
        elif strategy == 'setpoint_optimization':
            return self._apply_setpoint_optimization(parsed_objects, modifiable_params)
        elif strategy == 'variable_speed':
            return self._apply_variable_speed_upgrades(parsed_objects, modifiable_params)
        elif strategy == 'heat_recovery':
            return self._apply_heat_recovery(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_high_efficiency_upgrades(self, parsed_objects, modifiable_params):
        """Apply high efficiency equipment upgrades"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            # Cooling equipment
            if 'COOLING' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve COP
                    for param in obj.parameters:
                        if 'COP' in param.field_name.upper():
                            old_cop = param.numeric_value or float(param.value)
                            # Increase COP by 20-40%
                            improvement = random.uniform(1.2, 1.4)
                            new_cop = min(old_cop * improvement, 6.0)  # Cap at 6.0
                            
                            param.value = str(new_cop)
                            param.numeric_value = new_cop
                            
                            modifications.append(self._create_modification_result(
                                obj, 'cooling_cop', old_cop, new_cop, 'high_efficiency'
                            ))
                            break
            
            # Heating equipment
            elif 'HEATING' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve efficiency
                    for param in obj.parameters:
                        if 'EFFICIENCY' in param.field_name.upper():
                            old_eff = param.numeric_value or float(param.value)
                            # Increase efficiency by 10-20%
                            improvement = random.uniform(1.1, 1.2)
                            new_eff = min(old_eff * improvement, 0.99)  # Cap at 99%
                            
                            param.value = str(new_eff)
                            param.numeric_value = new_eff
                            
                            modifications.append(self._create_modification_result(
                                obj, 'heating_efficiency', old_eff, new_eff, 'high_efficiency'
                            ))
                            break
            
            # Fan equipment
            elif 'FAN' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve fan efficiency
                    for param in obj.parameters:
                        if param.field_name == 'Fan Total Efficiency':
                            old_eff = param.numeric_value or float(param.value)
                            # High efficiency fans can reach 85-90%
                            new_eff = random.uniform(0.85, 0.90)
                            
                            param.value = str(new_eff)
                            param.numeric_value = new_eff
                            
                            modifications.append(self._create_modification_result(
                                obj, 'fan_efficiency', old_eff, new_eff, 'high_efficiency'
                            ))
                            break
        
        return modifications
    
    def _apply_setpoint_optimization(self, parsed_objects, modifiable_params):
        """Optimize thermostat setpoints for energy savings"""
        modifications = []
        
        # This would typically modify schedule values
        # For now, we'll note that schedule modifications would be handled differently
        for obj_type, objects in modifiable_params.items():
            if 'THERMOSTATSETPOINT' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Note: Actual setpoint changes would require modifying the referenced schedules
                    # This is a placeholder to show the structure
                    modifications.append(ModificationResult(
                        success=True,
                        object_type=obj.object_type,
                        object_name=obj.name,
                        parameter='setpoint_schedules',
                        original_value='original_schedules',
                        new_value='optimized_schedules',
                        change_type='schedule_modification',
                        rule_applied='setpoint_optimization',
                        validation_status='valid',
                        message='Setpoint optimization would modify referenced schedule objects'
                    ))
        
        return modifications
    
    def _apply_variable_speed_upgrades(self, parsed_objects, modifiable_params):
        """Convert constant speed equipment to variable speed"""
        modifications = []
        
        # This would typically involve changing object types
        # For demonstration, we'll improve efficiency of existing equipment
        for obj_type, objects in modifiable_params.items():
            if 'PUMP' in obj_type or 'FAN' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Variable speed equipment is more efficient
                    for param in obj.parameters:
                        if 'EFFICIENCY' in param.field_name.upper():
                            old_eff = param.numeric_value or float(param.value)
                            # Variable speed improves efficiency by 15-25%
                            import random
                            improvement = random.uniform(1.15, 1.25)
                            new_eff = min(old_eff * improvement, 0.95)
                            
                            param.value = str(new_eff)
                            param.numeric_value = new_eff
                            
                            modifications.append(self._create_modification_result(
                                obj, 'efficiency', old_eff, new_eff, 'variable_speed'
                            ))
                            break
        
        return modifications
    
    def _apply_heat_recovery(self, parsed_objects, modifiable_params):
        """Apply heat recovery modifications"""
        modifications = []
        
        # Heat recovery typically requires adding new objects
        # For existing equipment, we can improve efficiency to simulate recovery benefits
        for obj_type, objects in modifiable_params.items():
            if 'COIL' in obj_type or 'CHILLER' in obj_type:
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Heat recovery effectively improves system efficiency
                    for param in obj.parameters:
                        if any(term in param.field_name.upper() for term in ['COP', 'EFFICIENCY']):
                            old_value = param.numeric_value or float(param.value)
                            # Heat recovery can improve efficiency by 10-20%
                            import random
                            improvement = random.uniform(1.1, 1.2)
                            
                            if 'COP' in param.field_name.upper():
                                new_value = min(old_value * improvement, 7.0)
                            else:
                                new_value = min(old_value * improvement, 0.99)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, param.field_name.lower().replace(' ', '_'), 
                                old_value, new_value, 'heat_recovery'
                            ))
                            break
        
        return modifications