"""
IDF Analyzer Main Module
Coordinates IDF parsing workflow
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

from .idf_parser import EnhancedIDFParser, BuildingData
from .fix_directories import fix_project_directories
from .idf_data_manager import IDFDataManager, create_idf_parameter_matrix

# Keep CATEGORY_MAPPINGS as is but remove SQL-related entries


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



class IDFAnalyzer:
    """IDF-only analyzer"""
    
    def __init__(self, project_path: Union[str, Path]):
        """Initialize IDF analyzer"""
        self.project_path = Path(project_path)
        
        # Ensure directories exist
        print(f"Ensuring directory structure for: {self.project_path}")
        fix_project_directories(str(self.project_path))
        
        self.data_manager = IDFDataManager(self.project_path)
        self.idf_parser = EnhancedIDFParser(CATEGORY_MAPPINGS, self.data_manager)
        
        self.category_mappings = CATEGORY_MAPPINGS
        self.output_definitions = {}
        
        print(f"\nInitialized IDF Analyzer v3.1")
        print(f"Project path: {self.project_path}")
    
    def analyze_idf_files(self, idf_files: List[str],
                         categories: List[str] = None,
                         building_id_map: Optional[Dict[str, str]] = None):
        """Analyze multiple IDF files"""
        
        if categories is None:
            categories = list(self.category_mappings.keys())
        
        print(f"\nAnalyzing {len(idf_files)} IDF files")
        print(f"Categories: {', '.join(categories)}")
        
        building_registry = []
        
        for idx, idf_path in enumerate(idf_files):
            print(f"\n{'='*60}")
            print(f"Processing IDF {idx+1}/{len(idf_files)}")
            print(f"IDF: {Path(idf_path).name}")
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
                
                # Register building
                registry_entry = {
                    'building_id': building_data.building_id,
                    'variant_id': building_data.metadata.get('variant_id', 'base'),
                    'idf_path': str(idf_path),
                    'zones': len(building_data.zones),
                    'surfaces': len(building_data.objects.get('BUILDINGSURFACE:DETAILED', [])),
                    'windows': len(building_data.objects.get('FENESTRATIONSURFACE:DETAILED', [])),
                    'output_variables': len(output_config.get('variables', [])),
                    'output_meters': len(output_config.get('meters', [])),
                    'status': 'completed',
                    'last_modified': datetime.now()
                }
                
                building_registry.append(registry_entry)
                
                print(f"\n✓ Building {building_data.building_id} completed")
                
            except Exception as e:
                print(f"\n[ERROR] Failed to process IDF: {e}")
                import traceback
                traceback.print_exc()
                
                building_registry.append({
                    'building_id': Path(idf_path).stem,
                    'idf_path': str(idf_path),
                    'error': str(e),
                    'status': 'failed',
                    'last_modified': datetime.now()
                })
        
        # Save metadata
        print("\n" + "="*60)
        print("SAVING PROJECT METADATA")
        print("="*60)
        
        registry_df = pd.DataFrame(building_registry)
        self.data_manager.update_building_registry(registry_df)
        
        # Flush buffered data
        print("\nFlushing buffered data...")
        self.data_manager.flush_category_buffers()
        
        # Update schemas
        print("Updating category schemas...")
        self.data_manager.update_category_schemas()
        
        # Update manifest
        print("Updating project manifest...")
        self.data_manager.update_project_manifest(
            total_buildings=len(building_registry),
            categories=categories
        )
        
        print(f"\n✓ IDF analysis complete!")
        print(f"Data stored in: {self.project_path}")
        
        self.show_data_summary()
    
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
        
        # Extract table definitions
        for obj in building_data.objects.get('OUTPUT:TABLE:SUMMARYREPORTS', []):
            for param in obj.parameters:
                if param.value:
                    output_config['tables'].append({
                        'report_name': param.value,
                        'type': 'summary'
                    })
        
        return output_config
    
    def show_data_summary(self):
        """Show summary of IDF data"""
        summary = self.data_manager.get_data_summary()
        
        print("\n" + "="*60)
        print("IDF DATA SUMMARY")
        print("="*60)
        
        print(f"\nProject Path: {summary['base_path']}")
        
        print(f"\nBuildings analyzed: {len(summary['buildings'])}")
        for building in summary['buildings'][:5]:
            print(f"  - {building}")
        if len(summary['buildings']) > 5:
            print(f"  ... and {len(summary['buildings']) - 5} more")
        
        print(f"\nOutput configurations:")
        total_vars = sum(len(config['variables']) for config in self.output_definitions.values())
        total_meters = sum(len(config['meters']) for config in self.output_definitions.values())
        print(f"  Total output variables: {total_vars}")
        print(f"  Total meters: {total_meters}")
        print(f"  Buildings with outputs: {len(self.output_definitions)}")
        
        print(f"\nConsolidated category files:")
        for file_name, info in summary['categories'].items():
            print(f"  {file_name}: {info.get('rows', 'N/A')} rows, {info.get('buildings', 'N/A')} buildings")
        
        print(f"\nRelationships: {', '.join(summary['relationships'])}")
    
    def load_category_data(self, category_file: str, building_ids: List[str] = None) -> pd.DataFrame:
        """Load data from a specific category file"""
        data = self.data_manager.load_category_data(category_file)
        
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
            return create_idf_parameter_matrix(self.data_manager, building_ids)
    
    def get_output_configuration(self, building_id: str) -> Dict[str, Any]:
        """Get output configuration for a specific building"""
        return self.output_definitions.get(building_id, {})
    
    def generate_minimal_output_set(self) -> List[Dict[str, str]]:
        """Generate minimal output set for basic analysis"""
        return [
            {'key_value': '*', 'variable_name': 'Zone Mean Air Temperature', 'reporting_frequency': 'Hourly'},
            {'key_value': '*', 'variable_name': 'Zone Air System Sensible Cooling Energy', 'reporting_frequency': 'Daily'},
            {'key_value': '*', 'variable_name': 'Zone Air System Sensible Heating Energy', 'reporting_frequency': 'Daily'},
            {'key_value': '*', 'variable_name': 'Facility Total Electric Demand Power', 'reporting_frequency': 'Hourly'},
            {'key_value': 'Environment', 'variable_name': 'Site Outdoor Air Drybulb Temperature', 'reporting_frequency': 'Hourly'}
        ]