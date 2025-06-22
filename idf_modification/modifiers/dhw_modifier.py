"""
DHW (Domestic Hot Water) Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class DHWModifier(BaseModifier):
    """Modifier for domestic hot water related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize DHW parameter definitions matching parser field names"""
        self.parameter_definitions = {
            'tank_volume': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Tank Volume',  # Must match parser's field name exactly
                field_index=1,
                data_type=float,
                units='m3',
                min_value=0.1,
                max_value=10.0,
                performance_impact='dhw_capacity'
            ),
            'setpoint_temperature_schedule': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Setpoint Temperature Schedule Name',
                field_index=2,
                data_type=str,
                performance_impact='dhw_energy'
            ),
            'deadband_temperature': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Deadband Temperature Difference',
                field_index=3,
                data_type=float,
                units='deltaC',
                min_value=0.5,
                max_value=10.0,
                performance_impact='dhw_cycling'
            ),
            'heater_capacity': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Heater Maximum Capacity',
                field_index=6,
                data_type=float,
                units='W',
                min_value=1000,
                max_value=50000,
                performance_impact='dhw_power'
            ),
            'heater_efficiency': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Heater Thermal Efficiency',
                field_index=11,
                data_type=float,
                units='',
                min_value=0.5,
                max_value=1.0,
                performance_impact='dhw_efficiency'
            ),
            'off_cycle_loss_coefficient': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Off Cycle Loss Coefficient to Ambient Temperature',
                field_index=25,
                data_type=float,
                units='W/K',
                min_value=0.0,
                max_value=10.0,
                performance_impact='dhw_standby_loss'
            ),
            'peak_flow_rate': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Peak Use Flow Rate',
                field_index=30,
                data_type=float,
                units='m3/s',
                min_value=0.0,
                max_value=0.01,
                performance_impact='dhw_sizing'
            ),
            'use_flow_rate': ParameterDefinition(
                object_type='WATERUSE:EQUIPMENT',
                field_name='Peak Flow Rate',
                field_index=4,
                data_type=float,
                units='m3/s',
                min_value=0.0,
                max_value=0.001,
                performance_impact='dhw_demand'
            )
        }
    
    def get_category_name(self) -> str:
        return 'dhw'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'WATERHEATER:MIXED',
            'WATERHEATER:STRATIFIED',
            'WATERUSE:EQUIPMENT',
            'WATERUSE:CONNECTIONS',
            'PLANTLOOP',
            'PUMP:VARIABLESPEED',
            'PUMP:CONSTANTSPEED',
            'PIPE:ADIABATIC',
            'PIPE:INDOOR',
            'PIPE:OUTDOOR'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['dhw']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply DHW-specific modifications"""
        
        if strategy == 'efficiency_upgrade':
            return self._apply_efficiency_upgrades(parsed_objects, modifiable_params)
        elif strategy == 'low_flow':
            return self._apply_low_flow_fixtures(parsed_objects, modifiable_params)
        elif strategy == 'heat_pump_conversion':
            return self._apply_heat_pump_conversion(parsed_objects, modifiable_params)
        else:
            # Default strategy - apply standard modifications
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_efficiency_upgrades(self, parsed_objects, modifiable_params):
        """Apply efficiency improvements to water heaters"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERHEATER:MIXED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Find and modify efficiency parameter
                    for param in obj.parameters:
                        if param.field_name == 'Heater Thermal Efficiency':
                            old_eff = param.numeric_value or float(param.value)
                            # Increase efficiency by 10-20%
                            import random
                            improvement = random.uniform(0.1, 0.2)
                            new_eff = min(0.99, old_eff * (1 + improvement))
                            
                            # Update the parameter
                            param.value = str(new_eff)
                            param.numeric_value = new_eff
                            
                            modifications.append(self._create_modification_result(
                                obj, 'heater_efficiency', old_eff, new_eff, 'efficiency_upgrade'
                            ))
                            break
                    
                    # Reduce standby losses
                    for param in obj.parameters:
                        if param.field_name == 'Off Cycle Loss Coefficient to Ambient Temperature':
                            old_loss = param.numeric_value or float(param.value)
                            # Reduce losses by 20-40%
                            reduction = random.uniform(0.2, 0.4)
                            new_loss = old_loss * (1 - reduction)
                            
                            param.value = str(new_loss)
                            param.numeric_value = new_loss
                            
                            modifications.append(self._create_modification_result(
                                obj, 'off_cycle_loss_coefficient', old_loss, new_loss, 'efficiency_upgrade'
                            ))
                            break
        
        return modifications
    
    def _apply_low_flow_fixtures(self, parsed_objects, modifiable_params):
        """Apply low-flow fixture modifications"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERUSE:EQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Find and modify flow rate
                    for param in obj.parameters:
                        if param.field_name == 'Peak Flow Rate':
                            old_flow = param.numeric_value or float(param.value)
                            # Reduce flow by 20-40%
                            import random
                            reduction = random.uniform(0.2, 0.4)
                            new_flow = old_flow * (1 - reduction)
                            
                            param.value = str(new_flow)
                            param.numeric_value = new_flow
                            
                            modifications.append(self._create_modification_result(
                                obj, 'use_flow_rate', old_flow, new_flow, 'low_flow_fixtures'
                            ))
                            break
        
        return modifications
    
    def _apply_heat_pump_conversion(self, parsed_objects, modifiable_params):
        """Convert to heat pump water heater"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERHEATER:MIXED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Heat pump water heaters have COP of 2-3
                    # Simulate by setting very high efficiency
                    for param in obj.parameters:
                        if param.field_name == 'Heater Thermal Efficiency':
                            old_eff = param.numeric_value or float(param.value)
                            # Heat pump equivalent efficiency
                            new_eff = min(0.99, old_eff * 2.5)
                            
                            param.value = str(new_eff)
                            param.numeric_value = new_eff
                            
                            modifications.append(self._create_modification_result(
                                obj, 'heater_efficiency', old_eff, new_eff, 'heat_pump_conversion'
                            ))
                            break
        
        return modifications