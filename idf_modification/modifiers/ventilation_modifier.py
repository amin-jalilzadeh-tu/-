"""
Ventilation Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class VentilationModifier(BaseModifier):
    """Modifier for ventilation-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize ventilation parameter definitions matching parser field names"""
        self.parameter_definitions = {
            # Mechanical ventilation
            'design_flow_rate': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Design Flow Rate',
                field_index=3,
                data_type=float,
                units='m3/s',
                performance_impact='ventilation_energy'
            ),
            'flow_rate_per_zone_area': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Flow Rate per Zone Floor Area',
                field_index=4,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.01,
                performance_impact='ventilation_energy'
            ),
            'flow_rate_per_person': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Flow Rate per Person',
                field_index=5,
                data_type=float,
                units='m3/s-person',
                min_value=0.0,
                max_value=0.05,
                performance_impact='indoor_air_quality'
            ),
            'air_changes_per_hour': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Air Changes per Hour',
                field_index=6,
                data_type=float,
                units='1/hr',
                min_value=0.0,
                max_value=20.0,
                performance_impact='ventilation_energy'
            ),
            'ventilation_type': ParameterDefinition(
                object_type='ZONEVENTILATION:DESIGNFLOWRATE',
                field_name='Ventilation Type',
                field_index=7,
                data_type=str,
                allowed_values=['Natural', 'Exhaust', 'Intake', 'Balanced'],
                performance_impact='ventilation_effectiveness'
            ),
            
            # Natural ventilation
            'opening_area': ParameterDefinition(
                object_type='AIRFLOWNETWORK:MULTIZONE:SURFACE',
                field_name='Opening Factor or Opening Area',
                field_index=3,
                data_type=float,
                units='m2',
                min_value=0.0,
                max_value=10.0,
                performance_impact='natural_ventilation'
            ),
            'opening_effectiveness': ParameterDefinition(
                object_type='ZONEVENTILATION:WINDANDSTACKOPENAREA',
                field_name='Opening Effectiveness',
                field_index=2,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='natural_ventilation_effectiveness'
            ),
            
            # Outdoor air requirements
            'outdoor_air_flow_per_person': ParameterDefinition(
                object_type='DESIGNSPECIFICATION:OUTDOORAIR',
                field_name='Outdoor Air Flow per Person',
                field_index=2,
                data_type=float,
                units='m3/s-person',
                min_value=0.0,
                max_value=0.05,
                performance_impact='indoor_air_quality'
            ),
            'outdoor_air_flow_per_zone_area': ParameterDefinition(
                object_type='DESIGNSPECIFICATION:OUTDOORAIR',
                field_name='Outdoor Air Flow per Zone Floor Area',
                field_index=3,
                data_type=float,
                units='m3/s-m2',
                min_value=0.0,
                max_value=0.005,
                performance_impact='ventilation_loads'
            ),
            
            # Demand controlled ventilation
            'minimum_co2_concentration': ParameterDefinition(
                object_type='ZONECONTROL:CONTAMINANTCONTROLLER',
                field_name='Carbon Dioxide Setpoint Schedule Name',
                field_index=3,
                data_type=str,
                performance_impact='demand_control_ventilation'
            ),
            
            # Heat recovery
            'sensible_effectiveness': ParameterDefinition(
                object_type='HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT',
                field_name='Sensible Effectiveness at 100% Heating Air Flow',
                field_index=3,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='heat_recovery_efficiency'
            ),
            'latent_effectiveness': ParameterDefinition(
                object_type='HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT',
                field_name='Latent Effectiveness at 100% Heating Air Flow',
                field_index=4,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='heat_recovery_efficiency'
            )
        }
    
    def get_category_name(self) -> str:
        return 'ventilation'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'ZONEVENTILATION:DESIGNFLOWRATE',
            'ZONEVENTILATION:WINDANDSTACKOPENAREA',
            'ZONEAIRBALANCE:OUTDOORAIR',
            'ZONEMIXING',
            'ZONECROSSMIXING',
            'ZONEREFRIGERATEDDOORMIXING',
            'DESIGNSPECIFICATION:OUTDOORAIR',
            'DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION',
            'CONTROLLER:OUTDOORAIR',
            'CONTROLLER:MECHANICALVENTILATION',
            'AIRFLOWNETWORK:MULTIZONE:ZONE',
            'AIRFLOWNETWORK:MULTIZONE:SURFACE',
            'AIRFLOWNETWORK:MULTIZONE:COMPONENT:DETAILEDOPENING',
            'AIRFLOWNETWORK:MULTIZONE:COMPONENT:SIMPLEOPENING',
            'HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT',
            'HEATEXCHANGER:AIRTOAIR:FLATPLATE',
            'ZONECONTROL:CONTAMINANTCONTROLLER'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['ventilation']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply ventilation-specific modifications"""
        
        if strategy == 'demand_controlled':
            return self._apply_demand_controlled_ventilation(parsed_objects, modifiable_params)
        elif strategy == 'natural_ventilation':
            return self._apply_natural_ventilation(parsed_objects, modifiable_params)
        elif strategy == 'heat_recovery':
            return self._apply_heat_recovery_ventilation(parsed_objects, modifiable_params)
        elif strategy == 'covid_mitigation':
            return self._apply_covid_mitigation(parsed_objects, modifiable_params)
        elif strategy == 'energy_recovery':
            return self._apply_energy_recovery(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_demand_controlled_ventilation(self, parsed_objects, modifiable_params):
        """Apply demand-controlled ventilation strategies"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'DESIGNSPECIFICATION:OUTDOORAIR':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce base ventilation rates for DCV
                    # Minimum rates with sensors
                    for param in obj.parameters:
                        if param.field_name == 'Outdoor Air Flow per Person':
                            old_value = param.numeric_value or float(param.value)
                            # Reduce to minimum with DCV (2.5 L/s per person)
                            new_value = 0.0025  # m3/s per person
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'outdoor_air_flow_per_person', old_value, new_value, 'demand_controlled'
                            ))
                            break
                    
                    # Also reduce area-based ventilation
                    for param in obj.parameters:
                        if param.field_name == 'Outdoor Air Flow per Zone Floor Area':
                            old_value = param.numeric_value or float(param.value)
                            # Minimal area-based rate with DCV
                            new_value = 0.0003  # m3/s-m2
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'outdoor_air_flow_per_zone_area', old_value, new_value, 'demand_controlled'
                            ))
                            break
        
        return modifications
    
    def _apply_natural_ventilation(self, parsed_objects, modifiable_params):
        """Enhance natural ventilation capabilities"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEVENTILATION:WINDANDSTACKOPENAREA':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase opening effectiveness
                    for param in obj.parameters:
                        if param.field_name == 'Opening Effectiveness':
                            old_value = param.numeric_value or float(param.value)
                            # High effectiveness for optimized openings
                            new_value = random.uniform(0.65, 0.85)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'opening_effectiveness', old_value, new_value, 'natural_ventilation'
                            ))
                            break
            
            elif obj_type == 'AIRFLOWNETWORK:MULTIZONE:SURFACE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase opening areas for better natural ventilation
                    for param in obj.parameters:
                        if param.field_name == 'Opening Factor or Opening Area':
                            old_value = param.numeric_value or float(param.value)
                            # Increase by 20-50%
                            increase = random.uniform(1.2, 1.5)
                            new_value = min(old_value * increase, 5.0)  # Cap at 5 m2
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'opening_area', old_value, new_value, 'natural_ventilation'
                            ))
                            break
        
        return modifications
    
    def _apply_heat_recovery_ventilation(self, parsed_objects, modifiable_params):
        """Apply heat recovery ventilation improvements"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve sensible effectiveness
                    for param in obj.parameters:
                        if 'Sensible Effectiveness' in param.field_name and 'Heating' in param.field_name:
                            old_value = param.numeric_value or float(param.value)
                            # High efficiency HRV: 75-85%
                            import random
                            new_value = random.uniform(0.75, 0.85)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'sensible_effectiveness', old_value, new_value, 'heat_recovery'
                            ))
                            break
                    
                    # Improve latent effectiveness
                    for param in obj.parameters:
                        if 'Latent Effectiveness' in param.field_name and 'Heating' in param.field_name:
                            old_value = param.numeric_value or float(param.value)
                            # ERV with good moisture recovery: 65-75%
                            new_value = random.uniform(0.65, 0.75)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'latent_effectiveness', old_value, new_value, 'heat_recovery'
                            ))
                            break
        
        return modifications
    
    def _apply_covid_mitigation(self, parsed_objects, modifiable_params):
        """Apply COVID-19 mitigation ventilation strategies"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEVENTILATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase air changes for pathogen dilution
                    for param in obj.parameters:
                        if param.field_name == 'Air Changes per Hour':
                            old_value = param.numeric_value or float(param.value)
                            # CDC recommendation: 6+ ACH
                            import random
                            new_value = random.uniform(6, 10)
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'air_changes_per_hour', old_value, new_value, 'covid_mitigation'
                            ))
                            break
            
            elif obj_type == 'DESIGNSPECIFICATION:OUTDOORAIR':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Maximize outdoor air
                    for param in obj.parameters:
                        if param.field_name == 'Outdoor Air Flow per Person':
                            old_value = param.numeric_value or float(param.value)
                            # High outdoor air rate: 10-15 L/s per person
                            new_value = random.uniform(0.01, 0.015)  # m3/s per person
                            
                            param.value = str(new_value)
                            param.numeric_value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'outdoor_air_flow_per_person', old_value, new_value, 'covid_mitigation'
                            ))
                            break
        
        return modifications
    
    def _apply_energy_recovery(self, parsed_objects, modifiable_params):
        """Apply energy recovery ventilation strategies"""
        modifications = []
        
        # First apply heat recovery improvements
        modifications.extend(self._apply_heat_recovery_ventilation(parsed_objects, modifiable_params))
        
        # Additionally optimize ventilation rates for energy efficiency
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'ZONEVENTILATION:DESIGNFLOWRATE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to balanced ventilation for ERV
                    for param in obj.parameters:
                        if param.field_name == 'Ventilation Type':
                            old_value = param.value
                            new_value = 'Balanced'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'ventilation_type', old_value, new_value, 'energy_recovery'
                            ))
                            break
        
        return modifications