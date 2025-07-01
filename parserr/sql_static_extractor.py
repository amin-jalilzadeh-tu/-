"""
Enhanced SQL Static Data Extractor
Extracts all non-timeseries data from EnergyPlus SQL files
Complements existing timeseries extraction
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLStaticExtractor:
    """Extract static/summary data from EnergyPlus SQL files"""
    
    def __init__(self, sql_path: Path, output_dir: Path, building_id: str, variant_id: str = 'base'):
        """
        Initialize static data extractor
        
        Args:
            sql_path: Path to SQL file
            output_dir: Base directory for output
            building_id: Building identifier
            variant_id: Variant identifier (base or variant number)
        """
        self.sql_path = Path(sql_path)
        self.output_dir = Path(output_dir)
        self.building_id = building_id
        self.variant_id = variant_id
        self.conn = sqlite3.connect(str(sql_path))
        
        # Create output directories
        self._create_output_dirs()
        
    def _create_output_dirs(self):
        """Create output directory structure"""
        self.dirs = {
            'performance': self.output_dir / 'performance_summaries',
            'sizing': self.output_dir / 'sizing_results',
            'characteristics': self.output_dir / 'building_characteristics',
            'metadata': self.output_dir / 'metadata',
            'detailed': self.output_dir / 'detailed_reports'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def extract_all(self):
        """Extract all static data"""
        logger.info(f"Starting static data extraction for {self.building_id} (variant: {self.variant_id})")
        
        # Extract each category
        self._extract_performance_summaries()
        self._extract_sizing_data()
        self._extract_building_characteristics()
        self._extract_metadata()
        self._extract_equipment_loads()
        
        logger.info("Static data extraction complete")
        
    def _extract_performance_summaries(self):
        """Extract performance summaries from TabularData"""
        logger.info("Extracting performance summaries...")
        
        # 1. Energy End Uses
        end_uses_df = self._extract_tabular_report('End Uses')
        if not end_uses_df.empty:
            end_uses_df['building_id'] = self.building_id
            end_uses_df['variant_id'] = self.variant_id
            output_path = self.dirs['performance'] / 'energy_end_uses.parquet'
            self._save_or_append(end_uses_df, output_path)
            logger.info(f"Saved {len(end_uses_df)} end use records")
        
        # 2. Site and Source Energy
        site_source_df = self._extract_tabular_report('Site and Source Energy')
        if not site_source_df.empty:
            site_source_df['building_id'] = self.building_id
            site_source_df['variant_id'] = self.variant_id
            output_path = self.dirs['performance'] / 'site_source_summary.parquet'
            self._save_or_append(site_source_df, output_path)
            logger.info(f"Saved {len(site_source_df)} site/source energy records")
        
        # 3. Comfort Metrics
        comfort_df = self._extract_tabular_report('Comfort and Setpoint Not Met Summary')
        if not comfort_df.empty:
            comfort_df['building_id'] = self.building_id
            comfort_df['variant_id'] = self.variant_id
            output_path = self.dirs['performance'] / 'comfort_metrics.parquet'
            self._save_or_append(comfort_df, output_path)
            logger.info(f"Saved {len(comfort_df)} comfort metric records")
        
        # 4. Energy Intensity
        intensity_df = self._extract_tabular_report('Utility Use Per Conditioned Floor Area')
        if not intensity_df.empty:
            intensity_df['building_id'] = self.building_id
            intensity_df['variant_id'] = self.variant_id
            output_path = self.dirs['performance'] / 'energy_intensity.parquet'
            self._save_or_append(intensity_df, output_path)
            logger.info(f"Saved {len(intensity_df)} energy intensity records")
            
        # 5. Peak Demands (from multiple reports)
        peak_df = self._extract_peak_demands()
        if not peak_df.empty:
            peak_df['building_id'] = self.building_id
            peak_df['variant_id'] = self.variant_id
            output_path = self.dirs['performance'] / 'peak_demands.parquet'
            self._save_or_append(peak_df, output_path)
            logger.info(f"Saved {len(peak_df)} peak demand records")
    
    def _extract_tabular_report(self, table_name: str) -> pd.DataFrame:
        """Extract a specific report from TabularData"""
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
                # Pivot to more usable format
                df_pivot = df.pivot_table(
                    index=['ReportName', 'TableName', 'RowName'],
                    columns='ColumnName',
                    values='Value',
                    aggfunc='first'
                ).reset_index()
                return df_pivot
            return df
        except Exception as e:
            logger.warning(f"Could not extract {table_name}: {e}")
            return pd.DataFrame()
    
    def _extract_peak_demands(self) -> pd.DataFrame:
        """Extract peak demand data from various sources"""
        # Try to get from DemandEndUseComponentsSummary
        query = """
        SELECT 
            s2.Value as TableName,
            s3.Value as EndUse,
            s4.Value as Metric,
            s5.Value as Units,
            td.Value
        FROM TabularData td
        LEFT JOIN Strings s1 ON td.ReportNameIndex = s1.StringIndex
        LEFT JOIN Strings s2 ON td.TableNameIndex = s2.StringIndex
        LEFT JOIN Strings s3 ON td.RowNameIndex = s3.StringIndex
        LEFT JOIN Strings s4 ON td.ColumnNameIndex = s4.StringIndex
        LEFT JOIN Strings s5 ON td.UnitsIndex = s5.StringIndex
        WHERE s1.Value = 'DemandEndUseComponentsSummary'
        AND s4.Value LIKE '%Peak%'
        """
        
        try:
            df = pd.read_sql_query(query, self.conn)
            return df
        except:
            return pd.DataFrame()
    
    def _extract_sizing_data(self):
        """Extract sizing data from various tables"""
        logger.info("Extracting sizing data...")
        
        # 1. Zone Sizes
        query = """
        SELECT * FROM ZoneSizes
        """
        try:
            zone_sizes = pd.read_sql_query(query, self.conn)
            if not zone_sizes.empty:
                zone_sizes['building_id'] = self.building_id
                zone_sizes['variant_id'] = self.variant_id
                output_path = self.dirs['sizing'] / 'zone_sizing.parquet'
                self._save_or_append(zone_sizes, output_path)
                logger.info(f"Saved {len(zone_sizes)} zone sizing records")
        except Exception as e:
            logger.warning(f"Could not extract ZoneSizes: {e}")
        
        # 2. System Sizes
        query = """
        SELECT * FROM SystemSizes
        """
        try:
            system_sizes = pd.read_sql_query(query, self.conn)
            if not system_sizes.empty:
                system_sizes['building_id'] = self.building_id
                system_sizes['variant_id'] = self.variant_id
                output_path = self.dirs['sizing'] / 'system_sizing.parquet'
                self._save_or_append(system_sizes, output_path)
                logger.info(f"Saved {len(system_sizes)} system sizing records")
        except Exception as e:
            logger.warning(f"Could not extract SystemSizes: {e}")
        
        # 3. Component Sizes
        query = """
        SELECT * FROM ComponentSizes
        """
        try:
            comp_sizes = pd.read_sql_query(query, self.conn)
            if not comp_sizes.empty:
                comp_sizes['building_id'] = self.building_id
                comp_sizes['variant_id'] = self.variant_id
                output_path = self.dirs['sizing'] / 'component_sizing.parquet'
                self._save_or_append(comp_sizes, output_path)
                logger.info(f"Saved {len(comp_sizes)} component sizing records")
        except Exception as e:
            logger.warning(f"Could not extract ComponentSizes: {e}")
    
    def _extract_building_characteristics(self):
        """Extract building characteristics"""
        logger.info("Extracting building characteristics...")
        
        # 1. Envelope Summary from TabularData
        envelope_df = self._extract_tabular_report('Envelope Summary')
        if not envelope_df.empty:
            envelope_df['building_id'] = self.building_id
            envelope_df['variant_id'] = self.variant_id
            output_path = self.dirs['characteristics'] / 'envelope_summary.parquet'
            self._save_or_append(envelope_df, output_path)
            logger.info(f"Saved {len(envelope_df)} envelope summary records")
        
        # 2. Construction Layers
        query = """
        SELECT 
            cl.ConstructionIndex,
            c.Name as ConstructionName,
            cl.LayerIndex,
            m.Name as MaterialName,
            m.Thickness,
            m.Conductivity,
            m.Density,
            m.SpecHeat
        FROM ConstructionLayers cl
        JOIN Constructions c ON cl.ConstructionIndex = c.ConstructionIndex
        JOIN Materials m ON cl.MaterialIndex = m.MaterialIndex
        ORDER BY cl.ConstructionIndex, cl.LayerIndex
        """
        try:
            layers_df = pd.read_sql_query(query, self.conn)
            if not layers_df.empty:
                layers_df['building_id'] = self.building_id
                layers_df['variant_id'] = self.variant_id
                output_path = self.dirs['characteristics'] / 'construction_details.parquet'
                self._save_or_append(layers_df, output_path)
                logger.info(f"Saved {len(layers_df)} construction layer records")
        except Exception as e:
            logger.warning(f"Could not extract construction layers: {e}")
        
        # 3. Zone Properties (enhanced)
        query = """
        SELECT 
            ZoneIndex,
            ZoneName,
            FloorArea,
            Volume,
            CeilingHeight,
            Multiplier,
            ExtGrossWallArea,
            ExtWindowArea,
            ExtNetWallArea
        FROM Zones
        """
        try:
            zones_df = pd.read_sql_query(query, self.conn)
            if not zones_df.empty:
                zones_df['building_id'] = self.building_id
                zones_df['variant_id'] = self.variant_id
                # Calculate window-wall ratio
                zones_df['window_wall_ratio'] = zones_df['ExtWindowArea'] / zones_df['ExtGrossWallArea']
                zones_df['window_wall_ratio'] = zones_df['window_wall_ratio'].fillna(0)
                output_path = self.dirs['characteristics'] / 'zone_properties.parquet'
                self._save_or_append(zones_df, output_path)
                logger.info(f"Saved {len(zones_df)} zone property records")
        except Exception as e:
            logger.warning(f"Could not extract zone properties: {e}")
    
    def _extract_metadata(self):
        """Extract simulation metadata"""
        logger.info("Extracting metadata...")
        
        # 1. Simulation Info
        query = """
        SELECT * FROM Simulations
        """
        try:
            sim_df = pd.read_sql_query(query, self.conn)
            if not sim_df.empty:
                sim_df['building_id'] = self.building_id
                sim_df['variant_id'] = self.variant_id
                output_path = self.dirs['metadata'] / 'simulation_info.parquet'
                self._save_or_append(sim_df, output_path)
                logger.info(f"Saved simulation info")
        except Exception as e:
            logger.warning(f"Could not extract simulation info: {e}")
        
        # 2. Environment Periods
        query = """
        SELECT * FROM EnvironmentPeriods
        """
        try:
            env_df = pd.read_sql_query(query, self.conn)
            if not env_df.empty:
                env_df['building_id'] = self.building_id
                env_df['variant_id'] = self.variant_id
                output_path = self.dirs['metadata'] / 'environment_periods.parquet'
                self._save_or_append(env_df, output_path)
                logger.info(f"Saved environment periods")
        except Exception as e:
            logger.warning(f"Could not extract environment periods: {e}")
        
        # 3. Errors (already extracted in other workflow but including for completeness)
        query = """
        SELECT * FROM Errors
        """
        try:
            errors_df = pd.read_sql_query(query, self.conn)
            if not errors_df.empty:
                errors_df['building_id'] = self.building_id
                errors_df['variant_id'] = self.variant_id
                output_path = self.dirs['metadata'] / 'simulation_errors.parquet'
                self._save_or_append(errors_df, output_path)
                logger.info(f"Saved {len(errors_df)} error records")
        except Exception as e:
            logger.warning(f"Could not extract errors: {e}")
    
    def _extract_equipment_loads(self):
        """Extract nominal equipment and loads"""
        logger.info("Extracting equipment loads...")
        
        # Equipment tables to extract
        equipment_tables = {
            'NominalElectricEquipment': 'equipment_electric_nominal.parquet',
            'NominalGasEquipment': 'equipment_gas_nominal.parquet',
            'NominalSteamEquipment': 'equipment_steam_nominal.parquet',
            'NominalHotWaterEquipment': 'equipment_hotwater_nominal.parquet',
            'NominalOtherEquipment': 'equipment_other_nominal.parquet',
            'NominalBaseboardHeaters': 'equipment_baseboard_nominal.parquet',
            'NominalInfiltration': 'infiltration_nominal.parquet',
            'NominalVentilation': 'ventilation_nominal.parquet'
        }
        
        for table_name, output_file in equipment_tables.items():
            query = f"SELECT * FROM {table_name}"
            try:
                df = pd.read_sql_query(query, self.conn)
                if not df.empty:
                    df['building_id'] = self.building_id
                    df['variant_id'] = self.variant_id
                    output_path = self.dirs['characteristics'] / output_file
                    self._save_or_append(df, output_path)
                    logger.info(f"Saved {len(df)} {table_name} records")
            except Exception as e:
                logger.debug(f"Could not extract {table_name}: {e}")
    
    def _save_or_append(self, df: pd.DataFrame, output_path: Path):
        """Save dataframe to parquet, appending if file exists"""
        if output_path.exists():
            # Read existing data and append
            existing_df = pd.read_parquet(output_path)
            # Remove duplicates based on building_id and variant_id
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            # Keep last occurrence of duplicates
            if 'building_id' in combined_df.columns and 'variant_id' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(
                    subset=['building_id', 'variant_id'], 
                    keep='last'
                )
            df = combined_df
        
        df.to_parquet(output_path, index=False)
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def extract_static_data_for_building(sql_path: Path, output_dir: Path, 
                                    building_id: str, variant_id: str = 'base'):
    """
    Extract all static data for a single building
    
    Args:
        sql_path: Path to SQL file
        output_dir: Output directory (e.g., parsed_data or parsed_modified_results)
        building_id: Building identifier
        variant_id: Variant identifier
    """
    extractor = SQLStaticExtractor(sql_path, output_dir, building_id, variant_id)
    try:
        extractor.extract_all()
    finally:
        extractor.close()


if __name__ == "__main__":
    # Example usage
    sql_path = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/Modified_Sim_Results/2020/simulation_bldg0_4136733.sql")
    output_dir = Path("/mnt/d/Documents/daily/E_Plus_2040_py/output/e0e23b56-96a2-44b9-9936-76c15af196fb/test_static_extraction")
    
    extract_static_data_for_building(sql_path, output_dir, "4136733", "variant_0")