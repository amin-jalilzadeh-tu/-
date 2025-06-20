"""
Material properties and construction modifications.

This module handles modifications to material properties and construction modifications.
"""
"""
Materials Modifier - Handles all material types
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class MaterialsModifier(BaseModifier):
    """Modifier for material-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize material parameter definitions"""
        self.parameter_definitions = {
            # Regular material parameters
            'thickness': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Thickness',
                field_index=2,
                data_type=float,
                units='m',
                min_value=0.001,
                max_value=1.0,
                performance_impact='thermal_resistance'
            ),
            'conductivity': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Conductivity',
                field_index=3,
                data_type=float,
                units='W/m-K',
                min_value=0.01,
                max_value=5.0,
                performance_impact='thermal_resistance'
            ),
            'density': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Density',
                field_index=4,
                data_type=float,
                units='kg/m3',
                min_value=10,
                max_value=3000,
                performance_impact='thermal_mass'
            ),
            'specific_heat': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Specific Heat',
                field_index=5,
                data_type=float,
                units='J/kg-K',
                min_value=100,
                max_value=5000,
                performance_impact='thermal_mass'
            ),
            'thermal_absorptance': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Thermal Absorptance',
                field_index=6,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='surface_heat_transfer'
            ),
            'solar_absorptance': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Solar Absorptance',
                field_index=7,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='solar_gains'
            ),
            
            # No mass material parameters
            'thermal_resistance': ParameterDefinition(
                object_type='MATERIAL:NOMASS',
                field_name='Thermal Resistance',
                field_index=2,
                data_type=float,
                units='m2-K/W',
                min_value=0.01,
                max_value=10.0,
                performance_impact='thermal_resistance'
            ),
            
            # Window material parameters
            'u_factor': ParameterDefinition(
                object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                field_name='U-Factor',
                field_index=1,
                data_type=float,
                units='W/m2-K',
                min_value=0.5,
                max_value=6.0,
                performance_impact='window_heat_transfer'
            ),
            'shgc': ParameterDefinition(
                object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                field_name='Solar Heat Gain Coefficient',
                field_index=2,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='solar_gains'
            ),
            'visible_transmittance': ParameterDefinition(
                object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                field_name='Visible Transmittance',
                field_index=3,
                data_type=float,
                min_value=0.0,
                max_value=1.0,
                performance_impact='daylighting'
            ),
            
            # Glazing parameters
            'glass_thickness': ParameterDefinition(
                object_type='WINDOWMATERIAL:GLAZING',
                field_name='Thickness',
                field_index=1,
                data_type=float,
                units='m',
                min_value=0.003,
                max_value=0.025,
                performance_impact='window_properties'
            ),
            'glass_conductivity': ParameterDefinition(
                object_type='WINDOWMATERIAL:GLAZING',
                field_name='Conductivity',
                field_index=3,
                data_type=float,
                units='W/m-K',
                min_value=0.5,
                max_value=2.0,
                performance_impact='window_heat_transfer'
            )
        }
    
    def get_category_name(self) -> str:
        return 'materials'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'MATERIAL',
            'MATERIAL:NOMASS',
            'MATERIAL:AIRGAP',
            'MATERIAL:INFRAREDTRANSPARENT',
            'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
            'WINDOWMATERIAL:GLAZING',
            'WINDOWMATERIAL:GAS',
            'WINDOWMATERIAL:GASMIXTURE',
            'WINDOWMATERIAL:BLIND',
            'WINDOWMATERIAL:SCREEN',
            'WINDOWMATERIAL:SHADE',
            'CONSTRUCTION',
            'CONSTRUCTION:CFACTORUNDERGROUNDWALL',
            'CONSTRUCTION:FFACTORGROUNDFLOOR',
            'CONSTRUCTION:INTERNALSOURCE'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['materials_materials', 'materials_windowmaterials', 'materials_constructions']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply material-specific modifications"""
        
        if strategy == 'super_insulation':
            return self._apply_super_insulation(idf, modifiable_params)
        elif strategy == 'thermal_mass_increase':
            return self._apply_thermal_mass_increase(idf, modifiable_params)
        elif strategy == 'cool_roof':
            return self._apply_cool_roof(idf, modifiable_params)
        elif strategy == 'high_performance_windows':
            return self._apply_high_performance_windows(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_super_insulation(self, idf, modifiable_params):
        """Apply super insulation improvements"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'MATERIAL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is insulation material (low conductivity)
                    if obj.Conductivity:
                        conductivity = float(obj.Conductivity)
                        
                        if conductivity < 0.1:  # Likely insulation
                            # Improve insulation by reducing conductivity
                            new_conductivity = conductivity * 0.5  # 50% improvement
                            obj.Conductivity = new_conductivity
                            
                            modifications.append(self._create_modification_result(
                                obj, 'conductivity', conductivity, new_conductivity, 
                                'super_insulation'
                            ))
                            
                            # Also increase thickness if possible
                            if obj.Thickness:
                                thickness = float(obj.Thickness)
                                new_thickness = min(thickness * 1.5, 0.3)  # 50% thicker, max 30cm
                                obj.Thickness = new_thickness
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'thickness', thickness, new_thickness, 
                                    'super_insulation'
                                ))
                                
            elif obj_type == 'MATERIAL:NOMASS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Thermal_Resistance:
                        resistance = float(obj.Thermal_Resistance)
                        # Double the thermal resistance
                        new_resistance = resistance * 2.0
                        obj.Thermal_Resistance = new_resistance
                        
                        modifications.append(self._create_modification_result(
                            obj, 'thermal_resistance', resistance, new_resistance, 
                            'super_insulation'
                        ))
        
        return modifications
    
    def _apply_thermal_mass_increase(self, idf, modifiable_params):
        """Increase thermal mass of materials"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'MATERIAL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a massive material (high density)
                    if obj.Density:
                        density = float(obj.Density)
                        
                        if density > 1000:  # Concrete, brick, etc.
                            # Increase thickness for more thermal mass
                            if obj.Thickness:
                                thickness = float(obj.Thickness)
                                new_thickness = min(thickness * 1.3, 0.5)  # 30% thicker
                                obj.Thickness = new_thickness
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'thickness', thickness, new_thickness, 
                                    'thermal_mass_increase'
                                ))
                            
                            # Could also increase specific heat slightly
                            if obj.Specific_Heat:
                                spec_heat = float(obj.Specific_Heat)
                                new_spec_heat = spec_heat * 1.1  # 10% increase
                                obj.Specific_Heat = new_spec_heat
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'specific_heat', spec_heat, new_spec_heat, 
                                    'thermal_mass_increase'
                                ))
        
        return modifications
    
    def _apply_cool_roof(self, idf, modifiable_params):
        """Apply cool roof properties"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'MATERIAL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a roof material
                    if 'roof' in obj.Name.lower() or 'roofing' in obj.Name.lower():
                        # Reduce solar absorptance (increase reflectance)
                        if obj.Solar_Absorptance:
                            solar_abs = float(obj.Solar_Absorptance)
                            new_solar_abs = 0.2  # Cool roof target
                            obj.Solar_Absorptance = new_solar_abs
                            
                            modifications.append(self._create_modification_result(
                                obj, 'solar_absorptance', solar_abs, new_solar_abs, 
                                'cool_roof'
                            ))
                        
                        # Increase thermal emittance
                        if obj.Thermal_Absorptance:
                            thermal_abs = float(obj.Thermal_Absorptance)
                            new_thermal_abs = 0.9  # High emittance
                            obj.Thermal_Absorptance = new_thermal_abs
                            
                            modifications.append(self._create_modification_result(
                                obj, 'thermal_absorptance', thermal_abs, new_thermal_abs, 
                                'cool_roof'
                            ))
        
        return modifications
    
    def _apply_high_performance_windows(self, idf, modifiable_params):
        """Upgrade to high performance windows"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Improve U-factor
                    if obj.U_Factor:
                        u_factor = float(obj.U_Factor)
                        # Triple-pane performance
                        new_u_factor = min(u_factor * 0.4, 1.0)  # 60% improvement
                        obj.U_Factor = new_u_factor
                        
                        modifications.append(self._create_modification_result(
                            obj, 'u_factor', u_factor, new_u_factor, 
                            'high_performance_windows'
                        ))
                    
                    # Optimize SHGC for climate
                    if obj.Solar_Heat_Gain_Coefficient:
                        shgc = float(obj.Solar_Heat_Gain_Coefficient)
                        # Lower SHGC for cooling-dominated climates
                        new_shgc = shgc * 0.7  # 30% reduction
                        obj.Solar_Heat_Gain_Coefficient = new_shgc
                        
                        modifications.append(self._create_modification_result(
                            obj, 'shgc', shgc, new_shgc, 
                            'high_performance_windows'
                        ))
                        
            elif obj_type == 'WINDOWMATERIAL:GLAZING':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Use low-e coating properties
                    if obj.Front_Side_Infrared_Hemispherical_Emissivity:
                        emissivity = float(obj.Front_Side_Infrared_Hemispherical_Emissivity)
                        new_emissivity = 0.1  # Low-e coating
                        obj.Front_Side_Infrared_Hemispherical_Emissivity = new_emissivity
                        obj.Back_Side_Infrared_Hemispherical_Emissivity = new_emissivity
                        
                        modifications.append(self._create_modification_result(
                            obj, 'emissivity', emissivity, new_emissivity, 
                            'low_e_coating'
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