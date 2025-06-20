"""
Site location and weather data modifications.

This module handles modifications to site location and weather data modifications.
"""
"""
Site Location Modifier - Handles site and location objects
"""
from typing import List, Dict, Any
from ..base_modifier import BaseModifier, ParameterDefinition

class SiteLocationModifier(BaseModifier):
    """Modifier for site and location related IDF objects"""
    
    def _initialize_parameters(self):
        """Initialize site location parameter definitions"""
        self.parameter_definitions = {
            # Site location
            'latitude': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Latitude',
                field_index=1,
                data_type=float,
                units='deg',
                min_value=-90,
                max_value=90,
                performance_impact='solar_angles'
            ),
            'longitude': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Longitude',
                field_index=2,
                data_type=float,
                units='deg',
                min_value=-180,
                max_value=180,
                performance_impact='solar_time'
            ),
            'elevation': ParameterDefinition(
                object_type='SITE:LOCATION',
                field_name='Elevation',
                field_index=4,
                data_type=float,
                units='m',
                min_value=-500,
                max_value=5000,
                performance_impact='air_properties'
            ),
            
            # Ground temperatures
            'january_ground_temp': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='January Ground Temperature',
                field_index=0,
                data_type=float,
                units='C',
                performance_impact='ground_heat_transfer'
            ),
            'july_ground_temp': ParameterDefinition(
                object_type='SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                field_name='July Ground Temperature',
                field_index=6,
                data_type=float,
                units='C',
                performance_impact='ground_heat_transfer'
            ),
            
            # Water mains temperature
            'annual_average_water_temp': ParameterDefinition(
                object_type='SITE:WATERMAINSTEMPERATURE',
                field_name='Annual Average Outdoor Air Temperature',
                field_index=1,
                data_type=float,
                units='C',
                performance_impact='dhw_inlet_temp'
            ),
            'maximum_water_temp_diff': ParameterDefinition(
                object_type='SITE:WATERMAINSTEMPERATURE',
                field_name='Maximum Difference In Monthly Average Outdoor Air Temperatures',
                field_index=2,
                data_type=float,
                units='deltaC',
                min_value=0,
                performance_impact='dhw_inlet_temp'
            ),
            
            # Design day parameters
            'design_day_max_temp': ParameterDefinition(
                object_type='SIZINGPERIOD:DESIGNDAY',
                field_name='Maximum Dry-Bulb Temperature',
                field_index=4,
                data_type=float,
                units='C',
                performance_impact='cooling_sizing'
            ),
            'design_day_temp_range': ParameterDefinition(
                object_type='SIZINGPERIOD:DESIGNDAY',
                field_name='Daily Dry-Bulb Temperature Range',
                field_index=5,
                data_type=float,
                units='deltaC',
                min_value=0,
                performance_impact='load_profiles'
            ),
            'design_day_humidity': ParameterDefinition(
                object_type='SIZINGPERIOD:DESIGNDAY',
                field_name='Wetbulb or DewPoint at Maximum Dry-Bulb',
                field_index=9,
                data_type=float,
                units='C',
                performance_impact='latent_loads'
            )
        }
    
    def get_category_name(self) -> str:
        return 'site_location'
    
    def get_modifiable_object_types(self) -> List[str]:
        return [
            'SITE:LOCATION',
            'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
            'SITE:WATERMAINSTEMPERATURE',
            'SITE:PRECIPITATION',
            'SIZINGPERIOD:DESIGNDAY',
            'SIZINGPERIOD:WEATHERFILECONDITIONTYPE',
            'SIZINGPERIOD:WEATHERFILEDAYS',
            'RUNPERIOD',
            'RUNPERIOD:CUSTOMRANGE',
            'RUNPERIODCONTROL:SPECIALDAYS',
            'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME'
        ]
    
    def _get_category_files(self) -> List[str]:
        return ['site_location']
    
    def apply_modifications(self, 
                          idf, 
                          modifiable_params: Dict[str, List[Dict[str, Any]]],
                          strategy: str = 'default') -> List:
        """Apply site location specific modifications"""
        
        if strategy == 'climate_change':
            return self._apply_climate_change(idf, modifiable_params)
        elif strategy == 'urban_heat_island':
            return self._apply_urban_heat_island(idf, modifiable_params)
        elif strategy == 'extreme_weather':
            return self._apply_extreme_weather(idf, modifiable_params)
        else:
            # Site location typically not modified
            return []
    
    def _apply_climate_change(self, idf, modifiable_params):
        """Apply climate change adjustments"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            # Adjust design days for future climate
            if obj_type == 'SIZINGPERIOD:DESIGNDAY':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase cooling design temperatures
                    if 'cooling' in obj.Name.lower() or 'summer' in obj.Name.lower():
                        if obj.Maximum_Dry_Bulb_Temperature:
                            old_temp = float(obj.Maximum_Dry_Bulb_Temperature)
                            # Increase by 2-3°C for climate change
                            new_temp = old_temp + 2.5
                            obj.Maximum_Dry_Bulb_Temperature = new_temp
                            
                            modifications.append(self._create_modification_result(
                                obj, 'design_day_max_temp', old_temp, new_temp,
                                'climate_change_cooling'
                            ))
                        
                        # Also increase humidity
                        if obj.Wetbulb_or_DewPoint_at_Maximum_Dry_Bulb:
                            old_wb = float(obj.Wetbulb_or_DewPoint_at_Maximum_Dry_Bulb)
                            new_wb = old_wb + 1.0  # Higher humidity
                            obj.Wetbulb_or_DewPoint_at_Maximum_Dry_Bulb = new_wb
                            
                            modifications.append(self._create_modification_result(
                                obj, 'design_day_humidity', old_wb, new_wb,
                                'climate_change_humidity'
                            ))
                    
                    # Adjust heating design days
                    elif 'heating' in obj.Name.lower() or 'winter' in obj.Name.lower():
                        if obj.Maximum_Dry_Bulb_Temperature:
                            old_temp = float(obj.Maximum_Dry_Bulb_Temperature)
                            # Increase winter temps by 1-2°C
                            new_temp = old_temp + 1.5
                            obj.Maximum_Dry_Bulb_Temperature = new_temp
                            
                            modifications.append(self._create_modification_result(
                                obj, 'design_day_max_temp', old_temp, new_temp,
                                'climate_change_heating'
                            ))
            
            # Adjust ground temperatures
            elif obj_type == 'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Increase all monthly ground temperatures
                    months = ['January', 'February', 'March', 'April', 'May', 'June',
                             'July', 'August', 'September', 'October', 'November', 'December']
                    
                    for i, month in enumerate(months):
                        field_name = f'{month}_Ground_Temperature'
                        if hasattr(obj, field_name):
                            old_temp = float(getattr(obj, field_name))
                            new_temp = old_temp + 1.5  # 1.5°C increase
                            setattr(obj, field_name, new_temp)
                            
                            if i == 0:  # Only track January for brevity
                                modifications.append(self._create_modification_result(
                                    obj, 'january_ground_temp', old_temp, new_temp,
                                    'climate_change_ground_temp'
                                ))
        
        return modifications
    
    def _apply_urban_heat_island(self, idf, modifiable_params):
        """Apply urban heat island effect"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            # Increase all temperatures for UHI effect
            if obj_type == 'SIZINGPERIOD:DESIGNDAY':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    if obj.Maximum_Dry_Bulb_Temperature:
                        old_temp = float(obj.Maximum_Dry_Bulb_Temperature)
                        # UHI adds 2-4°C in urban areas
                        new_temp = old_temp + 3.0
                        obj.Maximum_Dry_Bulb_Temperature = new_temp
                        
                        modifications.append(self._create_modification_result(
                            obj, 'design_day_max_temp', old_temp, new_temp,
                            'urban_heat_island'
                        ))
                    
                    # Reduce temperature range (less cooling at night)
                    if obj.Daily_Dry_Bulb_Temperature_Range:
                        old_range = float(obj.Daily_Dry_Bulb_Temperature_Range)
                        new_range = old_range * 0.7  # 30% reduction
                        obj.Daily_Dry_Bulb_Temperature_Range = new_range
                        
                        modifications.append(self._create_modification_result(
                            obj, 'design_day_temp_range', old_range, new_range,
                            'uhi_reduced_range'
                        ))
        
        return modifications
    
    def _apply_extreme_weather(self, idf, modifiable_params):
        """Apply extreme weather conditions"""
        modifications = []
        
        for obj_type, objects in modifiable_params.items():
            if obj_type == 'SIZINGPERIOD:DESIGNDAY':
                for obj_info in objects:
                    obj = obj_info['object']
                    
                    # Make extreme conditions more extreme
                    if 'cooling' in obj.Name.lower() or 'summer' in obj.Name.lower():
                        if obj.Maximum_Dry_Bulb_Temperature:
                            old_temp = float(obj.Maximum_Dry_Bulb_Temperature)
                            # Add 5°C for extreme heat
                            new_temp = old_temp + 5.0
                            obj.Maximum_Dry_Bulb_Temperature = new_temp
                            
                            modifications.append(self._create_modification_result(
                                obj, 'design_day_max_temp', old_temp, new_temp,
                                'extreme_heat'
                            ))
                    
                    elif 'heating' in obj.Name.lower() or 'winter' in obj.Name.lower():
                        if obj.Maximum_Dry_Bulb_Temperature:
                            old_temp = float(obj.Maximum_Dry_Bulb_Temperature)
                            # Subtract 5°C for extreme cold
                            new_temp = old_temp - 5.0
                            obj.Maximum_Dry_Bulb_Temperature = new_temp
                            
                            modifications.append(self._create_modification_result(
                                obj, 'design_day_max_temp', old_temp, new_temp,
                                'extreme_cold'
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