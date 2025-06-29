"""
SQL Helper Functions
Helper functions specific to SQL file handling
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any  # Add 'Any' here

def find_sql_files(job_output_dir: str, year_folders: List[str] = None) -> List[str]:
    """Find all SQL files in simulation results"""
    sql_files = []
    sim_results_dir = os.path.join(job_output_dir, "Sim_Results")
    
    if not os.path.isdir(sim_results_dir):
        return sql_files
    
    # Find year folders if not provided
    if year_folders is None:
        year_folders = []
        for item in os.listdir(sim_results_dir):
            item_path = os.path.join(sim_results_dir, item)
            if os.path.isdir(item_path) and item.isdigit():
                year_folders.append(item)
        
        if not year_folders:
            year_folders = ['']
    
    # Search for SQL files
    for year in year_folders:
        if year:
            search_dir = os.path.join(sim_results_dir, year)
        else:
            search_dir = sim_results_dir
        
        if os.path.isdir(search_dir):
            for file in os.listdir(search_dir):
                if file.endswith('.sql'):
                    sql_files.append(os.path.join(search_dir, file))
    
    return sql_files

def find_sql_for_building(job_output_dir: str, building_id: str, idx: int = None) -> Optional[str]:
    """Find SQL file for a specific building"""
    sim_results_dir = os.path.join(job_output_dir, "Sim_Results")
    
    # Find year folders
    year_folders = []
    if os.path.isdir(sim_results_dir):
        for item in os.listdir(sim_results_dir):
            item_path = os.path.join(sim_results_dir, item)
            if os.path.isdir(item_path) and item.isdigit():
                year_folders.append(item)
    
    if not year_folders:
        year_folders = ['']
    
    # Try different SQL naming patterns
    for year in year_folders:
        sql_patterns = [
            f"simulation_bldg{idx}_{building_id}.sql" if idx is not None else None,
            f"simulation_bldg{idx}_{building_id}_out.sql" if idx is not None else None,
            f"simulation_bldg{idx}.sql" if idx is not None else None,
            f"simulation_bldg{idx}_out.sql" if idx is not None else None,
            f"building_{building_id}.sql",
            f"building_{building_id}_out.sql",
            f"*{building_id}*.sql"
        ]
        
        for sql_pattern in sql_patterns:
            if sql_pattern is None:
                continue
                
            if year:
                search_dir = os.path.join(sim_results_dir, year)
            else:
                search_dir = sim_results_dir
            
            if '*' in sql_pattern:
                # Use glob pattern
                from pathlib import Path
                matching_files = list(Path(search_dir).glob(sql_pattern))
                if matching_files:
                    return str(matching_files[0])
            else:
                sql_path = os.path.join(search_dir, sql_pattern)
                if os.path.isfile(sql_path):
                    return sql_path
    
    return None

def find_sql_for_modified_idf(idf_path: str, sim_output_dir: str, 
                              variant_num: str = None) -> Optional[str]:
    """Find the SQL file corresponding to a modified IDF file"""
    from pathlib import Path
    
    sim_path = Path(sim_output_dir)
    idf_name = Path(idf_path).stem
    
    # Extract info from IDF name
    parts = idf_name.split('_')
    building_id = None
    
    if len(parts) >= 2 and parts[0] == 'building':
        building_id = parts[1]
    
    # Try different SQL naming patterns
    patterns = []
    
    if variant_num:
        patterns.extend([
            f"*variant_{variant_num}*.sql",
            f"*_{variant_num}.sql",
            f"simulation_{variant_num}.sql"
        ])
    
    if building_id:
        patterns.extend([
            f"*{building_id}*.sql",
            f"simulation_*{building_id}.sql"
        ])
    
    # Search for SQL files
    for pattern in patterns:
        sql_files = list(sim_path.glob(f"**/{pattern}"))
        if sql_files:
            return str(sql_files[0])
    
    return None

def prepare_sql_file_pairs(job_output_dir: str, idf_building_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """Prepare SQL file pairs with building IDs"""
    sql_building_pairs = []
    
    # Find all SQL files
    sql_files = find_sql_files(job_output_dir)
    
    # Try to match SQL files to buildings
    for sql_file in sql_files:
        # Extract building ID from SQL filename
        sql_name = os.path.basename(sql_file)
        
        # Try different patterns
        patterns = [
            r'simulation_bldg\d+_(\d+)\.sql',
            r'building_(\d+)\.sql',
            r'building_(\d+)_.*\.sql',
            r'(\d{6,})\.sql'
        ]
        
        building_id = None
        for pattern in patterns:
            match = re.search(pattern, sql_name)
            if match:
                building_id = match.group(1)
                break
        
        if building_id:
            sql_building_pairs.append((sql_file, building_id))
        else:
            # Use filename as building ID
            sql_building_pairs.append((sql_file, Path(sql_file).stem))
    
    return sql_building_pairs

def get_sql_data_info(parser_output_dir: str) -> Dict[str, any]:
    """Get information about parsed SQL data"""
    info = {
        'sql_data_dir': os.path.join(parser_output_dir, 'sql_results'),
        'timeseries': {},
        'metrics': {},
        'validation': {}
    }
    
    # Check timeseries data
    timeseries_dir = os.path.join(parser_output_dir, 'sql_results', 'timeseries')
    if os.path.isdir(timeseries_dir):
        # Check hourly data
        hourly_dir = os.path.join(timeseries_dir, 'hourly')
        if os.path.isdir(hourly_dir):
            hourly_files = [f for f in os.listdir(hourly_dir) if f.endswith('.parquet')]
            info['timeseries']['hourly'] = {
                'files': len(hourly_files),
                'categories': list(set(f.split('_')[0] for f in hourly_files))
            }
        
        # Check aggregated data
        for freq in ['daily', 'monthly']:
            freq_dir = os.path.join(timeseries_dir, 'aggregated', freq)
            if os.path.isdir(freq_dir):
                freq_files = [f for f in os.listdir(freq_dir) if f.endswith('.parquet')]
                info['timeseries'][freq] = {
                    'files': len(freq_files),
                    'categories': list(set(f.split('_')[0] for f in freq_files))
                }
    
    # Check metrics
    metrics_dir = os.path.join(parser_output_dir, 'sql_results', 'summary_metrics')
    if os.path.isdir(metrics_dir):
        for file in os.listdir(metrics_dir):
            if file.endswith('.parquet'):
                file_path = os.path.join(metrics_dir, file)
                try:
                    df = pd.read_parquet(file_path)
                    metric_name = file.replace('.parquet', '')
                    info['metrics'][metric_name] = {
                        'rows': len(df),
                        'buildings': df['building_id'].nunique() if 'building_id' in df.columns else 0
                    }
                except:
                    pass
    
    # Check validation results
    validation_dir = os.path.join(parser_output_dir, 'sql_results', 'output_validation')
    if os.path.isdir(validation_dir):
        for file in os.listdir(validation_dir):
            if file.endswith('.parquet'):
                validation_name = file.replace('.parquet', '')
                info['validation'][validation_name] = True
    
    return info

def validate_sql_outputs(sql_file: str, expected_outputs: List[Dict[str, str]]) -> Dict[str, Any]:
    """Validate that SQL file contains expected outputs"""
    import sqlite3
    
    validation_result = {
        'sql_file': sql_file,
        'total_expected': len(expected_outputs),
        'found': 0,
        'missing': [],
        'has_data': []
    }
    
    try:
        conn = sqlite3.connect(sql_file)
        
        # Get available outputs
        query = """
            SELECT DISTINCT Name, KeyValue, ReportingFrequency
            FROM ReportDataDictionary
        """
        available = pd.read_sql_query(query, conn)
        
        # Check each expected output
        for expected in expected_outputs:
            var_name = expected.get('variable_name', '')
            key_value = expected.get('key_value', '*')
            frequency = expected.get('reporting_frequency', 'Hourly')
            
            # Check if exists
            if key_value == '*':
                matches = available[
                    (available['Name'] == var_name) & 
                    (available['ReportingFrequency'] == frequency)
                ]
            else:
                matches = available[
                    (available['Name'] == var_name) & 
                    (available['KeyValue'] == key_value) &
                    (available['ReportingFrequency'] == frequency)
                ]
            
            if not matches.empty:
                validation_result['found'] += 1
                
                # Check if has data
                data_query = """
                    SELECT COUNT(*) as count
                    FROM ReportData rd
                    JOIN ReportDataDictionary rdd ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                    WHERE rdd.Name = ? AND rdd.ReportingFrequency = ?
                """
                
                params = [var_name, frequency]
                if key_value != '*':
                    data_query += " AND rdd.KeyValue = ?"
                    params.append(key_value)
                
                data_count = pd.read_sql_query(data_query, conn, params=params)
                
                if data_count.iloc[0]['count'] > 0:
                    validation_result['has_data'].append({
                        'variable': var_name,
                        'key': key_value,
                        'frequency': frequency,
                        'data_points': data_count.iloc[0]['count']
                    })
            else:
                validation_result['missing'].append({
                    'variable': var_name,
                    'key': key_value,
                    'frequency': frequency
                })
        
        conn.close()
        
    except Exception as e:
        validation_result['error'] = str(e)
    
    return validation_result