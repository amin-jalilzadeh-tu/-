"""
Envelope Modifier Module - Handle building envelope modifications
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import logging

from ..base_modifier import BaseModifier, ModificationParameter


class EnvelopeModifier(BaseModifier):
    """Modifier for envelope-related parameters (materials, constructions, windows)"""
    
    def __init__(self, category: str = 'envelope', parsed_data_path=None):
        super().__init__(category, parsed_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Define envelope object types
        self.envelope_objects = {
            'materials': [
                'MATERIAL',
                'MATERIAL:NOMASS',
                'MATERIAL:AIRGAP',
                'MATERIAL:INFRAREDTRANSPARENT'
            ],
            'window_materials': [
                'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                'WINDOWMATERIAL:GLAZING',
                'WINDOWMATERIAL:GAS',
                'WINDOWMATERIAL:BLIND',
                'WINDOWMATERIAL:SCREEN',
                'WINDOWMATERIAL:SHADE'
            ],
            'constructions': [
                'CONSTRUCTION',
                'CONSTRUCTION:CFACTORUNDERGROUNDWALL',
                'CONSTRUCTION:FFACTORGROUNDFLOOR'
            ]
        }
        
        # Typical thermal properties
        self.typical_properties = {
            'insulation': {
                'conductivity': [0.02, 0.05],  # W/m-K
                'density': [10, 50],  # kg/m³
                'specific_heat': [800, 1400]  # J/kg-K
            },
            'concrete': {
                'conductivity': [1.0, 2.0],
                'density': [2000, 2400],
                'specific_heat': [800, 1000]
            },
            'wood': {
                'conductivity': [0.1, 0.2],
                'density': [400, 800],
                'specific_heat': [1200, 2000]
            },
            'glazing': {
                'u_factor': [0.8, 6.0],  # W/m²-K
                'shgc': [0.2, 0.9],
                'visible_transmittance': [0.3, 0.9]
            }
        }
        
        # Parameter definitions
        self.parameter_map = self._build_parameter_map()
        
    def _build_parameter_map(self) -> Dict[str, Dict[str, Any]]:
        """Build parameter mapping for envelope objects"""
        return {
            'MATERIAL': {
                'conductivity': {
                    'field_name': 'Conductivity',
                    'field_index': 3,
                    'units': 'W/m-K',
                    'typical_range': [0.01, 3.0]
                },
                'thickness': {
                    'field_name': 'Thickness',
                    'field_index': 2,
                    'units': 'm',
                    'typical_range': [0.001, 0.5]
                },
                'density': {
                    'field_name': 'Density',
                    'field_index': 4,
                    'units': 'kg/m³',
                    'typical_range': [10, 3000]
                },
                'specific_heat': {
                    'field_name': 'Specific Heat',
                    'field_index': 5,
                    'units': 'J/kg-K',
                    'typical_range': [100, 3000]
                },
                'thermal_absorptance': {
                    'field_name': 'Thermal Absorptance',
                    'field_index': 6,
                    'units': 'fraction',
                    'typical_range': [0.7, 0.95]
                },
                'solar_absorptance': {
                    'field_name': 'Solar Absorptance',
                    'field_index': 7,
                    'units': 'fraction',
                    'typical_range': [0.1, 0.9]
                }
            },
            'MATERIAL:NOMASS': {
                'thermal_resistance': {
                    'field_name': 'Thermal Resistance',
                    'field_index': 2,
                    'units': 'm²-K/W',
                    'typical_range': [0.01, 5.0]
                },
                'thermal_absorptance': {
                    'field_name': 'Thermal Absorptance',
                    'field_index': 3,
                    'units': 'fraction',
                    'typical_range': [0.7, 0.95]
                },
                'solar_absorptance': {
                    'field_name': 'Solar Absorptance',
                    'field_index': 4,
                    'units': 'fraction',
                    'typical_range': [0.1, 0.9]
                }
            },
            'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM': {
                'u_factor': {
                    'field_name': 'U-Factor',
                    'field_index': 1,
                    'units': 'W/m²-K',
                    'typical_range': [0.8, 6.0]
                },
                'shgc': {
                    'field_name': 'Solar Heat Gain Coefficient',
                    'field_index': 2,
                    'units': 'fraction',
                    'typical_range': [0.2, 0.9]
                },
                'visible_transmittance': {
                    'field_name': 'Visible Transmittance',
                    'field_index': 3,
                    'units': 'fraction',
                    'typical_range': [0.3, 0.9]
                }
            },
            'WINDOWMATERIAL:GLAZING': {
                'thickness': {
                    'field_name': 'Thickness',
                    'field_index': 1,
                    'units': 'm',
                    'typical_range': [0.003, 0.012]
                },
                'solar_transmittance': {
                    'field_name': 'Solar Transmittance at Normal Incidence',
                    'field_index': 2,
                    'units': 'fraction',
                    'typical_range': [0.0, 0.9]
                },
                'conductivity': {
                    'field_name': 'Conductivity',
                    'field_index': 10,
                    'units': 'W/m-K',
                    'typical_range': [0.7, 1.4]
                }
            }
        }
    
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """Identify all envelope parameters in the IDF"""
        parameters = []
        
        # Process materials
        for mat_type in self.envelope_objects['materials']:
            if mat_type in idf.idfobjects:
                for material in idf.idfobjects[mat_type]:
                    # Skip air materials
                    if hasattr(material, 'Name') and 'air' in material.Name.lower():
                        continue
                    
                    # Get parameters for this material type
                    if mat_type in self.parameter_map:
                        param_defs = self.parameter_map[mat_type]
                        
                        for param_key, param_def in param_defs.items():
                            try:
                                field_index = param_def['field_index']
                                if len(material.obj) > field_index:
                                    current_value = material.obj[field_index]
                                    
                                    if current_value and current_value != '':
                                        # Determine material type for better constraints
                                        mat_category = self._categorize_material(material.Name)
                                        
                                        param = ModificationParameter(
                                            object_type=mat_type,
                                            object_name=material.Name,
                                            field_name=param_def['field_name'],
                                            field_index=field_index,
                                            current_value=float(current_value),
                                            units=param_def.get('units', ''),
                                            constraints={
                                                'min_value': param_def['typical_range'][0],
                                                'max_value': param_def['typical_range'][1],
                                                'material_category': mat_category
                                            }
                                        )
                                        parameters.append(param)
                                        
                            except Exception as e:
                                self.logger.debug(f"Could not extract {param_key} from {material.Name}: {e}")
        
        # Process window materials
        for win_type in self.envelope_objects['window_materials']:
            if win_type in idf.idfobjects:
                for window in idf.idfobjects[win_type]:
                    if win_type in self.parameter_map:
                        param_defs = self.parameter_map[win_type]
                        
                        for param_key, param_def in param_defs.items():
                            try:
                                field_index = param_def['field_index']
                                if len(window.obj) > field_index:
                                    current_value = window.obj[field_index]
                                    
                                    if current_value and current_value != '':
                                        param = ModificationParameter(
                                            object_type=win_type,
                                            object_name=window.Name,
                                            field_name=param_def['field_name'],
                                            field_index=field_index,
                                            current_value=float(current_value),
                                            units=param_def.get('units', ''),
                                            constraints={
                                                'min_value': param_def['typical_range'][0],
                                                'max_value': param_def['typical_range'][1]
                                            }
                                        )
                                        parameters.append(param)
                                        
                            except Exception as e:
                                self.logger.debug(f"Could not extract {param_key} from window: {e}")
        
        self.logger.info(f"Identified {len(parameters)} envelope parameters")
        return parameters
    
    def _categorize_material(self, material_name: str) -> str:
        """Categorize material based on name"""
        name_lower = material_name.lower()
        
        if any(word in name_lower for word in ['insul', 'foam', 'fiber']):
            return 'insulation'
        elif any(word in name_lower for word in ['concrete', 'masonry', 'brick']):
            return 'concrete'
        elif any(word in name_lower for word in ['wood', 'timber']):
            return 'wood'
        elif any(word in name_lower for word in ['gyp', 'plaster', 'board']):
            return 'gypsum'
        elif any(word in name_lower for word in ['metal', 'steel', 'aluminum']):
            return 'metal'
        else:
            return 'other'
    
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate modification values for envelope parameters"""
        if strategy == 'performance':
            return self._generate_performance_modifications(parameters, options)
        elif strategy == 'insulation_improvement':
            return self._generate_insulation_modifications(parameters, options)
        elif strategy == 'window_upgrade':
            return self._generate_window_modifications(parameters, options)
        elif strategy == 'thermal_mass':
            return self._generate_thermal_mass_modifications(parameters, options)
        elif strategy == 'reflectance':
            return self._generate_reflectance_modifications(parameters, options)
        elif strategy == 'random':
            return self._generate_random_modifications(parameters, options)
        else:
            return self._generate_default_modifications(parameters, options)
    
    def _generate_performance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance-based envelope modifications"""
        modification_set = {}
        
        # Get multipliers
        insulation_mult = options.get('insulation', 1.5)
        conductivity_mult = options.get('conductivity_multiplier', 0.7)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            # Improve insulation
            if param.field_name == 'Conductivity':
                mat_category = param.constraints.get('material_category', 'other')
                if mat_category == 'insulation':
                    # Reduce conductivity for insulation
                    new_value = self.apply_multiplier(param.current_value,
                                                    conductivity_mult,
                                                    min_val=0.02,
                                                    max_val=param.current_value)
                    modification_set[param_id] = new_value
                    
            elif param.field_name == 'Thickness':
                mat_category = param.constraints.get('material_category', 'other')
                if mat_category == 'insulation':
                    # Increase insulation thickness
                    new_value = self.apply_multiplier(param.current_value,
                                                    insulation_mult,
                                                    max_val=0.3)  # Max 30cm
                    modification_set[param_id] = new_value
                    
            elif param.field_name == 'Thermal Resistance':
                # Increase thermal resistance
                new_value = self.apply_multiplier(param.current_value,
                                                insulation_mult,
                                                max_val=5.0)
                modification_set[param_id] = new_value
                
            elif param.field_name == 'U-Factor':
                # Reduce U-factor for windows
                new_value = self.apply_multiplier(param.current_value,
                                                0.7,  # 30% improvement
                                                min_val=0.8)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_insulation_modifications(self,
                                         parameters: List[ModificationParameter],
                                         options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insulation-focused modifications"""
        modification_set = {}
        
        # Target R-values by component
        target_r_values = {
            'wall': options.get('wall_r_value', 3.5),
            'roof': options.get('roof_r_value', 6.0),
            'floor': options.get('floor_r_value', 3.0)
        }
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Conductivity':
                mat_category = param.constraints.get('material_category', 'other')
                if mat_category == 'insulation':
                    # Calculate new conductivity for target R-value
                    # Assuming we know thickness (would need to track)
                    new_value = param.current_value * 0.5  # Simple 50% reduction
                    new_value = max(new_value, 0.02)  # Minimum conductivity
                    modification_set[param_id] = new_value
                    
            elif param.field_name == 'Thermal Resistance':
                # Direct R-value modification
                component_type = self._guess_component_type(param.object_name)
                if component_type in target_r_values:
                    target_r = target_r_values[component_type]
                    if param.current_value < target_r:
                        modification_set[param_id] = target_r
                        
            elif param.field_name == 'Thickness' and param.constraints.get('material_category') == 'insulation':
                # Increase insulation thickness
                thickness_mult = options.get('thickness_multiplier', 1.5)
                new_value = self.apply_multiplier(param.current_value,
                                                thickness_mult,
                                                max_val=0.3)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_window_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate window upgrade modifications"""
        modification_set = {}
        
        # Target window properties
        target_u_factor = options.get('target_u_factor', 1.2)  # W/m²-K
        target_shgc = options.get('target_shgc', 0.4)
        target_vt = options.get('target_visible_transmittance', 0.6)
        
        for param in parameters:
            if param.object_type in self.envelope_objects['window_materials']:
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                if param.field_name == 'U-Factor':
                    # Improve U-factor
                    if param.current_value > target_u_factor:
                        modification_set[param_id] = target_u_factor
                        
                elif param.field_name == 'Solar Heat Gain Coefficient':
                    # Adjust SHGC based on climate
                    climate = options.get('climate', 'moderate')
                    if climate == 'hot':
                        # Lower SHGC for hot climates
                        new_value = min(param.current_value, target_shgc)
                    else:
                        # Allow higher SHGC for cold climates
                        new_value = param.current_value
                    modification_set[param_id] = new_value
                    
                elif param.field_name == 'Visible Transmittance':
                    # Maintain good daylighting
                    if param.current_value < target_vt:
                        modification_set[param_id] = target_vt
                        
        return [modification_set]
    
    def _generate_thermal_mass_modifications(self,
                                           parameters: List[ModificationParameter],
                                           options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate thermal mass modifications"""
        modification_set = {}
        
        # Thermal mass strategy
        increase_mass = options.get('increase_thermal_mass', True)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            mat_category = param.constraints.get('material_category', 'other')
            
            if param.field_name == 'Density' and mat_category in ['concrete', 'gypsum']:
                if increase_mass:
                    # Increase density for thermal mass
                    new_value = self.apply_multiplier(param.current_value, 1.1,
                                                    max_val=param.constraints['max_value'])
                else:
                    # Decrease for lightweight construction
                    new_value = self.apply_multiplier(param.current_value, 0.8,
                                                    min_val=param.constraints['min_value'])
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Specific Heat' and mat_category in ['concrete', 'gypsum']:
                if increase_mass:
                    # Increase specific heat
                    new_value = self.apply_multiplier(param.current_value, 1.1,
                                                    max_val=2000)
                    modification_set[param_id] = new_value
                    
        return [modification_set]
    
    def _generate_reflectance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate reflectance/absorptance modifications"""
        modification_set = {}
        
        # Cool roof strategy
        cool_roof = options.get('cool_roof', True)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Solar Absorptance':
                # Check if this is a roof material
                if 'roof' in param.object_name.lower():
                    if cool_roof:
                        # Reduce solar absorptance (increase reflectance)
                        new_value = min(param.current_value, 0.3)
                    else:
                        new_value = param.current_value
                    modification_set[param_id] = new_value
                    
            elif param.field_name == 'Thermal Absorptance':
                # Typically keep high for most materials
                if param.current_value < 0.85:
                    modification_set[param_id] = 0.9
                    
        return [modification_set]
    
    def _generate_random_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate random envelope modifications"""
        modification_set = {}
        
        seed = options.get('seed', None)
        if seed:
            np.random.seed(seed)
            
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            # Different ranges for different parameters
            if param.field_name == 'Conductivity':
                # Reduce conductivity randomly
                multiplier = np.random.uniform(0.5, 0.9)
            elif param.field_name == 'Thickness':
                # Increase thickness randomly
                multiplier = np.random.uniform(1.1, 1.5)
            elif param.field_name == 'U-Factor':
                # Improve U-factor
                multiplier = np.random.uniform(0.6, 0.9)
            else:
                # General ±20%
                multiplier = np.random.uniform(0.8, 1.2)
                
            new_value = self.apply_multiplier(param.current_value,
                                            multiplier,
                                            min_val=param.constraints.get('min_value'),
                                            max_val=param.constraints.get('max_value'))
            modification_set[param_id] = new_value
            
        return [modification_set]
    
    def _generate_default_modifications(self,
                                      parameters: List[ModificationParameter],
                                      options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default envelope modifications - improve insulation"""
        modification_set = {}
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Conductivity':
                # Reduce by 20%
                new_value = param.current_value * 0.8
                modification_set[param_id] = new_value
            elif param.field_name == 'Thermal Resistance':
                # Increase by 20%
                new_value = param.current_value * 1.2
                modification_set[param_id] = new_value
            elif param.field_name == 'U-Factor':
                # Reduce by 15%
                new_value = param.current_value * 0.85
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def apply_modifications(self, idf: IDF, modifications: Dict[str, Any]) -> bool:
        """Apply envelope modifications to IDF"""
        success = True
        applied_count = 0
        
        for param_id, new_value in modifications.items():
            try:
                # Parse parameter ID
                obj_type, obj_name, field_name = self.parse_parameter_id(param_id)
                
                # Find and modify object
                if obj_type in idf.idfobjects:
                    for obj in idf.idfobjects[obj_type]:
                        if hasattr(obj, 'Name') and obj.Name == obj_name:
                            # Find field index
                            if obj_type in self.parameter_map:
                                for param_key, param_def in self.parameter_map[obj_type].items():
                                    if param_def['field_name'] == field_name:
                                        field_index = param_def['field_index']
                                        
                                        # Apply modification
                                        old_value = obj.obj[field_index]
                                        obj.obj[field_index] = new_value
                                        
                                        self.logger.debug(f"Modified {obj_type} {obj_name} "
                                                        f"{field_name}: {old_value} → {new_value}")
                                        applied_count += 1
                                        break
                            break
                            
            except Exception as e:
                self.logger.error(f"Error applying modification {param_id}: {e}")
                success = False
                
        self.logger.info(f"Applied {applied_count} envelope modifications")
        return success
    
    def _guess_component_type(self, material_name: str) -> str:
        """Guess building component type from material name"""
        name_lower = material_name.lower()
        
        if any(word in name_lower for word in ['wall', 'exterior']):
            return 'wall'
        elif any(word in name_lower for word in ['roof', 'ceiling']):
            return 'roof'
        elif any(word in name_lower for word in ['floor', 'slab']):
            return 'floor'
        else:
            return 'unknown'
    
    def calculate_construction_u_value(self, idf: IDF, construction_name: str) -> Optional[float]:
        """Calculate U-value for a construction"""
        # Find construction
        construction = None
        for const in idf.idfobjects.get('CONSTRUCTION', []):
            if const.Name == construction_name:
                construction = const
                break
                
        if not construction:
            return None
            
        # Calculate R-value
        total_r = 0.0
        
        # Get layers
        for i in range(2, len(construction.obj)):  # Skip name and first field
            layer_name = construction.obj[i]
            if not layer_name:
                break
                
            # Find material
            for mat_type in self.envelope_objects['materials']:
                for material in idf.idfobjects.get(mat_type, []):
                    if material.Name == layer_name:
                        if mat_type == 'MATERIAL':
                            # R = thickness / conductivity
                            thickness = float(material.Thickness) if material.Thickness else 0
                            conductivity = float(material.Conductivity) if material.Conductivity else 1
                            total_r += thickness / conductivity
                        elif mat_type == 'MATERIAL:NOMASS':
                            # Direct R-value
                            total_r += float(material.Thermal_Resistance) if material.Thermal_Resistance else 0
                        elif mat_type == 'MATERIAL:AIRGAP':
                            # Typical air gap R-value
                            total_r += 0.15
                        break
        
        # Add surface film resistances (typical values)
        total_r += 0.04 + 0.13  # Interior + exterior films
        
        # U = 1/R
        return 1.0 / total_r if total_r > 0 else None
    
    def validate_envelope_properties(self, idf: IDF) -> Tuple[bool, List[str]]:
        """Validate envelope properties after modifications"""
        errors = []
        
        # Check material properties
        for mat_type in self.envelope_objects['materials']:
            for material in idf.idfobjects.get(mat_type, []):
                if mat_type == 'MATERIAL':
                    # Check conductivity
                    if hasattr(material, 'Conductivity'):
                        k = float(material.Conductivity) if material.Conductivity else 0
                        if k <= 0:
                            errors.append(f"{material.Name}: Invalid conductivity ({k})")
                        elif k > 5.0:
                            errors.append(f"{material.Name}: Conductivity too high ({k} W/m-K)")
                            
                    # Check thickness
                    if hasattr(material, 'Thickness'):
                        t = float(material.Thickness) if material.Thickness else 0
                        if t <= 0:
                            errors.append(f"{material.Name}: Invalid thickness ({t})")
                        elif t > 1.0:
                            errors.append(f"{material.Name}: Thickness too large ({t} m)")
        
        # Check window properties
        for win in idf.idfobjects.get('WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', []):
            if hasattr(win, 'U_Factor'):
                u = float(win.U_Factor) if win.U_Factor else 0
                if u <= 0 or u > 10:
                    errors.append(f"{win.Name}: Invalid U-factor ({u})")
                    
            if hasattr(win, 'Solar_Heat_Gain_Coefficient'):
                shgc = float(win.Solar_Heat_Gain_Coefficient) if win.Solar_Heat_Gain_Coefficient else 0
                if shgc < 0 or shgc > 1:
                    errors.append(f"{win.Name}: Invalid SHGC ({shgc})")
        
        return len(errors) == 0, errors
