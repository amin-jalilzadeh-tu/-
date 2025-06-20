"""
Equipment Modifier Module - Handle equipment load modifications
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import logging

from ..base_modifier import BaseModifier, ModificationParameter


class EquipmentModifier(BaseModifier):
    """Modifier for equipment-related parameters"""
    
    def __init__(self, category: str = 'equipment', parsed_data_path=None):
        super().__init__(category, parsed_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Define equipment object types
        self.equipment_objects = {
            'electric': ['ELECTRICEQUIPMENT'],
            'gas': ['GASEQUIPMENT'],
            'hot_water': ['HOTWATEREQUIPMENT'],
            'steam': ['STEAMEQUIPMENT'],
            'other': ['OTHEREQUIPMENT'],
            'exterior': ['EXTERIOREQUIPMENT', 'EXTERIOR:FUELFIREDHEATER']
        }
        
        # Typical equipment power densities by space type (W/m²)
        self.typical_epd = {
            'office': {
                'current': 10.8,
                'efficient': 7.5,
                'advanced': 5.0,
                'description': 'Office equipment and plug loads'
            },
            'classroom': {
                'current': 5.4,
                'efficient': 4.0,
                'advanced': 3.0,
                'description': 'Classroom equipment'
            },
            'retail': {
                'current': 4.3,
                'efficient': 3.2,
                'advanced': 2.5,
                'description': 'Retail equipment excluding lighting'
            },
            'residential': {
                'current': 4.5,
                'efficient': 3.5,
                'advanced': 2.5,
                'description': 'Residential plug loads'
            },
            'datacenter': {
                'current': 1000.0,
                'efficient': 750.0,
                'advanced': 500.0,
                'description': 'Data center IT equipment'
            },
            'kitchen': {
                'current': 350.0,
                'efficient': 250.0,
                'advanced': 200.0,
                'description': 'Commercial kitchen equipment'
            },
            'healthcare': {
                'current': 15.0,
                'efficient': 12.0,
                'advanced': 10.0,
                'description': 'Healthcare equipment'
            }
        }
        
        # Parameter definitions
        self.parameter_map = self._build_parameter_map()
        
    def _build_parameter_map(self) -> Dict[str, Dict[str, Any]]:
        """Build parameter mapping for equipment objects"""
        return {
            'ELECTRICEQUIPMENT': {
                'design_level': {
                    'field_name': 'Design Level',
                    'field_index': 4,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W',
                    'typical_range': [10, 100000]
                },
                'watts_per_area': {
                    'field_name': 'Watts per Zone Floor Area',
                    'field_index': 5,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W/m²',
                    'typical_range': [1.0, 50.0]
                },
                'watts_per_person': {
                    'field_name': 'Watts per Person',
                    'field_index': 6,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W/person',
                    'typical_range': [50, 500]
                },
                'fraction_latent': {
                    'field_name': 'Fraction Latent',
                    'field_index': 7,
                    'units': 'fraction',
                    'typical_range': [0.0, 0.5]
                },
                'fraction_radiant': {
                    'field_name': 'Fraction Radiant',
                    'field_index': 8,
                    'units': 'fraction',
                    'typical_range': [0.1, 0.5]
                },
                'fraction_lost': {
                    'field_name': 'Fraction Lost',
                    'field_index': 9,
                    'units': 'fraction',
                    'typical_range': [0.0, 0.3]
                }
            },
            'GASEQUIPMENT': {
                'design_level': {
                    'field_name': 'Design Level',
                    'field_index': 4,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W',
                    'typical_range': [100, 50000]
                },
                'power_per_area': {
                    'field_name': 'Power per Zone Floor Area',
                    'field_index': 5,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W/m²',
                    'typical_range': [1.0, 100.0]
                },
                'power_per_person': {
                    'field_name': 'Power per Person',
                    'field_index': 6,
                    'calc_method_field': 'Design Level Calculation Method',
                    'calc_method_index': 3,
                    'units': 'W/person',
                    'typical_range': [50, 1000]
                },
                'fraction_latent': {
                    'field_name': 'Fraction Latent',
                    'field_index': 7,
                    'units': 'fraction',
                    'typical_range': [0.0, 0.5]
                },
                'fraction_radiant': {
                    'field_name': 'Fraction Radiant',
                    'field_index': 8,
                    'units': 'fraction',
                    'typical_range': [0.1, 0.5]
                },
                'fraction_lost': {
                    'field_name': 'Fraction Lost',
                    'field_index': 9,
                    'units': 'fraction',
                    'typical_range': [0.0, 0.3]
                },
                'carbon_dioxide_rate': {
                    'field_name': 'Carbon Dioxide Generation Rate',
                    'field_index': 10,
                    'units': 'm³/s-W',
                    'typical_range': [0.0, 0.0000001]
                }
            },
            'EXTERIOREQUIPMENT': {
                'design_level': {
                    'field_name': 'Design Level',
                    'field_index': 3,
                    'units': 'W',
                    'typical_range': [100, 100000]
                }
            }
        }
    
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """Identify all equipment parameters in the IDF"""
        parameters = []
        
        # Process each equipment type
        for equip_category, equip_types in self.equipment_objects.items():
            for equip_type in equip_types:
                if equip_type in idf.idfobjects:
                    for equipment in idf.idfobjects[equip_type]:
                        if equip_type in self.parameter_map:
                            param_defs = self.parameter_map[equip_type]
                            
                            # For equipment with calculation methods
                            if equip_type in ['ELECTRICEQUIPMENT', 'GASEQUIPMENT']:
                                # Get calculation method
                                calc_method_index = param_defs['design_level']['calc_method_index']
                                calc_method = equipment.obj[calc_method_index] if len(equipment.obj) > calc_method_index else None
                                
                                # Extract appropriate parameter based on calc method
                                if calc_method == 'EquipmentLevel':
                                    param_def = param_defs['design_level']
                                elif calc_method == 'Watts/Area' or calc_method == 'Power/Area':
                                    param_key = 'watts_per_area' if equip_type == 'ELECTRICEQUIPMENT' else 'power_per_area'
                                    param_def = param_defs[param_key]
                                elif calc_method == 'Watts/Person' or calc_method == 'Power/Person':
                                    param_key = 'watts_per_person' if equip_type == 'ELECTRICEQUIPMENT' else 'power_per_person'
                                    param_def = param_defs[param_key]
                                else:
                                    continue
                                
                                # Extract value
                                field_index = param_def['field_index']
                                if len(equipment.obj) > field_index:
                                    current_value = equipment.obj[field_index]
                                    
                                    if current_value and current_value != '' and float(current_value) > 0:
                                        param = ModificationParameter(
                                            object_type=equip_type,
                                            object_name=equipment.Name,
                                            field_name=param_def['field_name'],
                                            field_index=field_index,
                                            current_value=float(current_value),
                                            units=param_def['units'],
                                            constraints={
                                                'min_value': param_def['typical_range'][0],
                                                'max_value': param_def['typical_range'][1],
                                                'calc_method': calc_method
                                            }
                                        )
                                        parameters.append(param)
                            
                            # Always check fractions
                            for fraction_type in ['fraction_latent', 'fraction_radiant', 'fraction_lost']:
                                if fraction_type in param_defs:
                                    param_def = param_defs[fraction_type]
                                    field_index = param_def['field_index']
                                    if len(equipment.obj) > field_index:
                                        current_value = equipment.obj[field_index]
                                        
                                        if current_value and current_value != '':
                                            param = ModificationParameter(
                                                object_type=equip_type,
                                                object_name=equipment.Name,
                                                field_name=param_def['field_name'],
                                                field_index=field_index,
                                                current_value=float(current_value),
                                                units=param_def['units'],
                                                constraints={
                                                    'min_value': param_def['typical_range'][0],
                                                    'max_value': param_def['typical_range'][1]
                                                }
                                            )
                                            parameters.append(param)
        
        self.logger.info(f"Identified {len(parameters)} equipment parameters")
        return parameters
    
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate modification values for equipment parameters"""
        if strategy == 'performance':
            return self._generate_performance_modifications(parameters, options)
        elif strategy == 'efficiency_upgrade':
            return self._generate_efficiency_modifications(parameters, options)
        elif strategy == 'load_reduction':
            return self._generate_load_reduction_modifications(parameters, options)
        elif strategy == 'schedule_optimization':
            return self._generate_schedule_modifications(parameters, options)
        elif strategy == 'random':
            return self._generate_random_modifications(parameters, options)
        else:
            return self._generate_default_modifications(parameters, options)
    
    def _generate_performance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance-based equipment modifications"""
        modification_set = {}
        
        # Get power multiplier
        power_mult = options.get('power_multiplier', 0.8)  # 20% reduction default
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if any(keyword in param.field_name.lower() for keyword in 
                   ['design level', 'watts', 'power']):
                # Reduce equipment power
                new_value = self.apply_multiplier(param.current_value,
                                                power_mult,
                                                min_val=param.constraints.get('min_value', 1.0))
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Fraction Lost':
                # Reduce losses (more efficient equipment)
                new_value = self.apply_multiplier(param.current_value,
                                                0.5,  # Halve losses
                                                min_val=0.0)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_efficiency_modifications(self,
                                         parameters: List[ModificationParameter],
                                         options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate efficiency upgrade modifications"""
        modification_set = {}
        
        # Get space type and target level
        space_type = options.get('space_type', 'office')
        target_level = options.get('target_level', 'efficient')
        
        target_epd = self.typical_epd.get(space_type, {}).get(target_level, 7.5)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if param.field_name == 'Watts per Zone Floor Area':
                # Set to target EPD
                if param.current_value > target_epd:
                    modification_set[param_id] = target_epd
                    
            elif param.field_name == 'Design Level':
                # Reduce by efficiency factor
                efficiency_factor = 0.7  # 30% more efficient
                new_value = param.current_value * efficiency_factor
                modification_set[param_id] = new_value
                
            elif param.field_name == 'Fraction Lost':
                # Efficient equipment has lower losses
                modification_set[param_id] = 0.05
                
            elif param.field_name == 'Fraction Radiant':
                # Efficient equipment typically has lower radiant fraction
                modification_set[param_id] = 0.2
                
        return [modification_set]
    
    def _generate_load_reduction_modifications(self,
                                             parameters: List[ModificationParameter],
                                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate load reduction modifications"""
        modification_set = {}
        
        # Reduction strategies
        reduction_target = options.get('reduction_percentage', 0.3)  # 30% reduction
        
        # Equipment types to prioritize for reduction
        priority_equipment = options.get('priority_types', ['ELECTRICEQUIPMENT'])
        
        for param in parameters:
            if param.object_type in priority_equipment:
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                if any(keyword in param.field_name.lower() for keyword in 
                       ['design level', 'watts', 'power']):
                    # Apply reduction
                    new_value = param.current_value * (1 - reduction_target)
                    new_value = max(new_value, 1.0)  # Minimum 1W
                    modification_set[param_id] = new_value
                    
        return [modification_set]
    
    def _generate_schedule_modifications(self,
                                       parameters: List[ModificationParameter],
                                       options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate schedule-based modifications (affects peak loads)"""
        modification_set = {}
        
        # Peak shaving factor
        peak_reduction = options.get('peak_reduction', 0.15)  # 15% peak reduction
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            # Check if this is office equipment (likely to be scheduled)
            if 'office' in param.object_name.lower() or 'computer' in param.object_name.lower():
                if any(keyword in param.field_name.lower() for keyword in 
                       ['design level', 'watts', 'power']):
                    # Reduce peak load (assuming schedule optimization)
                    new_value = param.current_value * (1 - peak_reduction)
                    modification_set[param_id] = new_value
                    
        return [modification_set]
    
    def _generate_random_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate random equipment modifications"""
        modification_set = {}
        
        seed = options.get('seed', None)
        if seed:
            np.random.seed(seed)
            
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            if any(keyword in param.field_name.lower() for keyword in 
                   ['design level', 'watts', 'power']):
                # Random reduction between 10-40%
                multiplier = np.random.uniform(0.6, 0.9)
                new_value = self.apply_multiplier(param.current_value,
                                                multiplier,
                                                min_val=param.constraints.get('min_value', 1.0))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_default_modifications(self,
                                      parameters: List[ModificationParameter],
                                      options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default equipment modifications - 15% reduction"""
        modification_set = {}
        
        for param in parameters:
            if any(keyword in param.field_name.lower() for keyword in 
                   ['design level', 'watts', 'power']):
                param_id = self.create_parameter_id(param.object_type,
                                                  param.object_name,
                                                  param.field_name)
                
                new_value = self.apply_multiplier(param.current_value, 0.85,
                                                min_val=param.constraints.get('min_value', 1.0))
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def apply_modifications(self, idf: IDF, modifications: Dict[str, Any]) -> bool:
        """Apply equipment modifications to IDF"""
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
                                        
                                        # Check calculation method if applicable
                                        if 'calc_method_index' in param_def:
                                            calc_method = obj.obj[param_def['calc_method_index']]
                                            
                                            # Skip if wrong calculation method
                                            if field_name == 'Watts per Zone Floor Area' and calc_method != 'Watts/Area':
                                                continue
                                            elif field_name == 'Design Level' and calc_method != 'EquipmentLevel':
                                                continue
                                        
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
                
        self.logger.info(f"Applied {applied_count} equipment modifications")
        return success
    
    def validate_equipment_loads(self, idf: IDF) -> Tuple[bool, List[str]]:
        """Validate equipment loads after modifications"""
        errors = []
        
        # Check electric equipment
        for equip in idf.idfobjects.get('ELECTRICEQUIPMENT', []):
            calc_method = equip.Design_Level_Calculation_Method if hasattr(equip, 'Design_Level_Calculation_Method') else None
            
            if calc_method == 'Watts/Area':
                epd = float(equip.Watts_per_Zone_Floor_Area) if equip.Watts_per_Zone_Floor_Area else 0
                if epd < 0:
                    errors.append(f"{equip.Name}: Negative power density ({epd} W/m²)")
                elif epd > 1000 and 'data' not in equip.Name.lower():
                    errors.append(f"{equip.Name}: Very high power density ({epd} W/m²)")
                    
            # Check fractions
            if hasattr(equip, 'Fraction_Latent') and hasattr(equip, 'Fraction_Radiant') and hasattr(equip, 'Fraction_Lost'):
                latent = float(equip.Fraction_Latent) if equip.Fraction_Latent else 0
                radiant = float(equip.Fraction_Radiant) if equip.Fraction_Radiant else 0
                lost = float(equip.Fraction_Lost) if equip.Fraction_Lost else 0
                total = latent + radiant + lost
                
                if total > 1.0:
                    errors.append(f"{equip.Name}: Heat fractions sum > 1.0 ({total})")
        
        # Check gas equipment
        for equip in idf.idfobjects.get('GASEQUIPMENT', []):
            if hasattr(equip, 'Carbon_Dioxide_Generation_Rate'):
                co2_rate = float(equip.Carbon_Dioxide_Generation_Rate) if equip.Carbon_Dioxide_Generation_Rate else 0
                if co2_rate < 0:
                    errors.append(f"{equip.Name}: Negative CO2 generation rate")
                elif co2_rate > 0.0001:
                    errors.append(f"{equip.Name}: Very high CO2 generation rate ({co2_rate})")
        
        return len(errors) == 0, errors
    
    def calculate_total_equipment_load(self, idf: IDF, zone_name: str = None) -> float:
        """Calculate total equipment load for a zone or building"""
        total_load = 0.0
        
        # Get zone area if specified
        zone_area = None
        if zone_name:
            for zone in idf.idfobjects.get('ZONE', []):
                if zone.Name == zone_name:
                    zone_area = float(zone.Floor_Area) if zone.Floor_Area and zone.Floor_Area != 'autocalculate' else None
                    break
        
        # Sum equipment loads
        for equip_type in ['ELECTRICEQUIPMENT', 'GASEQUIPMENT']:
            for equip in idf.idfobjects.get(equip_type, []):
                # Check if equipment is in specified zone
                if zone_name and hasattr(equip, 'Zone_or_ZoneList_or_Space_or_SpaceList_Name'):
                    if equip.Zone_or_ZoneList_or_Space_or_SpaceList_Name != zone_name:
                        continue
                
                calc_method = equip.Design_Level_Calculation_Method if hasattr(equip, 'Design_Level_Calculation_Method') else None
                
                if calc_method == 'EquipmentLevel':
                    load = float(equip.Design_Level) if equip.Design_Level else 0
                    total_load += load
                    
                elif calc_method == 'Watts/Area' and zone_area:
                    power_density = float(equip.Watts_per_Zone_Floor_Area) if equip.Watts_per_Zone_Floor_Area else 0
                    load = power_density * zone_area
                    total_load += load
        
        return total_load
