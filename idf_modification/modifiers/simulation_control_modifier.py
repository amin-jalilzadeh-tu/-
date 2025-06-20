"""
Simulation control parameter modifications.

This module handles modifications to simulation control parameter modifications.
"""
"""
Simulation Control Modifier - Handles simulation control objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class SimulationControlModifier(BaseModifier):
    """Modifier for simulation control related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize simulation control parameter definitions"""
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
                field_name='Shading Calculation Update Frequency',
                field_index=1,
                data_type=int,
                min_value=1,
                max_value=365,
                performance_impact='simulation_speed'
            ),
            'maximum_shadow_figures': ParameterDefinition(
                object_type='SHADOWCALCULATION',
                field_name='Maximum Figures in Shadow Overlap Calculations',
                field_index=2,
                data_type=int,
                min_value=200,
                max_value=50000,
                performance_impact='simulation_accuracy'
            ),
            
            # Convergence limits
            'loads_convergence_tolerance': ParameterDefinition(
                object_type='CONVERGENCELIMITS',
                field_name='Minimum System Timestep',
                field_index=0,
                data_type=float,
                units='minutes',
                min_value=1,
                max_value=60,
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
            
            # Solar distribution
            'solar_distribution': ParameterDefinition(
                object_type='BUILDING',
                field_name='Solar Distribution',
                field_index=5,
                data_type=str,
                allowed_values=['MinimalShadowing', 'FullExterior', 'FullInteriorAndExterior', 
                               'FullExteriorWithReflections', 'FullInteriorAndExteriorWithReflections'],
                performance_impact='solar_accuracy'
            ),
            
            # Surface convection algorithms
            'inside_convection_algorithm': ParameterDefinition(
                object_type='SURFACECONVECTIONALGORITHM:INSIDE',
                field_name='Algorithm',
                field_index=0,
                data_type=str,
                allowed_values=['Simple', 'TARP', 'CeilingDiffuser', 'AdaptiveConvectionAlgorithm'],
                performance_impact='heat_transfer_accuracy'
            ),
            'outside_convection_algorithm': ParameterDefinition(
                object_type='SURFACECONVECTIONALGORITHM:OUTSIDE',
                field_name='Algorithm',
                field_index=0,
                data_type=str,
                allowed_values=['SimpleCombined', 'TARP', 'MoWiTT', 'DOE-2', 'AdaptiveConvectionAlgorithm'],
                performance_impact='heat_transfer_accuracy'
            )
        }
    
    def get_category_name(self) -> str:
        return 'simulation_control'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'VERSION',
            'SIMULATIONCONTROL',
            'BUILDING',
            'TIMESTEP',
            'SHADOWCALCULATION',
            'SURFACECONVECTIONALGORITHM:INSIDE',
            'SURFACECONVECTIONALGORITHM:OUTSIDE',
            'HEATBALANCEALGORITHM',
            'CONVERGENCELIMITS'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['simulation_control']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply simulation control specific modifications"""
        
        if strategy == 'high_accuracy':
            return self._apply_high_accuracy(idf, modifiable_params)
        elif strategy == 'fast_simulation':
            return self._apply_fast_simulation(idf, modifiable_params)
        elif strategy == 'detailed_solar':
            return self._apply_detailed_solar(idf, modifiable_params)
        elif strategy == 'adaptive_algorithms':
            return self._apply_adaptive_algorithms(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_high_accuracy(self, idf, modifiable_params):
        """Apply high accuracy simulation settings"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            # Increase timesteps
            if obj_type == 'TIMESTEP':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Number_of_Timesteps_per_Hour:
                        old_timesteps = int(obj.Number_of_Timesteps_per_Hour)
                        new_timesteps = 6  # 10-minute timesteps
                        obj.Number_of_Timesteps_per_Hour = new_timesteps
                        
                        modifications.append(self._create_modification_result(
                            obj, 'timesteps_per_hour', old_timesteps, new_timesteps,
                            'high_accuracy_timestep'
                        ))
            
            # More frequent shadow calculations
            elif obj_type == 'SHADOWCALCULATION':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Shading_Calculation_Update_Frequency:
                        old_freq = int(obj.Shading_Calculation_Update_Frequency)
                        new_freq = 7  # Weekly updates
                        obj.Shading_Calculation_Update_Frequency = new_freq
                        
                        modifications.append(self._create_modification_result(
                            obj, 'shadow_calculation_frequency', old_freq, new_freq,
                            'frequent_shadow_updates'
                        ))
            
            # Detailed solar distribution
            elif obj_type == 'BUILDING':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Solar_Distribution:
                        old_solar = obj.Solar_Distribution
                        new_solar = 'FullInteriorAndExteriorWithReflections'
                        obj.Solar_Distribution = new_solar
                        
                        modifications.append(self._create_modification_result(
                            obj, 'solar_distribution', old_solar, new_solar,
                            'detailed_solar_distribution'
                        ))
        
        return modifications
    
    def _apply_fast_simulation(self, idf, modifiable_params):
        """Apply fast simulation settings"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            # Reduce timesteps
            if obj_type == 'TIMESTEP':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Number_of_Timesteps_per_Hour:
                        old_timesteps = int(obj.Number_of_Timesteps_per_Hour)
                        new_timesteps = 2  # 30-minute timesteps
                        obj.Number_of_Timesteps_per_Hour = new_timesteps
                        
                        modifications.append(self._create_modification_result(
                            obj, 'timesteps_per_hour', old_timesteps, new_timesteps,
                            'fast_simulation_timestep'
                        ))
            
            # Less frequent shadow calculations
            elif obj_type == 'SHADOWCALCULATION':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Shading_Calculation_Update_Frequency:
                        old_freq = int(obj.Shading_Calculation_Update_Frequency)
                        new_freq = 30  # Monthly updates
                        obj.Shading_Calculation_Update_Frequency = new_freq
                        
                        modifications.append(self._create_modification_result(
                            obj, 'shadow_calculation_frequency', old_freq, new_freq,
                            'infrequent_shadow_updates'
                        ))
            
            # Simplified solar distribution
            elif obj_type == 'BUILDING':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Solar_Distribution:
                        old_solar = obj.Solar_Distribution
                        new_solar = 'FullExterior'
                        obj.Solar_Distribution = new_solar
                        
                        modifications.append(self._create_modification_result(
                            obj, 'solar_distribution', old_solar, new_solar,
                            'simplified_solar_distribution'
                        ))
        
        return modifications
    
    def _apply_detailed_solar(self, idf, modifiable_params):
        """Apply detailed solar modeling"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'BUILDING':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Solar_Distribution:
                        old_solar = obj.Solar_Distribution
                        new_solar = 'FullInteriorAndExteriorWithReflections'
                        obj.Solar_Distribution = new_solar
                        
                        modifications.append(self._create_modification_result(
                            obj, 'solar_distribution', old_solar, new_solar,
                            'full_solar_with_reflections'
                        ))
            
            elif obj_type == 'SHADOWCALCULATION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Daily shadow updates
                    if obj.Shading_Calculation_Update_Frequency:
                        old_freq = int(obj.Shading_Calculation_Update_Frequency)
                        new_freq = 1  # Daily
                        obj.Shading_Calculation_Update_Frequency = new_freq
                        
                        modifications.append(self._create_modification_result(
                            obj, 'shadow_calculation_frequency', old_freq, new_freq,
                            'daily_shadow_calculation'
                        ))
                    
                    # Increase figure limit
                    if obj.Maximum_Figures_in_Shadow_Overlap_Calculations:
                        old_figures = int(obj.Maximum_Figures_in_Shadow_Overlap_Calculations)
                        new_figures = min(old_figures * 2, 30000)
                        obj.Maximum_Figures_in_Shadow_Overlap_Calculations = new_figures
                        
                        modifications.append(self._create_modification_result(
                            obj, 'maximum_shadow_figures', old_figures, new_figures,
                            'increased_shadow_figures'
                        ))
        
        return modifications
    
    def _apply_adaptive_algorithms(self, idf, modifiable_params):
        """Apply adaptive convection algorithms"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SURFACECONVECTIONALGORITHM:INSIDE':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Algorithm:
                        old_algo = obj.Algorithm
                        new_algo = 'AdaptiveConvectionAlgorithm'
                        obj.Algorithm = new_algo
                        
                        modifications.append(self._create_modification_result(
                            obj, 'inside_convection_algorithm', old_algo, new_algo,
                            'adaptive_inside_convection'
                        ))
            
            elif obj_type == 'SURFACECONVECTIONALGORITHM:OUTSIDE':
                for obj_info in objects:
                    obj = obj_info['object']
                    if obj.Algorithm:
                        old_algo = obj.Algorithm
                        new_algo = 'AdaptiveConvectionAlgorithm'
                        obj.Algorithm = new_algo
                        
                        modifications.append(self._create_modification_result(
                            obj, 'outside_convection_algorithm', old_algo, new_algo,
                            'adaptive_outside_convection'
                        ))
        
        return modifications
    
    def _create_modification_result(self, obj, param_name, old_value, new_value, rule):
        """Helper to create modification result"""
        from ..base_modifier import ModificationResult
        
        return ModificationResult(
            success=True,
            object_type=obj.obj[0],
            object_name=obj.Name if hasattr(obj, 'Name') else obj.obj[0],
            parameter=param_name,
            original_value=old_value,
            new_value=new_value,
            change_type='absolute',
            rule_applied=rule,
            validation_status='valid'
        )