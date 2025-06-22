"""
Simulation Control Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class SimulationControlModifier(BaseModifier):
    """Modifier for simulation control related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize simulation control parameter definitions matching parser field names"""
        self.parameter_definitions = {
            # Timestep
            'timesteps_per_hour': ParameterDefinition(
                object_type='TIMESTEP',
                field_name='Number of Timesteps per Hour',
                field_index=0,
                data_type=int,
                min_value=1,
                max_value=60,
                allowed_values=[1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60],
                performance_impact='simulation_accuracy'
            ),
            
            # Shadow calculation
            'shadow_calculation_frequency': ParameterDefinition(
                object_type='SHADOWCALCULATION',
                field_name='Calculation Frequency',
                field_index=0,
                data_type=int,
                min_value=1,
                max_value=365,
                performance_impact='simulation_speed'
            ),
            'maximum_shadow_figures': ParameterDefinition(
                object_type='SHADOWCALCULATION',
                field_name='Maximum Figures in Shadow Overlap Calculations',
                field_index=1,
                data_type=int,
                min_value=200,
                max_value=50000,
                performance_impact='simulation_accuracy'
            ),
            
            # Convergence limits
            'minimum_system_timestep': ParameterDefinition(
                object_type='CONVERGENCELIMITS',
                field_name='Minimum System Timestep',
                field_index=0,
                data_type=float,
                units='minutes',
                min_value=1,
                max_value=60,
                performance_impact='convergence'
            ),
            'maximum_hvac_iterations': ParameterDefinition(
                object_type='CONVERGENCELIMITS',
                field_name='Maximum HVAC Iterations',
                field_index=1,
                data_type=int,
                min_value=1,
                max_value=50,
                performance_impact='convergence'
            ),
            
            # Heat balance algorithm
            'algorithm_type': ParameterDefinition(
                object_type='HEATBALANCEALGORITHM',
                field_name='Algorithm',
                field_index=0,
                data_type=str,
                allowed_values=['ConductionTransferFunction', 'MoisturePenetrationDepthConductionTransferFunction', 
                               'ConductionFiniteDifference', 'CombinedHeatAndMoistureFiniteElement'],
                performance_impact='simulation_method'
            ),
            'surface_temperature_upper_limit': ParameterDefinition(
                object_type='HEATBALANCEALGORITHM',
                field_name='Surface Temperature Upper Limit',
                field_index=1,
                data_type=float,
                units='C',
                min_value=100,
                max_value=300,
                performance_impact='convergence'
            ),
            
            # Building parameters
            'terrain': ParameterDefinition(
                object_type='BUILDING',
                field_name='Terrain',
                field_index=5,
                data_type=str,
                allowed_values=['Country', 'Suburbs', 'City', 'Ocean', 'Urban'],
                performance_impact='wind_calculations'
            ),
            'solar_distribution': ParameterDefinition(
                object_type='BUILDING',
                field_name='Solar Distribution',
                field_index=7,
                data_type=str,
                allowed_values=['MinimalShadowing', 'FullExterior', 'FullInteriorAndExterior', 
                               'FullExteriorWithReflections', 'FullInteriorAndExteriorWithReflections'],
                performance_impact='solar_calculations'
            ),
            
            # Output control
            'output_variable_reporting_frequency': ParameterDefinition(
                object_type='OUTPUT:VARIABLE',
                field_name='Reporting Frequency',
                field_index=2,
                data_type=str,
                allowed_values=['Detailed', 'Timestep', 'Hourly', 'Daily', 'Monthly', 'RunPeriod', 'Environment', 'Annual'],
                performance_impact='output_file_size'
            )
        }
    
    def get_category_name(self) -> str:
        return 'simulation_control'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'SIMULATIONCONTROL',
            'BUILDING',
            'SHADOWCALCULATION',
            'TIMESTEP',
            'CONVERGENCELIMITS',
            'HEATBALANCEALGORITHM',
            'SURFACECONVECTIONALGORITHM:INSIDE',
            'SURFACECONVECTIONALGORITHM:OUTSIDE',
            'ZONECAPACITANCEMULTIPLIER:RESEARCHSPECIAL',
            'OUTPUT:VARIABLE',
            'OUTPUT:METER',
            'OUTPUT:SQLITE',
            'OUTPUTCONTROL:TABLE:STYLE'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['simulation_control']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply simulation control specific modifications"""
        
        if strategy == 'accuracy_focus':
            return self._apply_accuracy_focus(parsed_objects, modifiable_params)
        elif strategy == 'speed_focus':
            return self._apply_speed_focus(parsed_objects, modifiable_params)
        elif strategy == 'detailed_output':
            return self._apply_detailed_output(parsed_objects, modifiable_params)
        elif strategy == 'balanced':
            return self._apply_balanced_settings(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_accuracy_focus(self, parsed_objects, modifiable_params):
        """Apply settings for maximum simulation accuracy"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'TIMESTEP':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set high timesteps per hour for accuracy
                    for param in obj.parameters:
                        if param.field_name == 'Number of Timesteps per Hour':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 10  # 6-minute timesteps for good accuracy
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'timesteps_per_hour', old_value, new_value, 'accuracy_focus'
                            ))
                            break
            
            elif obj_type == 'SHADOWCALCULATION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Frequent shadow calculations
                    for param in obj.parameters:
                        if param.field_name == 'Calculation Frequency':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 7  # Weekly calculations
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shadow_calculation_frequency', old_value, new_value, 'accuracy_focus'
                            ))
                            break
                    
                    # High figure count for complex shading
                    for param in obj.parameters:
                        if param.field_name == 'Maximum Figures in Shadow Overlap Calculations':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 15000  # High figure count
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'maximum_shadow_figures', old_value, new_value, 'accuracy_focus'
                            ))
                            break
            
            elif obj_type == 'BUILDING':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Full solar distribution with reflections
                    for param in obj.parameters:
                        if param.field_name == 'Solar Distribution':
                            old_value = param.value
                            new_value = 'FullInteriorAndExteriorWithReflections'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'solar_distribution', old_value, new_value, 'accuracy_focus'
                            ))
                            break
        
        return modifications
    
    def _apply_speed_focus(self, parsed_objects, modifiable_params):
        """Apply settings for faster simulation speed"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'TIMESTEP':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Lower timesteps for speed
                    for param in obj.parameters:
                        if param.field_name == 'Number of Timesteps per Hour':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 4  # 15-minute timesteps
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'timesteps_per_hour', old_value, new_value, 'speed_focus'
                            ))
                            break
            
            elif obj_type == 'SHADOWCALCULATION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Less frequent shadow calculations
                    for param in obj.parameters:
                        if param.field_name == 'Calculation Frequency':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 30  # Monthly calculations
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shadow_calculation_frequency', old_value, new_value, 'speed_focus'
                            ))
                            break
                    
                    # Lower figure count
                    for param in obj.parameters:
                        if param.field_name == 'Maximum Figures in Shadow Overlap Calculations':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 1000  # Lower figure count
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'maximum_shadow_figures', old_value, new_value, 'speed_focus'
                            ))
                            break
            
            elif obj_type == 'BUILDING':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Simpler solar distribution
                    for param in obj.parameters:
                        if param.field_name == 'Solar Distribution':
                            old_value = param.value
                            new_value = 'FullExterior'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'solar_distribution', old_value, new_value, 'speed_focus'
                            ))
                            break
        
        return modifications
    
    def _apply_detailed_output(self, parsed_objects, modifiable_params):
        """Apply settings for detailed output reporting"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'OUTPUT:VARIABLE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to timestep reporting for maximum detail
                    for param in obj.parameters:
                        if param.field_name == 'Reporting Frequency':
                            old_value = param.value
                            new_value = 'Timestep'
                            
                            param.value = new_value
                            
                            modifications.append(self._create_modification_result(
                                obj, 'output_variable_reporting_frequency', old_value, new_value, 'detailed_output'
                            ))
                            break
        
        return modifications
    
    def _apply_balanced_settings(self, parsed_objects, modifiable_params):
        """Apply balanced settings for accuracy and speed"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'TIMESTEP':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Balanced timesteps
                    for param in obj.parameters:
                        if param.field_name == 'Number of Timesteps per Hour':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 6  # 10-minute timesteps
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'timesteps_per_hour', old_value, new_value, 'balanced'
                            ))
                            break
            
            elif obj_type == 'CONVERGENCELIMITS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Balanced convergence settings
                    for param in obj.parameters:
                        if param.field_name == 'Maximum HVAC Iterations':
                            old_value = param.numeric_value or int(param.value)
                            new_value = 25  # Balanced iterations
                            
                            param.value = str(new_value)
                            param.numeric_value = float(new_value)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'maximum_hvac_iterations', old_value, new_value, 'balanced'
                            ))
                            break
        
        return modifications