"""
Enhanced IDF Parser Module v3.1 - With Consolidated Output Support
Handles parsing and analysis of EnergyPlus IDF files with consolidated output definitions
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import json
from .data_manager import EnhancedHierarchicalDataManager

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class IDFParameter:
    """Represents a single parameter in an IDF object"""
    value: str
    field_name: Optional[str] = None
    field_type: Optional[str] = None
    units: Optional[str] = None
    comment: Optional[str] = None
    position: int = 0
    numeric_value: Optional[float] = None

@dataclass
class IDFObject:
    """Represents a complete IDF object with all parameters"""
    object_type: str
    name: str
    parameters: List[IDFParameter] = field(default_factory=list)
    zone_name: Optional[str] = None
    raw_text: str = ""
    line_number: int = 0
    category: Optional[str] = None

@dataclass
class BuildingData:
    """Container for all data from a single IDF file"""
    building_id: str
    file_path: Path
    objects: Dict[str, List[IDFObject]] = field(default_factory=dict)
    zones: Dict[str, Dict] = field(default_factory=dict)
    zone_surfaces: Dict[str, List[str]] = field(default_factory=dict)
    zone_equipment: Dict[str, List[str]] = field(default_factory=dict)
    parse_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    output_definitions: Dict[str, List] = field(default_factory=dict)  # Still used internally

# ============================================================================
# ENHANCED FILE MAPPING CONFIGURATION
# ============================================================================

# Define how object types map to output files
FILE_MAPPINGS = {
    # Simulation control (NEW GROUP)
    'simulation_control': ['VERSION', 'SIMULATIONCONTROL', 'TIMESTEP', 'RUNPERIOD', 
                          'RUNPERIODCONTROL:SPECIALDAYS', 'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME',
                          'BUILDING', 'SHADOWCALCULATION', 'SURFACECONVECTIONALGORITHM:INSIDE',
                          'SURFACECONVECTIONALGORITHM:OUTSIDE', 'HEATBALANCEALGORITHM', 'CONVERGENCELIMITS'],
    
    # Site and location (NEW GROUP)
    'site_location': ['SITE:LOCATION', 'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
                     'SITE:WATERMAINSTEMPERATURE', 'SITE:PRECIPITATION',
                     'SIZINGPERIOD:DESIGNDAY', 'SIZINGPERIOD:WEATHERFILECONDITIONTYPE',
                     'SIZINGPERIOD:WEATHERFILEDAYS'],
    
    # Geometry files (updated with ZONELIST)
    'geometry_zones': ['ZONE', 'ZONELIST'],  # Added ZONELIST
    'geometry_surfaces': ['BUILDINGSURFACE:DETAILED', 'FENESTRATIONSURFACE:DETAILED', 
                         'FLOOR:DETAILED', 'WALL:DETAILED', 'ROOFCEILING:DETAILED',
                         'WINDOW', 'DOOR', 'GLAZEDDOOR', 'GLOBALGEOMETRYRULES'],  # Added GLOBALGEOMETRYRULES
    
    # Materials files
    'materials_constructions': ['CONSTRUCTION', 'CONSTRUCTION:CFACTORUNDERGROUNDWALL',
                               'CONSTRUCTION:FFACTORGROUNDFLOOR', 'CONSTRUCTION:INTERNALSOURCE'],
    'materials_materials': ['MATERIAL', 'MATERIAL:NOMASS', 'MATERIAL:AIRGAP',
                           'MATERIAL:INFRAREDTRANSPARENT'],
    'materials_windowmaterials': ['WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', 'WINDOWMATERIAL:GLAZING',
                                 'WINDOWMATERIAL:GAS', 'WINDOWMATERIAL:GASMIXTURE',
                                 'WINDOWMATERIAL:BLIND', 'WINDOWMATERIAL:SCREEN',
                                 'WINDOWMATERIAL:SHADE'],
    
    # HVAC files (updated with NODELIST)
    'hvac_equipment': ['ZONEHVAC:IDEALLOADSAIRSYSTEM', 'ZONEHVAC:EQUIPMENTLIST',
                      'ZONEHVAC:EQUIPMENTCONNECTIONS', 'COIL:COOLING:DX:SINGLESPEED',
                      'COIL:COOLING:DX:TWOSPEED', 'COIL:COOLING:DX:VARIABLESPEED',
                      'COIL:HEATING:ELECTRIC', 'COIL:HEATING:GAS', 'COIL:HEATING:WATER',
                      'FAN:SYSTEMMODEL', 'FAN:CONSTANTVOLUME', 'FAN:VARIABLEVOLUME', 'FAN:ONOFF'],
    'hvac_systems': ['AIRLOOPHVAC', 'AIRLOOPHVAC:UNITARY:FURNACE:HEATONLY',
                    'AIRLOOPHVAC:UNITARY:FURNACE:HEATCOOL', 'CONTROLLER:OUTDOORAIR',
                    'CONTROLLER:WATERCOIL', 'SETPOINTMANAGER:SCHEDULED',
                    'SETPOINTMANAGER:SINGLEZONE:REHEAT', 'AVAILABILITYMANAGER:SCHEDULED',
                    'AVAILABILITYMANAGER:NIGHTCYCLE', 'SIZING:ZONE', 'SIZING:SYSTEM', 
                    'SIZING:PLANT', 'NODELIST'],  # Added NODELIST
    'hvac_thermostats': ['THERMOSTATSETPOINT:DUALSETPOINT', 'THERMOSTATSETPOINT:SINGLEHEATING',
                        'THERMOSTATSETPOINT:SINGLECOOLING', 'ZONECONTROL:THERMOSTAT'],
    
    # All outputs consolidated into ONE file
    'outputs_all': ['OUTPUT:VARIABLE', 'OUTPUT:METER', 'OUTPUT:METER:METERFILEONLY', 
                   'OUTPUT:METER:CUMULATIVE', 'OUTPUT:METER:CUMULATIVE:METERFILEONLY',
                   'OUTPUT:TABLE:SUMMARYREPORTS', 'OUTPUT:TABLE:MONTHLY', 
                   'OUTPUT:TABLE:TIMEBINS', 'OUTPUT:TABLE:ANNUAL',
                   'OUTPUT:SQLITE', 'OUTPUTCONTROL:TABLE:STYLE', 
                   'OUTPUTCONTROL:REPORTINGTOLERANCES', 'OUTPUTCONTROL:FILES',
                   'OUTPUT:VARIABLEDICTIONARY', 'OUTPUT:SURFACES:DRAWING',
                   'OUTPUT:SURFACES:LIST', 'OUTPUT:SCHEDULES', 'OUTPUT:CONSTRUCTIONS',
                   'OUTPUT:ENERGYMANAGEMENTSYSTEM', 'OUTPUT:DIAGNOSTICS',
                   'OUTPUT:DEBUGGINGDATA', 'OUTPUT:PREPROCESSORMACROS'],
    
    # Other categories remain the same
    'ventilation': ['ZONEVENTILATION:DESIGNFLOWRATE', 'ZONEVENTILATION:WINDANDSTACKDRIVENFLOW',
                   'ZONEAIRBALANCE:OUTDOORAIR', 'ZONECROSSMIXING', 'ZONEMIXING',
                   'DESIGNSPECIFICATION:OUTDOORAIR', 'DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION',
                   'CONTROLLER:MECHANICALVENTILATION', 'OUTDOORAIR:MIXER', 'OUTDOORAIR:NODE'],
    
    'infiltration': ['ZONEINFILTRATION:DESIGNFLOWRATE', 'ZONEINFILTRATION:EFFECTIVELEAKAGEAREA',
                    'ZONEINFILTRATION:FLOWCOEFFICIENT', 'SPACEINFILTRATION:DESIGNFLOWRATE',
                    'SPACEINFILTRATION:EFFECTIVELEAKAGEAREA', 'SPACEINFILTRATION:FLOWCOEFFICIENT'],
    
    'lighting': ['LIGHTS', 'DAYLIGHTING:CONTROLS', 'DAYLIGHTING:REFERENCEPOINT',
                'DAYLIGHTING:DELIGHT:REFERENCEPOINT', 'DAYLIGHTING:DELIGHT:CONTROLS',
                'LIGHTINGDESIGNDAY', 'EXTERIORLIGHTS'],
    
    'equipment': ['ELECTRICEQUIPMENT', 'GASEQUIPMENT', 'HOTWATEREQUIPMENT',
                 'STEAMEQUIPMENT', 'OTHEREQUIPMENT', 'EXTERIOREQUIPMENT',
                 'EXTERIOR:LIGHTS', 'REFRIGERATION:SYSTEM', 'REFRIGERATION:COMPRESSORRACK'],
    
    'dhw': ['WATERHEATER:MIXED', 'WATERHEATER:STRATIFIED', 'WATERUSE:EQUIPMENT',
           'WATERUSE:CONNECTIONS', 'PLANTLOOP', 'PUMP:VARIABLESPEED',
           'PUMP:CONSTANTSPEED', 'PIPE:ADIABATIC', 'PIPE:INDOOR', 'PIPE:OUTDOOR'],
    
    'shading': ['WINDOWSHADINGCONTROL', 'SHADING:SITE', 'SHADING:SITE:DETAILED',
               'SHADING:BUILDING', 'SHADING:BUILDING:DETAILED', 'SHADING:ZONE',
               'SHADING:ZONE:DETAILED', 'SHADING:OVERHANG', 'SHADING:OVERHANG:PROJECTION',
               'SHADING:FIN', 'SHADING:FIN:PROJECTION'],
    
    'schedules': ['SCHEDULETYPELIMITS', 'SCHEDULE:COMPACT', 'SCHEDULE:CONSTANT',
                 'SCHEDULE:DAY:HOURLY', 'SCHEDULE:DAY:INTERVAL', 'SCHEDULE:DAY:LIST',
                 'SCHEDULE:WEEK:DAILY', 'SCHEDULE:WEEK:COMPACT', 'SCHEDULE:YEAR',
                 'SCHEDULE:FILE']
}

# Create reverse mapping for quick lookup
OBJECT_TO_FILE = {}
for file_name, object_types in FILE_MAPPINGS.items():
    for obj_type in object_types:
        OBJECT_TO_FILE[obj_type.upper()] = file_name

# ============================================================================
# ENHANCED IDF PARSER CLASS
# ============================================================================

class EnhancedIDFParser:
    """Enhanced IDF Parser with consolidated output support"""
    
    def __init__(self, category_mappings: Optional[Dict] = None, 
                 data_manager: Optional[EnhancedHierarchicalDataManager] = None):
        self.field_names = self._initialize_comprehensive_field_names()
        self.category_mappings = category_mappings or {}
        self.category_map = self._build_category_map()
        self.data_manager = data_manager


    def set_content_filter(self, content_config: Dict[str, Any]):
        """Set content filtering configuration"""
        self.content_filter = content_config
        self.filter_mode = content_config.get('mode', 'all')
        
        # Pre-process filters for efficiency
        if self.filter_mode == 'categories_only':
            self.allowed_categories = set(content_config.get('categories', []))
            self.excluded_categories = set(content_config.get('exclude_categories', []))
        
        elif self.filter_mode == 'objects_only':
            self.allowed_objects = set(obj.upper() for obj in content_config.get('object_types', []))
            self.excluded_objects = set(obj.upper() for obj in content_config.get('exclude_objects', []))
        
        self.parse_parameters = content_config.get('parse_parameters', True)
        self.parse_relationships = content_config.get('parse_relationships', True)


    def _should_parse_object(self, object_type: str) -> bool:
        """Check if an object should be parsed based on filters"""
        if not hasattr(self, 'filter_mode'):
            return True
        
        if self.filter_mode == 'all':
            return True
        
        obj_type_upper = object_type.upper()
        
        if self.filter_mode == 'categories_only':
            # Check category
            category = self.category_map.get(obj_type_upper, 'other')
            
            if self.allowed_categories and category not in self.allowed_categories:
                return False
            
            if self.excluded_categories and category in self.excluded_categories:
                return False
            
            return True
        
        elif self.filter_mode == 'objects_only':
            # Check object type
            if self.allowed_objects and obj_type_upper not in self.allowed_objects:
                return False
            
            if self.excluded_objects and obj_type_upper in self.excluded_objects:
                return False
            
            return True
        
        return True















    
    def _initialize_comprehensive_field_names(self) -> Dict[str, List[str]]:
        """Initialize comprehensive field name mappings including output objects"""
        field_names = {
            # Simulation Control Objects
            'VERSION': [
                'Version Identifier'
            ],
            'SIMULATIONCONTROL': [
                'Do Zone Sizing Calculation',
                'Do System Sizing Calculation', 
                'Do Plant Sizing Calculation',
                'Run Simulation for Sizing Periods',
                'Run Simulation for Weather File Run Periods',
                'Do HVAC Sizing Simulation for Sizing Periods',
                'Maximum Number of HVAC Sizing Simulation Passes'
            ],
            'TIMESTEP': [
                'Number of Timesteps per Hour'
            ],
            'SITE:LOCATION': [
                'Name',
                'Latitude',
                'Longitude', 
                'Time Zone',
                'Elevation'
            ],
            'SIZINGPERIOD:DESIGNDAY': [
                'Name',
                'Month',
                'Day of Month',
                'Day Type',
                'Maximum Dry-Bulb Temperature',
                'Daily Dry-Bulb Temperature Range',
                'Dry-Bulb Temperature Range Modifier Type',
                'Dry-Bulb Temperature Range Modifier Day Schedule Name',
                'Humidity Condition Type',
                'Wetbulb or DewPoint at Maximum Dry-Bulb',
                'Humidity Condition Day Schedule Name',
                'Humidity Ratio at Maximum Dry-Bulb',
                'Enthalpy at Maximum Dry-Bulb',
                'Daily Wet-Bulb Temperature Range',
                'Barometric Pressure',
                'Wind Speed',
                'Wind Direction',
                'Rain Indicator',
                'Snow Indicator',
                'Daylight Saving Time Indicator',
                'Solar Model Indicator',
                'Beam Solar Day Schedule Name',
                'Diffuse Solar Day Schedule Name',
                'ASHRAE Clear Sky Optical Depth for Beam Irradiance (taub)',
                'ASHRAE Clear Sky Optical Depth for Diffuse Irradiance (taud)',
                'Sky Clearness'
            ],
            'RUNPERIOD': [
                'Name',
                'Begin Month',
                'Begin Day of Month',
                'Begin Year',
                'End Month',
                'End Day of Month',
                'End Year',
                'Day of Week for Start Day',
                'Use Weather File Holidays and Special Days',
                'Use Weather File Daylight Saving Period',
                'Apply Weekend Holiday Rule',
                'Use Weather File Rain Indicators',
                'Use Weather File Snow Indicators'
            ],
            'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE': [
                'January Ground Temperature',
                'February Ground Temperature',
                'March Ground Temperature',
                'April Ground Temperature',
                'May Ground Temperature',
                'June Ground Temperature',
                'July Ground Temperature',
                'August Ground Temperature',
                'September Ground Temperature',
                'October Ground Temperature',
                'November Ground Temperature',
                'December Ground Temperature'
            ],
            
            # Output Objects
            'OUTPUT:VARIABLE': [
                'Key Value',
                'Variable Name',
                'Reporting Frequency',
                'Schedule Name'
            ],
            'OUTPUT:METER': [
                'Key Name',
                'Reporting Frequency'
            ],
            'OUTPUT:METER:METERFILEONLY': [
                'Key Name',
                'Reporting Frequency'
            ],
            'OUTPUT:METER:CUMULATIVE': [
                'Key Name',
                'Reporting Frequency'
            ],
            'OUTPUT:METER:CUMULATIVE:METERFILEONLY': [
                'Key Name',
                'Reporting Frequency'
            ],
            'OUTPUT:TABLE:SUMMARYREPORTS': [
                'Report 1 Name',
                'Report 2 Name',
                'Report 3 Name',
                'Report 4 Name',
                'Report 5 Name',
                'Report 6 Name',
                'Report 7 Name',
                'Report 8 Name',
                'Report 9 Name',
                'Report 10 Name'
            ],
            'OUTPUT:TABLE:MONTHLY': [
                'Name',
                'Digits After Decimal',
                'Variable or Meter 1 Name',
                'Aggregation Type for Variable or Meter 1',
                'Variable or Meter 2 Name',
                'Aggregation Type for Variable or Meter 2',
                'Variable or Meter 3 Name',
                'Aggregation Type for Variable or Meter 3',
                'Variable or Meter 4 Name',
                'Aggregation Type for Variable or Meter 4',
                'Variable or Meter 5 Name',
                'Aggregation Type for Variable or Meter 5',
                'Variable or Meter 6 Name',
                'Aggregation Type for Variable or Meter 6'
            ],
            'OUTPUT:SQLITE': [
                'Option Type',
                'Unit Conversion for Tabular Data'
            ],
            'OUTPUTCONTROL:TABLE:STYLE': [
                'Column Separator',
                'Unit Conversion'
            ],
            'OUTPUT:VARIABLEDICTIONARY': [
                'Key Field',
                'Sort Option'
            ],
            
            # Zone and Geometry Objects
            'ZONE': [
                'Name', 'Direction of Relative North', 'X Origin', 'Y Origin', 
                'Z Origin', 'Type', 'Multiplier', 'Ceiling Height', 'Volume',
                'Floor Area', 'Zone Inside Convection Algorithm', 
                'Zone Outside Convection Algorithm', 'Part of Total Floor Area'
            ],
            'ZONELIST': [
                'Name',
                'Zone 1 Name',
                'Zone 2 Name',
                'Zone 3 Name',
                'Zone 4 Name',
                'Zone 5 Name'
                # Can have many more zones
            ],
            'BUILDINGSURFACE:DETAILED': [
                'Name', 'Surface Type', 'Construction Name', 'Zone Name',
                'Space Name', 'Outside Boundary Condition', 
                'Outside Boundary Condition Object', 'Sun Exposure',
                'Wind Exposure', 'View Factor to Ground', 'Number of Vertices'
            ],
            'FENESTRATIONSURFACE:DETAILED': [
                'Name', 'Surface Type', 'Construction Name', 'Building Surface Name',
                'Outside Boundary Condition Object', 'View Factor to Ground',
                'Frame and Divider Name', 'Multiplier', 'Number of Vertices'
            ],
            'GLOBALGEOMETRYRULES': [
                'Starting Vertex Position',
                'Vertex Entry Direction',
                'Coordinate System',
                'Daylighting Reference Point Coordinate System',
                'Rectangular Surface Coordinate System'
            ],
            
            # Building
            'BUILDING': [
                'Name', 'North Axis', 'Terrain', 'Loads Convergence Tolerance Value',
                'Temperature Convergence Tolerance Value', 'Solar Distribution',
                'Maximum Number of Warmup Days', 'Minimum Number of Warmup Days'
            ],
            
            # Materials
            'MATERIAL': [
                'Name', 'Roughness', 'Thickness', 'Conductivity', 'Density',
                'Specific Heat', 'Thermal Absorptance', 'Solar Absorptance',
                'Visible Absorptance'
            ],
            'MATERIAL:NOMASS': [
                'Name', 'Roughness', 'Thermal Resistance', 'Thermal Absorptance',
                'Solar Absorptance', 'Visible Absorptance'
            ],
            'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM': [
                'Name', 'U-Factor', 'Solar Heat Gain Coefficient', 'Visible Transmittance'
            ],
            'WINDOWMATERIAL:BLIND': [
                'Name', 'Slat Orientation', 'Slat Width', 'Slat Separation',
                'Slat Thickness', 'Slat Angle', 'Slat Conductivity',
                'Slat Beam Solar Transmittance', 'Front Side Slat Beam Solar Reflectance',
                'Back Side Slat Beam Solar Reflectance', 'Slat Diffuse Solar Transmittance',
                'Front Side Slat Diffuse Solar Reflectance', 'Back Side Slat Diffuse Solar Reflectance',
                'Slat Beam Visible Transmittance', 'Front Side Slat Beam Visible Reflectance',
                'Back Side Slat Beam Visible Reflectance', 'Slat Diffuse Visible Transmittance',
                'Front Side Slat Diffuse Visible Reflectance', 'Back Side Slat Diffuse Visible Reflectance',
                'Slat Infrared Hemispherical Transmittance', 'Front Side Slat Infrared Hemispherical Emissivity',
                'Back Side Slat Infrared Hemispherical Emissivity', 'Blind to Glass Distance',
                'Blind Top Opening Multiplier', 'Blind Bottom Opening Multiplier',
                'Blind Left Side Opening Multiplier', 'Blind Right Side Opening Multiplier',
                'Minimum Slat Angle', 'Maximum Slat Angle'
            ],
            'CONSTRUCTION': [
                'Name', 'Outside Layer', 'Layer 2', 'Layer 3', 'Layer 4',
                'Layer 5', 'Layer 6', 'Layer 7', 'Layer 8', 'Layer 9', 'Layer 10'
            ],
            
            # Internal Loads
            'LIGHTS': [
                'Name', 'Zone or ZoneList Name', 'Schedule Name',
                'Design Level Calculation Method', 'Lighting Level',
                'Watts per Zone Floor Area', 'Watts per Person',
                'Return Air Fraction', 'Fraction Radiant', 'Fraction Visible',
                'Fraction Replaceable', 'End-Use Subcategory',
                'Return Air Fraction Calculated from Plenum Temperature',
                'Return Air Fraction Function of Plenum Temperature Coefficient 1',
                'Return Air Fraction Function of Plenum Temperature Coefficient 2'
            ],
            'ELECTRICEQUIPMENT': [
                'Name', 'Zone or ZoneList Name', 'Schedule Name',
                'Design Level Calculation Method', 'Design Level',
                'Watts per Zone Floor Area', 'Watts per Person',
                'Fraction Latent', 'Fraction Radiant', 'Fraction Lost',
                'End-Use Subcategory'
            ],
            
            # Infiltration and Ventilation
            'ZONEINFILTRATION:DESIGNFLOWRATE': [
                'Name', 'Zone or ZoneList Name', 'Schedule Name',
                'Design Flow Rate Calculation Method', 'Design Flow Rate',
                'Flow per Zone Floor Area', 'Flow per Exterior Surface Area',
                'Air Changes per Hour', 'Constant Term Coefficient',
                'Temperature Term Coefficient', 'Velocity Term Coefficient',
                'Velocity Squared Term Coefficient'
            ],
            'ZONEVENTILATION:DESIGNFLOWRATE': [
                'Name', 'Zone or ZoneList Name', 'Schedule Name',
                'Design Flow Rate Calculation Method', 'Design Flow Rate',
                'Flow Rate per Zone Floor Area', 'Flow Rate per Person',
                'Air Changes per Hour', 'Ventilation Type', 'Fan Pressure Rise',
                'Fan Total Efficiency', 'Constant Term Coefficient',
                'Temperature Term Coefficient', 'Velocity Term Coefficient',
                'Velocity Squared Term Coefficient', 'Minimum Indoor Temperature',
                'Minimum Indoor Temperature Schedule Name', 'Maximum Indoor Temperature',
                'Maximum Indoor Temperature Schedule Name', 'Delta Temperature',
                'Delta Temperature Schedule Name', 'Minimum Outdoor Temperature',
                'Minimum Outdoor Temperature Schedule Name', 'Maximum Outdoor Temperature',
                'Maximum Outdoor Temperature Schedule Name', 'Maximum Wind Speed'
            ],
            
            # HVAC
            'ZONEHVAC:IDEALLOADSAIRSYSTEM': [
                'Name', 'Availability Schedule Name', 'Zone Supply Air Node Name',
                'Zone Exhaust Air Node Name', 'System Inlet Air Node Name',
                'Maximum Heating Supply Air Temperature', 'Minimum Cooling Supply Air Temperature',
                'Maximum Heating Supply Air Humidity Ratio', 'Minimum Cooling Supply Air Humidity Ratio',
                'Heating Limit', 'Maximum Heating Air Flow Rate', 'Maximum Sensible Heating Capacity',
                'Cooling Limit', 'Maximum Cooling Air Flow Rate', 'Maximum Total Cooling Capacity',
                'Heating Availability Schedule Name', 'Cooling Availability Schedule Name',
                'Dehumidification Control Type', 'Cooling Sensible Heat Ratio',
                'Humidification Control Type', 'Design Specification Outdoor Air Object Name',
                'Outdoor Air Inlet Node Name', 'Demand Controlled Ventilation Type',
                'Outdoor Air Economizer Type', 'Heat Recovery Type',
                'Sensible Heat Recovery Effectiveness', 'Latent Heat Recovery Effectiveness'
            ],
            'DESIGNSPECIFICATION:OUTDOORAIR': [
                'Name', 'Outdoor Air Method', 'Outdoor Air Flow per Person',
                'Outdoor Air Flow per Zone Floor Area', 'Outdoor Air Flow per Zone',
                'Outdoor Air Flow Air Changes per Hour', 'Outdoor Air Schedule Name'
            ],
            'THERMOSTATSETPOINT:DUALSETPOINT': [
                'Name', 'Heating Setpoint Temperature Schedule Name',
                'Cooling Setpoint Temperature Schedule Name'
            ],
            'NODELIST': [
                'Name',
                'Node 1 Name',
                'Node 2 Name',
                'Node 3 Name',
                'Node 4 Name',
                'Node 5 Name'
                # Can have many more nodes
            ],
            
            # DHW
            'WATERHEATER:MIXED': [
                'Name', 'Tank Volume', 'Setpoint Temperature Schedule Name',
                'Deadband Temperature Difference', 'Maximum Temperature Limit',
                'Heater Control Type', 'Heater Maximum Capacity', 'Heater Minimum Capacity',
                'Heater Ignition Minimum Flow Rate', 'Heater Ignition Delay',
                'Heater Fuel Type', 'Heater Thermal Efficiency', 'Part Load Factor Curve Name',
                'Off Cycle Parasitic Fuel Consumption Rate', 'Off Cycle Parasitic Fuel Type',
                'Off Cycle Parasitic Heat Fraction to Tank', 'On Cycle Parasitic Fuel Consumption Rate',
                'On Cycle Parasitic Fuel Type', 'On Cycle Parasitic Heat Fraction to Tank',
                'Ambient Temperature Indicator', 'Ambient Temperature Schedule Name',
                'Ambient Temperature Zone Name', 'Ambient Temperature Outdoor Air Node Name',
                'Off Cycle Loss Coefficient to Ambient Temperature', 'Off Cycle Loss Fraction to Zone',
                'On Cycle Loss Coefficient to Ambient Temperature', 'On Cycle Loss Fraction to Zone',
                'Peak Use Flow Rate', 'Use Flow Rate Fraction Schedule Name',
                'Cold Water Supply Temperature Schedule Name', 'Use Side Inlet Node Name',
                'Use Side Outlet Node Name', 'Use Side Effectiveness',
                'Source Side Inlet Node Name', 'Source Side Outlet Node Name',
                'Source Side Effectiveness', 'Use Side Design Flow Rate',
                'Source Side Design Flow Rate', 'Indirect Water Heating Recovery Time',
                'Source Side Flow Control Mode', 'Indirect Alternate Setpoint Temperature Schedule Name',
                'End-Use Subcategory'
            ],
            
            # Shading
            'WINDOWSHADINGCONTROL': [
                'Name', 'Zone or ZoneList Name', 'Sequential Shading Control Number',
                'Shading Type', 'Construction with Shading Name', 'Shading Control Type',
                'Schedule Name', 'Setpoint', 'Shading Control Is Scheduled',
                'Glare Control Is Active', 'Shading Device Material Name',
                'Type of Slat Angle Control for Blinds', 'Slat Angle Schedule Name',
                'Setpoint 2', 'Daylighting Control Object Name',
                'Multiple Surface Control Type', 'Fenestration Surface 1 Name',
                'Fenestration Surface 2 Name', 'Fenestration Surface 3 Name',
                'Fenestration Surface 4 Name', 'Fenestration Surface 5 Name'
            ],
            
            # Schedules
            'SCHEDULETYPELIMITS': [
                'Name', 'Lower Limit Value', 'Upper Limit Value', 
                'Numeric Type', 'Unit Type'
            ],
            'SCHEDULE:COMPACT': [
                'Name', 'Schedule Type Limits Name'
                # Note: Schedule:Compact has variable number of fields
            ],
            'SCHEDULE:CONSTANT': [
                'Name', 'Schedule Type Limits Name', 'Hourly Value'
            ]
        }
        
        return field_names
    
    def _build_category_map(self) -> Dict[str, str]:
        """Build object type to category mapping"""
        category_map = {}
        for category, config in self.category_mappings.items():
            for obj_type in config['idf_objects']:
                category_map[obj_type.upper()] = category
        return category_map
    
    def parse_file(self, file_path: Union[str, Path]) -> BuildingData:
        """Parse single IDF file with enhanced error handling"""
        file_path = Path(file_path)
        
        # Extract building ID from filename - Updated patterns
        patterns = [
            r'building_(\d+)\.idf',
            r'building_(\d+)_[a-f0-9]+\.idf',  # Handle hash suffixes
            r'bldg_(\d+)\.idf',
            r'(\d{6,})\.idf'  # Direct ID as filename
        ]
        
        building_id = None
        for pattern in patterns:
            match = re.search(pattern, file_path.name)
            if match:
                building_id = match.group(1)
                break
        
        if not building_id:
            building_id = file_path.stem
        
        building_data = BuildingData(
            building_id=building_id,
            file_path=file_path
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse objects
            objects = self._parse_content(content)
            
            # Organize objects
            self._organize_objects(objects, building_data)
            
            # Extract metadata
            self._extract_metadata(building_data)
            
            # Extract output definitions (still used internally)
            self._extract_output_definitions(building_data)
            
            # Build relationships
            self._build_relationships(building_data)
            
        except Exception as e:
            building_data.parse_errors.append(f"Error parsing file: {str(e)}")
            print(f"Error parsing {file_path}: {e}")
        
        return building_data
    
    def parse_and_save(self, file_path: Union[str, Path]) -> BuildingData:
        """Parse IDF file and save to hierarchical structure"""
        building_data = self.parse_file(file_path)
        
        if self.data_manager:
            # Save data by category - using buffering for efficiency
            self._save_by_category(building_data)
            
            # Save consolidated output definitions
            self._save_consolidated_outputs(building_data)
            
            # Save building snapshot
            self._save_building_snapshot(building_data)
            
            # Save relationships
            self._save_relationships(building_data)
            
            # Flush buffers at the end
            self.data_manager.flush_category_buffers()
        
        return building_data
    
    def _extract_output_definitions(self, building_data: BuildingData):
        """Extract and organize output definitions (internal use)"""
        output_types = {
            'variables': ['OUTPUT:VARIABLE'],
            'meters': ['OUTPUT:METER', 'OUTPUT:METER:METERFILEONLY', 
                       'OUTPUT:METER:CUMULATIVE', 'OUTPUT:METER:CUMULATIVE:METERFILEONLY'],
            'tables': ['OUTPUT:TABLE:SUMMARYREPORTS', 'OUTPUT:TABLE:MONTHLY',
                      'OUTPUT:TABLE:TIMEBINS', 'OUTPUT:TABLE:ANNUAL'],
            'control': ['OUTPUT:SQLITE', 'OUTPUTCONTROL:TABLE:STYLE',
                       'OUTPUT:VARIABLEDICTIONARY', 'OUTPUTCONTROL:REPORTINGTOLERANCES']
        }
        
        for output_category, object_types in output_types.items():
            building_data.output_definitions[output_category] = []
            
            for obj_type in object_types:
                if obj_type in building_data.objects:
                    building_data.output_definitions[output_category].extend(
                        building_data.objects[obj_type]
                    )
        
        # Update metadata with output counts
        building_data.metadata['output_variables'] = len(building_data.output_definitions.get('variables', []))
        building_data.metadata['output_meters'] = len(building_data.output_definitions.get('meters', []))
        building_data.metadata['output_tables'] = len(building_data.output_definitions.get('tables', []))
    
    def _save_consolidated_outputs(self, building_data: BuildingData):
        """Save all output definitions to a single consolidated file"""
        if not self.data_manager:
            return
        
        all_output_data = []
        
        # Process OUTPUT:VARIABLE definitions
        if 'variables' in building_data.output_definitions:
            for obj in building_data.output_definitions['variables']:
                row = {
                    'building_id': building_data.building_id,
                    'output_type': 'variable',
                    'output_subtype': 'variable',
                    'key_value': obj.parameters[0].value if len(obj.parameters) > 0 else '*',
                    'name': obj.parameters[1].value if len(obj.parameters) > 1 else '',
                    'reporting_frequency': obj.parameters[2].value if len(obj.parameters) > 2 else 'Hourly',
                    'schedule_name': obj.parameters[3].value if len(obj.parameters) > 3 else None
                }
                all_output_data.append(row)
        
        # Process OUTPUT:METER definitions
        if 'meters' in building_data.output_definitions:
            for obj in building_data.output_definitions['meters']:
                row = {
                    'building_id': building_data.building_id,
                    'output_type': 'meter',
                    'output_subtype': obj.object_type.lower().replace('output:', '').replace(':', '_'),
                    'key_value': None,  # Meters don't have key values
                    'name': obj.parameters[0].value if len(obj.parameters) > 0 else '',
                    'reporting_frequency': obj.parameters[1].value if len(obj.parameters) > 1 else 'Hourly',
                    'schedule_name': None
                }
                all_output_data.append(row)
        
        # Process OUTPUT:TABLE definitions
        if 'tables' in building_data.output_definitions:
            for obj in building_data.output_definitions['tables']:
                if obj.object_type == 'OUTPUT:TABLE:SUMMARYREPORTS':
                    # Each parameter is a report name
                    for i, param in enumerate(obj.parameters):
                        if param.value:
                            row = {
                                'building_id': building_data.building_id,
                                'output_type': 'table',
                                'output_subtype': 'summary',
                                'key_value': None,
                                'name': param.value,
                                'reporting_frequency': None,
                                'schedule_name': None
                            }
                            all_output_data.append(row)
                elif obj.object_type == 'OUTPUT:TABLE:MONTHLY':
                    row = {
                        'building_id': building_data.building_id,
                        'output_type': 'table',
                        'output_subtype': 'monthly',
                        'key_value': None,
                        'name': obj.parameters[0].value if len(obj.parameters) > 0 else '',
                        'reporting_frequency': 'Monthly',
                        'schedule_name': None
                    }
                    all_output_data.append(row)
        
        # Process output control settings
        if 'control' in building_data.output_definitions:
            for obj in building_data.output_definitions['control']:
                row = {
                    'building_id': building_data.building_id,
                    'output_type': 'control',
                    'output_subtype': obj.object_type.lower().replace('output:', '').replace('outputcontrol:', ''),
                    'key_value': None,
                    'name': obj.name if obj.name else obj.object_type,
                    'reporting_frequency': None,
                    'schedule_name': obj.parameters[0].value if len(obj.parameters) > 0 else None
                }
                all_output_data.append(row)
        
        # Buffer all output data together
        if all_output_data:
            self.data_manager.buffer_category_data('outputs_all', pd.DataFrame(all_output_data))
    
    def _save_by_category(self, building_data: BuildingData):
        """Save parsed data organized by category with consolidated files"""
        if not self.data_manager:
            return
        
        # Group objects by output file
        file_data = {}
        
        for obj_type, objects in building_data.objects.items():
            # Determine output file
            output_file = OBJECT_TO_FILE.get(obj_type.upper(), 'other')
            
            if output_file not in file_data:
                file_data[output_file] = []
            
            # Convert objects to dataframe rows
            for obj in objects:
                row_data = {
                    'building_id': building_data.building_id,
                    'object_type': obj.object_type,
                    'object_name': obj.name
                }
                
                # Add zone name for zone-specific objects
                if obj.zone_name and self._is_zone_specific_object(obj.object_type):
                    row_data['zone_name'] = obj.zone_name
                
                # Add key parameters with clean column names
                for param in obj.parameters:
                    if param.field_name and param.value:
                        # Clean field name for column name
                        col_name = param.field_name.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
                        row_data[col_name] = param.value
                        
                        # Add numeric value if exists and different from string value
                        if param.numeric_value is not None:
                            row_data[f"{col_name}_numeric"] = param.numeric_value
                
                file_data[output_file].append(row_data)
        
        # Save each file's data
        for file_name, rows in file_data.items():
            if rows and file_name != 'other':  # Skip 'other' category for now
                df = pd.DataFrame(rows)
                
                # Buffer the data for batch writing
                self.data_manager.buffer_category_data(file_name, df)
    
    def _is_zone_specific_object(self, object_type: str) -> bool:
        """Check if object type is zone-specific"""
        zone_specific_types = [
            'ZONE',
            'ZONELIST',
            'BUILDINGSURFACE:DETAILED',
            'FENESTRATIONSURFACE:DETAILED',
            'LIGHTS',
            'ELECTRICEQUIPMENT',
            'ZONEINFILTRATION:DESIGNFLOWRATE',
            'ZONEVENTILATION:DESIGNFLOWRATE',
            'ZONEHVAC:IDEALLOADSAIRSYSTEM',
            'ZONEHVAC:EQUIPMENTLIST',
            'ZONEHVAC:EQUIPMENTCONNECTIONS',
            'WINDOWSHADINGCONTROL'
        ]
        return object_type.upper() in zone_specific_types
    
    def _save_building_snapshot(self, building_data: BuildingData):
        """Save complete snapshot of building parameters"""
        if not self.data_manager:
            return
        
        all_params = []
        
        for obj_type, objects in building_data.objects.items():
            category = self.category_map.get(obj_type, 'other')
            output_file = OBJECT_TO_FILE.get(obj_type.upper(), 'other')
            
            for obj in objects:
                # Create compact representation
                param_dict = {
                    'building_id': building_data.building_id,
                    'category': category,
                    'output_file': output_file,
                    'object_type': obj.object_type,
                    'object_name': obj.name
                }
                
                # Only add zone name for zone-specific objects
                if obj.zone_name and self._is_zone_specific_object(obj.object_type):
                    param_dict['zone_name'] = obj.zone_name
                
                # Store key parameters directly
                key_params = {}
                for param in obj.parameters[:10]:  # Limit to first 10 parameters for snapshot
                    if param.field_name and param.value:
                        key_params[param.field_name] = param.value
                
                # Store parameters as JSON string
                param_dict['parameters'] = json.dumps(key_params) if key_params else None
                
                all_params.append(param_dict)
        
        if all_params:
            snapshot_df = pd.DataFrame(all_params)
            self.data_manager.save_building_snapshot(building_data.building_id, snapshot_df)
    
    # Keep all the parsing methods from original implementation
    def _parse_content(self, content: str) -> List[IDFObject]:
        """Parse IDF content into objects with improved parsing logic"""
        objects = []
        lines = content.split('\n')
        
        current_object_type = None
        current_params = []
        start_line = 0
        raw_text_lines = []
        in_object = False
        
        for line_num, line in enumerate(lines):
            # Skip empty lines and pure comment lines
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('!-'):
                continue
            
            # Split line into code and comment
            code_part = line
            comment_part = None
            
            if '!' in line and not stripped_line.startswith('!'):
                comment_index = line.index('!')
                code_part = line[:comment_index]
                comment_part = line[comment_index+1:].strip()
                if comment_part.startswith('- '):
                    comment_part = comment_part[2:]
            
            code_part = code_part.strip()
            
            if not code_part:
                continue
            
            # Check if this is a new object definition
            if code_part.endswith(',') and not in_object:
                potential_type = code_part.rstrip(',').strip()
                if potential_type and not potential_type.replace(':', '').replace('_', '').replace('.', '').replace('-', '').isdigit():
                    current_object_type = potential_type
                    current_params = []
                    start_line = line_num
                    raw_text_lines = [line]
                    in_object = True
            
            elif in_object:
                raw_text_lines.append(line)
                param_value = code_part.rstrip(',;').strip()
                
                param = IDFParameter(
                    value=param_value,
                    comment=comment_part,
                    position=len(current_params)
                )
                current_params.append(param)
                
                if code_part.endswith(';'):
                    if current_object_type:
                        obj = self._create_object(
                            current_object_type,
                            current_params,
                            '\n'.join(raw_text_lines),
                            start_line
                        )
                        if obj:
                            objects.append(obj)
                    
                    current_object_type = None
                    current_params = []
                    raw_text_lines = []
                    in_object = False
        
        return objects
    
    def _create_object(self, object_type: str, params: List[IDFParameter], 
                      raw_text: str, line_number: int) -> Optional[IDFObject]:
        """Create IDFObject with enhanced parameter extraction"""
        # Check if we should parse this object
        if not self._should_parse_object(object_type):
            return None
        
        if not params:
            return None
        


    # Check if we should parse parameters
        if hasattr(self, 'parse_parameters') and not self.parse_parameters:
            # Create minimal object with just name
            name = params[0].value if params[0].value else f"{object_type}_unnamed"
            category = self.category_map.get(object_type.upper(), 'other')
            
            return IDFObject(
                object_type=object_type,
                name=name,
                parameters=[params[0]],  # Keep only name parameter
                raw_text=raw_text,
                line_number=line_number,
                category=category
            )











        # Get field names for this object type
        field_names = self.field_names.get(object_type.upper(), self.field_names.get(object_type, []))
        
        # Special handling for Schedule:Compact which has variable fields
        if object_type.upper() == 'SCHEDULE:COMPACT':
            # First two fields are fixed, rest are variable
            for i, param in enumerate(params):
                if i < 2 and i < len(field_names):
                    param.field_name = field_names[i]
                else:
                    param.field_name = f'Field_{i+1}'
        else:
            # Regular field name assignment
            for i, param in enumerate(params):
                if i < len(field_names):
                    param.field_name = field_names[i]
                else:
                    param.field_name = f'Field_{i+1}'
        
        # Parse numeric values and units
        for param in params:
            if param.value:
                # Parse numeric value
                try:
                    param.numeric_value = float(param.value)
                except ValueError:
                    # Try scientific notation
                    try:
                        param.numeric_value = float(param.value.replace('e', 'E'))
                    except:
                        param.numeric_value = None
            
            # Extract units from comment
            param.units = self._extract_units(param.comment)
        
        # Object name is usually first parameter
        name = params[0].value if params[0].value else f"{object_type}_unnamed"
        
        # Determine category
        category = self.category_map.get(object_type.upper(), 'other')
        
        obj = IDFObject(
            object_type=object_type,
            name=name,
            parameters=params,
            raw_text=raw_text,
            line_number=line_number,
            category=category
        )
        
        # Extract zone name if applicable
        if self._is_zone_specific_object(object_type):
            obj.zone_name = self._extract_zone_name(obj)
        
        return obj
    
    def _extract_units(self, comment: Optional[str]) -> Optional[str]:
        """Extract units from comment string"""
        if not comment:
            return None
        
        # Common unit patterns in IDF comments
        unit_patterns = [
            r'\{([^}]+)\}',  # {W/m2-K}
            r'\[([^\]]+)\]',  # [m]
            r'\(([^)]+)\)',  # (deg)
        ]
        
        for pattern in unit_patterns:
            match = re.search(pattern, comment)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_zone_name(self, obj: IDFObject) -> Optional[str]:
        """Extract zone name from object with improved logic"""
        # For ZONE objects, the name is the zone name
        if obj.object_type.upper() == 'ZONE':
            return obj.name
        
        # For ZONELIST objects, we don't extract a zone name as it contains multiple zones
        if obj.object_type.upper() == 'ZONELIST':
            return None
        
        # For surfaces, zone is usually parameter 3 (index 3)
        if obj.object_type.upper() in ['BUILDINGSURFACE:DETAILED', 'FENESTRATIONSURFACE:DETAILED']:
            if len(obj.parameters) > 3:
                zone_name = obj.parameters[3].value
                if zone_name:
                    return zone_name
        
        # For equipment and other zone-related objects
        zone_keywords = ['Zone or ZoneList Name', 'Zone Name', 'Zone or ZoneList or Space or SpaceList Name']
        for i, param in enumerate(obj.parameters):
            if param.field_name in zone_keywords and param.value:
                return param.value
        
        # For objects with zone in the name
        if len(obj.parameters) > 1:
            zone_param = obj.parameters[1].value
            if zone_param and ('Zone' in zone_param or zone_param == 'ALL_ZONES'):
                return zone_param
        
        return None
    
    

    

    def _organize_objects(self, objects: List[IDFObject], building_data: BuildingData):
        """Organize objects by type and category with filtering"""
        for obj in objects:
            obj_type = obj.object_type.upper()
            
            # Check if we should parse this object
            if not self._should_parse_object(obj_type):
                continue
            
            # Store by object type
            if obj_type not in building_data.objects:
                building_data.objects[obj_type] = []
            building_data.objects[obj_type].append(obj)
            
            # Special handling for zones
            if obj_type == 'ZONE':
                building_data.zones[obj.name] = {
                    'object': obj,
                    'surfaces': [],
                    'equipment': [],
                    'controls': [],
                    'schedules': []
                }


    
    def _build_relationships(self, building_data: BuildingData):
        """Build relationships between objects"""
        # Map surfaces to zones
        for obj in building_data.objects.get('BUILDINGSURFACE:DETAILED', []):
            if obj.zone_name and obj.zone_name in building_data.zones:
                building_data.zones[obj.zone_name]['surfaces'].append(obj.name)
                building_data.zone_surfaces.setdefault(obj.zone_name, []).append(obj.name)
        
        # Map equipment to zones
        equipment_types = ['LIGHTS', 'ELECTRICEQUIPMENT', 'ZONEHVAC:IDEALLOADSAIRSYSTEM',
                          'ZONEINFILTRATION:DESIGNFLOWRATE', 'ZONEVENTILATION:DESIGNFLOWRATE']
        
        for eq_type in equipment_types:
            for obj in building_data.objects.get(eq_type.upper(), []):
                if obj.zone_name:
                    if obj.zone_name == 'ALL_ZONES':
                        # Add to all zones
                        for zone_name in building_data.zones:
                            building_data.zones[zone_name]['equipment'].append(obj.name)
                            building_data.zone_equipment.setdefault(zone_name, []).append(obj.name)
                    elif obj.zone_name in building_data.zones:
                        building_data.zones[obj.zone_name]['equipment'].append(obj.name)
                        building_data.zone_equipment.setdefault(obj.zone_name, []).append(obj.name)
    
    def _extract_metadata(self, building_data: BuildingData):
        """Extract key metadata from building including output info"""
        metadata = building_data.metadata
        
        # Building info
        if 'BUILDING' in building_data.objects:
            building_obj = building_data.objects['BUILDING'][0]
            metadata['building_name'] = building_obj.name
        
        # Zone count and types
        metadata['zone_count'] = len(building_data.zones)
        
        # Surface counts
        metadata['total_surfaces'] = len(building_data.objects.get('BUILDINGSURFACE:DETAILED', []))
        metadata['total_windows'] = len(building_data.objects.get('FENESTRATIONSURFACE:DETAILED', []))
        
        # Category counts
        metadata['category_counts'] = {}
        for obj_type, obj_list in building_data.objects.items():
            category = self.category_map.get(obj_type, 'other')
            if category not in metadata['category_counts']:
                metadata['category_counts'][category] = 0
            metadata['category_counts'][category] += len(obj_list)
        
        # File counts
        metadata['file_counts'] = {}
        for obj_type, obj_list in building_data.objects.items():
            output_file = OBJECT_TO_FILE.get(obj_type.upper(), 'other')
            if output_file not in metadata['file_counts']:
                metadata['file_counts'][output_file] = 0
            metadata['file_counts'][output_file] += len(obj_list)
        
        # Output reporting frequencies
        if 'variables' in building_data.output_definitions:
            frequencies = set()
            for obj in building_data.output_definitions['variables']:
                if len(obj.parameters) > 2:
                    frequencies.add(obj.parameters[2].value)
            metadata['output_frequencies'] = list(frequencies)
    
    def _save_relationships(self, building_data: BuildingData):
        """Save relationship data"""
        if not self.data_manager:
            return
        
        # Zone mappings
        zone_mappings = []
        for zone_name, zone_info in building_data.zones.items():
            zone_mappings.append({
                'building_id': building_data.building_id,
                'idf_zone_name': zone_name,
                'sql_zone_name': zone_name.upper(),  # Placeholder - will be updated by SQL analyzer
                'zone_type': self._determine_zone_type(zone_name),
                'multiplier': 1
            })
        
        if zone_mappings:
            self.data_manager.save_relationships('zone_mappings', pd.DataFrame(zone_mappings))
        
        # Surface adjacencies
        adjacencies = []
        # This would need more complex logic to determine actual adjacencies
        # Placeholder for now
        
        # Equipment assignments
        equipment_assignments = []
        for zone_name, equipment_list in building_data.zone_equipment.items():
            for equipment in equipment_list:
                equipment_assignments.append({
                    'building_id': building_data.building_id,
                    'equipment_name': equipment,
                    'equipment_type': self._get_equipment_type(equipment, building_data),
                    'assigned_zone': zone_name,
                    'schedule': 'ALWAYS_ON'  # Placeholder
                })
        
        if equipment_assignments:
            self.data_manager.save_relationships('equipment_assignments', pd.DataFrame(equipment_assignments))
    
    def _determine_zone_type(self, zone_name: str) -> str:
        """Determine zone type from name"""
        zone_name_lower = zone_name.lower()
        if 'core' in zone_name_lower:
            return 'Core'
        elif 'perimeter' in zone_name_lower:
            return 'Perimeter'
        elif 'plenum' in zone_name_lower:
            return 'Plenum'
        else:
            return 'Other'
    
    def _get_equipment_type(self, equipment_name: str, building_data: BuildingData) -> str:
        """Get equipment type from building data"""
        for obj_type, objects in building_data.objects.items():
            for obj in objects:
                if obj.name == equipment_name:
                    return obj.object_type
        return 'Unknown'