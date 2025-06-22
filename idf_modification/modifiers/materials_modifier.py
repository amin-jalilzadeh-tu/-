"""
Materials Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
import pandas as pd
from ..base_modifier import BaseModifier, ParameterDefinition

class MaterialsModifier(BaseModifier):
    """Modifier for material-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize material parameter definitions matching parser field names"""
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
                min_value=0.1,
                max_value=0.99,
                performance_impact='surface_heat_transfer'
            ),
            'solar_absorptance': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Solar Absorptance',
                field_index=7,
                data_type=float,
                min_value=0.1,
                max_value=0.99,
                performance_impact='solar_gains'
            ),
            'visible_absorptance': ParameterDefinition(
                object_type='MATERIAL',
                field_name='Visible Absorptance',
                field_index=8,
                data_type=float,
                min_value=0.1,
                max_value=0.99,
                performance_impact='daylighting'
            ),
            
            # No mass material parameters
            'thermal_resistance': ParameterDefinition(
                object_type='MATERIAL:NOMASS',
                field_name='Thermal Resistance',
                field_index=2,
                data_type=float,
                units='m2-K/W',
                min_value=0.001,
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
                min_value=0.1,
                max_value=0.9,
                performance_impact='solar_gains'
            ),
            'visible_transmittance': ParameterDefinition(
                object_type='WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                field_name='Visible Transmittance',
                field_index=3,
                data_type=float,
                min_value=0.1,
                max_value=0.9,
                performance_impact='daylighting'
            )
        }
    
    def get_category_name(self) -> str:
        return 'materials'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'MATERIAL',
            'MATERIAL:NOMASS',
            'MATERIAL:INFRAREDTRANSPARENT',
            'MATERIAL:AIRGAP',
            'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
            'WINDOWMATERIAL:GLAZING',
            'WINDOWMATERIAL:GAS',
            'WINDOWMATERIAL:GASMIXTURE',
            'WINDOWMATERIAL:SHADE',
            'WINDOWMATERIAL:BLIND',
            'WINDOWMATERIAL:SCREEN',
            'CONSTRUCTION',
            'CONSTRUCTION:COMPLEXFENESTRATIONSTATE',
            'CONSTRUCTION:WINDOWDATAFILE'
        ]
    
    # Updated materials_modifier.py snippet
    # Replace the _get_category_files method with this:

    def _get_category_files(self) -> List[str]:
        """
        Return list of parquet files to load for this category
        
        Note: The parser creates files with different names than expected,
        so we map them properly here.
        """
        # Return the expected file names - the ModificationEngine will handle the mapping
        return ['materials', 'constructions']

    # Add this alternative method to the MaterialsModifier class for direct file loading:

    def load_current_values(self, building_id: str) -> Dict[str, pd.DataFrame]:
        """
        Override to handle materials-specific file naming
        """
        self.logger.info(f"Loading current values for {self.get_category_name()}")
        current_values = {}
        
        # Define the actual file names created by the parser
        file_mappings = {
            'materials': {
                'files': ['materials_materials', 'materials_windowmaterials'],
                'combine': True  # Combine data from multiple files
            },
            'constructions': {
                'files': ['materials_constructions'],
                'combine': False
            }
        }
        
        parsed_data_path = self.parsed_data_path / 'idf_data' / 'by_category'
        
        for expected_name, mapping_info in file_mappings.items():
            combined_data = []
            
            for actual_file in mapping_info['files']:
                file_path = parsed_data_path / f"{actual_file}.parquet"
                if file_path.exists():
                    df = pd.read_parquet(file_path)
                    # Filter by building_id if column exists
                    if 'building_id' in df.columns:
                        df = df[df['building_id'] == building_id]
                    
                    if mapping_info.get('combine', False):
                        combined_data.append(df)
                    else:
                        current_values[expected_name] = df
                        
                    self.logger.debug(f"Loaded {len(df)} records from {actual_file}")
                else:
                    self.logger.warning(f"File not found: {file_path}")
            
            # Combine data if needed
            if combined_data and mapping_info.get('combine', False):
                current_values[expected_name] = pd.concat(combined_data, ignore_index=True)
                self.logger.debug(f"Combined {len(combined_data)} files into {expected_name}")
        
        self.current_values = current_values
        return current_values
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply material-specific modifications"""
        
        if strategy == 'insulation_upgrade':
            return self._apply_insulation_upgrade(parsed_objects, modifiable_params)
        elif strategy == 'window_upgrade':
            return self._apply_window_upgrade(parsed_objects, modifiable_params)
        elif strategy == 'thermal_mass':
            return self._apply_thermal_mass_increase(parsed_objects, modifiable_params)
        elif strategy == 'cool_roof':
            return self._apply_cool_roof(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_insulation_upgrade(self, parsed_objects, modifiable_params):
        """Apply insulation upgrades to materials"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'MATERIAL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an insulation material (low conductivity)
                    conductivity_param = None
                    for param in obj.parameters:
                        if param.field_name == 'Conductivity':
                            conductivity_param = param
                            break
                    
                    if conductivity_param and conductivity_param.numeric_value:
                        current_conductivity = conductivity_param.numeric_value
                        
                        # If it's insulation (conductivity < 0.1 W/m-K)
                        if current_conductivity < 0.1:
                            # Improve insulation by reducing conductivity 20-40%
                            reduction = random.uniform(0.2, 0.4)
                            new_conductivity = current_conductivity * (1 - reduction)
                            
                            conductivity_param.value = str(new_conductivity)
                            conductivity_param.numeric_value = new_conductivity
                            
                            modifications.append(self._create_modification_result(
                                obj, 'conductivity', current_conductivity, new_conductivity, 'insulation_upgrade'
                            ))
                            
                            # Also increase thickness for better insulation
                            for param in obj.parameters:
                                if param.field_name == 'Thickness' and param.numeric_value:
                                    old_thickness = param.numeric_value
                                    # Increase thickness by 20-50%
                                    increase = random.uniform(1.2, 1.5)
                                    new_thickness = min(old_thickness * increase, 0.5)  # Cap at 0.5m
                                    
                                    param.value = str(new_thickness)
                                    param.numeric_value = new_thickness
                                    
                                    modifications.append(self._create_modification_result(
                                        obj, 'thickness', old_thickness, new_thickness, 'insulation_upgrade'
                                    ))
                                    break
            
            elif obj_type == 'MATERIAL:NOMASS':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase thermal resistance
                    for param in obj.parameters:
                        if param.field_name == 'Thermal Resistance' and param.numeric_value:
                            old_resistance = param.numeric_value
                            # Increase resistance by 50-100%
                            increase = random.uniform(1.5, 2.0)
                            new_resistance = min(old_resistance * increase, 10.0)  # Cap at R-10
                            
                            param.value = str(new_resistance)
                            param.numeric_value = new_resistance
                            
                            modifications.append(self._create_modification_result(
                                obj, 'thermal_resistance', old_resistance, new_resistance, 'insulation_upgrade'
                            ))
                            break
        
        return modifications
    
    def _apply_window_upgrade(self, parsed_objects, modifiable_params):
        """Apply high-performance window upgrades"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Upgrade to high-performance windows
                    # Lower U-factor (better insulation)
                    for param in obj.parameters:
                        if param.field_name == 'U-Factor' and param.numeric_value:
                            old_u_factor = param.numeric_value
                            # High-performance windows: U-factor 0.8-1.5
                            import random
                            new_u_factor = random.uniform(0.8, 1.5)
                            
                            param.value = str(new_u_factor)
                            param.numeric_value = new_u_factor
                            
                            modifications.append(self._create_modification_result(
                                obj, 'u_factor', old_u_factor, new_u_factor, 'window_upgrade'
                            ))
                            break
                    
                    # Optimize SHGC based on climate (simplified)
                    for param in obj.parameters:
                        if param.field_name == 'Solar Heat Gain Coefficient' and param.numeric_value:
                            old_shgc = param.numeric_value
                            # Low SHGC for cooling climates, high for heating climates
                            # This is simplified - real implementation would check climate
                            new_shgc = random.uniform(0.25, 0.4)  # Low SHGC for cooling
                            
                            param.value = str(new_shgc)
                            param.numeric_value = new_shgc
                            
                            modifications.append(self._create_modification_result(
                                obj, 'shgc', old_shgc, new_shgc, 'window_upgrade'
                            ))
                            break
                    
                    # Maintain high visible transmittance
                    for param in obj.parameters:
                        if param.field_name == 'Visible Transmittance':
                            old_vt = param.numeric_value or float(param.value)
                            # High VT for daylighting: 0.6-0.8
                            new_vt = random.uniform(0.6, 0.8)
                            
                            param.value = str(new_vt)
                            param.numeric_value = new_vt
                            
                            modifications.append(self._create_modification_result(
                                obj, 'visible_transmittance', old_vt, new_vt, 'window_upgrade'
                            ))
                            break
        
        return modifications
    
    def _apply_thermal_mass_increase(self, parsed_objects, modifiable_params):
        """Increase thermal mass of materials"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'MATERIAL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase density for thermal mass
                    for param in obj.parameters:
                        if param.field_name == 'Density' and param.numeric_value:
                            old_density = param.numeric_value
                            # Only increase if not already high density
                            if old_density < 2000:
                                # Increase by 20-50%
                                increase = random.uniform(1.2, 1.5)
                                new_density = min(old_density * increase, 2500)
                                
                                param.value = str(new_density)
                                param.numeric_value = new_density
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'density', old_density, new_density, 'thermal_mass'
                                ))
                            break
                    
                    # Increase specific heat
                    for param in obj.parameters:
                        if param.field_name == 'Specific Heat' and param.numeric_value:
                            old_cp = param.numeric_value
                            # Increase by 10-30%
                            increase = random.uniform(1.1, 1.3)
                            new_cp = min(old_cp * increase, 2000)
                            
                            param.value = str(new_cp)
                            param.numeric_value = new_cp
                            
                            modifications.append(self._create_modification_result(
                                obj, 'specific_heat', old_cp, new_cp, 'thermal_mass'
                            ))
                            break
        
        return modifications
    
    def _apply_cool_roof(self, parsed_objects, modifiable_params):
        """Apply cool roof properties"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'MATERIAL':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a roof material (simplified check)
                    if 'ROOF' in obj.name.upper():
                        # Reduce solar absorptance (increase reflectance)
                        for param in obj.parameters:
                            if param.field_name == 'Solar Absorptance' and param.numeric_value:
                                old_absorptance = param.numeric_value
                                # Cool roofs have solar absorptance 0.2-0.3
                                import random
                                new_absorptance = random.uniform(0.2, 0.3)
                                
                                param.value = str(new_absorptance)
                                param.numeric_value = new_absorptance
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'solar_absorptance', old_absorptance, new_absorptance, 'cool_roof'
                                ))
                                break
                        
                        # Increase thermal emittance (absorptance)
                        for param in obj.parameters:
                            if param.field_name == 'Thermal Absorptance' and param.numeric_value:
                                old_emittance = param.numeric_value
                                # High emittance for cool roofs: 0.85-0.95
                                new_emittance = random.uniform(0.85, 0.95)
                                
                                param.value = str(new_emittance)
                                param.numeric_value = new_emittance
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'thermal_absorptance', old_emittance, new_emittance, 'cool_roof'
                                ))
                                break
        
        return modifications