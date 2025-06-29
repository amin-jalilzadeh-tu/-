"""
Helper functions for parser integration with orchestrator
"""
import pandas as pd
import os
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import re




# In helpers.py, update prepare_idf_sql_pairs_with_mapping:

def prepare_idf_sql_pairs_with_mapping(job_output_dir: str) -> Tuple[List[Tuple[str, str]], Dict[str, str]]:
    """
    Prepare IDF/SQL pairs with proper building ID mapping
    
    Returns:
        Tuple of (idf_sql_pairs, building_id_map)
    """
    idf_sql_pairs = []
    building_id_map = {}
    
    # Read the building registry
    idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
    if not os.path.isfile(idf_map_csv):
        return [], {}
    
    df_map = pd.read_csv(idf_map_csv)
    
    # Look for simulation results based on year folders
    sim_results_dir = os.path.join(job_output_dir, "Sim_Results")
    
    # Find year folders (e.g., 2020, 2050)
    year_folders = []
    if os.path.isdir(sim_results_dir):
        for item in os.listdir(sim_results_dir):
            item_path = os.path.join(sim_results_dir, item)
            if os.path.isdir(item_path) and item.isdigit():
                year_folders.append(item)
    
    if not year_folders:
        # Try direct SQL files in Sim_Results
        year_folders = ['']
    
    # Process each building
    for idx, row in df_map.iterrows():
        if row.get('idf_name') and row['idf_name'] != 'ERROR_CREATING_IDF':
            # IDF path
            idf_path = os.path.join(job_output_dir, "output_IDFs", row['idf_name'])
            
            # Get the building ID
            building_id = str(row['ogc_fid'])
            
            # Try to find SQL file
            sql_found = False
            for year in year_folders:
                # Try different SQL naming patterns
                sql_patterns = [
                    # New pattern with ID
                    f"simulation_bldg{idx}_{building_id}.sql",
                    f"simulation_bldg{idx}_{building_id}_out.sql",
                    # Legacy patterns
                    f"simulation_bldg{idx}.sql",
                    f"simulation_bldg{idx}_out.sql",
                    # IDF-based patterns
                    f"{row['idf_name'].replace('.idf', '.sql')}",
                    f"{row['idf_name'].replace('.idf', '_out.sql')}"
                ]
                
                for sql_name in sql_patterns:
                    if year:
                        sql_path = os.path.join(sim_results_dir, year, sql_name)
                    else:
                        sql_path = os.path.join(sim_results_dir, sql_name)
                    
                    if os.path.isfile(sql_path):
                        idf_sql_pairs.append((idf_path, sql_path))
                        building_id_map[idf_path] = building_id
                        sql_found = True
                        break
                
                if sql_found:
                    break
            
            if not sql_found:
                print(f"Warning: No SQL file found for building {building_id} (idx={idx})")
    
    return idf_sql_pairs, building_id_map


def get_parsed_data_info(parser_output_dir: str) -> Dict[str, any]:
    """
    Get information about parsed data
    """
    info = {
        'parsed_data_dir': parser_output_dir,
        'categories': {},
        'total_buildings': 0,
        'total_files': 0
    }
    
    # Check category files
    category_dir = os.path.join(parser_output_dir, 'idf_data', 'by_category')
    if os.path.isdir(category_dir):
        for file in os.listdir(category_dir):
            if file.endswith('.parquet'):
                file_path = os.path.join(category_dir, file)
                try:
                    df = pd.read_parquet(file_path)
                    category_name = file.replace('.parquet', '')
                    info['categories'][category_name] = {
                        'rows': len(df),
                        'buildings': df['building_id'].nunique() if 'building_id' in df.columns else 0
                    }
                    info['total_files'] += 1
                except:
                    pass
    
    # Count unique buildings
    building_dir = os.path.join(parser_output_dir, 'idf_data', 'by_building')
    if os.path.isdir(building_dir):
        building_files = [f for f in os.listdir(building_dir) if f.endswith('_snapshot.parquet')]
        info['total_buildings'] = len(building_files)
    
    return info



def prepare_selective_file_pairs(job_output_dir: str, parse_mode: str, parse_types: Dict[str, bool],
                                building_selection: Dict[str, any], idf_map_csv: str = None) -> List[Tuple[Optional[str], Optional[str], str]]:
    """
    Prepare file pairs based on parsing configuration
    
    Returns:
        List of tuples (idf_path, sql_path, building_id) where either path can be None
    """
    file_pairs = []
    
    # Handle specific files mode
    if parse_mode == "specific_files":
        specific_files = building_selection.get("specific_files", {})
        idf_files = specific_files.get("idf", [])
        sql_files = specific_files.get("sql", [])
        
        # Create pairs from specific files
        for idf_path in idf_files:
            if os.path.isfile(idf_path):
                building_id = extract_building_id_from_path(idf_path)
                file_pairs.append((idf_path, None, building_id))
        
        for sql_path in sql_files:
            if os.path.isfile(sql_path):
                building_id = extract_building_id_from_path(sql_path)
                file_pairs.append((None, sql_path, building_id))
        
        return file_pairs
    
    # For other modes, we need the building registry
    if not idf_map_csv or not os.path.isfile(idf_map_csv):
        # Try to find IDF and SQL files directly
        return find_files_directly(job_output_dir, parse_types, building_selection)
    
    # Read building registry
    df_map = pd.read_csv(idf_map_csv)
    
    # Filter buildings based on selection
    df_filtered = filter_buildings(df_map, building_selection)
    
    # Create file pairs based on parse_types
    for idx, row in df_filtered.iterrows():
        building_id = str(row['ogc_fid'])
        idf_path = None
        sql_path = None
        
        # Get IDF path if requested
        if parse_types.get('idf', True) and row.get('idf_name') and row['idf_name'] != 'ERROR_CREATING_IDF':
            idf_path = os.path.join(job_output_dir, "output_IDFs", row['idf_name'])
            if not os.path.isfile(idf_path):
                idf_path = None
        
        # Get SQL path if requested
        if parse_types.get('sql', True):
            sql_path = find_sql_file(job_output_dir, idx, building_id)
        
        # Add pair if at least one file exists
        if idf_path or sql_path:
            file_pairs.append((idf_path, sql_path, building_id))
    
    return file_pairs


def filter_buildings(df_map: pd.DataFrame, building_selection: Dict[str, any]) -> pd.DataFrame:
    """Filter buildings based on selection criteria"""
    mode = building_selection.get("mode", "all")
    
    if mode == "all":
        return df_map
    
    elif mode == "specific":
        building_ids = building_selection.get("building_ids", [])
        return df_map[df_map['ogc_fid'].isin(building_ids)]
    
    elif mode == "range":
        range_config = building_selection.get("building_range", {})
        start = range_config.get("start", 0)
        end = range_config.get("end", len(df_map))
        return df_map.iloc[start:end]
    
    elif mode == "pattern":
        patterns = building_selection.get("building_patterns", [])
        mask = pd.Series([False] * len(df_map))
        for pattern in patterns:
            # Convert pattern to regex
            regex_pattern = pattern.replace('*', '.*')
            mask |= df_map['ogc_fid'].astype(str).str.match(regex_pattern)
        return df_map[mask]
    
    return df_map


def find_sql_file(job_output_dir: str, idx: int, building_id: str) -> Optional[str]:
    """Find SQL file for a building"""
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
            f"simulation_bldg{idx}_{building_id}.sql",
            f"simulation_bldg{idx}_{building_id}_out.sql",
            f"simulation_bldg{idx}.sql",
            f"simulation_bldg{idx}_out.sql",
        ]
        
        for sql_name in sql_patterns:
            if year:
                sql_path = os.path.join(sim_results_dir, year, sql_name)
            else:
                sql_path = os.path.join(sim_results_dir, sql_name)
            
            if os.path.isfile(sql_path):
                return sql_path
    
    return None


def find_files_directly(job_output_dir: str, parse_types: Dict[str, bool], 
                       building_selection: Dict[str, any]) -> List[Tuple[Optional[str], Optional[str], str]]:
    """Find IDF/SQL files directly when no registry available"""
    file_pairs = []
    
    # Find IDF files
    idf_files = []
    if parse_types.get('idf', True):
        idf_dir = os.path.join(job_output_dir, "output_IDFs")
        if os.path.isdir(idf_dir):
            idf_files = [f for f in os.listdir(idf_dir) if f.endswith('.idf')]
    
    # Find SQL files
    sql_files = []
    if parse_types.get('sql', True):
        sim_results_dir = os.path.join(job_output_dir, "Sim_Results")
        if os.path.isdir(sim_results_dir):
            for root, dirs, files in os.walk(sim_results_dir):
                sql_files.extend([os.path.join(root, f) for f in files if f.endswith('.sql')])
    
    # Create pairs
    for idf_file in idf_files:
        building_id = extract_building_id_from_path(idf_file)
        idf_path = os.path.join(job_output_dir, "output_IDFs", idf_file)
        file_pairs.append((idf_path, None, building_id))
    
    for sql_path in sql_files:
        building_id = extract_building_id_from_path(sql_path)
        file_pairs.append((None, sql_path, building_id))
    
    return file_pairs


def extract_building_id_from_path(file_path: str) -> str:
    """Extract building ID from file path"""
    filename = os.path.basename(file_path)
    
    # Try different patterns
    patterns = [
        r'building_(\d+)_variant_\d+',  # NEW: Handle variant pattern
        r'building_(\d+)',
        r'simulation_bldg\d+_(\d+)',
        r'(\d{6,})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
    
    # Fallback to filename without extension
    return os.path.splitext(filename)[0]


def find_sql_for_modified_idf(idf_path: str, sim_output_dir: str, 
                              variant_num: str = None) -> Optional[str]:
    """
    Find the SQL file corresponding to a modified IDF file.
    
    Args:
        idf_path: Path to the IDF file
        sim_output_dir: Directory containing simulation results
        variant_num: Variant number if known
        
    Returns:
        Path to SQL file if found, None otherwise
    """
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