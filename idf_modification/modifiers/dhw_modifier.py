"""
Domestic Hot Water (DHW) system modifications.

This module handles modifications to domestic hot water (dhw) system modifications.
"""
"""
DHW (Domestic Hot Water) Modifier - Handles water heating objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class DHWModifier(BaseModifier):
    """Modifier for domestic hot water related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize DHW parameter definitions"""
        self.parameter_definitions = {
            'tank_volume': ParameterDefinition(
                object_type='WATERHEATER:MIXED',
                field_name='Tank Volume',
                field_index=1,
                data_type=float,
                units='m3',
                min_value=0.1,
                max_value=10.0,
                performance_impact='dhw_capacity'
            ),
            'setpoint_temperature': ParameterDefinition(
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
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply DHW-specific modifications"""
        
        if strategy == 'high_efficiency_water_heater':
            return self._apply_high_efficiency_heater(idf, modifiable_params)
        elif strategy == 'heat_pump_water_heater':
            return self._apply_heat_pump_conversion(idf, modifiable_params)
        elif strategy == 'temperature_optimization':
            return self._apply_temperature_optimization(idf, modifiable_params)
        elif strategy == 'demand_reduction':
            return self._apply_demand_reduction(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_high_efficiency_heater(self, idf, modifiable_params):
        """Upgrade to high efficiency water heater"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERHEATER:MIXED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve efficiency
                    if obj.Heater_Thermal_Efficiency:
                        old_eff = float(obj.Heater_Thermal_Efficiency)
                        new_eff = min(0.95, old_eff * 1.15)  # 15% improvement, max 95%
                        obj.Heater_Thermal_Efficiency = new_eff
                        
                        modifications.append(self._create_modification_result(
                            obj, 'heater_efficiency', old_eff, new_eff, 'high_efficiency_upgrade'
                        ))
                    
                    # Reduce standby losses
                    if obj.Off_Cycle_Loss_Coefficient_to_Ambient_Temperature:
                        old_loss = float(obj.Off_Cycle_Loss_Coefficient_to_Ambient_Temperature)
                        new_loss = old_loss * 0.5  # 50% reduction in standby losses
                        obj.Off_Cycle_Loss_Coefficient_to_Ambient_Temperature = new_loss
                        
                        modifications.append(self._create_modification_result(
                            obj, 'off_cycle_loss_coefficient', old_loss, new_loss, 'improved_insulation'
                        ))
        
        return modifications
    
    def _apply_temperature_optimization(self, idf, modifiable_params):
        """Optimize DHW temperature setpoints"""
        modifications = []
        
        # This would modify temperature schedules
        # For now, adjust deadband for better efficiency
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERHEATER:MIXED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Deadband_Temperature_Difference:
                        old_db = float(obj.Deadband_Temperature_Difference)
                        # Increase deadband to reduce cycling
                        new_db = min(5.0, old_db * 1.5)
                        obj.Deadband_Temperature_Difference = new_db
                        
                        modifications.append(self._create_modification_result(
                            obj, 'deadband_temperature', old_db, new_db, 'reduce_cycling'
                        ))
        
        return modifications
    
    def _apply_demand_reduction(self, idf, modifiable_params):
        """Reduce hot water demand"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERUSE:EQUIPMENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Peak_Flow_Rate:
                        old_flow = float(obj.Peak_Flow_Rate)
                        # Reduce flow by 20-30% (low-flow fixtures)
                        import random
                        reduction = random.uniform(0.2, 0.3)
                        new_flow = old_flow * (1 - reduction)
                        obj.Peak_Flow_Rate = new_flow
                        
                        modifications.append(self._create_modification_result(
                            obj, 'use_flow_rate', old_flow, new_flow, 'low_flow_fixtures'
                        ))
        
        return modifications
    
    def _apply_heat_pump_conversion(self, idf, modifiable_params):
        """Convert to heat pump water heater"""
        # This would be more complex - changing object types
        # For now, improve efficiency significantly
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WATERHEATER:MIXED':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Heat pump water heaters have COP of 2-3
                    if obj.Heater_Thermal_Efficiency:
                        old_eff = float(obj.Heater_Thermal_Efficiency)
                        # Simulate heat pump by setting very high efficiency
                        new_eff = min(0.99, old_eff * 2.5)
                        obj.Heater_Thermal_Efficiency = new_eff
                        
                        modifications.append(self._create_modification_result(
                            obj, 'heater_efficiency', old_eff, new_eff, 'heat_pump_conversion'
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