"""
Enhanced SQL Data Extractor with Comprehensive Coverage
Addresses common parsing issues including zone coverage, missing data, and index mapping
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import json
from datetime import datetime
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedSQLExtractor:
    """Enhanced SQL extractor with comprehensive coverage and validation"""
    
    def __init__(self, sql_path: Path, output_dir: Path, building_id: str, variant_id: str = 'base'):
        """Initialize enhanced extractor"""
        self.sql_path = Path(sql_path)
        self.output_dir = Path(output_dir)
        self.building_id = building_id
        self.variant_id = variant_id
        self.conn = sqlite3.connect(str(sql_path))
        
        # Initialize tracking
        self.zone_mapping = {}
        self.extraction_log = []
        self.missing_data = []
        
        # Create output directories
        self._create_output_dirs()
        
        # Build zone mapping first
        self._build_zone_mapping()
        
    def _create_output_dirs(self):
        """Create comprehensive output directory structure"""
        self.dirs = {
            'performance': self.output_dir / 'performance_summaries',
            'sizing': self.output_dir / 'sizing_results',
            'characteristics': self.output_dir / 'building_characteristics',
            'metadata': self.output_dir / 'metadata',
            'detailed': self.output_dir / 'detailed_reports',
            'equipment': self.output_dir / 'equipment_loads',
            'schedules': self.output_dir / 'schedules',
            'zones': self.output_dir / 'zone_data',
            'validation': self.output_dir / 'validation_reports'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _build_zone_mapping(self):
        """Build comprehensive zone mapping for cross-referencing"""
        logger.info("Building zone mapping...")
        
        # Get all zones with multiple identifiers
        query = """
        SELECT 
            ZoneIndex,
            ZoneName,
            FloorArea,
            Volume,
            Multiplier
        FROM Zones
        """
        
        try:
            zones_df = pd.read_sql_query(query, self.conn)
            
            # Create bidirectional mapping
            for _, zone in zones_df.iterrows():
                self.zone_mapping[zone['ZoneIndex']] = {
                    'name': zone['ZoneName'],
                    'area': zone['FloorArea'],
                    'volume': zone['Volume'],
                    'multiplier': zone['Multiplier']
                }
                self.zone_mapping[zone['ZoneName']] = zone['ZoneIndex']
            
            logger.info(f"Built zone mapping for {len(zones_df)} zones")
            
            # Save zone mapping for reference
            mapping_path = self.dirs['metadata'] / 'zone_mapping.json'
            with open(mapping_path, 'w') as f:
                json.dump(self.zone_mapping, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to build zone mapping: {e}")
            self.missing_data.append(('Zone Mapping', str(e)))
    
    def extract_all_enhanced(self):
        """Extract all data with enhanced coverage"""
        logger.info(f"Starting enhanced extraction for {self.building_id} (variant: {self.variant_id})")
        
        # Core extractions
        self._extract_zone_data_comprehensive()
        self._extract_all_tabular_reports()
        self._extract_all_nominal_equipment()
        self._extract_sizing_comprehensive()
        self._extract_schedules_comprehensive()
        self._extract_construction_comprehensive()
        self._extract_system_components()
        self._extract_surface_details()
        self._extract_meter_data()
        
        # Validation and reporting
        self._validate_extraction()
        self._create_extraction_report()
        
        logger.info("Enhanced extraction complete")
    
    def _extract_zone_data_comprehensive(self):
        """Extract comprehensive zone data with full coverage"""
        logger.info("Extracting comprehensive zone data...")
        
        # 1. Zone properties with all fields
        query = """
        SELECT 
            z.*,
            COUNT(DISTINCT s.SurfaceIndex) as surface_count
        FROM Zones z
        LEFT JOIN Surfaces s ON z.ZoneName = s.ZoneName
        GROUP BY z.ZoneIndex
        """
        
        try:
            zones_df = pd.read_sql_query(query, self.conn)
            zones_df['building_id'] = self.building_id
            zones_df['variant_id'] = self.variant_id
            
            output_path = self.dirs['zones'] / 'zone_properties_full.parquet'
            zones_df.to_parquet(output_path, index=False)
            self._log_extraction('Zone Properties Full', len(zones_df))
            
        except Exception as e:
            self._log_error('Zone Properties Full', e)
        
        # 2. Zone-specific loads with proper mapping
        load_tables = [
            'NominalLighting',
            'NominalElectricEquipment', 
            'NominalGasEquipment',
            'NominalPeople',
            'NominalInfiltration',
            'NominalVentilation'
        ]
        
        for table in load_tables:
            self._extract_zone_loads(table)
    
    def _extract_zone_loads(self, table_name: str):
        """Extract zone loads with proper zone mapping"""
        query = f"""
        SELECT 
            t.*,
            z.ZoneIndex,
            z.FloorArea,
            z.Volume
        FROM {table_name} t
        LEFT JOIN Zones z ON t.ZoneName = z.ZoneName
        """
        
        try:
            df = pd.read_sql_query(query, self.conn)
            
            if not df.empty:
                # Add normalized values
                if 'DesignLevel' in df.columns and 'FloorArea' in df.columns:
                    df['watts_per_m2'] = df['DesignLevel'] / df['FloorArea']
                
                df['building_id'] = self.building_id
                df['variant_id'] = self.variant_id
                
                output_file = f"zone_{table_name.lower()}.parquet"
                output_path = self.dirs['zones'] / output_file
                df.to_parquet(output_path, index=False)
                self._log_extraction(f'Zone {table_name}', len(df))
                
                # Check zone coverage
                zones_covered = df['ZoneName'].nunique()
                total_zones = len(self.zone_mapping) // 2  # Divided by 2 due to bidirectional mapping
                if zones_covered < total_zones:
                    self.missing_data.append((
                        f'{table_name} Zone Coverage',
                        f'Only {zones_covered}/{total_zones} zones have data'
                    ))
                    
        except Exception as e:
            self._log_error(f'Zone {table_name}', e)
    
    def _extract_all_tabular_reports(self):
        """Extract ALL tabular reports systematically"""
        logger.info("Extracting all tabular reports...")
        
        # Get all unique table names
        query = """
        SELECT DISTINCT s.Value as TableName
        FROM TabularData td
        JOIN Strings s ON td.TableNameIndex = s.StringIndex
        ORDER BY s.Value
        """
        
        try:
            tables_df = pd.read_sql_query(query, self.conn)
            
            for table_name in tables_df['TableName']:
                self._extract_tabular_report_enhanced(table_name)
                
        except Exception as e:
            self._log_error('Tabular Reports List', e)
    
    def _extract_tabular_report_enhanced(self, table_name: str):
        """Extract tabular report with enhanced structure"""
        query = f"""
        SELECT 
            s1.Value as ReportName,
            s2.Value as TableName,
            s3.Value as RowName,
            s4.Value as ColumnName,
            s5.Value as Units,
            td.Value,
            td.RowId,
            td.ColumnId
        FROM TabularData td
        LEFT JOIN Strings s1 ON td.ReportNameIndex = s1.StringIndex
        LEFT JOIN Strings s2 ON td.TableNameIndex = s2.StringIndex
        LEFT JOIN Strings s3 ON td.RowNameIndex = s3.StringIndex
        LEFT JOIN Strings s4 ON td.ColumnNameIndex = s4.StringIndex
        LEFT JOIN Strings s5 ON td.UnitsIndex = s5.StringIndex
        WHERE s2.Value = '{table_name}'
        """
        
        try:
            df = pd.read_sql_query(query, self.conn)
            
            if not df.empty:
                # Create both raw and pivoted versions
                # Raw version
                df['building_id'] = self.building_id
                df['variant_id'] = self.variant_id
                
                safe_table_name = table_name.replace(' ', '_').replace('/', '_')
                raw_path = self.dirs['detailed'] / f'tabular_{safe_table_name}_raw.parquet'
                df.to_parquet(raw_path, index=False)
                
                # Pivoted version
                try:
                    df_pivot = df.pivot_table(
                        index=['ReportName', 'TableName', 'RowName'],
                        columns='ColumnName',
                        values='Value',
                        aggfunc='first'
                    ).reset_index()
                    
                    df_pivot['building_id'] = self.building_id
                    df_pivot['variant_id'] = self.variant_id
                    
                    pivot_path = self.dirs['detailed'] / f'tabular_{safe_table_name}_pivot.parquet'
                    df_pivot.to_parquet(pivot_path, index=False)
                    
                except Exception as pivot_error:
                    logger.warning(f"Could not pivot {table_name}: {pivot_error}")
                
                self._log_extraction(f'Tabular {table_name}', len(df))
                
        except Exception as e:
            self._log_error(f'Tabular {table_name}', e)
    
    def _extract_all_nominal_equipment(self):
        """Extract all nominal equipment tables"""
        logger.info("Extracting all nominal equipment...")
        
        # Get all tables that start with 'Nominal'
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE 'Nominal%'
        ORDER BY name
        """
        
        try:
            tables_df = pd.read_sql_query(query, self.conn)
            
            for table_name in tables_df['name']:
                self._extract_nominal_table(table_name)
                
        except Exception as e:
            self._log_error('Nominal Tables List', e)
    
    def _extract_nominal_table(self, table_name: str):
        """Extract a nominal equipment table"""
        query = f"SELECT * FROM {table_name}"
        
        try:
            df = pd.read_sql_query(query, self.conn)
            
            if not df.empty:
                df['building_id'] = self.building_id
                df['variant_id'] = self.variant_id
                
                output_file = f"{table_name.lower()}.parquet"
                output_path = self.dirs['equipment'] / output_file
                df.to_parquet(output_path, index=False)
                self._log_extraction(table_name, len(df))
                
        except Exception as e:
            self._log_error(table_name, e)
    
    def _extract_sizing_comprehensive(self):
        """Extract all sizing-related data"""
        logger.info("Extracting comprehensive sizing data...")
        
        sizing_tables = [
            'ZoneSizes',
            'SystemSizes',
            'ComponentSizes',
            'SubcomponentSizes'  # May not exist in all files
        ]
        
        for table in sizing_tables:
            query = f"SELECT * FROM {table}"
            
            try:
                df = pd.read_sql_query(query, self.conn)
                
                if not df.empty:
                    # Add zone mapping for ZoneSizes
                    if table == 'ZoneSizes' and 'ZoneName' in df.columns:
                        df = df.merge(
                            pd.DataFrame.from_dict(
                                {k: v for k, v in self.zone_mapping.items() 
                                 if isinstance(v, dict)},
                                orient='index'
                            ).reset_index().rename(columns={'index': 'ZoneIndex'}),
                            left_on='ZoneName',
                            right_on='name',
                            how='left'
                        )
                    
                    df['building_id'] = self.building_id
                    df['variant_id'] = self.variant_id
                    
                    output_file = f"{table.lower()}.parquet"
                    output_path = self.dirs['sizing'] / output_file
                    df.to_parquet(output_path, index=False)
                    self._log_extraction(table, len(df))
                    
            except Exception as e:
                if "no such table" not in str(e).lower():
                    self._log_error(table, e)
    
    def _extract_schedules_comprehensive(self):
        """Extract all schedule data comprehensively"""
        logger.info("Extracting comprehensive schedule data...")
        
        # 1. Schedule definitions
        query = """
        SELECT 
            s.*,
            st.Value as ScheduleType
        FROM Schedules s
        LEFT JOIN Strings st ON s.ScheduleTypeIndex = st.StringIndex
        """
        
        try:
            schedules_df = pd.read_sql_query(query, self.conn)
            
            if not schedules_df.empty:
                schedules_df['building_id'] = self.building_id
                schedules_df['variant_id'] = self.variant_id
                
                output_path = self.dirs['schedules'] / 'schedule_definitions.parquet'
                schedules_df.to_parquet(output_path, index=False)
                self._log_extraction('Schedule Definitions', len(schedules_df))
                
                # 2. Schedule data
                self._extract_schedule_data()
                
        except Exception as e:
            self._log_error('Schedule Definitions', e)
    
    def _extract_schedule_data(self):
        """Extract schedule hourly/sub-hourly data"""
        query = """
        SELECT 
            sd.*,
            s.ScheduleName,
            s.ScheduleType
        FROM ScheduleData sd
        JOIN Schedules s ON sd.ScheduleIndex = s.ScheduleIndex
        """
        
        try:
            df = pd.read_sql_query(query, self.conn)
            
            if not df.empty:
                df['building_id'] = self.building_id
                df['variant_id'] = self.variant_id
                
                # Save by schedule type for easier access
                for sched_type in df['ScheduleType'].unique():
                    type_df = df[df['ScheduleType'] == sched_type]
                    
                    safe_type = str(sched_type).replace(' ', '_').replace('/', '_')
                    output_path = self.dirs['schedules'] / f'schedule_data_{safe_type}.parquet'
                    type_df.to_parquet(output_path, index=False)
                
                self._log_extraction('Schedule Data', len(df))
                
        except Exception as e:
            self._log_error('Schedule Data', e)
    
    def _extract_construction_comprehensive(self):
        """Extract all construction and material data"""
        logger.info("Extracting construction data...")
        
        # 1. Materials with all properties
        query = """
        SELECT * FROM Materials
        """
        
        try:
            materials_df = pd.read_sql_query(query, self.conn)
            
            if not materials_df.empty:
                materials_df['building_id'] = self.building_id
                materials_df['variant_id'] = self.variant_id
                
                output_path = self.dirs['characteristics'] / 'materials_full.parquet'
                materials_df.to_parquet(output_path, index=False)
                self._log_extraction('Materials', len(materials_df))
                
        except Exception as e:
            self._log_error('Materials', e)
        
        # 2. Construction assemblies with layer details
        query = """
        SELECT 
            c.*,
            cl.LayerIndex,
            cl.MaterialIndex,
            m.Name as MaterialName,
            m.Thickness,
            m.Conductivity,
            m.Density,
            m.SpecHeat,
            m.Roughness,
            m.ThermalResistance
        FROM Constructions c
        LEFT JOIN ConstructionLayers cl ON c.ConstructionIndex = cl.ConstructionIndex
        LEFT JOIN Materials m ON cl.MaterialIndex = m.MaterialIndex
        ORDER BY c.ConstructionIndex, cl.LayerIndex
        """
        
        try:
            constructions_df = pd.read_sql_query(query, self.conn)
            
            if not constructions_df.empty:
                constructions_df['building_id'] = self.building_id
                constructions_df['variant_id'] = self.variant_id
                
                output_path = self.dirs['characteristics'] / 'construction_assemblies.parquet'
                constructions_df.to_parquet(output_path, index=False)
                self._log_extraction('Construction Assemblies', len(constructions_df))
                
        except Exception as e:
            self._log_error('Construction Assemblies', e)
    
    def _extract_system_components(self):
        """Extract HVAC system components"""
        logger.info("Extracting system components...")
        
        # Tables that might contain system component data
        component_tables = [
            'Fans',
            'Pumps',
            'Coils',
            'Chillers',
            'Boilers',
            'Towers',
            'HeatExchangers'
        ]
        
        for table in component_tables:
            query = f"SELECT * FROM {table}"
            
            try:
                df = pd.read_sql_query(query, self.conn)
                
                if not df.empty:
                    df['building_id'] = self.building_id
                    df['variant_id'] = self.variant_id
                    
                    output_path = self.dirs['equipment'] / f'{table.lower()}.parquet'
                    df.to_parquet(output_path, index=False)
                    self._log_extraction(table, len(df))
                    
            except Exception as e:
                if "no such table" not in str(e).lower():
                    self._log_error(table, e)
    
    def _extract_surface_details(self):
        """Extract surface geometry and properties"""
        logger.info("Extracting surface details...")
        
        query = """
        SELECT 
            s.*,
            c.Name as ConstructionName,
            z.ZoneIndex
        FROM Surfaces s
        LEFT JOIN Constructions c ON s.ConstructionIndex = c.ConstructionIndex
        LEFT JOIN Zones z ON s.ZoneName = z.ZoneName
        """
        
        try:
            surfaces_df = pd.read_sql_query(query, self.conn)
            
            if not surfaces_df.empty:
                surfaces_df['building_id'] = self.building_id
                surfaces_df['variant_id'] = self.variant_id
                
                output_path = self.dirs['characteristics'] / 'surfaces_detailed.parquet'
                surfaces_df.to_parquet(output_path, index=False)
                self._log_extraction('Surfaces', len(surfaces_df))
                
        except Exception as e:
            self._log_error('Surfaces', e)
    
    def _extract_meter_data(self):
        """Extract meter definitions and data"""
        logger.info("Extracting meter data...")
        
        # Meter definitions
        query = """
        SELECT * FROM Meters
        """
        
        try:
            meters_df = pd.read_sql_query(query, self.conn)
            
            if not meters_df.empty:
                meters_df['building_id'] = self.building_id
                meters_df['variant_id'] = self.variant_id
                
                output_path = self.dirs['metadata'] / 'meter_definitions.parquet'
                meters_df.to_parquet(output_path, index=False)
                self._log_extraction('Meter Definitions', len(meters_df))
                
        except Exception as e:
            self._log_error('Meter Definitions', e)
    
    def _validate_extraction(self):
        """Validate extraction completeness"""
        logger.info("Validating extraction...")
        
        validation_results = {
            'extraction_timestamp': datetime.now().isoformat(),
            'building_id': self.building_id,
            'variant_id': self.variant_id,
            'total_zones': len(self.zone_mapping) // 2,
            'extracted_items': self.extraction_log,
            'missing_data': self.missing_data,
            'errors': [item for item in self.extraction_log if 'ERROR' in item]
        }
        
        # Check critical data presence
        critical_checks = {
            'zones': self.dirs['zones'] / 'zone_properties_full.parquet',
            'sizing': self.dirs['sizing'] / 'zonesizes.parquet',
            'schedules': self.dirs['schedules'] / 'schedule_definitions.parquet',
            'constructions': self.dirs['characteristics'] / 'construction_assemblies.parquet'
        }
        
        validation_results['critical_data_status'] = {}
        for check_name, check_path in critical_checks.items():
            validation_results['critical_data_status'][check_name] = check_path.exists()
        
        # Save validation results
        validation_path = self.dirs['validation'] / 'extraction_validation.json'
        with open(validation_path, 'w') as f:
            json.dump(validation_results, f, indent=2)
        
        logger.info(f"Validation complete. Results saved to {validation_path}")
    
    def _create_extraction_report(self):
        """Create detailed extraction report"""
        report = {
            'extraction_summary': {
                'building_id': self.building_id,
                'variant_id': self.variant_id,
                'extraction_date': datetime.now().isoformat(),
                'sql_file': str(self.sql_path),
                'output_directory': str(self.output_dir)
            },
            'extraction_log': self.extraction_log,
            'missing_data': self.missing_data,
            'zone_coverage': self._analyze_zone_coverage(),
            'file_inventory': self._create_file_inventory()
        }
        
        report_path = self.dirs['validation'] / 'extraction_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print(f"\n=== EXTRACTION SUMMARY ===")
        print(f"Building ID: {self.building_id}")
        print(f"Variant: {self.variant_id}")
        print(f"Total extractions: {len([e for e in self.extraction_log if 'ERROR' not in e])}")
        print(f"Errors: {len([e for e in self.extraction_log if 'ERROR' in e])}")
        print(f"Missing data items: {len(self.missing_data)}")
        
        if self.missing_data:
            print("\nMissing Data:")
            for item, details in self.missing_data[:5]:
                print(f"  - {item}: {details}")
            if len(self.missing_data) > 5:
                print(f"  ... and {len(self.missing_data) - 5} more")
    
    def _analyze_zone_coverage(self):
        """Analyze zone coverage across extracted data"""
        coverage = {}
        total_zones = len(self.zone_mapping) // 2
        
        # Check zone coverage in various outputs
        zone_files = [
            (self.dirs['zones'] / 'zone_nominallighting.parquet', 'Lighting'),
            (self.dirs['zones'] / 'zone_nominalelectricequipment.parquet', 'Electric Equipment'),
            (self.dirs['zones'] / 'zone_nominalpeople.parquet', 'People'),
            (self.dirs['sizing'] / 'zonesizes.parquet', 'Zone Sizing')
        ]
        
        for file_path, category in zone_files:
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    zones_found = df['ZoneName'].nunique() if 'ZoneName' in df.columns else 0
                    coverage[category] = {
                        'zones_found': zones_found,
                        'total_zones': total_zones,
                        'coverage_pct': (zones_found / total_zones * 100) if total_zones > 0 else 0
                    }
                except:
                    coverage[category] = {'status': 'error reading file'}
            else:
                coverage[category] = {'status': 'file not found'}
        
        return coverage
    
    def _create_file_inventory(self):
        """Create inventory of all generated files"""
        inventory = {}
        
        for category, dir_path in self.dirs.items():
            files = list(dir_path.glob('*.parquet'))
            inventory[category] = [f.name for f in files]
        
        return inventory
    
    def _log_extraction(self, item: str, count: int):
        """Log successful extraction"""
        self.extraction_log.append(f"{item}: {count} records")
        logger.info(f"Extracted {item}: {count} records")
    
    def _log_error(self, item: str, error: Exception):
        """Log extraction error"""
        self.extraction_log.append(f"ERROR - {item}: {str(error)}")
        logger.error(f"Failed to extract {item}: {error}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def extract_enhanced_sql_data(sql_path: Path, output_dir: Path, 
                             building_id: str, variant_id: str = 'base'):
    """
    Extract SQL data with enhanced coverage
    
    Args:
        sql_path: Path to SQL file
        output_dir: Output directory
        building_id: Building identifier  
        variant_id: Variant identifier
    """
    extractor = EnhancedSQLExtractor(sql_path, output_dir, building_id, variant_id)
    try:
        extractor.extract_all_enhanced()
    finally:
        extractor.close()


if __name__ == "__main__":
    # Example usage
    sql_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/5affdc56-ed12-4d09-87ae-a23358a32eef/Modified_Sim_Results/2020/simulation_bldg0_4136733.sql")
    output_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/5affdc56-ed12-4d09-87ae-a23358a32eef/enhanced_parsed_data")
    
    extract_enhanced_sql_data(sql_path, output_dir, "4136733", "base")