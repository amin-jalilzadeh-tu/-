"""
Enhanced SQL Analyzer Module v3.1 - With Output Validation
Handles extraction and analysis of EnergyPlus SQL results with output validation
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
import re
from datetime import datetime
from .data_manager import EnhancedHierarchicalDataManager, aggregate_timeseries

class EnhancedSQLAnalyzer:
    """Enhanced SQL analyzer with output validation capabilities"""
    
    def __init__(self, sql_path: Path, data_manager: Optional[EnhancedHierarchicalDataManager] = None):
        """Initialize SQL analyzer with database connection and data manager"""
        self.sql_path = sql_path
        self.sql_conn = sqlite3.connect(str(self.sql_path))
        self._sql_cache = {}
        self.data_manager = data_manager
        self.building_id = self._extract_building_id()
        self._available_outputs = None  # Cache for available outputs
    
    # In sql_analyzer.py, update the _extract_building_id method:

    def _extract_building_id(self) -> str:
        """Extract building ID from SQL file name - Updated for new naming convention"""
        # Handle different naming patterns
        patterns = [
            # New pattern: simulation_bldg0_4136737.sql
            r'simulation_bldg\d+_(\d+)\.sql',  # Extract the actual ID after underscore
            # Legacy pattern: simulation_bldg0.sql
            r'simulation_bldg(\d+)\.sql',      # Old pattern - returns index
            # Other patterns
            r'building_(\d+)\.sql',
            r'building_(\d+)_\w+\.sql',
            r'(\d{6,})'  # Look for 6+ digit numbers
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.sql_path.name)
            if match:
                building_id = match.group(1)
                
                # For legacy simulation_bldg pattern without ID, try to map using CSV
                if 'simulation_bldg' in self.sql_path.name and '_' not in self.sql_path.name:
                    # This is the old format, try to find mapping
                    parent_dir = self.sql_path.parent.parent
                    idf_map_path = parent_dir / 'extracted_idf_buildings.csv'
                    
                    if idf_map_path.exists():
                        try:
                            df_map = pd.read_csv(idf_map_path)
                            idx = int(building_id)
                            if idx < len(df_map):
                                actual_id = str(df_map.iloc[idx]['ogc_fid'])
                                return actual_id
                        except Exception as e:
                            logger.warning(f"Error reading building mapping: {e}")
                    
                    # If no mapping found, return with bldg_ prefix
                    logger.warning(f"No mapping found for {self.sql_path.name}, using index {building_id}")
                    return f"bldg_{building_id}"
                
                return building_id
        
        # Fallback to stem without extension
        return self.sql_path.stem
    
    # In sql_analyzer.py, find and replace the get_available_outputs method with this corrected version:

    def get_available_outputs(self) -> pd.DataFrame:
        """Get all available outputs in the SQL database"""
        if self._available_outputs is not None:
            return self._available_outputs
        
        # Fixed query with table prefixes to avoid ambiguous column names
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
            # Create empty DataFrame with expected columns
            self._available_outputs = pd.DataFrame(columns=[
                'ReportDataDictionaryIndex', 'VariableName', 'KeyValue', 
                'Units', 'ReportingFrequency', 'DataPoints', 'HasData', 'Category'
            ])
        
        return self._available_outputs
    
    def _categorize_variable(self, variable_name: str) -> str:
        """Categorize a variable based on its name"""
        var_lower = variable_name.lower()
        
        if 'energy' in var_lower:
            return 'energy'
        elif 'temperature' in var_lower or 'comfort' in var_lower:
            return 'comfort'
        elif 'hvac' in var_lower or 'coil' in var_lower or 'fan' in var_lower:
            return 'hvac'
        elif 'surface' in var_lower or 'window' in var_lower:
            return 'envelope'
        elif 'site' in var_lower or 'environment' in var_lower:
            return 'environmental'
        elif 'lights' in var_lower or 'lighting' in var_lower:
            return 'lighting'
        elif 'equipment' in var_lower:
            return 'equipment'
        elif 'ventilation' in var_lower or 'infiltration' in var_lower:
            return 'ventilation'
        elif 'water' in var_lower:
            return 'dhw'
        else:
            return 'other'
    
    def validate_requested_outputs(self, requested_outputs: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate that requested outputs are available in SQL"""
        available = self.get_available_outputs()
        
        validation_result = {
            'building_id': self.building_id,
            'total_requested': len(requested_outputs),
            'found': 0,
            'missing': [],
            'partial': [],
            'coverage': 0.0,
            'data_completeness': {}
        }
        
        # Create lookup set for fast checking
        available_set = set()
        for _, row in available.iterrows():
            available_set.add((
                row['VariableName'],
                row['KeyValue'],
                row['ReportingFrequency']
            ))
        
        # Check each requested output
        for req_output in requested_outputs:
            var_name = req_output.get('variable_name', '')
            key_value = req_output.get('key_value', '*')
            frequency = req_output.get('reporting_frequency', 'Hourly')
            
            found = False
            partial = False
            
            if key_value == '*':
                # Check if variable exists for any key
                matching_vars = available[
                    (available['VariableName'] == var_name) & 
                    (available['ReportingFrequency'] == frequency)
                ]
                
                if not matching_vars.empty:
                    found = True
                    # Check if all have data
                    if not matching_vars['HasData'].all():
                        partial = True
            else:
                # Check specific key
                if (var_name, key_value, frequency) in available_set:
                    found = True
                    # Check if has data
                    specific_var = available[
                        (available['VariableName'] == var_name) & 
                        (available['KeyValue'] == key_value) &
                        (available['ReportingFrequency'] == frequency)
                    ]
                    if not specific_var.empty and not specific_var.iloc[0]['HasData']:
                        partial = True
            
            if found:
                validation_result['found'] += 1
                if partial:
                    validation_result['partial'].append({
                        'variable': var_name,
                        'key': key_value,
                        'frequency': frequency,
                        'reason': 'No data points found'
                    })
            else:
                validation_result['missing'].append({
                    'variable': var_name,
                    'key': key_value,
                    'frequency': frequency
                })
        
        # Calculate coverage
        if validation_result['total_requested'] > 0:
            validation_result['coverage'] = (
                validation_result['found'] / validation_result['total_requested']
            ) * 100
        
        # Analyze data completeness by category
        for category in available['Category'].unique():
            cat_vars = available[available['Category'] == category]
            with_data = cat_vars[cat_vars['HasData']]
            validation_result['data_completeness'][category] = {
                'total_variables': len(cat_vars),
                'variables_with_data': len(with_data),
                'completeness': len(with_data) / len(cat_vars) * 100 if len(cat_vars) > 0 else 0
            }
        
        return validation_result
    
    def build_zone_mapping(self, idf_zones: List[str]) -> Dict[str, str]:
        """Create robust mapping between IDF zone names and SQL zone names"""
        zone_mapping = {}
        
        # Get zones from SQL with improved query
        sql_zones_query = """
            SELECT DISTINCT ZoneName as Zone
            FROM Zones
            UNION
            SELECT DISTINCT KeyValue as Zone
            FROM ReportDataDictionary
            WHERE KeyValue != 'Environment'
            AND (KeyValue LIKE 'Zone%' OR KeyValue LIKE 'ZONE%' 
                 OR KeyValue IN (SELECT ZoneName FROM Zones))
        """
        
        try:
            sql_zones_df = pd.read_sql_query(sql_zones_query, self.sql_conn)
            sql_zones = sql_zones_df['Zone'].tolist()
        except Exception as e:
            print(f"Error querying SQL zones: {e}")
            sql_zones = []
        
        print(f"\nSQL zones found: {len(sql_zones)}")
        if len(sql_zones) < 20:  # Only print if reasonable number
            for zone in sql_zones:
                print(f"  - {zone}")
        
        print(f"\nIDF zones to map: {len(idf_zones)}")
        
        # Map IDF zones to SQL zones with multiple strategies
        for idf_zone in idf_zones:
            mapped = False
            
            # Strategy 1: Exact match
            if idf_zone in sql_zones:
                zone_mapping[idf_zone] = idf_zone
                mapped = True
            
            # Strategy 2: Case-insensitive exact match
            if not mapped:
                for sql_zone in sql_zones:
                    if idf_zone.upper() == sql_zone.upper():
                        zone_mapping[idf_zone] = sql_zone
                        mapped = True
                        break
            
            # Strategy 3: IDF lowercase/mixed -> SQL uppercase
            if not mapped:
                upper_zone = idf_zone.upper()
                if upper_zone in sql_zones:
                    zone_mapping[idf_zone] = upper_zone
                    mapped = True
            
            # Strategy 4: Remove spaces and underscores for comparison
            if not mapped:
                idf_normalized = re.sub(r'[\s_-]', '', idf_zone.upper())
                for sql_zone in sql_zones:
                    sql_normalized = re.sub(r'[\s_-]', '', sql_zone.upper())
                    if idf_normalized == sql_normalized:
                        zone_mapping[idf_zone] = sql_zone
                        mapped = True
                        break
            
            # Strategy 5: Pattern matching for common zone naming conventions
            if not mapped:
                patterns = [
                    (r'^Zone(\d+)_(\w+)$', r'ZONE\1_\2'),
                    (r'^Zone(\d+)$', r'ZONE\1'),
                    (r'^(\w+)Zone(\d+)$', r'\1ZONE\2'),
                ]
                
                for pattern, replacement in patterns:
                    match = re.match(pattern, idf_zone, re.IGNORECASE)
                    if match:
                        potential_sql_zone = re.sub(pattern, replacement, idf_zone, flags=re.IGNORECASE).upper()
                        if potential_sql_zone in sql_zones:
                            zone_mapping[idf_zone] = potential_sql_zone
                            mapped = True
                            break
            
            # Final fallback: assume SQL zone is uppercase version
            if not mapped:
                zone_mapping[idf_zone] = idf_zone.upper()
                print(f"  Warning: No exact match found for '{idf_zone}', assuming '{idf_zone.upper()}'")
        
        # Special handling for ALL_ZONES
        zone_mapping['ALL_ZONES'] = 'Environment'
        
        # Save zone mapping if data manager available
        if self.data_manager:
            mapping_df = pd.DataFrame([
                {
                    'building_id': self.building_id,
                    'idf_zone_name': idf_zone,
                    'sql_zone_name': sql_zone,
                    'mapping_confidence': 1.0 if idf_zone == sql_zone else 0.8
                }
                for idf_zone, sql_zone in zone_mapping.items()
            ])
            self.data_manager.save_relationships('zone_mappings', mapping_df)
        
        # Print mapping summary
        print(f"\nZone mapping established for {len(zone_mapping)} zones:")
        for idf_zone, sql_zone in sorted(zone_mapping.items())[:10]:  # Show first 10
            if idf_zone != sql_zone:
                print(f"  {idf_zone} → {sql_zone}")
        
        return zone_mapping
    
    def extract_and_save_all(self, zone_mapping: Dict[str, str], 
                            variables_by_category: Dict[str, List[str]],
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None):
        """Extract all data and save to hierarchical structure"""
        if not self.data_manager:
            print("Warning: No data manager configured. Data will not be saved.")
            return
        
        # Get date range if not specified
        if not start_date or not end_date:
            start_date, end_date = self._get_date_range()
        
        # Get available outputs for validation
        available_outputs = self.get_available_outputs()
        
        # Track extraction statistics
        extraction_stats = {
            'categories_processed': 0,
            'variables_extracted': 0,
            'data_points_extracted': 0,
            'missing_variables': []
        }
        
        # Extract time series by category
        for category, variables in variables_by_category.items():
            print(f"\nExtracting {category} variables...")
            
            # Filter to only available variables
            available_vars = []
            for var in variables:
                if var in available_outputs['VariableName'].values:
                    available_vars.append(var)
                else:
                    extraction_stats['missing_variables'].append({
                        'category': category,
                        'variable': var
                    })
            
            if not available_vars:
                print(f"  No available variables for {category}")
                continue
                
            ts_data = self.extract_timeseries(available_vars, zone_mapping, start_date, end_date)
            
            if not ts_data.empty:
                extraction_stats['categories_processed'] += 1
                extraction_stats['variables_extracted'] += len(available_vars)
                extraction_stats['data_points_extracted'] += len(ts_data)
                
                # Add building_id column
                ts_data['building_id'] = self.building_id
                
                # Map to output category names
                output_category = self._map_output_category(category)
                
                # Save hourly data
                year = ts_data['DateTime'].dt.year.mode()[0] if not ts_data.empty else datetime.now().year
                self.data_manager.save_timeseries_data(ts_data, 'hourly', output_category, year)
                
                # Create and save daily aggregations
                print(f"  Creating daily aggregations for {output_category}...")
                daily_data = self._create_daily_aggregations(ts_data)
                if not daily_data.empty:
                    self.data_manager.save_timeseries_data(daily_data, 'daily', output_category)
                
                # Create and save monthly aggregations
                print(f"  Creating monthly aggregations for {output_category}...")
                monthly_data = self._create_monthly_aggregations(ts_data)
                if not monthly_data.empty:
                    self.data_manager.save_timeseries_data(monthly_data, 'monthly', output_category)
        
        # Extract and save schedules
        print("\nExtracting schedules...")
        schedules = self._extract_all_schedules()
        if not schedules.empty:
            schedules['building_id'] = self.building_id
            self.data_manager.save_schedules(schedules)
        
        # Create and save summary metrics
        print("\nCreating summary metrics...")
        self._create_and_save_summary_metrics(zone_mapping)
        
        # Save extraction statistics
        self._save_extraction_stats(extraction_stats)
        
        # Report extraction summary
        print(f"\nExtraction Summary:")
        print(f"  Categories processed: {extraction_stats['categories_processed']}")
        print(f"  Variables extracted: {extraction_stats['variables_extracted']}")
        print(f"  Data points: {extraction_stats['data_points_extracted']:,}")
        if extraction_stats['missing_variables']:
            print(f"  Missing variables: {len(extraction_stats['missing_variables'])}")
    




    def extract_selective(self, content_config: Dict[str, Any], 
                        variables_by_category: Dict[str, List[str]]):
        """Extract SQL data based on selective configuration"""
        if not self.data_manager:
            print("Warning: No data manager configured. Data will not be saved.")
            return
        
        # Apply time filter if specified
        time_filter = content_config.get('time_filter', {})
        start_date = time_filter.get('start_date')
        end_date = time_filter.get('end_date')
        
        # Get date range if not specified
        if not start_date or not end_date:
            start_date, end_date = self._get_date_range()
        
        # Apply additional time filters
        month_filter = time_filter.get('months')
        hour_filter = time_filter.get('hours')
        
        # Apply frequency filter
        frequency_filter = content_config.get('frequency_filter')
        
        # Apply zone filter
        zone_filter = content_config.get('zone_filter', {})
        
        # Track extraction statistics
        extraction_stats = {
            'categories_processed': 0,
            'variables_extracted': 0,
            'data_points_extracted': 0,
            'filtered_out': 0
        }
        
        # Extract components based on configuration
        components = content_config.get('components', {
            'timeseries': True,
            'schedules': True,
            'summary_metrics': True,
            'output_validation': True
        })
        
        # Extract time series if requested
        if components.get('timeseries', True):
            for category, variables in variables_by_category.items():
                print(f"\nExtracting {category} variables...")
                
                # Apply variable filtering
                filtered_vars = self._filter_variables(variables, content_config)
                
                if not filtered_vars:
                    print(f"  No variables to extract for {category} after filtering")
                    continue
                
                # Build query with filters
                query = self._build_filtered_query(
                    filtered_vars, 
                    start_date, 
                    end_date,
                    month_filter,
                    hour_filter,
                    frequency_filter,
                    zone_filter
                )
                
                try:
                    df = pd.read_sql_query(query['sql'], self.sql_conn, params=query['params'])
                    
                    if not df.empty:
                        extraction_stats['categories_processed'] += 1
                        extraction_stats['variables_extracted'] += len(filtered_vars)
                        extraction_stats['data_points_extracted'] += len(df)
                        
                        # Add building_id column
                        df['building_id'] = self.building_id
                        
                        # Map to output category names
                        output_category = self._map_output_category(category)
                        
                        # Save data
                        year = df['DateTime'].dt.year.mode()[0] if 'DateTime' in df.columns else datetime.now().year
                        self.data_manager.save_timeseries_data(df, 'hourly', output_category, year)
                        
                        # Create aggregations if not disabled
                        if content_config.get('create_aggregations', True):
                            self._create_and_save_aggregations(df, output_category)
                
                except Exception as e:
                    print(f"  Error extracting {category}: {e}")
        
        # Extract schedules if requested
        if components.get('schedules', True):
            print("\nExtracting schedules...")
            schedules = self._extract_all_schedules()
            if not schedules.empty:
                schedules['building_id'] = self.building_id
                self.data_manager.save_schedules(schedules)
        
        # Create summary metrics if requested
        if components.get('summary_metrics', True):
            print("\nCreating summary metrics...")
            # Build minimal zone mapping for metrics
            zone_mapping = {}  # Would need to be passed or built
            self._create_and_save_summary_metrics(zone_mapping)
        
        # Report extraction summary
        print(f"\nSelective extraction summary:")
        print(f"  Categories processed: {extraction_stats['categories_processed']}")
        print(f"  Variables extracted: {extraction_stats['variables_extracted']}")
        print(f"  Data points: {extraction_stats['data_points_extracted']:,}")


    def _filter_variables(self, variables: List[str], content_config: Dict[str, Any]) -> List[str]:
        """Filter variables based on configuration"""
        variables_config = content_config.get('variables', {})
        
        # Apply include patterns
        include_patterns = variables_config.get('variable_patterns', [])
        if include_patterns:
            included = []
            for var in variables:
                if any(self._match_pattern(var, p) for p in include_patterns):
                    included.append(var)
            variables = included
        
        # Apply exclude patterns
        exclude_patterns = variables_config.get('exclude_patterns', [])
        if exclude_patterns:
            variables = [
                var for var in variables 
                if not any(self._match_pattern(var, p) for p in exclude_patterns)
            ]
        
        return variables


    def _build_filtered_query(self, variables: List[str], start_date: str, end_date: str,
                            month_filter: List[int] = None, hour_filter: List[int] = None,
                            frequency_filter: List[str] = None, zone_filter: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build SQL query with all filters applied"""
        
        # Base query parts
        select_parts = [
            "t.TimeIndex",
            "datetime(printf('%04d-%02d-%02d %02d:%02d:00', t.Year, t.Month, t.Day, t.Hour, t.Minute)) as DateTime",
            "rdd.Name as Variable",
            "rdd.KeyValue as Zone",
            "rd.Value",
            "rdd.Units",
            "rdd.ReportingFrequency"
        ]
        
        where_parts = [
            "rdd.Name IN ({})".format(','.join(['?'] * len(variables))),
            "t.EnvironmentPeriodIndex IN (SELECT EnvironmentPeriodIndex FROM EnvironmentPeriods WHERE EnvironmentType = 3)",
            "date(printf('%04d-%02d-%02d', t.Year, t.Month, t.Day)) BETWEEN ? AND ?"
        ]
        
        params = variables + [start_date, end_date]
        
        # Add month filter
        if month_filter:
            where_parts.append(f"t.Month IN ({','.join(['?'] * len(month_filter))})")
            params.extend(month_filter)
        
        # Add hour filter
        if hour_filter:
            where_parts.append(f"t.Hour IN ({','.join(['?'] * len(hour_filter))})")
            params.extend(hour_filter)
        
        # Add frequency filter
        if frequency_filter:
            where_parts.append(f"rdd.ReportingFrequency IN ({','.join(['?'] * len(frequency_filter))})")
            params.extend(frequency_filter)
        
        # Add zone filter
        if zone_filter and zone_filter.get('mode') != 'all':
            zone_mode = zone_filter.get('mode', 'all')
            
            if zone_mode == 'specific':
                zones = zone_filter.get('zones', [])
                if zones:
                    where_parts.append(f"rdd.KeyValue IN ({','.join(['?'] * len(zones))})")
                    params.extend(zones)
            
            elif zone_mode == 'pattern':
                patterns = zone_filter.get('zone_patterns', [])
                if patterns:
                    pattern_conditions = []
                    for pattern in patterns:
                        sql_pattern = pattern.replace('*', '%')
                        pattern_conditions.append("rdd.KeyValue LIKE ?")
                        params.append(sql_pattern)
                    where_parts.append(f"({' OR '.join(pattern_conditions)})")
            
            elif zone_mode == 'exclude':
                exclude_zones = zone_filter.get('exclude_zones', [])
                if exclude_zones:
                    where_parts.append(f"rdd.KeyValue NOT IN ({','.join(['?'] * len(exclude_zones))})")
                    params.extend(exclude_zones)
        
        # Build final query
        query = f"""
            SELECT {', '.join(select_parts)}
            FROM ReportData rd
            JOIN Time t ON rd.TimeIndex = t.TimeIndex
            JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
            WHERE {' AND '.join(where_parts)}
            ORDER BY t.TimeIndex, rdd.Name
        """
        
        return {'sql': query, 'params': params}



















    def _save_extraction_stats(self, stats: Dict[str, Any]):
        """Save extraction statistics"""
        if not self.data_manager:
            return
        
        stats_df = pd.DataFrame([{
            'building_id': self.building_id,
            'extraction_date': datetime.now().isoformat(),
            'categories_processed': stats['categories_processed'],
            'variables_extracted': stats['variables_extracted'],
            'data_points_extracted': stats['data_points_extracted'],
            'missing_variables_count': len(stats['missing_variables'])
        }])
        
        self.data_manager.save_analysis_ready_data(stats_df, 'extraction_statistics')
        
        # Save missing variables detail
        if stats['missing_variables']:
            missing_df = pd.DataFrame(stats['missing_variables'])
            missing_df['building_id'] = self.building_id
            self.data_manager.save_analysis_ready_data(missing_df, 'missing_variables_detail')
    
    def analyze_output_data_quality(self) -> Dict[str, Any]:
        """Analyze the quality of output data"""
        quality_report = {
            'building_id': self.building_id,
            'total_outputs': 0,
            'outputs_with_data': 0,
            'outputs_without_data': 0,
            'data_gaps': [],
            'frequency_analysis': {},
            'category_quality': {}
        }
        
        available = self.get_available_outputs()
        
        quality_report['total_outputs'] = len(available)
        quality_report['outputs_with_data'] = len(available[available['HasData']])
        quality_report['outputs_without_data'] = len(available[~available['HasData']])
        
        # Analyze by frequency
        for freq in available['ReportingFrequency'].unique():
            freq_data = available[available['ReportingFrequency'] == freq]
            quality_report['frequency_analysis'][freq] = {
                'total': len(freq_data),
                'with_data': len(freq_data[freq_data['HasData']]),
                'completeness': len(freq_data[freq_data['HasData']]) / len(freq_data) * 100
            }
        
        # Analyze by category
        for category in available['Category'].unique():
            cat_data = available[available['Category'] == category]
            quality_report['category_quality'][category] = {
                'total': len(cat_data),
                'with_data': len(cat_data[cat_data['HasData']]),
                'completeness': len(cat_data[cat_data['HasData']]) / len(cat_data) * 100,
                'avg_data_points': cat_data['DataPoints'].mean()
            }
        
        # Identify outputs with no data
        no_data = available[~available['HasData']]
        if not no_data.empty:
            quality_report['data_gaps'] = no_data[['VariableName', 'KeyValue', 'ReportingFrequency']].to_dict('records')
        
        return quality_report
    
    def _map_output_category(self, category: str) -> str:
        """Map category names to output file names"""
        category_map = {
            'geometry': 'zones',
            'hvac': 'hvac',
            'dhw': 'hvac',  # Group DHW with HVAC
            'equipment': 'equipment',
            'lighting': 'lighting',
            'ventilation': 'ventilation',
            'infiltration': 'ventilation',  # Group infiltration with ventilation
            'materials': 'zones',  # Surface temperatures go with zones
            'shading': 'zones'  # Solar radiation goes with zones
        }
        
        # For general energy variables
        if category not in category_map:
            return 'energy'
        
        return category_map.get(category, category)
    
    def _determine_variable_categories(self) -> Dict[str, str]:
        """Determine which variables belong to which output categories"""
        return {
            # Energy variables
            'Energy': 'energy',
            'Electricity': 'energy',
            'Gas': 'energy',
            'Water': 'energy',
            
            # HVAC variables
            'Cooling': 'hvac',
            'Heating': 'hvac',
            'Fan': 'hvac',
            'Pump': 'hvac',
            'Coil': 'hvac',
            'Air System': 'hvac',
            'Thermostat': 'hvac',
            
            # Zone variables
            'Zone Mean Air Temperature': 'zones',
            'Zone Air Temperature': 'zones',
            'Zone Thermal Comfort': 'zones',
            'Surface': 'zones',
            'Solar': 'zones',
            
            # Equipment
            'Electric Equipment': 'equipment',
            'Gas Equipment': 'equipment',
            
            # Lighting
            'Lights': 'lighting',
            'Daylighting': 'lighting',
            
            # Ventilation
            'Ventilation': 'ventilation',
            'Infiltration': 'ventilation',
            'Outdoor Air': 'ventilation'
        }
    
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
            
            # Check if we got valid dates
            if pd.isna(dates['min_date']) or pd.isna(dates['max_date']):
                raise ValueError("Invalid dates returned")
                
            return str(dates['min_date']), str(dates['max_date'])
            
        except Exception as e:
            print(f"Error getting date range with formatted query: {e}")
            
            # Try alternative approach
            try:
                alt_query = """
                    SELECT 
                        MIN(Year) as min_year,
                        MAX(Year) as max_year,
                        MIN(Month) as min_month,
                        MAX(Month) as max_month
                    FROM Time
                    WHERE EnvironmentPeriodIndex IN (
                        SELECT EnvironmentPeriodIndex 
                        FROM EnvironmentPeriods 
                        WHERE EnvironmentType = 3
                    )
                """
                dates = pd.read_sql_query(alt_query, self.sql_conn).iloc[0]
                
                # Construct approximate date range
                min_date = f"{dates['min_year']}-01-01"
                max_date = f"{dates['max_year']}-12-31"
                
                print(f"Using approximate date range: {min_date} to {max_date}")
                return min_date, max_date
                
            except Exception as e2:
                print(f"Error getting date range with alternative query: {e2}")
                # Default to a typical year
                return '2020-01-01', '2020-12-31'
    
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
        
        print(f"\n  Available SQL variables:")
        for _, var in available_vars.iterrows():
            print(f"    - {var['Name']} → {var['KeyValue']} ({var['ReportingFrequency']})")
        
        # Get date range if not specified
        if not start_date or not end_date:
            start_date, end_date = self._get_date_range()
            print(f"  Date range: {start_date} to {end_date}")
        
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
            print(f"  Error with datetime query, trying alternative: {e}")
            # Try alternative query that might work better with some SQL databases
            query_alt = """
                SELECT 
                    t.TimeIndex,
                    t.Year,
                    t.Month,
                    t.Day,
                    t.Hour,
                    t.Minute,
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
                ORDER BY t.TimeIndex, rdd.Name
            """.format(','.join(['?'] * len(variables)))
            
            try:
                df = pd.read_sql_query(query_alt, self.sql_conn, params=variables)
                # Construct DateTime from components
                if not df.empty:
                    # Handle Hour 24 (midnight of next day)
                    df['Hour_adj'] = df['Hour'].apply(lambda x: 0 if x == 24 else x)
                    df['Day_adj'] = df.apply(lambda row: row['Day'] + 1 if row['Hour'] == 24 else row['Day'], axis=1)
                    
                    # Create DateTime
                    df['DateTime'] = pd.to_datetime(
                        df[['Year', 'Month', 'Day_adj', 'Hour_adj', 'Minute']].rename(
                            columns={'Day_adj': 'day', 'Hour_adj': 'hour', 'Minute': 'minute',
                                    'Year': 'year', 'Month': 'month'}
                        )
                    )
                    
                    # Filter by date range
                    df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]
                    
                    # Drop temporary columns
                    df = df.drop(['Year', 'Month', 'Day', 'Hour', 'Minute', 'Hour_adj', 'Day_adj'], axis=1)
            except Exception as e2:
                print(f"  Error with alternative query: {e2}")
                return pd.DataFrame()
        
        if not df.empty:
            # Convert datetime - handle both string and numeric timestamps
            if pd.api.types.is_numeric_dtype(df['DateTime']):
                # It's a Unix timestamp
                sample_value = df['DateTime'].iloc[0] if len(df) > 0 else 0
                if sample_value > 1e12:  # Milliseconds
                    df['DateTime'] = pd.to_datetime(df['DateTime'], unit='ms')
                elif sample_value > 1e9:  # Seconds
                    df['DateTime'] = pd.to_datetime(df['DateTime'], unit='s')
            else:
                # String datetime
                df['DateTime'] = pd.to_datetime(df['DateTime'])
            
            # Add IDF zone names
            reverse_mapping = {v: k for k, v in zone_mapping.items()}
            df['IDF_Zone'] = df['Zone'].map(reverse_mapping).fillna(df['Zone'])
            
            # Summary statistics
            print(f"\n  Time series data summary:")
            print(f"    Total records: {len(df):,}")
            print(f"    Date range: {df['DateTime'].min()} to {df['DateTime'].max()}")
            print(f"    Unique zones: {df['Zone'].nunique()}")
            print(f"    Unique variables: {df['Variable'].nunique()}")
            print(f"    Non-zero values: {(df['Value'] != 0).sum():,} ({(df['Value'] != 0).sum() / len(df) * 100:.1f}%)")
            
            # Check for specific issues
            if (df['Value'] == 0).all():
                print("    WARNING: All values are zero!")
                
                # Debug: Check if there's data for Environment level
                env_data = df[df['Zone'] == 'Environment']
                if not env_data.empty:
                    print(f"    Environment data points: {len(env_data)}")
                    print(f"    Environment non-zero: {(env_data['Value'] != 0).sum()}")
        else:
            print("  No time series data found")
        
        return df
    
    def _create_daily_aggregations(self, hourly_data: pd.DataFrame) -> pd.DataFrame:
        """Create daily aggregations from hourly data"""
        if hourly_data.empty:
            return pd.DataFrame()
        
        # Make a copy to avoid modifying the original
        data_copy = hourly_data.copy()
        
        # Define aggregation rules by variable type
        # Energy variables should be summed
        energy_mask = data_copy['Variable'].str.contains('Energy|Consumption', na=False)
        
        # Rate/Power variables should be averaged
        rate_mask = data_copy['Variable'].str.contains('Rate|Power|Temperature', na=False)
        
        daily_groups = []
        
        # Process energy variables (sum)
        if energy_mask.any():
            energy_data = data_copy[energy_mask].copy()
            agg_data = aggregate_timeseries(energy_data, 'D', 'sum')
            daily_groups.append(agg_data)
        
        # Process rate/power/temperature variables (mean)
        if (~energy_mask).any():
            other_data = data_copy[~energy_mask].copy()
            agg_data = aggregate_timeseries(other_data, 'D', 'mean')
            daily_groups.append(agg_data)
        
        if daily_groups:
            return pd.concat(daily_groups, ignore_index=True)
        
        return pd.DataFrame()
    
    def _create_monthly_aggregations(self, hourly_data: pd.DataFrame) -> pd.DataFrame:
        """Create monthly aggregations from hourly data"""
        if hourly_data.empty:
            return pd.DataFrame()
        
        # Make a copy to avoid modifying the original
        data_copy = hourly_data.copy()
        
        # Similar to daily but with monthly frequency
        energy_mask = data_copy['Variable'].str.contains('Energy|Consumption', na=False)
        
        monthly_groups = []
        
        # Process energy variables (sum)
        if energy_mask.any():
            energy_data = data_copy[energy_mask].copy()
            agg_data = aggregate_timeseries(energy_data, 'M', 'sum')
            monthly_groups.append(agg_data)
        
        # Process other variables (mean)
        if (~energy_mask).any():
            other_data = data_copy[~energy_mask].copy()
            agg_data = aggregate_timeseries(other_data, 'M', 'mean')
            monthly_groups.append(agg_data)
        
        if monthly_groups:
            return pd.concat(monthly_groups, ignore_index=True)
        
        return pd.DataFrame()
    
    def _extract_all_schedules(self) -> pd.DataFrame:
        """Extract all schedule data from SQL"""
        try:
            # Get schedule metadata
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
            
            # For now, return basic schedule info
            # Could be enhanced to extract detailed schedule values
            return schedules
            
        except Exception as e:
            print(f"Error extracting schedules: {e}")
            return pd.DataFrame()
    
    def _create_and_save_summary_metrics(self, zone_mapping: Dict[str, str]):
        """Create and save enhanced summary metrics"""
        if not self.data_manager:
            return
        
        # Building-level metrics
        building_metrics = {
            'building_id': self.building_id,
            'sql_file': str(self.sql_path),
            'extraction_date': datetime.now().isoformat()
        }
        
        # Zone-level metrics list
        zone_metrics_list = []
        
        # Get simulation metadata
        try:
            sim_query = """
                SELECT 
                    EnergyPlusVersion,
                    TimeStamp,
                    NumTimestepsPerHour
                FROM Simulations
                LIMIT 1
            """
            sim_data = pd.read_sql_query(sim_query, self.sql_conn)
            if not sim_data.empty:
                building_metrics['energyplus_version'] = sim_data.iloc[0]['EnergyPlusVersion']
                building_metrics['simulation_timestamp'] = sim_data.iloc[0]['TimeStamp']
                building_metrics['timesteps_per_hour'] = sim_data.iloc[0]['NumTimestepsPerHour']
        except:
            pass
        
        # Get zone information and metrics
        try:
            zones_query = """
                SELECT 
                    ZoneName,
                    FloorArea,
                    Volume
                FROM Zones
            """
            zone_data = pd.read_sql_query(zones_query, self.sql_conn)
            
            if not zone_data.empty:
                # Building totals
                building_metrics['zone_count'] = len(zone_data)
                building_metrics['total_floor_area'] = zone_data['FloorArea'].sum()
                building_metrics['total_volume'] = zone_data['Volume'].sum()
                
                # Per-zone metrics
                for _, zone in zone_data.iterrows():
                    zone_metric = {
                        'building_id': self.building_id,
                        'zone_name': zone['ZoneName'],
                        'floor_area': zone['FloorArea'],
                        'volume': zone['Volume']
                    }
                    zone_metrics_list.append(zone_metric)
        except:
            pass
        
        # Get energy totals by category
        try:
            energy_categories = [
                ('heating', 'Heating'),
                ('cooling', 'Cooling'),
                ('lighting', 'Lights'),
                ('equipment', 'Electric Equipment'),
                ('fans', 'Fan'),
                ('pumps', 'Pump'),
                ('water_heating', 'Water Heater')
            ]
            
            for metric_name, search_term in energy_categories:
                energy_query = f"""
                    SELECT 
                        SUM(rd.Value) as TotalValue,
                        AVG(rd.Value) as AvgValue,
                        MAX(rd.Value) as MaxValue
                    FROM ReportData rd
                    JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                    WHERE rdd.Name LIKE '%{search_term}%Energy%'
                """
                
                try:
                    energy_data = pd.read_sql_query(energy_query, self.sql_conn)
                    if not energy_data.empty and energy_data.iloc[0]['TotalValue'] is not None:
                        building_metrics[f'total_{metric_name}_energy'] = energy_data.iloc[0]['TotalValue']
                        building_metrics[f'avg_{metric_name}_power'] = energy_data.iloc[0]['AvgValue']
                        building_metrics[f'peak_{metric_name}_power'] = energy_data.iloc[0]['MaxValue']
                except:
                    pass
        except:
            pass
        
        # Get zone-level energy metrics
        try:
            zone_energy_query = """
                SELECT 
                    rdd.KeyValue as Zone,
                    rdd.Name as Variable,
                    SUM(rd.Value) as TotalEnergy,
                    AVG(rd.Value) as AvgPower,
                    MAX(rd.Value) as PeakPower
                FROM ReportData rd
                JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                WHERE rdd.Name LIKE '%Zone%Energy%'
                AND rdd.KeyValue != 'Environment'
                GROUP BY rdd.KeyValue, rdd.Name
            """
            
            zone_energy = pd.read_sql_query(zone_energy_query, self.sql_conn)
            
            if not zone_energy.empty:
                # Merge with existing zone metrics
                for zone_metric in zone_metrics_list:
                    zone_name = zone_metric['zone_name']
                    zone_data = zone_energy[zone_energy['Zone'] == zone_name]
                    
                    if not zone_data.empty:
                        # Add energy metrics to zone
                        for var_type in ['Heating', 'Cooling', 'Lights', 'Equipment']:
                            var_data = zone_data[zone_data['Variable'].str.contains(var_type, na=False)]
                            if not var_data.empty:
                                zone_metric[f'{var_type.lower()}_energy'] = var_data['TotalEnergy'].sum()
                                zone_metric[f'{var_type.lower()}_peak_power'] = var_data['PeakPower'].max()
        except:
            pass
        
        # Get comfort metrics
        try:
            comfort_query = """
                SELECT 
                    rdd.KeyValue as Zone,
                    AVG(rd.Value) as AvgTemperature,
                    MIN(rd.Value) as MinTemperature,
                    MAX(rd.Value) as MaxTemperature
                FROM ReportData rd
                JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                WHERE rdd.Name = 'Zone Mean Air Temperature'
                AND rdd.KeyValue != 'Environment'
                GROUP BY rdd.KeyValue
            """
            
            comfort_data = pd.read_sql_query(comfort_query, self.sql_conn)
            
            if not comfort_data.empty:
                # Add to zone metrics
                for zone_metric in zone_metrics_list:
                    zone_name = zone_metric['zone_name']
                    zone_comfort = comfort_data[comfort_data['Zone'] == zone_name]
                    
                    if not zone_comfort.empty:
                        zone_metric['avg_temperature'] = zone_comfort.iloc[0]['AvgTemperature']
                        zone_metric['min_temperature'] = zone_comfort.iloc[0]['MinTemperature']
                        zone_metric['max_temperature'] = zone_comfort.iloc[0]['MaxTemperature']
        except:
            pass
        
        # Add output coverage metrics
        available_outputs = self.get_available_outputs()
        building_metrics['total_outputs_available'] = len(available_outputs)
        building_metrics['outputs_with_data'] = len(available_outputs[available_outputs['HasData']])
        building_metrics['output_coverage'] = (
            building_metrics['outputs_with_data'] / building_metrics['total_outputs_available'] * 100
            if building_metrics['total_outputs_available'] > 0 else 0
        )
        
        # Save building metrics
        building_metrics_df = pd.DataFrame([building_metrics])
        self.data_manager.save_summary_metrics('building_metrics', building_metrics_df)
        
        # Save zone metrics
        if zone_metrics_list:
            zone_metrics_df = pd.DataFrame(zone_metrics_list)
            self.data_manager.save_summary_metrics('zone_metrics', zone_metrics_df)
    
    def get_available_variables(self, category_variables: List[str]) -> pd.DataFrame:
        """Get info about available variables for a category"""
        if not category_variables:
            return pd.DataFrame()
        
        available_vars_query = """
            SELECT DISTINCT 
                Name, 
                Units, 
                COUNT(*) as DataPoints
            FROM ReportDataDictionary rdd
            JOIN ReportData rd ON rdd.ReportDataDictionaryIndex = rd.ReportDataDictionaryIndex
            WHERE Name IN ({})
            GROUP BY Name, Units
        """.format(','.join(['?'] * len(category_variables)))
        
        try:
            available_vars = pd.read_sql_query(
                available_vars_query, 
                self.sql_conn, 
                params=category_variables
            )
        except:
            available_vars = pd.DataFrame()
        
        return available_vars
    
    def close(self):
        """Close database connection"""
        self.sql_conn.close()