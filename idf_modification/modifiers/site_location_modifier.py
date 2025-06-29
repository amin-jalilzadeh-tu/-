"""
Site Location Modifier - Compatible with parsed IDF structure
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class SiteLocationModifier(BaseModifier):
    """Modifier for site and location related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize site location parameter definitions matching parser field names"""
        self.parameter_definitions = {
            # Site:Location parameters
            'latitude': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Latitude',
                field_index=1,
                data_type=float,
                units='degrees',
                min_value=-90,
                max_value=90,
                performance_impact='solar_angles'
            ),
            'longitude': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Longitude',
                field_index=2,
                data_type=float,
                units='degrees',
                min_value=-180,
                max_value=180,
                performance_impact='solar_timing'
            ),
            'time_zone': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Time Zone',
                field_index=3,
                data_type=float,
                units='hours',
                min_value=-12,
                max_value=14,
                performance_impact='solar_timing'
            ),
            'elevation': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Elevation',
                field_index=4,
                data_type=float,
                units='m',
                min_value=-300,
                max_value=8848,
                performance_impact='air_pressure'
            ),
            
            # Site:GroundTemperature parameters - ALL 12 MONTHS
            'ground_temp_january': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='January Ground Temperature',
                field_index=0,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_february': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='February Ground Temperature',
                field_index=1,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_march': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='March Ground Temperature',
                field_index=2,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_april': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='April Ground Temperature',
                field_index=3,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_may': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='May Ground Temperature',
                field_index=4,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_june': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='June Ground Temperature',
                field_index=5,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_july': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='July Ground Temperature',
                field_index=6,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_august': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='August Ground Temperature',
                field_index=7,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_september': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='September Ground Temperature',
                field_index=8,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_october': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='October Ground Temperature',
                field_index=9,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_november': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='November Ground Temperature',
                field_index=10,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            'ground_temp_december': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='December Ground Temperature',
                field_index=11,
                data_type=float,
                units='C',
                min_value=-30,
                max_value=40,
                performance_impact='ground_heat_transfer'
            ),
            
            # Site:WeatherStation parameters
            'wind_sensor_height': ParameterDefinition(
                object_type='SITE:HEIGHTVARIATION',
                field_name='Wind Sensor Height Above Ground',
                field_index=0,
                data_type=float,
                units='m',
                min_value=0.5,
                max_value=100,
                performance_impact='wind_calculations'
            ),
            
            # SizingPeriod:DesignDay parameters
            'design_day_max_temp': ParameterDefinition(
                object_type='SIZINGPERIOD:DESIGNDAY',
                field_name='Maximum Dry-Bulb Temperature',
                field_index=1,
                data_type=float,
                units='C',
                min_value=-50,
                max_value=60,
                performance_impact='equipment_sizing'
            ),
            'design_day_min_temp': ParameterDefinition(
                object_type='SIZINGPERIOD:DESIGNDAY',
                field_name='Minimum Dry-Bulb Temperature',
                field_index=2,
                data_type=float,
                units='C',
                min_value=-50,
                max_value=60,
                performance_impact='equipment_sizing'
            ),
            'design_day_humidity': ParameterDefinition(
                object_type='SIZINGPERIOD:DESIGNDAY',
                field_name='Humidity Condition at Maximum Dry-Bulb',
                field_index=10,
                data_type=float,
                units='kgWater/kgDryAir',
                min_value=0,
                max_value=0.03,
                performance_impact='equipment_sizing'
            ),
            
            # RunPeriod parameters
            'begin_month': ParameterDefinition(
                object_type='RUNPERIOD',
                field_name='Begin Month',
                field_index=1,
                data_type=int,
                min_value=1,
                max_value=12,
                performance_impact='simulation_period'
            ),
            'begin_day': ParameterDefinition(
                object_type='RUNPERIOD',
                field_name='Begin Day of Month',
                field_index=2,
                data_type=int,
                min_value=1,
                max_value=31,
                performance_impact='simulation_period'
            ),
            'end_month': ParameterDefinition(
                object_type='RUNPERIOD',
                field_name='End Month',
                field_index=3,
                data_type=int,
                min_value=1,
                max_value=12,
                performance_impact='simulation_period'
            ),
            'end_day': ParameterDefinition(
                object_type='RUNPERIOD',
                field_name='End Day of Month',
                field_index=4,
                data_type=int,
                min_value=1,
                max_value=31,
                performance_impact='simulation_period'
            )
        }
    def get_category_name(self) -> str:
        return 'site_location'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'SITE:LOCATION',
            'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
            'SITE:GROUNDTEMPERATURE:FCfactorMethod',
            'SITE:GROUNDTEMPERATURE:SHALLOW',
            'SITE:GROUNDTEMPERATURE:DEEP',
            'SITE:GROUNDREFLECTANCE',
            'SITE:HEIGHTVARIATION',
            'SITE:WATERMAINSTEMPERATURE',
            'SIZINGPERIOD:DESIGNDAY',
            'SIZINGPERIOD:WEATHERFILECONDITIONTYPE',
            'SIZINGPERIOD:WEATHERFILEDAYS',
            'RUNPERIOD',
            'RUNPERIODCONTROL:SPECIALDAYS',
            'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['site_location']
    
    def apply_modifications(self, 
                          parsed_objects: Dict[str, List[Any]], 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply site location specific modifications"""
        
        if strategy == 'climate_adjustment':
            return self._apply_climate_adjustment(parsed_objects, modifiable_params)
        elif strategy == 'extreme_weather':
            return self._apply_extreme_weather(parsed_objects, modifiable_params)
        elif strategy == 'ground_coupling':
            return self._apply_ground_coupling(parsed_objects, modifiable_params)
        elif strategy == 'seasonal_analysis':
            return self._apply_seasonal_analysis(parsed_objects, modifiable_params)
        else:
            return super().apply_modifications(parsed_objects, modifiable_params, strategy)
    
    def _apply_climate_adjustment(self, parsed_objects, modifiable_params):
        """Adjust site parameters for climate studies"""
        modifications = []
        import random
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SITE:LOCATION':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Adjust elevation for pressure studies
                    for param in obj.parameters:
                        if param.field_name == 'Elevation':
                            old_elevation = param.numeric_value or float(param.value)
                            # Test different elevations
                            adjustment = random.uniform(-200, 500)
                            new_elevation = max(0, old_elevation + adjustment)
                            
                            param.value = str(new_elevation)
                            param.numeric_value = new_elevation
                            
                            modifications.append(self._create_modification_result(
                                obj, 'elevation', old_elevation, new_elevation, 'climate_adjustment'
                            ))
                            break
            
            elif obj_type == 'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Adjust ground temperatures for climate change scenarios
                    temp_increase = random.uniform(1, 3)  # 1-3°C warming
                    
                    # Adjust all monthly temperatures
                    for i, param in enumerate(obj.parameters):
                        if param.numeric_value is not None:
                            old_temp = param.numeric_value
                            new_temp = old_temp + temp_increase
                            
                            param.value = str(new_temp)
                            param.numeric_value = new_temp
                            
                            month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                                          'july', 'august', 'september', 'october', 'november', 'december']
                            if i < len(month_names):
                                modifications.append(self._create_modification_result(
                                    obj, f'ground_temp_{month_names[i]}', old_temp, new_temp, 'climate_adjustment'
                                ))
        
        return modifications
    
    def _apply_extreme_weather(self, parsed_objects, modifiable_params):
        """Apply extreme weather conditions for resilience testing"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SIZINGPERIOD:DESIGNDAY':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Check if this is a cooling or heating design day
                    is_cooling = 'COOLING' in obj.name.upper() or 'SUMMER' in obj.name.upper()
                    is_heating = 'HEATING' in obj.name.upper() or 'WINTER' in obj.name.upper()
                    
                    if is_cooling:
                        # Increase maximum temperature for extreme heat
                        for param in obj.parameters:
                            if param.field_name == 'Maximum Dry-Bulb Temperature':
                                old_temp = param.numeric_value or float(param.value)
                                # Add 3-5°C for extreme heat
                                import random
                                increase = random.uniform(3, 5)
                                new_temp = old_temp + increase
                                
                                param.value = str(new_temp)
                                param.numeric_value = new_temp
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'design_day_max_temp', old_temp, new_temp, 'extreme_weather'
                                ))
                                break
                    
                    elif is_heating:
                        # Decrease minimum temperature for extreme cold
                        for param in obj.parameters:
                            if param.field_name == 'Minimum Dry-Bulb Temperature':
                                old_temp = param.numeric_value or float(param.value)
                                # Subtract 3-5°C for extreme cold
                                decrease = random.uniform(3, 5)
                                new_temp = old_temp - decrease
                                
                                param.value = str(new_temp)
                                param.numeric_value = new_temp
                                
                                modifications.append(self._create_modification_result(
                                    obj, 'design_day_min_temp', old_temp, new_temp, 'extreme_weather'
                                ))
                                break
        
        return modifications
    
    def _apply_ground_coupling(self, parsed_objects, modifiable_params):
        """Optimize ground coupling parameters"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Apply more stable ground temperatures (damped variation)
                    # Calculate average temperature
                    temps = []
                    for param in obj.parameters[:12]:  # First 12 params are monthly temps
                        if param.numeric_value is not None:
                            temps.append(param.numeric_value)
                    
                    if temps:
                        avg_temp = sum(temps) / len(temps)
                        
                        # Reduce variation around average
                        for i, param in enumerate(obj.parameters[:12]):
                            if param.numeric_value is not None:
                                old_temp = param.numeric_value
                                # Reduce variation by 50%
                                new_temp = avg_temp + (old_temp - avg_temp) * 0.5
                                
                                param.value = str(new_temp)
                                param.numeric_value = new_temp
                                
                                month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                                              'july', 'august', 'september', 'october', 'november', 'december']
                                if i < len(month_names):
                                    modifications.append(self._create_modification_result(
                                        obj, f'ground_temp_{month_names[i]}', old_temp, new_temp, 'ground_coupling'
                                    ))
        
        return modifications
    
    def _apply_seasonal_analysis(self, parsed_objects, modifiable_params):
        """Modify run period for seasonal analysis"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'RUNPERIOD':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Set to summer period (June-August)
                    import random
                    season = random.choice(['summer', 'winter', 'spring', 'fall'])
                    
                    if season == 'summer':
                        begin_month, end_month = 6, 8
                    elif season == 'winter':
                        begin_month, end_month = 12, 2
                    elif season == 'spring':
                        begin_month, end_month = 3, 5
                    else:  # fall
                        begin_month, end_month = 9, 11
                    
                    # Update begin month
                    for param in obj.parameters:
                        if param.field_name == 'Begin Month':
                            old_value = param.numeric_value or int(param.value)
                            
                            param.value = str(begin_month)
                            param.numeric_value = float(begin_month)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'begin_month', old_value, begin_month, f'seasonal_analysis_{season}'
                            ))
                            break
                    
                    # Update end month
                    for param in obj.parameters:
                        if param.field_name == 'End Month':
                            old_value = param.numeric_value or int(param.value)
                            
                            param.value = str(end_month)
                            param.numeric_value = float(end_month)
                            
                            modifications.append(self._create_modification_result(
                                obj, 'end_month', old_value, end_month, f'seasonal_analysis_{season}'
                            ))
                            break
        
        return modifications