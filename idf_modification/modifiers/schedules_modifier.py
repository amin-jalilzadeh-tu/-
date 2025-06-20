"""
Schedule and occupancy pattern modifications.

This module handles modifications to schedule and occupancy pattern modifications.
"""
"""
Schedules Modifier - Handles schedule objects
"""
from typing import List, Dict, Any
import re
from ..base_modifier import BaseModifier, ParameterDefinition

class SchedulesModifier(BaseModifier):
    """Modifier for schedule-related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize schedule parameter definitions"""
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
            )
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
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply schedule-specific modifications"""
        
        if strategy == 'occupancy_optimization':
            return self._apply_occupancy_optimization(idf, modifiable_params)
        elif strategy == 'temperature_setback':
            return self._apply_temperature_setback(idf, modifiable_params)
        elif strategy == 'lighting_controls':
            return self._apply_lighting_controls(idf, modifiable_params)
        elif strategy == 'equipment_scheduling':
            return self._apply_equipment_scheduling(idf, modifiable_params)
        else:
            return super().apply_modifications(idf, modifiable_params, strategy)
    
    def _apply_occupancy_optimization(self, idf, modifiable_params):
        """Optimize occupancy schedules"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an occupancy schedule
                    if 'occup' in obj.Name.lower():
                        modifications.extend(
                            self._modify_compact_schedule_values(
                                obj, 
                                time_periods={'night': 0.0, 'early_morning': 0.05},
                                rule='occupancy_optimization'
                            )
                        )
        
        return modifications
    
    def _apply_temperature_setback(self, idf, modifiable_params):
        """Apply temperature setback strategies"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a heating setpoint schedule
                    if 'heat' in obj.Name.lower() and 'setpoint' in obj.Name.lower():
                        # Reduce nighttime and weekend heating setpoints
                        modifications.extend(
                            self._modify_temperature_schedule(
                                obj, 
                                adjustment=-2.0,  # 2°C setback
                                periods=['night', 'weekend'],
                                rule='heating_setback'
                            )
                        )
                    
                    # Check if this is a cooling setpoint schedule
                    elif 'cool' in obj.Name.lower() and 'setpoint' in obj.Name.lower():
                        # Increase nighttime and weekend cooling setpoints
                        modifications.extend(
                            self._modify_temperature_schedule(
                                obj, 
                                adjustment=2.0,  # 2°C setup
                                periods=['night', 'weekend'],
                                rule='cooling_setup'
                            )
                        )
        
        return modifications
    
    def _apply_lighting_controls(self, idf, modifiable_params):
        """Apply advanced lighting control schedules"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a lighting schedule
                    if 'light' in obj.Name.lower():
                        # Implement daylight dimming approximation
                        modifications.extend(
                            self._modify_compact_schedule_values(
                                obj,
                                multipliers={'day': 0.7, 'night': 0.1},
                                rule='daylight_dimming'
                            )
                        )
        
        return modifications
    
    def _apply_equipment_scheduling(self, idf, modifiable_params):
        """Optimize equipment operation schedules"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SCHEDULE:COMPACT':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is an equipment schedule
                    if 'equip' in obj.Name.lower():
                        # Reduce equipment operation during unoccupied hours
                        modifications.extend(
                            self._modify_compact_schedule_values(
                                obj,
                                multipliers={'night': 0.3, 'weekend': 0.5},
                                rule='equipment_scheduling'
                            )
                        )
        
        return modifications
    
    def _modify_compact_schedule_values(self, schedule_obj, 
                                      time_periods=None, 
                                      multipliers=None,
                                      rule='schedule_modification'):
        """Modify values in a Schedule:Compact object"""
        modifications = []
        
        # Schedule:Compact has variable structure after field 2
        # Need to parse through the fields to find and modify values
        
        current_time_period = None
        
        for i in range(2, len(schedule_obj.obj)):
            field_value = str(schedule_obj.obj[i])
            
            # Check if this is a time period identifier
            if any(keyword in field_value.lower() for keyword in 
                   ['through:', 'for:', 'weekdays', 'weekends', 'alldays']):
                # Track current period type
                if 'weekend' in field_value.lower():
                    current_time_period = 'weekend'
                elif 'weekday' in field_value.lower():
                    current_time_period = 'weekday'
                    
            # Check if this is a time specification
            elif 'until:' in field_value.lower():
                # Extract hour
                match = re.search(r'until:\s*(\d+):(\d+)', field_value.lower())
                if match:
                    hour = int(match.group(1))
                    if hour < 6:
                        current_time_period = 'night'
                    elif hour < 8:
                        current_time_period = 'early_morning'
                    elif hour < 18:
                        current_time_period = 'day'
                    else:
                        current_time_period = 'evening'
                        
            # Check if this is a numeric value
            else:
                try:
                    value = float(field_value)
                    
                    # Determine if we should modify this value
                    modify = False
                    new_value = value
                    
                    if time_periods and current_time_period in time_periods:
                        new_value = time_periods[current_time_period]
                        modify = True
                    elif multipliers and current_time_period in multipliers:
                        new_value = value * multipliers[current_time_period]
                        modify = True
                    
                    if modify and new_value != value:
                        # Apply the modification
                        schedule_obj.obj[i] = new_value
                        
                        # Track the modification
                        from ..base_modifier import ModificationResult
                        result = ModificationResult(
                            success=True,
                            object_type='SCHEDULE:COMPACT',
                            object_name=schedule_obj.Name,
                            parameter=f'value_field_{i}_{current_time_period}',
                            original_value=value,
                            new_value=new_value,
                            change_type='absolute',
                            rule_applied=rule,
                            validation_status='valid'
                        )
                        modifications.append(result)
                        
                except ValueError:
                    # Not a numeric value, skip
                    pass
        
        return modifications
    
    def _modify_temperature_schedule(self, schedule_obj, adjustment, periods, rule):
        """Modify temperature values in a schedule"""
        modifications = []
        
        current_period = None
        
        for i in range(2, len(schedule_obj.obj)):
            field_value = str(schedule_obj.obj[i])
            
            # Determine current period
            if 'weekend' in field_value.lower():
                current_period = 'weekend'
            elif 'weekday' in field_value.lower():
                current_period = 'weekday'
            elif 'until:' in field_value.lower():
                match = re.search(r'until:\s*(\d+):', field_value.lower())
                if match:
                    hour = int(match.group(1))
                    current_period = 'night' if hour < 6 or hour > 22 else 'day'
            
            # Check if this is a temperature value
            try:
                value = float(field_value)
                
                # Temperature values are typically between 10-35°C
                if 10 <= value <= 35 and current_period in periods:
                    new_value = value + adjustment
                    
                    # Apply limits
                    new_value = max(10, min(35, new_value))
                    
                    if new_value != value:
                        schedule_obj.obj[i] = new_value
                        
                        from ..base_modifier import ModificationResult
                        result = ModificationResult(
                            success=True,
                            object_type='SCHEDULE:COMPACT',
                            object_name=schedule_obj.Name,
                            parameter=f'temperature_{current_period}',
                            original_value=value,
                            new_value=new_value,
                            change_type='absolute',
                            rule_applied=rule,
                            validation_status='valid'
                        )
                        modifications.append(result)
                        
            except ValueError:
                pass
        
        return modifications