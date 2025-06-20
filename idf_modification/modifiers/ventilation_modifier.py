"""
Ventilation system and airflow modifications.

This module handles modifications to ventilation system and airflow modifications.
"""
"""
Ventilation Modifier - Handles ventilation objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class VentilationModifier(BaseModifier):
    """Modifier for ventilation-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize ventilation parameter definitions"""
        self.parameter_definitions = {
            # Design flow rate ventilation
            'design_flow_rate': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Design Flow Rate',
                field_index=4,
                data_type=float,
                units='m3/s',
                performance_impact='ventilation_loads'
            ),
            'flow_per_zone_area': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Flow Rate per Zone Floor Area',
                field_index=5,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.01,
                performance_impact='ventilation_loads'
            ),
            'flow_per_person': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Flow Rate per Person',
                field_index=6,
                data_type=float,
                units='m3/s-person',
                min_value=0.0,
                max_value=0.05,
                performance_impact='iaq'
            ),
            'air_changes_per_hour': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Air Changes per Hour',
                field_index=7,
                data_type=float,
                units='1/hr',
                min_value=0.0,
                max_value=10.0,
                performance_impact='ventilation_loads'
            ),
            'fan_pressure_rise': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Fan Pressure Rise',
                field_index=9,
                data_type=float,
                units='Pa',
                min_value=0.0,
                max_value=1000.0,
                performance_impact='fan_energy'
            ),
            'fan_total_efficiency': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Fan Total Efficiency',
                field_index=10,
                data_type=float,
                min_value=0.1,
                max_value=1.0,
                performance_impact='fan_energy'
            ),
            
            # Outdoor air specification
            'outdoor_air_per_person': ParameterDefinition(
                object_type='DESIGNSPECIFICATION:OUTDOORAIR',
                field_name='Outdoor Air Flow per Person',
                field_index=2,
                data_type=float,
                units='m3/s-person',
                min_value=0.0,
                max_value=0.05,
                performance_impact='outdoor_air_loads'
            ),
            'outdoor_air_per_area': ParameterDefinition(
                object_type='DESIGNSPECIFICATION:OUTDOORAIR',
                field_name='Outdoor Air Flow per Zone Floor Area',
                field_index=3,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.005,
                performance_impact='outdoor_air_loads'
            ),
            'outdoor_air_per_zone': ParameterDefinition(
                object_type='DESIGNSPECIFICATION:OUTDOORAIR',
                field_name='Outdoor Air Flow per Zone',
                field_index=4,
                data_type=float,
                units='m3/s',
                performance_impact='outdoor_air_loads'
            ),
            
            # Natural ventilation
            'opening_area_fraction': ParameterDefinition(
                object_type='ZONEVENTILATION:WINDANDSTACKDRIVENFLOW',
                field_name='Opening Area Fraction',
                field_index=2,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='natural_ventilation'
            ),
            'discharge_coefficient': ParameterDefinition(
                object_type='ZONEVENTILATION:WINDANDSTACKDRIVENFLOW',
                field_name='Discharge Coefficient',
                field_index=11,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='natural_ventilation'
            )
        }
    
    def get_category_name(self) -> str:
        return 'ventilation'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ZONEVENTILATION:DESIGNFLOWRATE',
            'ZONEVENTILATION:WINDANDSTACKDRIVENFLOW',
            'ZONEAIRBALANCE:OUTDOORAIR',
            'ZONECROSSMIXING',
            'ZONEMIXING',
            'DESIGNSPECIFICATION:OUTDOORAIR',
            'DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION',
            'CONTROLLER:MECHANICALVENTILATION',
            'CONTROLLER:OUTDOORAIR',
            'OUTDOORAIR:MIXER',
            'OUTDOORAIR:NODE',
            'AIRFLOWNETWORK:SIMULATIONCONTROL',
            'AIRFLOWNETWORK:MULTIZONE:ZONE',
            'AIRFLOWNETWORK:MULTIZONE:SURFACE'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['ventilation']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply ventilation-specific modifications"""
        
        if strategy == 'demand_controlled_ventilation':
            return self._apply_dcv(idf, modifiable_params)
        elif strategy == 'natural_ventilation':
            return self._apply_natural_ventilation(idf, modifiable_params)
        elif strategy == 'energy_recovery':
            return self._apply_energy_recovery(idf, modifiable_params)
        elif strategy == 'minimum_ventilation':
            return self._apply_minimum_ventilation(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_dcv(self, idf, modifiable_params):
        """Apply demand controlled ventilation"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'DESIGNSPECIFICATION:OUTDOORAIR':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce base ventilation rates (DCV will increase when needed)
                    if obj.Outdoor_Air_Flow_per_Person:
                        old_flow = float(obj.Outdoor_Air_Flow_per_Person)
                        # Reduce to minimum code requirement
                        new_flow = 0.0025  # 2.5 L/s per person minimum
                        obj.Outdoor_Air_Flow_per_Person = new_flow
                        
                        modifications.append(self._create_modification_result(
                            obj, 'outdoor_air_per_person', old_flow, new_flow,
                            'dcv_minimum_rate'
                        ))
                    
                    # Also reduce area-based ventilation
                    if obj.Outdoor_Air_Flow_per_Zone_Floor_Area:
                        old_flow = float(obj.Outdoor_Air_Flow_per_Zone_Floor_Area)
                        new_flow = old_flow * 0.5  # 50% reduction
                        obj.Outdoor_Air_Flow_per_Zone_Floor_Area = new_flow
                        
                        modifications.append(self._create_modification_result(
                            obj, 'outdoor_air_per_area', old_flow, new_flow,
                            'dcv_reduced_base'
                        ))
        
        return modifications
    
    def _apply_natural_ventilation(self, idf, modifiable_params):
        """Enhance natural ventilation"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEVENTILATION:WINDANDSTACKDRIVENFLOW':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase opening area
                    if obj.Opening_Area_Fraction:
                        old_fraction = float(obj.Opening_Area_Fraction)
                        new_fraction = min(old_fraction * 1.5, 0.5)  # 50% increase, max 50%
                        obj.Opening_Area_Fraction = new_fraction
                        
                        modifications.append(self._create_modification_result(
                            obj, 'opening_area_fraction', old_fraction, new_fraction,
                            'enhanced_natural_vent'
                        ))
                    
                    # Improve discharge coefficient
                    if obj.Discharge_Coefficient:
                        old_coef = float(obj.Discharge_Coefficient)
                        new_coef = min(old_coef * 1.2, 0.8)  # 20% improvement
                        obj.Discharge_Coefficient = new_coef
                        
                        modifications.append(self._create_modification_result(
                            obj, 'discharge_coefficient', old_coef, new_coef,
                            'improved_discharge'
                        ))
            
            # Reduce mechanical ventilation when natural is available
            elif obj_type == 'ZONEVENTILATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if hybrid ventilation (has min/max temperature limits)
                    if obj.Minimum_Indoor_Temperature and obj.Maximum_Indoor_Temperature:
                        # This is hybrid - reduce mechanical component
                        if obj.Design_Flow_Rate:
                            old_flow = float(obj.Design_Flow_Rate)
                            new_flow = old_flow * 0.6  # 40% reduction
                            obj.Design_Flow_Rate = new_flow
                            
                            modifications.append(self._create_modification_result(
                                obj, 'design_flow_rate', old_flow, new_flow,
                                'hybrid_ventilation'
                            ))
        
        return modifications
    
    def _apply_energy_recovery(self, idf, modifiable_params):
        """Apply energy recovery ventilation"""
        modifications = []
        
        # For existing ventilation, improve fan efficiency (simulating ERV benefits)
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEVENTILATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve fan efficiency
                    if obj.Fan_Total_Efficiency:
                        old_eff = float(obj.Fan_Total_Efficiency)
                        # ERV reduces fan energy
                        new_eff = min(old_eff * 1.3, 0.85)  # 30% improvement
                        obj.Fan_Total_Efficiency = new_eff
                        
                        modifications.append(self._create_modification_result(
                            obj, 'fan_total_efficiency', old_eff, new_eff,
                            'erv_fan_efficiency'
                        ))
                    
                    # Can maintain higher ventilation rates with ERV
                    if obj.Air_Changes_per_Hour:
                        old_ach = float(obj.Air_Changes_per_Hour)
                        # Increase ventilation without energy penalty
                        new_ach = old_ach * 1.2  # 20% increase
                        obj.Air_Changes_per_Hour = new_ach
                        
                        modifications.append(self._create_modification_result(
                            obj, 'air_changes_per_hour', old_ach, new_ach,
                            'erv_increased_ventilation'
                        ))
        
        return modifications
    
    def _apply_minimum_ventilation(self, idf, modifiable_params):
        """Reduce to minimum code ventilation"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'DESIGNSPECIFICATION:OUTDOORAIR':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to ASHRAE 62.1 minimums
                    if obj.Outdoor_Air_Flow_per_Person:
                        old_flow = float(obj.Outdoor_Air_Flow_per_Person)
                        # 2.5 L/s per person (0.0025 m3/s)
                        new_flow = 0.0025
                        obj.Outdoor_Air_Flow_per_Person = new_flow
                        
                        modifications.append(self._create_modification_result(
                            obj, 'outdoor_air_per_person', old_flow, new_flow,
                            'ashrae_minimum_person'
                        ))
                    
                    if obj.Outdoor_Air_Flow_per_Zone_Floor_Area:
                        old_flow = float(obj.Outdoor_Air_Flow_per_Zone_Floor_Area)
                        # 0.3 L/s-m2 (0.0003 m3/s-m2) for offices
                        new_flow = 0.0003
                        obj.Outdoor_Air_Flow_per_Zone_Floor_Area = new_flow
                        
                        modifications.append(self._create_modification_result(
                            obj, 'outdoor_air_per_area', old_flow, new_flow,
                            'ashrae_minimum_area'
                        ))
            
            elif obj_type == 'ZONEVENTILATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce all ventilation rates by 30%
                    calc_method = obj.Design_Flow_Rate_Calculation_Method
                    
                    if calc_method == 'Flow/Zone' and obj.Design_Flow_Rate:
                        old_flow = float(obj.Design_Flow_Rate)
                        new_flow = old_flow * 0.7
                        obj.Design_Flow_Rate = new_flow
                        
                        modifications.append(self._create_modification_result(
                            obj, 'design_flow_rate', old_flow, new_flow,
                            'minimum_ventilation'
                        ))
                    
                    elif calc_method == 'AirChanges/Hour' and obj.Air_Changes_per_Hour:
                        old_ach = float(obj.Air_Changes_per_Hour)
                        new_ach = old_ach * 0.7
                        obj.Air_Changes_per_Hour = new_ach
                        
                        modifications.append(self._create_modification_result(
                            obj, 'air_changes_per_hour', old_ach, new_ach,
                            'minimum_ventilation'
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