"""
Enhanced Schedule Extractor for SQL Data
Extracts detailed schedule information including usage patterns
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class ScheduleExtractor:
    """Extract detailed schedule information from SQL and IDF data"""
    
    def __init__(self, sql_path: Path, output_dir: Path, building_id: str, variant_id: str = 'base'):
        """
        Initialize schedule extractor
        
        Args:
            sql_path: Path to SQL file
            output_dir: Directory for output
            building_id: Building identifier
            variant_id: Variant identifier
        """
        self.sql_path = sql_path
        self.output_dir = Path(output_dir)
        self.building_id = building_id
        self.variant_id = variant_id
        self.conn = sqlite3.connect(str(sql_path))
        
        # Create output directory
        self.schedule_dir = self.output_dir / 'schedules'
        self.schedule_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_all_schedules(self):
        """Extract all schedule-related information"""
        logger.info(f"Extracting schedule data for {self.building_id} ({self.variant_id})")
        
        # 1. Extract basic schedule metadata
        self._extract_schedule_metadata()
        
        # 2. Extract schedule usage from equipment/loads
        self._extract_schedule_usage()
        
        # 3. Extract actual schedule values if available in timeseries
        self._extract_schedule_timeseries()
        
        # 4. Analyze schedule patterns
        self._analyze_schedule_patterns()
        
        logger.info("Schedule extraction complete")
    
    def _extract_schedule_metadata(self):
        """Extract basic schedule information from Schedules table"""
        try:
            query = "SELECT * FROM Schedules"
            schedules_df = pd.read_sql_query(query, self.conn)
            
            if not schedules_df.empty:
                schedules_df['building_id'] = self.building_id
                schedules_df['variant_id'] = self.variant_id
                
                # Save metadata
                output_path = self.schedule_dir / 'schedule_metadata.parquet'
                self._save_or_append(schedules_df, output_path)
                logger.info(f"Saved {len(schedules_df)} schedule metadata records")
        except Exception as e:
            logger.warning(f"Could not extract schedule metadata: {e}")
    
    def _extract_schedule_usage(self):
        """Extract how schedules are used by different components"""
        usage_data = []
        
        # Equipment schedules
        equipment_tables = [
            ('NominalElectricEquipment', 'ElectricEquipment'),
            ('NominalLighting', 'Lighting'),
            ('NominalPeople', 'People'),
            ('NominalInfiltration', 'Infiltration'),
            ('NominalVentilation', 'Ventilation')
        ]
        
        for table_name, equipment_type in equipment_tables:
            try:
                # Query to get schedule assignments
                query = f"""
                SELECT 
                    ObjectName,
                    ZoneIndex,
                    ScheduleIndex,
                    '{equipment_type}' as EquipmentType
                FROM {table_name}
                WHERE ScheduleIndex IS NOT NULL
                """
                
                df = pd.read_sql_query(query, self.conn)
                if not df.empty:
                    # Join with Schedules table to get schedule names
                    schedule_query = """
                    SELECT ScheduleIndex, ScheduleName 
                    FROM Schedules
                    """
                    schedules = pd.read_sql_query(schedule_query, self.conn)
                    
                    df = df.merge(schedules, on='ScheduleIndex', how='left')
                    df['building_id'] = self.building_id
                    df['variant_id'] = self.variant_id
                    
                    usage_data.append(df)
                    
            except Exception as e:
                logger.debug(f"No data for {table_name}: {e}")
        
        # Combine all usage data
        if usage_data:
            all_usage = pd.concat(usage_data, ignore_index=True)
            output_path = self.schedule_dir / 'schedule_usage.parquet'
            self._save_or_append(all_usage, output_path)
            logger.info(f"Saved {len(all_usage)} schedule usage records")
    
    def _extract_schedule_timeseries(self):
        """Extract actual schedule values from timeseries if available"""
        try:
            # Check if any schedule values are reported
            query = """
            SELECT DISTINCT 
                rdd.ReportDataDictionaryIndex,
                rdd.Name,
                rdd.KeyValue,
                rdd.Units
            FROM ReportDataDictionary rdd
            WHERE rdd.Name LIKE '%Schedule Value%'
               OR rdd.KeyValue LIKE '%SCHEDULE%'
            """
            
            schedule_vars = pd.read_sql_query(query, self.conn)
            
            if not schedule_vars.empty:
                logger.info(f"Found {len(schedule_vars)} schedule variables in timeseries")
                
                # Extract hourly values for each schedule
                for _, var in schedule_vars.iterrows():
                    self._extract_single_schedule_timeseries(
                        var['ReportDataDictionaryIndex'],
                        var['Name'],
                        var['KeyValue']
                    )
            else:
                logger.info("No schedule timeseries data found in SQL")
                
        except Exception as e:
            logger.warning(f"Could not extract schedule timeseries: {e}")
    
    def _extract_single_schedule_timeseries(self, dict_index: int, var_name: str, key_value: str):
        """Extract timeseries for a single schedule"""
        try:
            # Get typical day profiles (e.g., Jan 15, Apr 15, Jul 15, Oct 15)
            typical_days = [(1, 15), (4, 15), (7, 15), (10, 15)]
            
            all_profiles = []
            
            for month, day in typical_days:
                query = f"""
                SELECT 
                    t.Hour,
                    t.Minute,
                    AVG(rd.Value) as Value
                FROM ReportData rd
                JOIN Time t ON rd.TimeIndex = t.TimeIndex
                WHERE rd.ReportDataDictionaryIndex = {dict_index}
                  AND t.Month = {month}
                  AND t.Day = {day}
                  AND t.WarmupFlag = 0
                GROUP BY t.Hour, t.Minute
                ORDER BY t.Hour, t.Minute
                """
                
                df = pd.read_sql_query(query, self.conn)
                
                if not df.empty:
                    df['Month'] = month
                    df['Day'] = day
                    df['ScheduleName'] = key_value
                    df['VariableName'] = var_name
                    df['building_id'] = self.building_id
                    df['variant_id'] = self.variant_id
                    all_profiles.append(df)
            
            if all_profiles:
                profiles_df = pd.concat(all_profiles, ignore_index=True)
                
                # Save schedule profile
                safe_name = key_value.replace(':', '_').replace(' ', '_')
                output_path = self.schedule_dir / f'schedule_profile_{safe_name}.parquet'
                profiles_df.to_parquet(output_path, index=False)
                logger.info(f"Saved profile for schedule: {key_value}")
                
        except Exception as e:
            logger.debug(f"Could not extract profile for {key_value}: {e}")
    
    def _analyze_schedule_patterns(self):
        """Analyze schedule patterns and create summary"""
        try:
            # Load schedule metadata
            metadata_path = self.schedule_dir / 'schedule_metadata.parquet'
            if not metadata_path.exists():
                return
            
            metadata = pd.read_parquet(metadata_path)
            
            # Analyze schedule types
            schedule_analysis = []
            
            for _, schedule in metadata.iterrows():
                analysis = {
                    'building_id': self.building_id,
                    'variant_id': self.variant_id,
                    'ScheduleName': schedule['ScheduleName'],
                    'ScheduleType': schedule['ScheduleType'],
                    'MinValue': schedule['ScheduleMinimum'],
                    'MaxValue': schedule['ScheduleMaximum'],
                    'Range': schedule['ScheduleMaximum'] - schedule['ScheduleMinimum']
                }
                
                # Categorize schedule based on name and range
                if 'ALWAYS' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'Constant'
                elif analysis['Range'] == 0:
                    analysis['Category'] = 'Constant'
                elif 'LIGHT' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'Lighting'
                elif 'EQUIP' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'Equipment'
                elif 'HEATING' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'Heating Setpoint'
                elif 'COOLING' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'Cooling Setpoint'
                elif 'DHW' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'Domestic Hot Water'
                elif 'HVAC' in schedule['ScheduleName'].upper():
                    analysis['Category'] = 'HVAC Availability'
                else:
                    analysis['Category'] = 'Other'
                
                schedule_analysis.append(analysis)
            
            # Save analysis
            if schedule_analysis:
                analysis_df = pd.DataFrame(schedule_analysis)
                output_path = self.schedule_dir / 'schedule_analysis.parquet'
                self._save_or_append(analysis_df, output_path)
                logger.info(f"Saved schedule analysis for {len(analysis_df)} schedules")
                
        except Exception as e:
            logger.warning(f"Could not analyze schedule patterns: {e}")
    
    def _save_or_append(self, df: pd.DataFrame, output_path: Path):
        """Save or append dataframe to parquet file"""
        if output_path.exists():
            existing_df = pd.read_parquet(output_path)
            # Remove duplicates based on building_id and variant_id
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            if 'building_id' in combined_df.columns and 'variant_id' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(
                    subset=['building_id', 'variant_id', 'ScheduleName'] 
                    if 'ScheduleName' in combined_df.columns 
                    else ['building_id', 'variant_id'],
                    keep='last'
                )
            df = combined_df
        
        df.to_parquet(output_path, index=False)
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def extract_schedules_for_building(sql_path: Path, output_dir: Path, 
                                  building_id: str, variant_id: str = 'base'):
    """
    Extract schedule data for a single building
    
    Args:
        sql_path: Path to SQL file
        output_dir: Output directory
        building_id: Building identifier
        variant_id: Variant identifier
    """
    extractor = ScheduleExtractor(sql_path, output_dir, building_id, variant_id)
    try:
        extractor.extract_all_schedules()
    finally:
        extractor.close()