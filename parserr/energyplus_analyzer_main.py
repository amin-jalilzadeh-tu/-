"""
Enhanced EnergyPlus Analysis System v3.1 - Main Module with Output Support
Includes comprehensive output definition parsing and validation
"""
import os
import sys
import json
import pandas as pd
from pathlib import Path
import importlib.util
import re
from datetime import datetime
import time
import traceback
import warnings
import logging
from typing import Union, List, Dict, Optional, Any, Tuple, Set  # Add typing imports



warnings.filterwarnings('ignore')

# Import custom modules
from .data_manager import EnhancedHierarchicalDataManager, create_parameter_matrix
from .idf_parser import EnhancedIDFParser, BuildingData
from .sql_analyzer import EnhancedSQLAnalyzer

# Fix directories before starting
from .fix_directories import fix_project_directories

# ============================================================================
# ENHANCED CATEGORY MAPPINGS WITH OUTPUTS
# ============================================================================

CATEGORY_MAPPINGS = {
    'simulation_control': {
        'idf_objects': [
            'VERSION',
            'SIMULATIONCONTROL',
            'BUILDING',
            'TIMESTEP',
            'SITE:LOCATION',
            'SITE:GROUNDTEMPERATURE:BUILDINGSURFACE',
            'SITE:WATERMAINSTEMPERATURE',
            'SITE:PRECIPITATION',
            'SIZINGPERIOD:DESIGNDAY',
            'RUNPERIOD',
            'RUNPERIOD:CUSTOMRANGE',
            'RUNPERIODCONTROL:SPECIALDAYS',
            'RUNPERIODCONTROL:DAYLIGHTSAVINGTIME',
            'SHADOWCALCULATION',
            'SURFACECONVECTIONALGORITHM:INSIDE',
            'SURFACECONVECTIONALGORITHM:OUTSIDE',
            'HEATBALANCEALGORITHM',
            'CONVERGENCELIMITS'
        ],
        'sql_variables': [],
        'parameters': {},
        'key_metrics': []
    },
    
    'outputs': {
        'idf_objects': [
            'OUTPUT:VARIABLE',
            'OUTPUT:METER',
            'OUTPUT:TABLE:SUMMARYREPORTS',
            'OUTPUT:TABLE:MONTHLY',
            'OUTPUT:TABLE:TIMEBINS',
            'OUTPUT:SQLITE',
            'OUTPUTCONTROL:TABLE:STYLE',
            'OUTPUT:SURFACES:DRAWING',
            'OUTPUT:SURFACES:LIST',
            'OUTPUT:SCHEDULES',
            'OUTPUT:CONSTRUCTIONS',
            'OUTPUT:ENERGYMANAGEMENTSYSTEM',
            'OUTPUT:DIAGNOSTICS',
            'OUTPUT:DEBUGGINGDATA',
            'OUTPUT:PREPROCESSORMACROS',
            'OUTPUT:VARIABLEDICTIONARY',
            'OUTPUTCONTROL:REPORTINGTOLERANCES',
            'OUTPUTCONTROL:FILES'
        ],
        'sql_variables': [],  # These define what goes INTO SQL
        'parameters': {
            'variable_name': 'Variable Name',
            'key_value': 'Key Value',
            'reporting_frequency': 'Reporting Frequency',
            'meter_name': 'Key Name',
            'report_name': 'Report Name',
            'table_name': 'Name',
            'option_type': 'Option Type',
            'column_separator': 'Column Separator'
        },
        'key_metrics': ['total_output_variables', 'total_meters', 'reporting_frequencies', 'output_tables']
    },
    
    'schedules': {
        'idf_objects': [
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
        ],
        'sql_variables': [],
        'parameters': {},
        'key_metrics': []
    },
    
    'geometry': {
        'idf_objects': [
            'ZONE',
            'BUILDINGSURFACE:DETAILED',
            'FENESTRATIONSURFACE:DETAILED',
            'GLOBALGEOMETRYRULES',
            'FLOOR:DETAILED',
            'WALL:DETAILED',
            'ROOFCEILING:DETAILED',
            'WINDOW',
            'DOOR',
            'GLAZEDDOOR',
            'INTERIORSTARTINGPOINT',
            'DAYLIGHTINGDEVICE:TUBULAR'
        ],
        'sql_variables': [
            'Zone Mean Air Temperature',
            'Zone Air Temperature',
            'Zone Thermal Comfort Mean Radiant Temperature',
            'Zone Total Internal Total Heat Gain Rate',
            'Zone Total Internal Total Heat Gain Energy'
        ],
        'parameters': {
            'floor_area': 'Floor Area',
            'volume': 'Volume',
            'ceiling_height': 'Ceiling Height',
            'area': 'Area',
            'azimuth': 'Azimuth',
            'tilt': 'Tilt',
            'vertices': 'Number of Vertices',
            'zone_multiplier': 'Multiplier'
        },
        'key_metrics': ['total_floor_area', 'total_volume', 'window_wall_ratio']
    },
    
    'materials': {
        'idf_objects': [
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
        ],
        'sql_variables': [
            'Surface Inside Face Temperature',
            'Surface Outside Face Temperature',
            'Surface Inside Face Conduction Heat Transfer Rate',
            'Surface Outside Face Conduction Heat Transfer Rate',
            'Surface Average Face Conduction Heat Transfer Rate',
            'Surface Heat Storage Rate',
            'Surface Inside Face Convection Heat Transfer Rate',
            'Surface Outside Face Convection Heat Transfer Rate'
        ],
        'parameters': {
            'thickness': 'Thickness',
            'conductivity': 'Conductivity',
            'density': 'Density',
            'specific_heat': 'Specific Heat',
            'thermal_resistance': 'Thermal Resistance',
            'u_factor': 'U-Factor',
            'solar_heat_gain': 'Solar Heat Gain Coefficient',
            'roughness': 'Roughness'
        },
        'key_metrics': ['average_u_value', 'thermal_mass', 'envelope_performance']
    },
    
    'dhw': {
        'idf_objects': [
            'WATERHEATER:MIXED',
            'WATERHEATER:STRATIFIED',
            'WATERUSE:EQUIPMENT',
            'WATERUSE:CONNECTIONS',
            'PLANTLOOP',
            'PUMP:VARIABLESPEED',
            'PUMP:CONSTANTSPEED',
            'PIPE:ADIABATIC',
            'PIPE:INDOOR',
            'PIPE:OUTDOOR'
        ],
        'sql_variables': [
            'Water Heater Heating Energy',
            'Water Heater Heating Rate',
            'Water Heater Tank Temperature',
            'Water Heater Heat Loss Energy',
            'Water Heater Heat Loss Rate',
            'Water Use Equipment Hot Water Volume Flow Rate',
            'Water Use Equipment Hot Water Volume',
            'Water Use Equipment Total Volume Flow Rate',
            'Water Use Equipment Mains Water Volume'
        ],
        'parameters': {
            'tank_volume': 'Tank Volume',
            'heater_capacity': 'Heater Maximum Capacity',
            'setpoint_schedule': 'Setpoint Temperature Schedule Name',
            'thermal_efficiency': 'Heater Thermal Efficiency',
            'flow_rate': 'Peak Flow Rate',
            'fuel_type': 'Heater Fuel Type'
        },
        'key_metrics': ['total_hot_water_use', 'water_heating_energy', 'system_efficiency']
    },
    
    'equipment': {
        'idf_objects': [
            'ELECTRICEQUIPMENT',
            'GASEQUIPMENT',
            'HOTWATEREQUIPMENT',
            'STEAMEQUIPMENT',
            'OTHEREQUIPMENT',
            'EXTERIOREQUIPMENT',
            'EXTERIOR:LIGHTS',
            'REFRIGERATION:SYSTEM',
            'REFRIGERATION:COMPRESSORRACK'
        ],
        'sql_variables': [
            'Zone Electric Equipment Electricity Rate',
            'Zone Electric Equipment Electricity Energy',
            'Zone Electric Equipment Total Heating Rate',
            'Zone Electric Equipment Total Heating Energy',
            'Zone Electric Equipment Radiant Heating Rate',
            'Zone Electric Equipment Radiant Heating Energy',
            'Zone Electric Equipment Convective Heating Rate',
            'Zone Electric Equipment Latent Gain Rate',
            'Zone Gas Equipment Gas Rate',
            'Zone Gas Equipment Gas Energy'
        ],
        'parameters': {
            'design_level': 'Design Level',
            'watts_per_area': 'Watts per Zone Floor Area',
            'schedule': 'Schedule Name',
            'fraction_latent': 'Fraction Latent',
            'fraction_radiant': 'Fraction Radiant',
            'fraction_lost': 'Fraction Lost',
            'end_use': 'End-Use Subcategory'
        },
        'key_metrics': ['total_equipment_power', 'peak_demand', 'annual_consumption']
    },
    
    'lighting': {
        'idf_objects': [
            'LIGHTS',
            'DAYLIGHTING:CONTROLS',
            'DAYLIGHTING:REFERENCEPOINT',
            'DAYLIGHTING:DELIGHT:REFERENCEPOINT',
            'DAYLIGHTING:DELIGHT:CONTROLS',
            'LIGHTINGDESIGNDAY',
            'EXTERIORLIGHTS',
            'OUTPUT:ILLUMINANCEMAP',
            'OUTPUTCONTROL:ILLUMINANCEMAP:STYLE'
        ],
        'sql_variables': [
            'Zone Lights Electricity Rate',
            'Zone Lights Electricity Energy',
            'Zone Lights Total Heating Rate',
            'Zone Lights Total Heating Energy',
            'Zone Lights Visible Radiation Rate',
            'Zone Lights Visible Radiation Energy',
            'Zone Lights Convective Heating Rate',
            'Zone Lights Radiant Heating Rate',
            'Zone Lights Return Air Heating Rate',
            'Daylighting Reference Point 1 Illuminance',
            'Daylighting Lighting Power Multiplier'
        ],
        'parameters': {
            'design_level': 'Lighting Level',
            'watts_per_area': 'Watts per Zone Floor Area',
            'schedule': 'Schedule Name',
            'fraction_radiant': 'Fraction Radiant',
            'fraction_visible': 'Fraction Visible',
            'fraction_replaceable': 'Fraction Replaceable',
            'return_air_fraction': 'Return Air Fraction',
            'end_use': 'End-Use Subcategory'
        },
        'key_metrics': ['lighting_power_density', 'annual_lighting_energy', 'daylighting_savings']
    },
    
    'hvac': {
        'idf_objects': [
            'ZONEHVAC:IDEALLOADSAIRSYSTEM',
            'ZONEHVAC:EQUIPMENTLIST',
            'ZONEHVAC:EQUIPMENTCONNECTIONS',
            'COIL:COOLING:DX:SINGLESPEED',
            'COIL:COOLING:DX:TWOSPEED',
            'COIL:COOLING:DX:VARIABLESPEED',
            'COIL:HEATING:ELECTRIC',
            'COIL:HEATING:GAS',
            'COIL:HEATING:WATER',
            'FAN:SYSTEMMODEL',
            'FAN:CONSTANTVOLUME',
            'FAN:VARIABLEVOLUME',
            'FAN:ONOFF',
            'THERMOSTATSETPOINT:DUALSETPOINT',
            'THERMOSTATSETPOINT:SINGLEHEATING',
            'THERMOSTATSETPOINT:SINGLECOOLING',
            'ZONECONTROL:THERMOSTAT',
            'SIZING:ZONE',
            'SIZING:SYSTEM',
            'SIZING:PLANT',
            'AIRLOOPHVAC',
            'AIRLOOPHVAC:UNITARY:FURNACE:HEATONLY',
            'AIRLOOPHVAC:UNITARY:FURNACE:HEATCOOL',
            'CONTROLLER:OUTDOORAIR',
            'CONTROLLER:WATERCOIL',
            'SETPOINTMANAGER:SCHEDULED',
            'SETPOINTMANAGER:SINGLEZONE:REHEAT',
            'AVAILABILITYMANAGER:SCHEDULED',
            'AVAILABILITYMANAGER:NIGHTCYCLE'
        ],
        'sql_variables': [
            'Zone Air System Sensible Cooling Rate',
            'Zone Air System Sensible Cooling Energy',
            'Zone Air System Sensible Heating Rate',
            'Zone Air System Sensible Heating Energy',
            'Zone Air System Total Cooling Rate',
            'Zone Air System Total Cooling Energy',
            'Zone Air System Total Heating Rate',
            'Zone Air System Total Heating Energy',
            'Cooling Coil Total Cooling Rate',
            'Heating Coil Heating Rate',
            'Fan Electricity Rate',
            'Fan Electricity Energy',
            'System Node Temperature',
            'System Node Mass Flow Rate',
            'Zone Mean Air Temperature',
            'Zone Thermostat Cooling Setpoint Temperature',
            'Zone Thermostat Heating Setpoint Temperature',
            'Zone Predicted Sensible Load to Cooling Setpoint Heat Transfer Rate',
            'Zone Predicted Sensible Load to Heating Setpoint Heat Transfer Rate'
        ],
        'parameters': {
            'cooling_capacity': 'Maximum Total Cooling Capacity',
            'heating_capacity': 'Maximum Sensible Heating Capacity',
            'cooling_setpoint': 'Cooling Setpoint Temperature Schedule Name',
            'heating_setpoint': 'Heating Setpoint Temperature Schedule Name',
            'schedule': 'Availability Schedule Name',
            'design_supply_air_flow': 'Design Supply Air Flow Rate',
            'cooling_cop': 'Cooling COP',
            'heating_efficiency': 'Heating Efficiency'
        },
        'key_metrics': ['total_cooling_load', 'total_heating_load', 'system_cop', 'unmet_hours']
    },
    
    'ventilation': {
        'idf_objects': [
            'ZONEVENTILATION:DESIGNFLOWRATE',
            'ZONEVENTILATION:WINDANDSTACKDRIVENFLOW',
            'ZONEAIRBALANCE:OUTDOORAIR',
            'ZONECROSSMIXING',
            'ZONEMIXING',
            'DESIGNSPECIFICATION:OUTDOORAIR',
            'DESIGNSPECIFICATION:ZONEAIRDISTRIBUTION',
            'CONTROLLER:MECHANICALVENTILATION',
            'CONTROLLER:OUTDOORAIR',
            'OUTDOORAIR:MIXER',
            'OUTDOORAIR:NODE',
            'AIRFLOWNETWORK:SIMULATIONCONTROL',
            'AIRFLOWNETWORK:MULTIZONE:ZONE',
            'AIRFLOWNETWORK:MULTIZONE:SURFACE'
        ],
        'sql_variables': [
            'Zone Ventilation Sensible Heat Gain Energy',
            'Zone Ventilation Sensible Heat Loss Energy',
            'Zone Ventilation Latent Heat Gain Energy',
            'Zone Ventilation Latent Heat Loss Energy',
            'Zone Ventilation Total Heat Gain Energy',
            'Zone Ventilation Total Heat Loss Energy',
            'Zone Ventilation Current Density Volume Flow Rate',
            'Zone Ventilation Standard Density Volume Flow Rate',
            'Zone Ventilation Mass Flow Rate',
            'Zone Ventilation Air Change Rate',
            'Zone Ventilation Fan Electricity Energy',
            'Zone Mechanical Ventilation Current Density Volume Flow Rate',
            'Zone Mechanical Ventilation Standard Density Volume Flow Rate',
            'Zone Mechanical Ventilation Mass Flow Rate',
            'Zone Mechanical Ventilation Air Change Rate'
        ],
        'parameters': {
            'design_flow_rate': 'Design Flow Rate',
            'flow_per_area': 'Flow Rate per Zone Floor Area',
            'flow_per_person': 'Flow Rate per Person',
            'air_changes': 'Air Changes per Hour',
            'schedule': 'Schedule Name',
            'ventilation_type': 'Ventilation Type',
            'fan_efficiency': 'Fan Total Efficiency',
            'minimum_outdoor_air': 'Minimum Outdoor Air Flow Rate',
            'temperature_schedule': 'Minimum Indoor Temperature Schedule Name'
        },
        'key_metrics': ['average_ventilation_rate', 'ventilation_energy_loss', 'air_change_effectiveness']
    },
    
    'infiltration': {
        'idf_objects': [
            'ZONEINFILTRATION:DESIGNFLOWRATE',
            'ZONEINFILTRATION:EFFECTIVELEAKAGEAREA',
            'ZONEINFILTRATION:FLOWCOEFFICIENT',
            'SPACEINFILTRATION:DESIGNFLOWRATE',
            'SPACEINFILTRATION:EFFECTIVELEAKAGEAREA',
            'SPACEINFILTRATION:FLOWCOEFFICIENT',
            'ZONEAIRBALANCE:OUTDOORAIR'
        ],
        'sql_variables': [
            'Zone Infiltration Sensible Heat Gain Energy',
            'Zone Infiltration Sensible Heat Loss Energy',
            'Zone Infiltration Latent Heat Gain Energy',
            'Zone Infiltration Latent Heat Loss Energy',
            'Zone Infiltration Total Heat Gain Energy',
            'Zone Infiltration Total Heat Loss Energy',
            'Zone Infiltration Current Density Volume Flow Rate',
            'Zone Infiltration Standard Density Volume Flow Rate',
            'Zone Infiltration Mass Flow Rate',
            'Zone Infiltration Air Change Rate',
            'Zone Infiltration Volume',
            'AFN Zone Infiltration Sensible Heat Gain Energy',
            'AFN Zone Infiltration Sensible Heat Loss Energy'
        ],
        'parameters': {
            'design_flow_rate': 'Design Flow Rate',
            'flow_per_area': 'Flow per Exterior Surface Area',
            'air_changes': 'Air Changes per Hour',
            'schedule': 'Schedule Name',
            'constant_coef': 'Constant Term Coefficient',
            'temp_coef': 'Temperature Term Coefficient',
            'velocity_coef': 'Velocity Term Coefficient',
            'velocity_squared_coef': 'Velocity Squared Term Coefficient'
        },
        'key_metrics': ['average_infiltration_rate', 'infiltration_energy_impact', 'peak_infiltration']
    },
    
    'shading': {
        'idf_objects': [
            'WINDOWSHADINGCONTROL',
            'SHADING:SITE',
            'SHADING:SITE:DETAILED',
            'SHADING:BUILDING',
            'SHADING:BUILDING:DETAILED',
            'SHADING:ZONE',
            'SHADING:ZONE:DETAILED',
            'SHADING:OVERHANG',
            'SHADING:OVERHANG:PROJECTION',
            'SHADING:FIN',
            'SHADING:FIN:PROJECTION'
        ],
        'sql_variables': [
            'Surface Shading Device Is On Time Fraction',
            'Surface Window Blind Slat Angle',
            'Surface Window Shading Device Absorbed Solar Radiation Rate',
            'Surface Window Shading Device Absorbed Solar Radiation Energy',
            'Surface Window Transmitted Solar Radiation Rate',
            'Surface Window Transmitted Solar Radiation Energy',
            'Surface Outside Face Incident Solar Radiation Rate per Area',
            'Surface Outside Face Incident Beam Solar Radiation Rate per Area',
            'Surface Outside Face Incident Sky Diffuse Solar Radiation Rate per Area',
            'Surface Outside Face Incident Ground Diffuse Solar Radiation Rate per Area',
            'Zone Windows Total Transmitted Solar Radiation Rate',
            'Zone Windows Total Transmitted Solar Radiation Energy',
            'Zone Exterior Windows Total Transmitted Beam Solar Radiation Rate',
            'Zone Exterior Windows Total Transmitted Diffuse Solar Radiation Rate'
        ],
        'parameters': {
            'shading_type': 'Shading Type',
            'schedule': 'Shading Control Schedule Name',
            'setpoint': 'Setpoint',
            'slat_angle': 'Slat Angle',
            'construction': 'Construction with Shading Name',
            'control_type': 'Shading Control Type',
            'glare_control': 'Glare Control Is Active'
        },
        'key_metrics': ['shading_effectiveness', 'solar_heat_gain_reduction', 'annual_shading_hours']
    }
}

# ============================================================================
# ENHANCED MAIN ANALYZER CLASS
# ============================================================================

class EnergyPlusAnalyzer:
    """Enhanced analyzer with output support"""
    
    def __init__(self, project_path: Union[str, Path]):
        """Initialize analyzer with project path"""
        self.project_path = Path(project_path)
        
        # Ensure all directories exist before starting
        print(f"Ensuring directory structure for: {self.project_path}")
        fix_project_directories(str(self.project_path))
        
        self.data_manager = EnhancedHierarchicalDataManager(self.project_path)
        
        # Initialize components
        self.idf_parser = EnhancedIDFParser(CATEGORY_MAPPINGS, self.data_manager)
        self.sql_analyzers = {}  # Will store SQL analyzers by building
        
        # Category mappings
        self.category_mappings = CATEGORY_MAPPINGS
        
        # Output tracking
        self.output_definitions = {}  # Store output definitions by building
        
        print(f"\nInitialized Enhanced EnergyPlus Analyzer v3.1")
        print(f"Project path: {self.project_path}")
    
    def analyze_project(self, idf_sql_pairs: List[Tuple[str, str]],
                    categories: List[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    validate_outputs: bool = True,
                    building_id_map: Optional[Dict[str, str]] = None):  # New parameter
        """Analyze multiple IDF/SQL file pairs with output validation"""
        
        if categories is None:
            categories = list(self.category_mappings.keys())
        
        print(f"\nAnalyzing {len(idf_sql_pairs)} buildings")
        print(f"Categories: {', '.join(categories)}")
        
        # Process each building
        building_registry = []
        output_validation_results = []
        
        for idx, (idf_path, sql_path) in enumerate(idf_sql_pairs):
            print(f"\n{'='*60}")
            print(f"Processing building {idx+1}/{len(idf_sql_pairs)}")
            print(f"IDF: {Path(idf_path).name}")
            print(f"SQL: {Path(sql_path).name}")
            print(f"{'='*60}")
            
            try:
                # Parse IDF
                print("\nParsing IDF file...")
                building_data = self.idf_parser.parse_and_save(idf_path)
                
                # Override building_id if mapping provided
                if building_id_map and str(idf_path) in building_id_map:
                    building_data.building_id = building_id_map[str(idf_path)]
                    print(f"Using mapped building ID: {building_data.building_id}")
                
                # Extract output definitions
                output_config = self._extract_output_definitions(building_data)
                self.output_definitions[building_data.building_id] = output_config
                
                # Initialize SQL analyzer
                print("\nInitializing SQL analyzer...")
                sql_analyzer = EnhancedSQLAnalyzer(Path(sql_path), self.data_manager)
                self.sql_analyzers[building_data.building_id] = sql_analyzer
                
                # Build zone mapping
                print("\nBuilding zone name mapping...")
                zone_mapping = sql_analyzer.build_zone_mapping(list(building_data.zones.keys()))
                
                # Validate outputs if requested
                if validate_outputs:
                    print("\nValidating output completeness...")
                    validation_result = self._validate_outputs(building_data.building_id, sql_analyzer, output_config)
                    output_validation_results.append(validation_result)
                    
                    # Show validation summary
                    print(f"  Output coverage: {validation_result['coverage']:.1f}%")
                    if validation_result['missing']:
                        print(f"  Missing outputs: {len(validation_result['missing'])}")
                    if validation_result['partial']:
                        print(f"  Partial data: {len(validation_result['partial'])}")
                
                # Extract SQL data by category
                variables_by_category = {
                    cat: self.category_mappings[cat]['sql_variables'] 
                    for cat in categories
                    if self.category_mappings[cat]['sql_variables']
                }
                
                print("\nExtracting SQL time series data...")
                try:
                    sql_analyzer.extract_and_save_all(
                        zone_mapping, 
                        variables_by_category,
                        start_date,
                        end_date
                    )
                except Exception as e:
                    print(f"Warning: Error during SQL data extraction: {str(e)}")
                    print("Continuing with partial data...")
                
                # Add to registry
                building_registry.append({
                    'building_id': building_data.building_id,
                    'ogc_fid': building_data.building_id,
                    'idf_path': str(idf_path),
                    'sql_path': str(sql_path),
                    'zone_count': len(building_data.zones),
                    'output_variables': len(output_config['variables']),
                    'output_meters': len(output_config['meters']),
                    'status': 'completed',
                    'last_modified': pd.Timestamp.now()
                })
                
            except Exception as e:
                print(f"\nError processing building {idx+1}: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # Add failed building to registry
                building_registry.append({
                    'building_id': f'building_{idx}',
                    'ogc_fid': f'building_{idx}',
                    'idf_path': str(idf_path),
                    'sql_path': str(sql_path),
                    'zone_count': 0,
                    'output_variables': 0,
                    'output_meters': 0,
                    'status': 'failed',
                    'last_modified': pd.Timestamp.now()
                })
        
        # Update project metadata
        print("\nUpdating project metadata...")
        self.data_manager.update_building_registry(pd.DataFrame(building_registry))
        self.data_manager.update_project_manifest(len(building_registry), categories)
        self.data_manager.update_category_schemas()
        
        # Save output validation results
        if output_validation_results:
            self._save_output_validation_results(output_validation_results)
        
        # Create parameter matrix
        print("\nCreating parameter matrix...")
        try:
            parameter_matrix = create_parameter_matrix(self.data_manager)
            print(f"Parameter matrix created with shape: {parameter_matrix.shape}")
        except Exception as e:
            print(f"Warning: Could not create parameter matrix: {e}")
        
        # Generate output documentation
        print("\nGenerating output documentation...")
        self._generate_output_documentation()
        
        print(f"\nAnalysis complete!")
        print(f"Data stored in: {self.project_path}")
        
        # Show summary
        self.show_data_summary()
    












    def analyze_project_selective(self, file_pairs: List[Tuple[Optional[str], Optional[str], str]],
                                idf_content_config: Dict[str, Any] = None,
                                sql_content_config: Dict[str, Any] = None,
                                output_options: Dict[str, Any] = None,
                                performance_options: Dict[str, Any] = None,
                                validation_options: Dict[str, Any] = None,
                                validate_outputs: bool = True):
        """
        Analyze files with selective content parsing
        
        Args:
            file_pairs: List of (idf_path, sql_path, building_id) tuples
            idf_content_config: Configuration for IDF content filtering
            sql_content_config: Configuration for SQL content filtering
            output_options: Output format and compression options
            performance_options: Performance settings
            validation_options: Validation settings
        """
        
        # Default configurations
        if idf_content_config is None:
            idf_content_config = {"mode": "all"}
        if sql_content_config is None:
            sql_content_config = {"mode": "all"}
        
        print(f"\nAnalyzing {len(file_pairs)} files with selective parsing")
        print(f"IDF content mode: {idf_content_config.get('mode', 'all')}")
        print(f"SQL content mode: {sql_content_config.get('mode', 'all')}")
        
        # Validate configuration before starting
        if validation_options and validation_options.get('validate_before_parsing', True):
            validation_passed = self._validate_parsing_config(file_pairs, idf_content_config, sql_content_config)
            if not validation_passed and not validation_options.get('continue_on_error', True):
                print("Validation failed. Stopping parsing.")
                return
        
        # Process each file pair
        building_registry = []
        parse_results = []
        
        for idx, (idf_path, sql_path, building_id) in enumerate(file_pairs):
            print(f"\n{'='*60}")
            print(f"Processing file {idx+1}/{len(file_pairs)}")
            print(f"Building ID: {building_id}")
            if idf_path:
                print(f"IDF: {Path(idf_path).name}")
            if sql_path:
                print(f"SQL: {Path(sql_path).name}")
            print(f"{'='*60}")
            
            try:
                # Track what was parsed
                parsed_info = {
                    'building_id': building_id,
                    'idf_parsed': False,
                    'sql_parsed': False,
                    'idf_categories': [],
                    'sql_variables': [],
                    'errors': []
                }
                
                # Parse IDF if provided
                if idf_path and os.path.isfile(idf_path):
                    print("\nParsing IDF file...")
                    try:
                        # Configure parser with content filters
                        self.idf_parser.set_content_filter(idf_content_config)
                        
                        building_data = self.idf_parser.parse_and_save(idf_path)
                        building_data.building_id = building_id  # Override with our ID
                        
                        parsed_info['idf_parsed'] = True
                        parsed_info['idf_categories'] = list(building_data.metadata.get('category_counts', {}).keys())
                        
                        # Extract output definitions if needed
                        if self._should_parse_outputs(idf_content_config):
                            output_config = self._extract_output_definitions(building_data)
                            self.output_definitions[building_id] = output_config
                        
                    except Exception as e:
                        print(f"Error parsing IDF: {str(e)}")
                        parsed_info['errors'].append(f"IDF parse error: {str(e)}")
                        if not validation_options.get('continue_on_error', True):
                            raise
                
                # Parse SQL if provided
                if sql_path and os.path.isfile(sql_path):
                    print("\nParsing SQL file...")
                    try:
                        # Initialize SQL analyzer with content filter
                        sql_analyzer = EnhancedSQLAnalyzer(Path(sql_path), self.data_manager)
                        sql_analyzer.building_id = building_id  # Override with our ID
                        self.sql_analyzers[building_id] = sql_analyzer
                        
                        # Apply SQL content filters
                        filtered_categories = self._filter_sql_categories(self.category_mappings, sql_content_config)
                        
                        if filtered_categories:
                            # Extract only requested content
                            sql_analyzer.extract_selective(
                                content_config=sql_content_config,
                                variables_by_category=filtered_categories
                            )
                            
                            parsed_info['sql_parsed'] = True
                            parsed_info['sql_variables'] = list(filtered_categories.keys())
                        
                    except Exception as e:
                        print(f"Error parsing SQL: {str(e)}")
                        parsed_info['errors'].append(f"SQL parse error: {str(e)}")
                        if not validation_options.get('continue_on_error', True):
                            raise
                
                # Add to parse results
                parse_results.append(parsed_info)
                
                # Add to registry
                building_registry.append({
                    'building_id': building_id,
                    'ogc_fid': building_id,
                    'idf_path': str(idf_path) if idf_path else None,
                    'sql_path': str(sql_path) if sql_path else None,
                    'idf_parsed': parsed_info['idf_parsed'],
                    'sql_parsed': parsed_info['sql_parsed'],
                    'parse_errors': len(parsed_info['errors']),
                    'status': 'completed' if not parsed_info['errors'] else 'completed_with_errors',
                    'last_modified': pd.Timestamp.now()
                })
                
            except Exception as e:
                print(f"\nError processing building {building_id}: {str(e)}")
                if not validation_options.get('continue_on_error', True):
                    raise
                
                # Add failed building to registry
                building_registry.append({
                    'building_id': building_id,
                    'ogc_fid': building_id,
                    'idf_path': str(idf_path) if idf_path else None,
                    'sql_path': str(sql_path) if sql_path else None,
                    'idf_parsed': False,
                    'sql_parsed': False,
                    'parse_errors': 1,
                    'status': 'failed',
                    'last_modified': pd.Timestamp.now()
                })
        
        # Flush any buffered data
        if self.data_manager:
            self.data_manager.flush_category_buffers()
        
        # Update project metadata
        print("\nUpdating project metadata...")
        self.data_manager.update_building_registry(pd.DataFrame(building_registry))
        
        # Get actual categories parsed
        parsed_categories = set()
        for result in parse_results:
            parsed_categories.update(result['idf_categories'])
            parsed_categories.update(result['sql_variables'])
        
        self.data_manager.update_project_manifest(len(building_registry), list(parsed_categories))
        self.data_manager.update_category_schemas()
        
        # Save parse results
        if validation_options and validation_options.get('save_validation_report', True):
            self._save_parse_results(parse_results)
        
        # Create parameter matrix if requested
        if output_options and output_options.get('create_summary', True):
            print("\nCreating parameter matrix...")
            try:
                parameter_matrix = create_parameter_matrix(self.data_manager)
                print(f"Parameter matrix created with shape: {parameter_matrix.shape}")
            except Exception as e:
                print(f"Warning: Could not create parameter matrix: {e}")
        
        print(f"\nSelective parsing complete!")
        print(f"Files processed: {len(file_pairs)}")
        print(f"Successful: {sum(1 for r in parse_results if not r['errors'])}")
        print(f"With errors: {sum(1 for r in parse_results if r['errors'])}")
        
        # Show summary
        self.show_data_summary()


    def _should_parse_outputs(self, idf_content_config: Dict[str, Any]) -> bool:
        """Check if output definitions should be parsed"""
        mode = idf_content_config.get('mode', 'all')
        
        if mode == 'all':
            return True
        
        if mode == 'categories_only':
            return 'outputs' in idf_content_config.get('categories', [])
        
        if mode == 'objects_only':
            output_objects = ['OUTPUT:VARIABLE', 'OUTPUT:METER', 'OUTPUT:TABLE:SUMMARYREPORTS']
            requested_objects = idf_content_config.get('object_types', [])
            return any(obj in requested_objects for obj in output_objects)
        
        return False


    def _filter_sql_categories(self, category_mappings: Dict[str, Dict], 
                            sql_content_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """Filter SQL variables based on configuration"""
        mode = sql_content_config.get('mode', 'all')
        
        if mode == 'all':
            # Return all variables
            return {
                cat: config['sql_variables'] 
                for cat, config in category_mappings.items()
                if config['sql_variables']
            }
        
        variables_config = sql_content_config.get('variables', {})
        var_mode = variables_config.get('mode', 'all')
        
        filtered = {}
        
        if var_mode == 'categories':
            # Only specified categories
            requested_categories = variables_config.get('categories', [])
            for cat, config in category_mappings.items():
                if cat in requested_categories and config['sql_variables']:
                    filtered[cat] = config['sql_variables']
        
        elif var_mode == 'specific':
            # Only specified variables
            requested_vars = variables_config.get('variable_names', [])
            for cat, config in category_mappings.items():
                cat_vars = [v for v in config['sql_variables'] if v in requested_vars]
                if cat_vars:
                    filtered[cat] = cat_vars
        
        elif var_mode == 'pattern':
            # Pattern matching
            patterns = variables_config.get('variable_patterns', [])
            exclude_patterns = variables_config.get('exclude_patterns', [])
            
            for cat, config in category_mappings.items():
                cat_vars = []
                for var in config['sql_variables']:
                    # Check include patterns
                    include = any(self._match_pattern(var, p) for p in patterns) if patterns else True
                    # Check exclude patterns
                    exclude = any(self._match_pattern(var, p) for p in exclude_patterns)
                    
                    if include and not exclude:
                        cat_vars.append(var)
                
                if cat_vars:
                    filtered[cat] = cat_vars
        
        else:
            # Default to all
            return self._filter_sql_categories(category_mappings, {'mode': 'all'})
        
        return filtered


    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Match text against a pattern (supports * wildcard)"""
        # Convert pattern to regex
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(regex_pattern, text, re.IGNORECASE))


    def _validate_parsing_config(self, file_pairs: List[Tuple], 
                            idf_content_config: Dict[str, Any],
                            sql_content_config: Dict[str, Any]) -> bool:
        """Validate parsing configuration before starting"""
        print("\nValidating parsing configuration...")
        
        valid = True
        warnings = []
        errors = []
        
        # Check file existence
        for idf_path, sql_path, building_id in file_pairs:
            if idf_path and not os.path.isfile(idf_path):
                errors.append(f"IDF file not found: {idf_path}")
                valid = False
            if sql_path and not os.path.isfile(sql_path):
                errors.append(f"SQL file not found: {sql_path}")
                valid = False
        
        # Validate IDF content config
        if idf_content_config.get('mode') == 'objects_only':
            requested_objects = idf_content_config.get('object_types', [])
            if not requested_objects:
                warnings.append("IDF objects_only mode but no object_types specified")
        
        # Validate SQL content config
        if sql_content_config.get('mode') == 'selective':
            variables_config = sql_content_config.get('variables', {})
            if variables_config.get('mode') == 'specific' and not variables_config.get('variable_names'):
                warnings.append("SQL specific variables mode but no variable_names specified")
        
        # Print results
        if errors:
            print(f"\nValidation ERRORS ({len(errors)}):")
            for error in errors[:5]:  # Show first 5
                print(f"  - {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")
        
        if warnings:
            print(f"\nValidation warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
        
        if valid:
            print("\nValidation passed!")
        else:
            print("\nValidation failed!")
        
        return valid


    def _save_parse_results(self, parse_results: List[Dict[str, Any]]):
        """Save detailed parse results"""
        results_df = pd.DataFrame(parse_results)
        
        # Save to project metadata
        results_path = self.project_path / 'metadata' / 'parse_results.parquet'
        results_df.to_parquet(results_path, index=False)
        
        # Create summary
        summary = {
            'total_buildings': len(parse_results),
            'idf_parsed': sum(1 for r in parse_results if r['idf_parsed']),
            'sql_parsed': sum(1 for r in parse_results if r['sql_parsed']),
            'both_parsed': sum(1 for r in parse_results if r['idf_parsed'] and r['sql_parsed']),
            'with_errors': sum(1 for r in parse_results if r['errors']),
            'timestamp': datetime.now().isoformat()
        }
        
        summary_path = self.project_path / 'metadata' / 'parse_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)











    
    def _extract_output_definitions(self, building_data: BuildingData) -> Dict[str, Any]:
        """Extract output definitions from building data"""
        output_config = {
            'variables': [],
            'meters': [],
            'tables': [],
            'reporting_frequencies': set(),
            'sqlite_options': None,
            'table_style': None
        }
        
        # Extract OUTPUT:VARIABLE definitions
        for obj in building_data.objects.get('OUTPUT:VARIABLE', []):
            if len(obj.parameters) >= 3:
                var_def = {
                    'key_value': obj.parameters[0].value if obj.parameters[0].value else '*',
                    'variable_name': obj.parameters[1].value if len(obj.parameters) > 1 else '',
                    'reporting_frequency': obj.parameters[2].value if len(obj.parameters) > 2 else 'Hourly'
                }
                output_config['variables'].append(var_def)
                output_config['reporting_frequencies'].add(var_def['reporting_frequency'])
        
        # Extract OUTPUT:METER definitions
        for obj in building_data.objects.get('OUTPUT:METER', []):
            if len(obj.parameters) >= 2:
                meter_def = {
                    'meter_name': obj.parameters[0].value if obj.parameters[0].value else '',
                    'reporting_frequency': obj.parameters[1].value if len(obj.parameters) > 1 else 'Hourly'
                }
                output_config['meters'].append(meter_def)
                output_config['reporting_frequencies'].add(meter_def['reporting_frequency'])
        
        # Extract OUTPUT:TABLE definitions
        for obj in building_data.objects.get('OUTPUT:TABLE:SUMMARYREPORTS', []):
            for param in obj.parameters:
                if param.value:
                    output_config['tables'].append({
                        'report_name': param.value,
                        'type': 'summary'
                    })
        
        for obj in building_data.objects.get('OUTPUT:TABLE:MONTHLY', []):
            if obj.parameters:
                output_config['tables'].append({
                    'table_name': obj.parameters[0].value if obj.parameters[0].value else 'Monthly Table',
                    'type': 'monthly'
                })
        
        # Extract OUTPUT:SQLITE
        for obj in building_data.objects.get('OUTPUT:SQLITE', []):
            if obj.parameters:
                output_config['sqlite_options'] = obj.parameters[0].value
        
        # Extract OUTPUTCONTROL:TABLE:STYLE
        for obj in building_data.objects.get('OUTPUTCONTROL:TABLE:STYLE', []):
            if obj.parameters:
                output_config['table_style'] = obj.parameters[0].value
        
        return output_config
    
    def _validate_outputs(self, building_id: str, sql_analyzer: EnhancedSQLAnalyzer, 
                     output_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that SQL contains requested outputs"""
        validation_result = {
            'building_id': building_id,
            'total_requested': len(output_config['variables']),
            'found': 0,
            'missing': [],
            'partial': [],
            'coverage': 0.0
        }
        
        # Get available variables from SQL
        try:
            available_query = """
                SELECT DISTINCT Name, KeyValue, ReportingFrequency
                FROM ReportDataDictionary
            """
            available_vars = pd.read_sql_query(available_query, sql_analyzer.sql_conn)
            
            # Create lookup set
            available_set = set()
            for _, row in available_vars.iterrows():
                available_set.add((row['Name'], row['KeyValue'], row['ReportingFrequency']))
            
            # Check each requested output
            for var_def in output_config['variables']:
                key = var_def['key_value']
                var_name = var_def['variable_name']
                freq = var_def['reporting_frequency']
                
                # Check if exists (handle wildcards)
                found = False
                if key == '*':
                    # Check if variable exists for any key
                    for avail_key in available_vars['KeyValue'].unique():
                        if (var_name, avail_key, freq) in available_set:
                            found = True
                            break
                else:
                    if (var_name, key, freq) in available_set:
                        found = True
                
                if found:
                    validation_result['found'] += 1
                else:
                    validation_result['missing'].append({
                        'variable': var_name,
                        'key': key,
                        'frequency': freq
                    })
            
            # Calculate coverage
            if validation_result['total_requested'] > 0:
                validation_result['coverage'] = (validation_result['found'] / validation_result['total_requested']) * 100
            
        except Exception as e:
            print(f"Error during output validation: {e}")
        
        return validation_result
    
    def _save_output_validation_results(self, validation_results: List[Dict[str, Any]]):
        """Save output validation results"""
        # Convert to DataFrame
        validation_df = pd.DataFrame(validation_results)
        
        # Save to metadata
        output_path = self.project_path / 'metadata' / 'output_validation.parquet'
        validation_df.to_parquet(output_path, index=False)
        
        # Also save missing outputs detail
        all_missing = []
        for result in validation_results:
            for missing in result.get('missing', []):
                missing['building_id'] = result['building_id']
                all_missing.append(missing)
        
        if all_missing:
            missing_df = pd.DataFrame(all_missing)
            missing_path = self.project_path / 'metadata' / 'missing_outputs.parquet'
            missing_df.to_parquet(missing_path, index=False)
    
    def _generate_output_documentation(self):
        """Generate comprehensive output documentation"""
        doc = {
            'project': str(self.project_path),
            'timestamp': pd.Timestamp.now().isoformat(),
            'buildings': {},
            'summary': {
                'total_buildings': len(self.output_definitions),
                'unique_variables': set(),
                'unique_meters': set(),
                'reporting_frequencies': set()
            }
        }
        
        # Categorize outputs
        output_categories = {
            'energy': [],
            'comfort': [],
            'hvac': [],
            'envelope': [],
            'environmental': [],
            'other': []
        }
        
        for building_id, config in self.output_definitions.items():
            doc['buildings'][building_id] = {
                'variables': len(config['variables']),
                'meters': len(config['meters']),
                'frequencies': list(config['reporting_frequencies'])
            }
            
            # Categorize variables
            for var in config['variables']:
                var_name = var['variable_name']
                doc['summary']['unique_variables'].add(var_name)
                
                # Categorize
                if 'Energy' in var_name or 'Rate' in var_name:
                    output_categories['energy'].append(var_name)
                elif 'Temperature' in var_name or 'Comfort' in var_name:
                    output_categories['comfort'].append(var_name)
                elif 'HVAC' in var_name or 'Coil' in var_name or 'Fan' in var_name:
                    output_categories['hvac'].append(var_name)
                elif 'Surface' in var_name or 'Window' in var_name:
                    output_categories['envelope'].append(var_name)
                elif 'Site' in var_name or 'Environment' in var_name:
                    output_categories['environmental'].append(var_name)
                else:
                    output_categories['other'].append(var_name)
            
            # Track meters
            for meter in config['meters']:
                doc['summary']['unique_meters'].add(meter['meter_name'])
            
            # Track frequencies
            doc['summary']['reporting_frequencies'].update(config['reporting_frequencies'])
        
        # Convert sets to lists for JSON serialization
        doc['summary']['unique_variables'] = sorted(list(doc['summary']['unique_variables']))
        doc['summary']['unique_meters'] = sorted(list(doc['summary']['unique_meters']))
        doc['summary']['reporting_frequencies'] = sorted(list(doc['summary']['reporting_frequencies']))
        
        # Add categorized outputs
        doc['output_categories'] = {
            cat: sorted(list(set(vars))) for cat, vars in output_categories.items()
        }
        
        # Save documentation
        doc_path = self.project_path / 'metadata' / 'output_documentation.json'
        with open(doc_path, 'w') as f:
            json.dump(doc, f, indent=2)
    
    def get_output_configuration(self, building_id: str) -> Dict[str, Any]:
        """Get output configuration for a specific building"""
        return self.output_definitions.get(building_id, {})
    
    def compare_output_configurations(self, building_ids: List[str] = None) -> Dict[str, Any]:
        """Compare output configurations across buildings"""
        if building_ids is None:
            building_ids = list(self.output_definitions.keys())
        
        comparison = {
            'common_variables': [],
            'unique_variables': {},
            'frequency_differences': {},
            'consistency_score': 0.0
        }
        
        if not building_ids:
            return comparison
        
        # Get all variables for each building
        building_vars = {}
        for bid in building_ids:
            if bid in self.output_definitions:
                vars_set = set()
                for var in self.output_definitions[bid]['variables']:
                    vars_set.add((var['variable_name'], var['reporting_frequency']))
                building_vars[bid] = vars_set
        
        if building_vars:
            # Find common variables
            common = set.intersection(*building_vars.values())
            comparison['common_variables'] = sorted(list(common))
            
            # Find unique variables
            for bid, vars_set in building_vars.items():
                unique = vars_set - common
                if unique:
                    comparison['unique_variables'][bid] = sorted(list(unique))
            
            # Calculate consistency score
            total_vars = len(set.union(*building_vars.values()))
            if total_vars > 0:
                comparison['consistency_score'] = len(common) / total_vars * 100
        
        return comparison
    
    def suggest_output_optimization(self, target_size_mb: int = 100) -> Dict[str, Any]:
        """Suggest output optimizations to reduce file size"""
        suggestions = {
            'remove_surface_outputs': [],
            'reduce_frequency': [],
            'remove_redundant': [],
            'estimated_reduction': 0
        }
        
        # Analyze current output definitions
        for building_id, config in self.output_definitions.items():
            for var in config['variables']:
                var_name = var['variable_name']
                freq = var['reporting_frequency']
                
                # Suggest removing detailed surface outputs for large models
                if 'Surface' in var_name and var['key_value'] == '*':
                    suggestions['remove_surface_outputs'].append({
                        'building': building_id,
                        'variable': var_name,
                        'reason': 'High data volume for all surfaces'
                    })
                
                # Suggest reducing frequency for non-critical variables
                if freq == 'Timestep' and 'Temperature' not in var_name:
                    suggestions['reduce_frequency'].append({
                        'building': building_id,
                        'variable': var_name,
                        'current': freq,
                        'suggested': 'Hourly'
                    })
        
        return suggestions
    
    def generate_minimal_output_set(self) -> List[Dict[str, str]]:
        """Generate minimal output set for basic analysis"""
        return [
            {'key_value': '*', 'variable_name': 'Zone Mean Air Temperature', 'reporting_frequency': 'Hourly'},
            {'key_value': '*', 'variable_name': 'Zone Air System Sensible Cooling Energy', 'reporting_frequency': 'Daily'},
            {'key_value': '*', 'variable_name': 'Zone Air System Sensible Heating Energy', 'reporting_frequency': 'Daily'},
            {'key_value': '*', 'variable_name': 'Facility Total Electric Demand Power', 'reporting_frequency': 'Hourly'},
            {'key_value': 'Environment', 'variable_name': 'Site Outdoor Air Drybulb Temperature', 'reporting_frequency': 'Hourly'}
        ]
    
    def generate_comprehensive_output_set(self) -> List[Dict[str, str]]:
        """Generate comprehensive output set for detailed analysis"""
        # This would return the full set from your paste.txt
        # For brevity, showing structure
        outputs = []
        
        # Add all the outputs from paste.txt
        standard_outputs = [
            ('*', 'Zone Air System Sensible Heating Energy', 'Hourly'),
            ('*', 'Zone Air System Sensible Cooling Energy', 'Hourly'),
            ('*', 'Zone Mean Air Temperature', 'Hourly'),
            # ... add all others from paste.txt
        ]
        
        for key, var, freq in standard_outputs:
            outputs.append({
                'key_value': key,
                'variable_name': var,
                'reporting_frequency': freq
            })
        
        return outputs
    
    # Keep all existing methods from the original class
    def analyze_single_building(self, idf_path: Union[str, Path], 
                              sql_path: Union[str, Path],
                              categories: List[str] = None):
        """Analyze a single building"""
        self.analyze_project([(idf_path, sql_path)], categories)
    
    def show_data_summary(self):
        """Show enhanced summary including output information"""
        summary = self.data_manager.get_data_summary()
        
        print("\n" + "="*60)
        print("DATA SUMMARY")
        print("="*60)
        
        print(f"\nProject Path: {summary['base_path']}")
        
        print(f"\nBuildings analyzed: {len(summary['buildings'])}")
        for building in summary['buildings'][:5]:
            print(f"  - {building}")
        if len(summary['buildings']) > 5:
            print(f"  ... and {len(summary['buildings']) - 5} more")
        
        # Add output summary
        print(f"\nOutput configurations:")
        total_vars = sum(len(config['variables']) for config in self.output_definitions.values())
        total_meters = sum(len(config['meters']) for config in self.output_definitions.values())
        print(f"  Total output variables: {total_vars}")
        print(f"  Total meters: {total_meters}")
        print(f"  Buildings with outputs: {len(self.output_definitions)}")
        
        print(f"\nConsolidated category files:")
        for file_name, info in summary['categories'].items():
            print(f"  {file_name}: {info.get('rows', 'N/A')} rows, {info.get('buildings', 'N/A')} buildings")
        
        print(f"\nTime series data:")
        if 'hourly' in summary['timeseries']:
            print(f"  Hourly: {', '.join(summary['timeseries']['hourly'])}")
        if 'daily' in summary['timeseries']:
            print(f"  Daily: {', '.join(summary['timeseries']['daily'])}")
        if 'monthly' in summary['timeseries']:
            print(f"  Monthly: {', '.join(summary['timeseries']['monthly'])}")
        
        print(f"\nRelationships: {', '.join(summary['relationships'])}")
        
        # Check for output validation results
        validation_path = self.project_path / 'metadata' / 'output_validation.parquet'
        if validation_path.exists():
            validation_df = pd.read_parquet(validation_path)
            avg_coverage = validation_df['coverage'].mean()
            print(f"\nOutput validation:")
            print(f"  Average coverage: {avg_coverage:.1f}%")
            print(f"  Buildings validated: {len(validation_df)}")
    
    # Keep all other existing methods...
    def load_category_data(self, category_file: str, building_ids: List[str] = None) -> pd.DataFrame:
        """Load data from a specific category file"""
        data = self.data_manager.load_category_data(category_file)
        
        if building_ids and not data.empty:
            data = data[data['building_id'].isin(building_ids)]
        
        return data
    
    def load_timeseries_data(self, category: str, building_ids: List[str] = None,
                           year: int = None, frequency: str = 'hourly') -> pd.DataFrame:
        """Load time series data for analysis"""
        data = self.data_manager.load_timeseries_data(category, year, frequency)
        
        if building_ids and not data.empty:
            data = data[data['building_id'].isin(building_ids)]
        
        return data
    
    def get_parameter_matrix(self, building_ids: List[str] = None) -> pd.DataFrame:
        """Get parameter matrix for analysis"""
        matrix_path = self.project_path / 'analysis_ready' / 'parameter_matrix.parquet'
        
        if matrix_path.exists():
            matrix = pd.read_parquet(matrix_path)
            if building_ids:
                matrix = matrix[matrix['building_id'].isin(building_ids)]
            return matrix
        else:
            # Create if doesn't exist
            return create_parameter_matrix(self.data_manager, building_ids)
    
    def get_building_metrics(self, building_ids: List[str] = None) -> pd.DataFrame:
        """Get building-level summary metrics"""
        metrics_path = self.project_path / 'sql_results' / 'summary_metrics' / 'building_metrics.parquet'
        
        if metrics_path.exists():
            metrics = pd.read_parquet(metrics_path)
            if building_ids:
                metrics = metrics[metrics['building_id'].isin(building_ids)]
            return metrics
        
        return pd.DataFrame()
    
    def get_zone_metrics(self, building_ids: List[str] = None) -> pd.DataFrame:
        """Get zone-level summary metrics"""
        metrics_path = self.project_path / 'sql_results' / 'summary_metrics' / 'zone_metrics.parquet'
        
        if metrics_path.exists():
            metrics = pd.read_parquet(metrics_path)
            if building_ids:
                metrics = metrics[metrics['building_id'].isin(building_ids)]
            return metrics
        
        return pd.DataFrame()
    
    def close(self):
        """Close all database connections"""
        for sql_analyzer in self.sql_analyzers.values():
            sql_analyzer.close()


# ============================================================================
# ENHANCED QUICK ACCESS FUNCTIONS
# ============================================================================

def quick_analyze(idf_path: str, sql_path: str, output_dir: str = "energyplus_analysis"):
    """Quick analysis of a single building with output validation"""
    analyzer = EnergyPlusAnalyzer(output_dir)
    analyzer.analyze_single_building(idf_path, sql_path)
    return analyzer


def batch_analyze(file_pairs: List[Tuple[str, str]], output_dir: str = "energyplus_analysis",
                 validate_outputs: bool = True):
    """Batch analysis of multiple buildings with output validation"""
    analyzer = EnergyPlusAnalyzer(output_dir)
    analyzer.analyze_project(file_pairs, validate_outputs=validate_outputs)
    return analyzer


# ============================================================================
# OUTPUT-SPECIFIC ANALYSIS FUNCTIONS
# ============================================================================

def analyze_output_consistency(analyzer: EnergyPlusAnalyzer):
    """Analyze output consistency across buildings"""
    print("\nAnalyzing output consistency...")
    
    comparison = analyzer.compare_output_configurations()
    
    print(f"\nOutput Consistency Report:")
    print(f"  Consistency score: {comparison['consistency_score']:.1f}%")
    print(f"  Common variables: {len(comparison['common_variables'])}")
    
    if comparison['unique_variables']:
        print(f"\nBuildings with unique outputs:")
        for building_id, unique_vars in comparison['unique_variables'].items():
            print(f"  {building_id}: {len(unique_vars)} unique outputs")


def optimize_outputs_for_scale(analyzer: EnergyPlusAnalyzer, target_buildings: int):
    """Suggest output optimizations for large-scale analysis"""
    print(f"\nOptimizing outputs for {target_buildings} buildings...")
    
    if target_buildings > 100:
        print("\nRecommended optimizations for scale:")
        print("1. Remove surface-level outputs (use zone-level instead)")
        print("2. Use daily frequency for energy totals")
        print("3. Use hourly only for temperatures and critical variables")
        print("4. Remove detailed window/shading outputs")
        
        # Generate optimized set
        optimized = []
        for var in analyzer.generate_comprehensive_output_set():
            # Skip surface outputs for scale
            if 'Surface' not in var['variable_name'] or 'Temperature' in var['variable_name']:
                # Adjust frequency for non-critical variables
                if 'Energy' in var['variable_name'] and var['reporting_frequency'] == 'Hourly':
                    var['reporting_frequency'] = 'Daily'
                optimized.append(var)
        
        print(f"\nOptimized from {len(analyzer.generate_comprehensive_output_set())} to {len(optimized)} outputs")
        return optimized
    else:
        return analyzer.generate_comprehensive_output_set()


# ============================================================================
# ENHANCED EXAMPLE ANALYSIS FUNCTIONS
# ============================================================================

def validate_simulation_outputs(analyzer: EnergyPlusAnalyzer):
    """Validate that simulations produced expected outputs"""
    validation_path = analyzer.project_path / 'metadata' / 'output_validation.parquet'
    
    if not validation_path.exists():
        print("No output validation data available")
        return
    
    validation_df = pd.read_parquet(validation_path)
    
    print("\nOutput Validation Summary:")
    print("-" * 60)
    
    # Buildings with perfect coverage
    perfect = validation_df[validation_df['coverage'] == 100.0]
    print(f"Buildings with 100% output coverage: {len(perfect)}")
    
    # Buildings with issues
    issues = validation_df[validation_df['coverage'] < 100.0]
    if not issues.empty:
        print(f"\nBuildings with missing outputs:")
        for _, building in issues.iterrows():
            print(f"  {building['building_id']}: {building['coverage']:.1f}% coverage")
            print(f"    Missing: {building['total_requested'] - building['found']} outputs")
    
    # Check for systematic missing outputs
    missing_path = analyzer.project_path / 'metadata' / 'missing_outputs.parquet'
    if missing_path.exists():
        missing_df = pd.read_parquet(missing_path)
        
        # Group by variable to find commonly missing outputs
        missing_counts = missing_df.groupby('variable').size().sort_values(ascending=False)
        
        if not missing_counts.empty:
            print(f"\nMost commonly missing outputs:")
            for var, count in missing_counts.head(10).items():
                print(f"  {var}: missing in {count} buildings")


# ============================================================================
# MAIN USAGE EXAMPLE
# ============================================================================

def main():
    """Example usage of the enhanced EnergyPlus analyzer with output support"""
    
    # Example file paths - update these to your actual files
    test_cases = [
        (
            r"D:\Documents\E_Plus_2030_py\output\9c343c15-9f89-4533-8ba9-5eb7d8d917b8\output_IDFs\building_4136737.idf",
            r"D:\Documents\E_Plus_2030_py\output\9c343c15-9f89-4533-8ba9-5eb7d8d917b8\Sim_Results\2020\simulation_bldg1.sql"
        ),
        (
            r"D:\Documents\E_Plus_2030_py\output\9c343c15-9f89-4533-8ba9-5eb7d8d917b8\output_IDFs\building_4136738.idf",
            r"D:\Documents\E_Plus_2030_py\output\9c343c15-9f89-4533-8ba9-5eb7d8d917b8\Sim_Results\2020\simulation_bldg2.sql"
        )
    ]
    
    # Create analyzer and process buildings
    project_path = "energyplus_project_analysis_v3"
    analyzer = EnergyPlusAnalyzer(project_path)
    
    # Analyze all buildings with output validation
    analyzer.analyze_project(test_cases, validate_outputs=True)
    
    # Example: Analyze output consistency
    print("\n" + "="*60)
    print("OUTPUT ANALYSIS")
    print("="*60)
    
    analyze_output_consistency(analyzer)
    
    # Example: Validate simulation outputs
    validate_simulation_outputs(analyzer)
    
    # Example: Get output configuration for a building
    if analyzer.output_definitions:
        first_building = list(analyzer.output_definitions.keys())[0]
        config = analyzer.get_output_configuration(first_building)
        
        print(f"\nOutput configuration for {first_building}:")
        print(f"  Variables: {len(config['variables'])}")
        print(f"  Meters: {len(config['meters'])}")
        print(f"  Reporting frequencies: {config['reporting_frequencies']}")
    
    # Example: Load outputs data
    print("\n" + "="*60)
    print("LOADING OUTPUT DEFINITIONS")
    print("="*60)
    
    outputs_data = analyzer.load_category_data('outputs_variables')
    if not outputs_data.empty:
        print(f"\nOutput variables defined: {len(outputs_data)}")
        print("\nSample output definitions:")
        print(outputs_data[['building_id', 'key_value', 'variable_name', 'reporting_frequency']].head())
        
        # Analyze frequency distribution
        freq_dist = outputs_data['reporting_frequency'].value_counts()
        print("\nReporting frequency distribution:")
        for freq, count in freq_dist.items():
            print(f"  {freq}: {count} outputs")
    
    # Example: Optimize for scale
    print("\n" + "="*60)
    print("OUTPUT OPTIMIZATION")
    print("="*60)
    
    optimized_outputs = optimize_outputs_for_scale(analyzer, 1000)
    
    # Close connections
    analyzer.close()
    
    print(f"\n\nAll data saved to: {project_path}")
    print("\nNext steps:")
    print("1. Review output validation results to ensure data completeness")
    print("2. Use output configuration to optimize future simulations")
    print("3. Standardize outputs across buildings for consistent analysis")
    print("4. Generate minimal output sets for large-scale runs")


if __name__ == "__main__":
    main()