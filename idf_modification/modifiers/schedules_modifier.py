"""
Schedules Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
import re
from ..base_modifier import BaseModifier, ParameterDefinition

class SchedulesModifier(BaseModifier):
    """Modifier for schedule-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize schedule parameter definitions matching parser field names"""
        self.parameter_definitions = {
            'constant_value': ParameterDefinition(
                object_type='SCHEDULE:CONSTANT',
                field_name='Hourly Value',
                field_index=2,
                data_type=float,
                performance_impact='schedule_values'
            ),
            'lower_limit': ParameterDefinition(
                object_type='SCHEDULETYPELIMITS',
                field_name='Lower Limit Value',
                field_index=1,
                data_type=float,
                performance_impact='schedule_bounds'
            ),
            'upper_limit': ParameterDefinition(
                object_type='SCHEDULETYPELIMITS',
                field_name='Upper Limit Value', 
                field_index=2,
                data_type=float,
                performance_impact='schedule_bounds'
            ),
            # For Schedule:Compact, we handle fields dynamically
        }
    
    def get_category_name(self) -> str:
        return 'schedules'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'SCHEDULETYPELIMITS',
            'SCHEDULE:COMPACT',
            'SCHEDULE:CONSTANT',
            'SCHEDULE:DAY:HOURLY',
            'SCHEDULE:DAY:INTERVAL',
            'SCHEDULE:DAY:LIST',
            'SCHEDULE:WEEK:DAILY',
            'SCHEDULE:WEEK:COMPACT',
            'SCHEDULE:YEAR',
            'SCHEDULE:FILE'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['schedules']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply schedule-specific modifications"""
        
        if strategy == 'occupancy_optimization':
            return self._apply_occupancy_optimization(parsed_objects, modifiable_params)
        elif strategy == 'setback_setpoint':
            return self._apply_setback_setpoint(parsed_objects, modifiable_params)
        elif strategy == 'equipment_scheduling':
            return self._apply_equipment_scheduling(parsed_objects, modifiable_params)
        elif strategy == 'extended_hours':
            return self._apply_extended_hours(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_occupancy_optimization(self, parsed_objects, modifiable_params):
        """Optimize schedules based on occupancy patterns"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an occupancy schedule
                    if any(term in obj.name.upper() for term in ['OCCUPANCY', 'PEOPLE', 'OCC']):
                        modifications.extend(self._modify_compact_schedule_values(
                            obj, 'occupancy_optimization', reduction_factor=0.1
                        ))
            
            elif obj_type == 'SCHEDULE:CONSTANT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Reduce constant occupancy values
                    if 'OCCUPANCY' in obj.name.upper():
                        for param in obj.parameters:
                            if param.field_name == 'Hourly Value' and param.numeric_value:
                                old_value = param.numeric_value
                                # Reduce by 10% for better match to actual occupancy
                                new_value = old_value * 0.9
                                
                                param.value = str(new_value)
                                param.numeric_value = new_value
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'constant_value', old_value, new_value, 'occupancy_optimization'
                                ))
                                break
        
        return modifications
    
    def _apply_setback_setpoint(self, parsed_objects, modifiable_params):
        """Apply temperature setback during unoccupied hours"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a temperature setpoint schedule
                    if any(term in obj.name.upper() for term in ['SETPOINT', 'HEATING', 'COOLING', 'TEMP']):
                        if 'HEATING' in obj.name.upper():
                            # Lower heating setpoints during unoccupied hours
                            modifications.extend(self._modify_compact_schedule_values(
                                obj, 'setback_heating', temperature_adjustment=-2.0
                            ))
                        elif 'COOLING' in obj.name.upper():
                            # Raise cooling setpoints during unoccupied hours
                            modifications.extend(self._modify_compact_schedule_values(
                                obj, 'setback_cooling', temperature_adjustment=2.0
                            ))
        
        return modifications
    
    def _apply_equipment_scheduling(self, parsed_objects, modifiable_params):
        """Optimize equipment operation schedules"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an equipment schedule
                    if any(term in obj.name.upper() for term in ['EQUIPMENT', 'ELEC', 'PLUG']):
                        # Reduce equipment operation during low occupancy
                        modifications.extend(self._modify_compact_schedule_values(
                            obj, 'equipment_scheduling', reduction_factor=0.2
                        ))
        
        return modifications
    
    def _apply_extended_hours(self, parsed_objects, modifiable_params):
        """Extend operational hours for certain schedules"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an HVAC availability schedule
                    if any(term in obj.name.upper() for term in ['AVAILABILITY', 'FAN', 'HVAC']):
                        # Extend availability hours
                        modifications.extend(self._modify_compact_schedule_values(
                            obj, 'extended_hours', extend_operation=True
                        ))
        
        return modifications
    
    def _modify_compact_schedule_values(self, obj, rule, **kwargs):
        """Helper to modify Schedule:Compact values"""
        modifications = []
        import random
        
        # Schedule:Compact has variable fields after the first two
        # We need to parse through the fields to find time/value pairs
        for i, param in enumerate(obj.parameters):
            if i < 2:  # Skip name and type limit fields
                continue
            
            # Check if this is a numeric value (not a day type or time)
            if param.numeric_value is not None:
                # Check if previous parameter is a time specification
                if i > 0 and self._is_time_field(obj.parameters[i-1].value):
                    old_value = param.numeric_value
                    new_value = old_value
                    
                    if 'reduction_factor' in kwargs:
                        new_value = old_value * (1 - kwargs['reduction_factor'])
                    elif 'temperature_adjustment' in kwargs:
                        # For temperature schedules
                        time_str = obj.parameters[i-1].value
                        if self._is_unoccupied_time(time_str):
                            new_value = old_value + kwargs['temperature_adjustment']
                    elif 'extend_operation' in kwargs:
                        # For availability schedules (0 or 1)
                        if old_value < 0.5:  # Currently off
                            # Random chance to extend operation
                            if random.random() < 0.3:
                                new_value = 1.0
                    
                    if new_value != old_value:
                        param.value = str(new_value)
                        param.numeric_value = new_value
                        
                        modifications.append(self._create_modification_result(
                            obj, f'schedule_value_{i}', old_value, new_value, rule
                        ))
        
        return modifications
    
    def _is_time_field(self, value: str) -> bool:
        """Check if a field value represents a time"""
        if not value:
            return False
        # Common time patterns in Schedule:Compact
        time_patterns = [
            r'^\d{1,2}:\d{2}$',  # HH:MM
            r'^Until:\s*\d{1,2}:\d{2}$',  # Until: HH:MM
            r'^\d{1,2}:\d{2}:\d{2}$',  # HH:MM:SS
        ]
        return any(re.match(pattern, value.strip()) for pattern in time_patterns)
    
    def _is_unoccupied_time(self, time_str: str) -> bool:
        """Check if a time represents unoccupied hours"""
        # Simple check - before 7am or after 6pm
        match = re.search(r'(\d{1,2}):', time_str)
        if match:
            hour = int(match.group(1))
            return hour < 7 or hour >= 18
        return False