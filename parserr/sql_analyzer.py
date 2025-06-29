"""
Enhanced SQL Analyzer Module v4.0 - Fixed Building/Variant Identification
Handles extraction and analysis of EnergyPlus SQL results with proper variant tracking
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import re
from datetime import datetime
from .sql_data_manager import SQLDataManager

# Helper function for aggregation
def aggregate_timeseries(df, freq, method):
    """Simple aggregation wrapper"""
    df = df.copy()
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    df = df.set_index('DateTime')
    
    # Get grouping columns (all except Value)
    group_cols = [col for col in df.columns if col not in ['Value']]
    
    # Group and aggregate
    if group_cols:
        grouped = df.groupby(group_cols)['Value']
        if method == 'sum':
            result = grouped.resample(freq).sum()
        elif method == 'mean':
            result = grouped.resample(freq).mean()
        else:
            result = grouped.resample(freq).agg(method)
        return result.reset_index()
    else:
        # No grouping columns, just resample
        if method == 'sum':
            return df.resample(freq).sum().reset_index()
        else:
            return df.resample(freq).mean().reset_index()


# Enhanced category mappings for SQL variables
SQL_CATEGORY_MAPPINGS = {
    'energy_meters': [
        'Electricity:Facility', 'Electricity:Building', 'Electricity:HVAC',
        'Gas:Facility', 'Gas:Building', 'DistrictCooling:Facility',
        'DistrictHeating:Facility', 'Cooling:EnergyTransfer', 
        'Heating:EnergyTransfer', 'HeatRejection:EnergyTransfer'
    ],
    'site_weather': [
        'Site Outdoor Air Drybulb Temperature', 'Site Outdoor Air Wetbulb Temperature',
        'Site Outdoor Air Relative Humidity', 'Site Wind Speed', 'Site Wind Direction',
        'Site Diffuse Solar Radiation Rate per Area', 'Site Direct Solar Radiation Rate per Area',
        'Site Rain Status', 'Site Snow Depth', 'Site Ground Temperature'
    ],
    'geometry': [
        'Zone Mean Air Temperature', 'Zone Air Temperature', 'Zone Operative Temperature',
        'Zone Thermal Comfort Mean Radiant Temperature', 'Zone Mean Radiant Temperature',
        'Zone Air Relative Humidity', 'Zone Air Humidity Ratio'
    ],
    'materials': [
        'Surface Inside Face Temperature', 'Surface Outside Face Temperature',
        'Surface Inside Face Conduction Heat Transfer Rate', 'Surface Outside Face Conduction Heat Transfer Rate',
        'Surface Inside Face Convection Heat Transfer Rate', 'Surface Outside Face Convection Heat Transfer Rate',
        'Surface Inside Face Net Surface Thermal Radiation Heat Gain Rate',
        'Surface Window Heat Gain Rate', 'Surface Window Heat Loss Rate'
    ],
    'dhw': [
        'Water Heater Heating Energy', 'Water Heater Heating Rate',
        'Water Heater Tank Temperature', 'Water Heater Heat Loss Energy',
        'Water Use Equipment Hot Water Volume', 'Water Use Equipment Cold Water Volume',
        'Water Use Equipment Total Volume', 'Water Use Equipment Hot Water Temperature'
    ],
    'equipment': [
        'Zone Electric Equipment Electricity Energy', 'Zone Electric Equipment Electricity Rate',
        'Zone Electric Equipment Total Heating Energy', 'Zone Electric Equipment Total Heating Rate',
        'Zone Gas Equipment Gas Energy', 'Zone Gas Equipment Gas Rate',
        'Zone Other Equipment Total Heating Energy', 'Zone Other Equipment Total Heating Rate'
    ],
    'lighting': [
        'Zone Lights Electricity Energy', 'Zone Lights Electricity Rate',
        'Zone Lights Total Heating Energy', 'Zone Lights Total Heating Rate',
        'Zone Lights Visible Radiation Rate', 'Daylighting Reference Point Illuminance',
        'Daylighting Lighting Power Multiplier'
    ],
    'hvac': [
        'Zone Air System Sensible Cooling Energy', 'Zone Air System Sensible Heating Energy',
        'Zone Air System Sensible Cooling Rate', 'Zone Air System Sensible Heating Rate',
        'Zone Ideal Loads Zone Sensible Cooling Rate', 'Zone Ideal Loads Zone Sensible Heating Rate',
        'Zone Thermostat Heating Setpoint Temperature', 'Zone Thermostat Cooling Setpoint Temperature',
        'Fan Electricity Energy', 'Fan Electricity Rate',
        'Cooling Coil Total Cooling Energy', 'Heating Coil Heating Energy'
    ],
    'ventilation': [
        'Zone Mechanical Ventilation Mass Flow Rate', 'Zone Mechanical Ventilation Volume Flow Rate',
        'Zone Mechanical Ventilation Air Change Rate', 'Zone Ventilation Air Change Rate',
        'Zone Ventilation Volume', 'Zone Ventilation Mass',
        'Zone Ventilation Sensible Heat Loss Energy', 'Zone Ventilation Sensible Heat Gain Energy',
        'System Node Mass Flow Rate', 'System Node Volume Flow Rate'
    ],
    'infiltration': [
        'Zone Infiltration Air Change Rate', 'Zone Infiltration Volume',
        'Zone Infiltration Mass', 'Zone Infiltration Mass Flow Rate',
        'Zone Infiltration Sensible Heat Loss Energy', 'Zone Infiltration Sensible Heat Gain Energy',
        'Zone Infiltration Latent Heat Loss Energy', 'Zone Infiltration Latent Heat Gain Energy'
    ],
    'shading': [
        'Surface Window Transmitted Solar Radiation Rate', 'Surface Window Transmitted Beam Solar Radiation Rate',
        'Surface Window Transmitted Diffuse Solar Radiation Rate', 'Zone Windows Total Transmitted Solar Radiation Rate',
        'Zone Windows Total Heat Gain Rate', 'Zone Windows Total Heat Loss Rate',
        'Surface Shading Device Is On Time Fraction', 'Surface Window Blind Slat Angle'
    ]
}


class EnhancedSQLAnalyzer:
    """Enhanced SQL analyzer with proper variant tracking"""
    
    def __init__(self, sql_path: Path, data_manager: Optional[SQLDataManager] = None, 
                 base_buildings: Optional[Set[str]] = None, is_modified_results: bool = False):
        """
        Initialize SQL analyzer with database connection and data manager
        
        Args:
            sql_path: Path to SQL file
            data_manager: SQL data manager instance
            base_buildings: Set of building IDs that are base buildings
            is_modified_results: Whether this is from Modified_Sim_Results
        """
        self.sql_path = sql_path
        self.sql_conn = sqlite3.connect(str(self.sql_path))
        self._sql_cache = {}
        self.data_manager = data_manager
        self.base_buildings = base_buildings or set()
        self.is_modified_results = is_modified_results
        self._available_outputs = None
        
        # Extract building ID and variant ID
        self.building_id, self.variant_id = self._extract_building_and_variant_id()
    
    def _extract_building_and_variant_id(self) -> Tuple[str, str]:
        """Extract building ID and variant ID from SQL file name"""
        filename = self.sql_path.name
        
        # Pattern: simulation_bldg{index}_{building_id}.sql
        match = re.search(r'simulation_bldg(\d+)_(\d+)\.sql', filename)
        if match:
            bldg_index = int(match.group(1))
            building_id = match.group(2)
            
            if self.is_modified_results:
                # In Modified_Sim_Results, bldg index indicates variant
                # bldg0 -> variant_0, bldg1 -> variant_1, etc.
                variant_id = f'variant_{bldg_index}'
            else:
                # In base Sim_Results, all are base
                variant_id = 'base'
            
            return building_id, variant_id
        
        # Fallback patterns
        patterns = [
            r'building_(\d+)_variant_(\d+)\.sql',
            r'building_(\d+)\.sql',
            r'(\d{6,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                building_id = match.group(1)
                if len(match.groups()) > 1:
                    variant_id = f'variant_{match.group(2)}'
                else:
                    variant_id = 'base'
                return building_id, variant_id
        
        # Ultimate fallback
        return self.sql_path.stem, 'base'
    
    def get_available_outputs(self) -> pd.DataFrame:
        """Get all available outputs in the SQL database"""
        if self._available_outputs is not None:
            return self._available_outputs
        
        query = """
            SELECT 
                rdd.ReportDataDictionaryIndex,
                rdd.Name as VariableName,
                rdd.KeyValue,
                rdd.Units,
                rdd.ReportingFrequency,
                COUNT(DISTINCT rd.TimeIndex) as DataPoints
            FROM ReportDataDictionary rdd
            LEFT JOIN ReportData rd ON rdd.ReportDataDictionaryIndex = rd.ReportDataDictionaryIndex
            GROUP BY rdd.ReportDataDictionaryIndex, rdd.Name, rdd.KeyValue, rdd.Units, rdd.ReportingFrequency
            ORDER BY rdd.Name, rdd.KeyValue
        """
        
        try:
            self._available_outputs = pd.read_sql_query(query, self.sql_conn)
            
            # Add additional metadata
            self._available_outputs['HasData'] = self._available_outputs['DataPoints'] > 0
            self._available_outputs['Category'] = self._available_outputs['VariableName'].apply(
                self._categorize_variable
            )
            
        except Exception as e:
            print(f"Error getting available outputs: {e}")
            self._available_outputs = pd.DataFrame(columns=[
                'ReportDataDictionaryIndex', 'VariableName', 'KeyValue', 
                'Units', 'ReportingFrequency', 'DataPoints', 'HasData', 'Category'
            ])
        
        return self._available_outputs
    
    def _categorize_variable(self, variable_name: str) -> str:
        """Categorize a variable based on its name using detailed mappings"""
        # Check each category for exact match
        for category, variables in SQL_CATEGORY_MAPPINGS.items():
            if variable_name in variables:
                return category
        
        # If no exact match, fall back to pattern matching
        var_lower = variable_name.lower()
        
        if any(meter in variable_name for meter in ['Electricity:', 'Gas:', 'Cooling:', 'Heating:']):
            return 'energy_meters'
        elif 'site' in var_lower and any(word in var_lower for word in ['outdoor', 'solar', 'wind', 'rain']):
            return 'site_weather'
        elif 'zone' in var_lower and any(word in var_lower for word in ['temperature', 'humidity', 'comfort']):
            return 'geometry'
        elif 'surface' in var_lower and any(word in var_lower for word in ['temperature', 'conduction', 'convection']):
            return 'materials'
        elif any(word in var_lower for word in ['water heater', 'water use', 'hot water']):
            return 'dhw'
        elif 'equipment' in var_lower and 'electric' in var_lower:
            return 'equipment'
        elif 'lights' in var_lower or 'lighting' in var_lower:
            return 'lighting'
        elif any(word in var_lower for word in ['cooling energy', 'heating energy', 'thermostat', 'fan', 'coil']):
            return 'hvac'
        elif 'ventilation' in var_lower:
            return 'ventilation'
        elif 'infiltration' in var_lower:
            return 'infiltration'
        elif any(word in var_lower for word in ['shading', 'blind', 'transmitted solar']):
            return 'shading'
        else:
            return 'other'
    
    def extract_timeseries(self, variables: List[str], 
                          zone_mapping: Dict[str, str],
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """Extract SQL time series data for specified variables"""
        
        # Get available variables
        available_vars_query = """
            SELECT DISTINCT Name, KeyValue, Units, ReportingFrequency
            FROM ReportDataDictionary
            WHERE Name IN ({})
            ORDER BY Name, KeyValue
        """.format(','.join(['?'] * len(variables)))
        
        try:
            available_vars = pd.read_sql_query(available_vars_query, self.sql_conn, params=variables)
        except Exception as e:
            print(f"  Error querying available variables: {e}")
            return pd.DataFrame()
        
        if available_vars.empty:
            print(f"  No SQL variables found")
            return pd.DataFrame()
        
        # Get date range if not specified
        if not start_date or not end_date:
            start_date, end_date = self._get_date_range()
        
        # Build comprehensive query
        query = """
            SELECT 
                t.TimeIndex,
                CASE 
                    WHEN t.Hour = 24 THEN datetime(printf('%04d-%02d-%02d 00:00:00', t.Year, t.Month, t.Day), '+1 day')
                    ELSE datetime(printf('%04d-%02d-%02d %02d:%02d:00', t.Year, t.Month, t.Day, t.Hour, t.Minute))
                END as DateTime,
                rdd.Name as Variable,
                rdd.KeyValue as Zone,
                rd.Value,
                rdd.Units,
                rdd.ReportingFrequency
            FROM ReportData rd
            JOIN Time t ON rd.TimeIndex = t.TimeIndex
            JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
            WHERE rdd.Name IN ({})
            AND t.EnvironmentPeriodIndex IN (
                SELECT EnvironmentPeriodIndex 
                FROM EnvironmentPeriods 
                WHERE EnvironmentType = 3
            )
            AND date(printf('%04d-%02d-%02d', t.Year, t.Month, t.Day)) BETWEEN ? AND ?
            ORDER BY t.TimeIndex, rdd.Name
        """.format(','.join(['?'] * len(variables)))
        
        params = variables + [start_date, end_date]
        
        try:
            df = pd.read_sql_query(query, self.sql_conn, params=params)
        except Exception as e:
            print(f"  Error with datetime query: {e}")
            return pd.DataFrame()
        
        # Add category to each variable
        if not df.empty and 'Variable' in df.columns:
            df['category'] = df['Variable'].apply(self._categorize_variable)
            
            # Convert datetime
            df['DateTime'] = pd.to_datetime(df['DateTime'])
            
            # Add building and variant IDs
            df['building_id'] = self.building_id
            df['variant_id'] = self.variant_id
        
        return df
    
    def extract_and_save_all(self, zone_mapping: Dict[str, str], 
                            variables_by_category: Dict[str, List[str]],
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            variant_id: str = None):
        """Extract all SQL data and save to data manager"""
        if not self.data_manager:
            print("Warning: No data manager configured. Data will not be saved.")
            return
        
        # Use the variant_id determined during initialization
        actual_variant_id = self.variant_id
        
        # Track extraction statistics
        extraction_stats = {
            'categories_processed': 0,
            'variables_extracted': 0,
            'data_points_extracted': 0,
            'missing_variables': []
        }
        
        # Extract time series data by category
        all_timeseries_data = []
        
        for category, variables in variables_by_category.items():
            if not variables:
                continue
                
            print(f"\n  Extracting {category} variables...")
            
            # Extract time series
            try:
                timeseries_df = self.extract_timeseries(
                    variables, 
                    zone_mapping,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if not timeseries_df.empty:
                    all_timeseries_data.append(timeseries_df)
                    
                    # Update stats
                    extraction_stats['categories_processed'] += 1
                    extraction_stats['variables_extracted'] += len(timeseries_df['Variable'].unique())
                    extraction_stats['data_points_extracted'] += len(timeseries_df)
                    
                    print(f"    Extracted {len(timeseries_df):,} data points")
                else:
                    print(f"    No data extracted for {category}")
                    
            except Exception as e:
                print(f"    Error extracting {category}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save all timeseries data at once
        if all_timeseries_data:
            combined_df = pd.concat(all_timeseries_data, ignore_index=True)
            
            # Save raw data by frequency
            for freq in combined_df['ReportingFrequency'].unique():
                freq_df = combined_df[combined_df['ReportingFrequency'] == freq].copy()
                self.data_manager.save_raw_timeseries(
                    freq_df, 
                    'all_variables',  # Use a generic category name
                    freq,
                    variant_id=actual_variant_id,
                    is_base=(actual_variant_id == 'base')
                )
        
        # Extract and save schedules
        print("\n  Extracting schedules...")
        try:
            schedules = self._extract_all_schedules()
            if not schedules.empty:
                schedules['building_id'] = self.building_id
                schedules['variant_id'] = actual_variant_id
                self.data_manager.save_schedules(schedules)
                print(f"    Extracted {len(schedules)} schedules")
        except Exception as e:
            print(f"    Error extracting schedules: {e}")
        
        print(f"\n  Extraction complete:")
        print(f"    Building: {self.building_id}, Variant: {actual_variant_id}")
        print(f"    Categories: {extraction_stats['categories_processed']}")
        print(f"    Variables: {extraction_stats['variables_extracted']}")
        print(f"    Data points: {extraction_stats['data_points_extracted']:,}")
    
    def _get_date_range(self) -> Tuple[str, str]:
        """Get simulation date range"""
        try:
            date_range_query = """
                SELECT 
                    MIN(date(printf('%04d-%02d-%02d', Year, Month, Day))) as min_date,
                    MAX(date(printf('%04d-%02d-%02d', Year, Month, Day))) as max_date
                FROM Time
                WHERE EnvironmentPeriodIndex IN (
                    SELECT EnvironmentPeriodIndex 
                    FROM EnvironmentPeriods 
                    WHERE EnvironmentType = 3
                )
            """
            dates = pd.read_sql_query(date_range_query, self.sql_conn).iloc[0]
            
            if pd.isna(dates['min_date']) or pd.isna(dates['max_date']):
                raise ValueError("Invalid dates returned")
                
            return str(dates['min_date']), str(dates['max_date'])
            
        except Exception as e:
            print(f"Error getting date range: {e}")
            return '2020-01-01', '2020-12-31'
    
    def _extract_all_schedules(self) -> pd.DataFrame:
        """Extract all schedule data from SQL"""
        try:
            schedules_query = """
                SELECT 
                    ScheduleIndex,
                    ScheduleName,
                    ScheduleType,
                    ScheduleMinimum,
                    ScheduleMaximum
                FROM Schedules
            """
            schedules = pd.read_sql_query(schedules_query, self.sql_conn)
            return schedules
            
        except Exception as e:
            print(f"Error extracting schedules: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close database connection"""
        self.sql_conn.close()