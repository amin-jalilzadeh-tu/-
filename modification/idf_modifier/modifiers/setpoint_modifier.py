"""
Setpoint Modifier Module - Handle thermostat setpoint modifications
"""
from typing import Dict, List, Any, Optional, Tuple, Set
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
import logging
import re

from ..base_modifier import BaseModifier, ModificationParameter


class SetpointModifier(BaseModifier):
    """Modifier for thermostat setpoint parameters"""
    
    def __init__(self, category: str = 'setpoints', parsed_data_path=None):
        super().__init__(category, parsed_data_path)
        self.logger = logging.getLogger(__name__)
        
        # Define setpoint object types
        self.setpoint_objects = {
            'thermostats': [
                'THERMOSTATSETPOINT:DUALSETPOINT',
                'THERMOSTATSETPOINT:SINGLEHEATING',
                'THERMOSTATSETPOINT:SINGLECOOLING'
            ],
            'schedules': [
                'SCHEDULE:COMPACT',
                'SCHEDULE:CONSTANT',
                'SCHEDULE:DAY:HOURLY',
                'SCHEDULE:DAY:INTERVAL',
                'SCHEDULE:WEEK:DAILY',
                'SCHEDULE:YEAR'
            ],
            'controls': [
                'ZONECONTROL:THERMOSTAT',
                'ZONECONTROL:HUMIDISTAT',
                'ZONECONTROL:THERMOSTAT:OPERATIVETEMPERATURE'
            ]
        }
        
        # Typical setpoint ranges by building type (°C)
        self.typical_setpoints = {
            'office': {
                'heating': {'occupied': 21.0, 'unoccupied': 15.0},
                'cooling': {'occupied': 24.0, 'unoccupied': 28.0},
                'deadband': 3.0
            },
            'residential': {
                'heating': {'occupied': 20.0, 'unoccupied': 18.0},
                'cooling': {'occupied': 25.0, 'unoccupied': 28.0},
                'deadband': 5.0
            },
            'retail': {
                'heating': {'occupied': 20.0, 'unoccupied': 14.0},
                'cooling': {'occupied': 24.0, 'unoccupied': 30.0},
                'deadband': 4.0
            },
            'warehouse': {
                'heating': {'occupied': 18.0, 'unoccupied': 10.0},
                'cooling': {'occupied': 26.0, 'unoccupied': 35.0},
                'deadband': 8.0
            },
            'healthcare': {
                'heating': {'occupied': 22.0, 'unoccupied': 20.0},
                'cooling': {'occupied': 23.0, 'unoccupied': 25.0},
                'deadband': 1.0
            }
        }
        
        # Parameter definitions
        self.parameter_map = self._build_parameter_map()
        
    def _build_parameter_map(self) -> Dict[str, Dict[str, Any]]:
        """Build parameter mapping for setpoint objects"""
        return {
            'THERMOSTATSETPOINT:DUALSETPOINT': {
                'heating_schedule': {
                    'field_name': 'Heating Setpoint Temperature Schedule Name',
                    'field_index': 1,
                    'type': 'schedule_reference'
                },
                'cooling_schedule': {
                    'field_name': 'Cooling Setpoint Temperature Schedule Name',
                    'field_index': 2,
                    'type': 'schedule_reference'
                }
            },
            'THERMOSTATSETPOINT:SINGLEHEATING': {
                'setpoint_schedule': {
                    'field_name': 'Setpoint Temperature Schedule Name',
                    'field_index': 1,
                    'type': 'schedule_reference'
                }
            },
            'THERMOSTATSETPOINT:SINGLECOOLING': {
                'setpoint_schedule': {
                    'field_name': 'Setpoint Temperature Schedule Name',
                    'field_index': 1,
                    'type': 'schedule_reference'
                }
            },
            'SCHEDULE:COMPACT': {
                'temperature_values': {
                    'field_name': 'Temperature Values',
                    'type': 'variable_fields',
                    'typical_range': [10.0, 35.0]
                }
            },
            'SCHEDULE:CONSTANT': {
                'value': {
                    'field_name': 'Hourly Value',
                    'field_index': 2,
                    'typical_range': [10.0, 35.0]
                }
            }
        }
    
    def identify_parameters(self, idf: IDF, building_id: str) -> List[ModificationParameter]:
        """Identify all setpoint parameters in the IDF"""
        parameters = []
        
        # First, find all thermostat setpoint schedules
        heating_schedules = set()
        cooling_schedules = set()
        
        # Process thermostat objects
        for tstat_type in self.setpoint_objects['thermostats']:
            if tstat_type in idf.idfobjects:
                for tstat in idf.idfobjects[tstat_type]:
                    if tstat_type == 'THERMOSTATSETPOINT:DUALSETPOINT':
                        if hasattr(tstat, 'Heating_Setpoint_Temperature_Schedule_Name'):
                            heating_schedules.add(tstat.Heating_Setpoint_Temperature_Schedule_Name)
                        if hasattr(tstat, 'Cooling_Setpoint_Temperature_Schedule_Name'):
                            cooling_schedules.add(tstat.Cooling_Setpoint_Temperature_Schedule_Name)
                    
                    elif tstat_type == 'THERMOSTATSETPOINT:SINGLEHEATING':
                        if hasattr(tstat, 'Setpoint_Temperature_Schedule_Name'):
                            heating_schedules.add(tstat.Setpoint_Temperature_Schedule_Name)
                    
                    elif tstat_type == 'THERMOSTATSETPOINT:SINGLECOOLING':
                        if hasattr(tstat, 'Setpoint_Temperature_Schedule_Name'):
                            cooling_schedules.add(tstat.Setpoint_Temperature_Schedule_Name)
        
        # Now process the identified schedules
        all_setpoint_schedules = heating_schedules.union(cooling_schedules)
        
        # Process SCHEDULE:COMPACT objects
        if 'SCHEDULE:COMPACT' in idf.idfobjects:
            for schedule in idf.idfobjects['SCHEDULE:COMPACT']:
                if schedule.Name in all_setpoint_schedules:
                    # Determine if heating or cooling
                    schedule_type = 'heating' if schedule.Name in heating_schedules else 'cooling'
                    
                    # Extract temperature values from compact schedule
                    temp_values = self._extract_compact_schedule_values(schedule)
                    
                    for time_period, temp_value in temp_values.items():
                        param = ModificationParameter(
                            object_type='SCHEDULE:COMPACT',
                            object_name=schedule.Name,
                            field_name=f'Temperature_{time_period}',
                            field_index=-1,  # Variable position in compact schedules
                            current_value=temp_value,
                            units='°C',
                            constraints={
                                'min_value': 10.0,
                                'max_value': 35.0,
                                'schedule_type': schedule_type,
                                'time_period': time_period
                            }
                        )
                        parameters.append(param)
        
        # Process SCHEDULE:CONSTANT objects
        if 'SCHEDULE:CONSTANT' in idf.idfobjects:
            for schedule in idf.idfobjects['SCHEDULE:CONSTANT']:
                if schedule.Name in all_setpoint_schedules:
                    schedule_type = 'heating' if schedule.Name in heating_schedules else 'cooling'
                    
                    if hasattr(schedule, 'Hourly_Value') and schedule.Hourly_Value:
                        param = ModificationParameter(
                            object_type='SCHEDULE:CONSTANT',
                            object_name=schedule.Name,
                            field_name='Hourly Value',
                            field_index=2,
                            current_value=float(schedule.Hourly_Value),
                            units='°C',
                            constraints={
                                'min_value': 10.0,
                                'max_value': 35.0,
                                'schedule_type': schedule_type
                            }
                        )
                        parameters.append(param)
        
        self.logger.info(f"Identified {len(parameters)} setpoint parameters")
        return parameters
    
    def _extract_compact_schedule_values(self, schedule) -> Dict[str, float]:
        """Extract temperature values from a compact schedule"""
        values = {}
        current_type = None
        
        # Parse through schedule fields
        for i in range(2, len(schedule.obj)):  # Skip name and type limits
            field = schedule.obj[i]
            
            if not field:
                continue
                
            # Check if this is a control statement
            field_str = str(field).lower()
            if any(keyword in field_str for keyword in 
                   ['through:', 'for:', 'until:', 'weekdays', 'weekends', 
                    'alldays', 'saturday', 'sunday', 'holiday', 'summerdesignday',
                    'winterdesignday', 'allotherdays']):
                # Track the current period type
                if 'weekdays' in field_str:
                    current_type = 'weekdays'
                elif 'weekends' in field_str:
                    current_type = 'weekends'
                elif 'alldays' in field_str:
                    current_type = 'alldays'
                continue
            
            # Try to parse as temperature value
            try:
                temp_value = float(field)
                # Check if this is a reasonable temperature value
                if 5.0 <= temp_value <= 40.0:
                    # Store with appropriate key
                    if current_type:
                        key = f"{current_type}_{len(values)}"
                    else:
                        key = f"value_{len(values)}"
                    values[key] = temp_value
            except ValueError:
                continue
                
        return values
    
    def generate_modifications(self, 
                             parameters: List[ModificationParameter],
                             strategy: str,
                             options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate modification values for setpoint parameters"""
        if strategy == 'performance':
            return self._generate_performance_modifications(parameters, options)
        elif strategy == 'adaptive_comfort':
            return self._generate_adaptive_comfort_modifications(parameters, options)
        elif strategy == 'extended_setback':
            return self._generate_extended_setback_modifications(parameters, options)
        elif strategy == 'demand_response':
            return self._generate_demand_response_modifications(parameters, options)
        elif strategy == 'random':
            return self._generate_random_modifications(parameters, options)
        else:
            return self._generate_default_modifications(parameters, options)
    
    def _generate_performance_modifications(self,
                                          parameters: List[ModificationParameter],
                                          options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate performance-based setpoint modifications"""
        modification_set = {}
        
        # Get adjustments
        heating_adjustment = options.get('heating_adjustment', -1.0)  # Lower by 1°C
        cooling_adjustment = options.get('cooling_adjustment', 1.0)   # Raise by 1°C
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            schedule_type = param.constraints.get('schedule_type', 'unknown')
            
            if schedule_type == 'heating':
                # Lower heating setpoints
                new_value = self.apply_offset(param.current_value,
                                            heating_adjustment,
                                            min_val=15.0,
                                            max_val=25.0)
                modification_set[param_id] = new_value
                
            elif schedule_type == 'cooling':
                # Raise cooling setpoints
                new_value = self.apply_offset(param.current_value,
                                            cooling_adjustment,
                                            min_val=20.0,
                                            max_val=30.0)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_adaptive_comfort_modifications(self,
                                               parameters: List[ModificationParameter],
                                               options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate adaptive comfort based modifications"""
        modification_set = {}
        
        # Building type for comfort ranges
        building_type = options.get('building_type', 'office')
        comfort_ranges = self.typical_setpoints.get(building_type, self.typical_setpoints['office'])
        
        # Adaptive comfort band expansion
        band_expansion = options.get('comfort_band_expansion', 2.0)  # °C
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            schedule_type = param.constraints.get('schedule_type', 'unknown')
            time_period = param.constraints.get('time_period', '')
            
            # Determine if occupied or unoccupied period
            is_occupied = 'weekday' in time_period.lower() or 'allday' in time_period.lower()
            
            if schedule_type == 'heating':
                if is_occupied:
                    # Slightly lower occupied heating
                    new_value = comfort_ranges['heating']['occupied'] - band_expansion/2
                else:
                    # More aggressive unoccupied setback
                    new_value = comfort_ranges['heating']['unoccupied'] - band_expansion
                
                new_value = max(new_value, 10.0)  # Minimum 10°C
                modification_set[param_id] = new_value
                
            elif schedule_type == 'cooling':
                if is_occupied:
                    # Slightly higher occupied cooling
                    new_value = comfort_ranges['cooling']['occupied'] + band_expansion/2
                else:
                    # More aggressive unoccupied setup
                    new_value = comfort_ranges['cooling']['unoccupied'] + band_expansion
                
                new_value = min(new_value, 35.0)  # Maximum 35°C
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def _generate_extended_setback_modifications(self,
                                               parameters: List[ModificationParameter],
                                               options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate extended setback modifications"""
        modification_set = {}
        
        # Setback parameters
        heating_setback = options.get('heating_setback_temp', 15.0)
        cooling_setup = options.get('cooling_setup_temp', 30.0)
        maintain_occupied = options.get('maintain_occupied_setpoints', True)
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            schedule_type = param.constraints.get('schedule_type', 'unknown')
            time_period = param.constraints.get('time_period', '')
            
            # Only modify unoccupied periods
            is_unoccupied = 'weekend' in time_period.lower() or 'night' in time_period.lower()
            
            if is_unoccupied or not maintain_occupied:
                if schedule_type == 'heating':
                    modification_set[param_id] = heating_setback
                elif schedule_type == 'cooling':
                    modification_set[param_id] = cooling_setup
            else:
                # Small adjustment for occupied periods
                if schedule_type == 'heating':
                    new_value = param.current_value - 0.5
                    modification_set[param_id] = max(new_value, 18.0)
                elif schedule_type == 'cooling':
                    new_value = param.current_value + 0.5
                    modification_set[param_id] = min(new_value, 26.0)
                    
        return [modification_set]
    
    def _generate_demand_response_modifications(self,
                                              parameters: List[ModificationParameter],
                                              options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate demand response modifications"""
        modification_set = {}
        
        # DR event parameters
        dr_offset = options.get('demand_response_offset', 3.0)  # °C
        peak_hours = options.get('peak_hours', [14, 15, 16, 17])  # 2-5 PM
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            schedule_type = param.constraints.get('schedule_type', 'unknown')
            time_period = param.constraints.get('time_period', '')
            
            # Check if this is a peak period
            is_peak = any(str(hour) in time_period for hour in peak_hours)
            
            if is_peak:
                if schedule_type == 'cooling':
                    # Raise cooling setpoint during DR event
                    new_value = param.current_value + dr_offset
                    new_value = min(new_value, 28.0)  # Cap at 28°C
                    modification_set[param_id] = new_value
                elif schedule_type == 'heating':
                    # Lower heating setpoint during DR event
                    new_value = param.current_value - dr_offset
                    new_value = max(new_value, 18.0)  # Floor at 18°C
                    modification_set[param_id] = new_value
            else:
                # Pre-cooling/heating strategy
                if schedule_type == 'cooling' and any(str(h) in time_period for h in [12, 13]):
                    # Pre-cool before DR event
                    new_value = param.current_value - 1.0
                    modification_set[param_id] = new_value
                    
        return [modification_set]
    
    def _generate_random_modifications(self,
                                     parameters: List[ModificationParameter],
                                     options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate random setpoint modifications"""
        modification_set = {}
        
        seed = options.get('seed', None)
        if seed:
            np.random.seed(seed)
            
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            schedule_type = param.constraints.get('schedule_type', 'unknown')
            
            if schedule_type == 'heating':
                # Random adjustment between -2 and 0°C
                offset = np.random.uniform(-2.0, 0.0)
                new_value = self.apply_offset(param.current_value, offset,
                                            min_val=15.0, max_val=25.0)
            elif schedule_type == 'cooling':
                # Random adjustment between 0 and 2°C
                offset = np.random.uniform(0.0, 2.0)
                new_value = self.apply_offset(param.current_value, offset,
                                            min_val=20.0, max_val=30.0)
            else:
                new_value = param.current_value
                
            modification_set[param_id] = new_value
            
        return [modification_set]
    
    def _generate_default_modifications(self,
                                      parameters: List[ModificationParameter],
                                      options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Default setpoint modifications - widen deadband"""
        modification_set = {}
        
        for param in parameters:
            param_id = self.create_parameter_id(param.object_type,
                                              param.object_name,
                                              param.field_name)
            
            schedule_type = param.constraints.get('schedule_type', 'unknown')
            
            if schedule_type == 'heating':
                # Lower by 1°C
                new_value = self.apply_offset(param.current_value, -1.0,
                                            min_val=15.0, max_val=25.0)
                modification_set[param_id] = new_value
            elif schedule_type == 'cooling':
                # Raise by 1°C
                new_value = self.apply_offset(param.current_value, 1.0,
                                            min_val=20.0, max_val=30.0)
                modification_set[param_id] = new_value
                
        return [modification_set]
    
    def apply_modifications(self, idf: IDF, modifications: Dict[str, Any]) -> bool:
        """Apply setpoint modifications to IDF"""
        success = True
        applied_count = 0
        
        for param_id, new_value in modifications.items():
            try:
                # Parse parameter ID
                obj_type, obj_name, field_name = self.parse_parameter_id(param_id)
                
                # Special handling for compact schedules
                if obj_type == 'SCHEDULE:COMPACT':
                    success_local = self._modify_compact_schedule(idf, obj_name, 
                                                                 field_name, new_value)
                    if success_local:
                        applied_count += 1
                    else:
                        success = False
                        
                elif obj_type == 'SCHEDULE:CONSTANT':
                    # Modify constant schedule
                    for schedule in idf.idfobjects['SCHEDULE:CONSTANT']:
                        if schedule.Name == obj_name:
                            old_value = schedule.Hourly_Value
                            schedule.Hourly_Value = new_value
                            self.logger.debug(f"Modified {obj_name} constant value: "
                                            f"{old_value} → {new_value}")
                            applied_count += 1
                            break
                            
            except Exception as e:
                self.logger.error(f"Error applying modification {param_id}: {e}")
                success = False
                
        self.logger.info(f"Applied {applied_count} setpoint modifications")
        return success
    
    def _modify_compact_schedule(self, idf: IDF, schedule_name: str, 
                               field_name: str, new_value: float) -> bool:
        """Modify a value in a compact schedule"""
        for schedule in idf.idfobjects['SCHEDULE:COMPACT']:
            if schedule.Name == schedule_name:
                # Find and modify the appropriate value
                modified = False
                
                for i in range(2, len(schedule.obj)):
                    field = schedule.obj[i]
                    if not field:
                        continue
                        
                    # Try to parse as temperature value
                    try:
                        temp_value = float(field)
                        # Check if this is a temperature value
                        if 5.0 <= temp_value <= 40.0:
                            # Simple approach: modify all temperature values
                            # In practice, would need more sophisticated matching
                            schedule.obj[i] = new_value
                            modified = True
                            self.logger.debug(f"Modified {schedule_name} compact schedule: "
                                            f"{temp_value} → {new_value}")
                    except ValueError:
                        continue
                        
                return modified
                
        return False
    
    def validate_setpoints(self, idf: IDF) -> Tuple[bool, List[str]]:
        """Validate setpoints after modifications"""
        errors = []
        
        # Track heating and cooling setpoints by zone
        zone_setpoints = {}
        
        # Process thermostats
        for tstat in idf.idfobjects.get('THERMOSTATSETPOINT:DUALSETPOINT', []):
            heating_schedule = tstat.Heating_Setpoint_Temperature_Schedule_Name
            cooling_schedule = tstat.Cooling_Setpoint_Temperature_Schedule_Name
            
            # Get setpoint values from schedules
            heating_temps = self._get_schedule_values(idf, heating_schedule)
            cooling_temps = self._get_schedule_values(idf, cooling_schedule)
            
            # Check for reasonable values
            if heating_temps:
                min_heat = min(heating_temps)
                max_heat = max(heating_temps)
                if min_heat < 10:
                    errors.append(f"{tstat.Name}: Heating setpoint too low ({min_heat}°C)")
                if max_heat > 30:
                    errors.append(f"{tstat.Name}: Heating setpoint too high ({max_heat}°C)")
                    
            if cooling_temps:
                min_cool = min(cooling_temps)
                max_cool = max(cooling_temps)
                if min_cool < 18:
                    errors.append(f"{tstat.Name}: Cooling setpoint too low ({min_cool}°C)")
                if max_cool > 35:
                    errors.append(f"{tstat.Name}: Cooling setpoint too high ({max_cool}°C)")
                    
            # Check deadband
            if heating_temps and cooling_temps:
                avg_heat = sum(heating_temps) / len(heating_temps)
                avg_cool = sum(cooling_temps) / len(cooling_temps)
                deadband = avg_cool - avg_heat
                
                if deadband < 0.5:
                    errors.append(f"{tstat.Name}: Deadband too small ({deadband}°C)")
                elif deadband > 10:
                    errors.append(f"{tstat.Name}: Deadband too large ({deadband}°C)")
        
        return len(errors) == 0, errors
    
    def _get_schedule_values(self, idf: IDF, schedule_name: str) -> List[float]:
        """Extract all temperature values from a schedule"""
        values = []
        
        # Check constant schedules
        for schedule in idf.idfobjects.get('SCHEDULE:CONSTANT', []):
            if schedule.Name == schedule_name:
                if schedule.Hourly_Value:
                    values.append(float(schedule.Hourly_Value))
                return values
        
        # Check compact schedules
        for schedule in idf.idfobjects.get('SCHEDULE:COMPACT', []):
            if schedule.Name == schedule_name:
                for i in range(2, len(schedule.obj)):
                    field = schedule.obj[i]
                    if field:
                        try:
                            temp_value = float(field)
                            if 5.0 <= temp_value <= 40.0:
                                values.append(temp_value)
                        except ValueError:
                            continue
                return values
                
        return values
    
    def create_optimized_schedule(self, idf: IDF, schedule_name: str,
                                heating_occupied: float = 21.0,
                                heating_unoccupied: float = 15.0,
                                cooling_occupied: float = 24.0,
                                cooling_unoccupied: float = 28.0,
                                is_heating: bool = True):
        """Create an optimized setpoint schedule"""
        # Create new compact schedule
        schedule_type = 'heating' if is_heating else 'cooling'
        occupied = heating_occupied if is_heating else cooling_occupied
        unoccupied = heating_unoccupied if is_heating else cooling_unoccupied
        
        idf.newidfobject(
            'SCHEDULE:COMPACT',
            Name=schedule_name,
            Schedule_Type_Limits_Name='Temperature',
            Field_1='Through: 12/31',
            Field_2='For: Weekdays',
            Field_3='Until: 6:00',
            Field_4=unoccupied,
            Field_5='Until: 7:00',
            Field_6=(occupied + unoccupied) / 2,  # Ramp up
            Field_7='Until: 8:00',
            Field_8=occupied,
            Field_9='Until: 18:00',
            Field_10=occupied,
            Field_11='Until: 19:00',
            Field_12=(occupied + unoccupied) / 2,  # Ramp down
            Field_13='Until: 24:00',
            Field_14=unoccupied,
            Field_15='For: Weekends',
            Field_16='Until: 24:00',
            Field_17=unoccupied,
            Field_18='For: Holidays',
            Field_19='Until: 24:00',
            Field_20=unoccupied,
            Field_21='For: SummerDesignDay',
            Field_22='Until: 24:00',
            Field_23=occupied if not is_heating else unoccupied,
            Field_24='For: WinterDesignDay',
            Field_25='Until: 24:00',
            Field_26=occupied if is_heating else unoccupied
        )
        
        self.logger.info(f"Created optimized {schedule_type} schedule: {schedule_name}")
