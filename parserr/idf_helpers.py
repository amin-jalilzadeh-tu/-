"""
IDF Helper Functions
Helper functions specific to IDF file handling
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional

def prepare_idf_files(job_output_dir: str) -> Tuple[List[str], Dict[str, str]]:
    """Prepare IDF files with building ID mapping"""
    idf_files = []
    building_id_map = {}
    
    # Read the building registry
    idf_map_csv = os.path.join(job_output_dir, "extracted_idf_buildings.csv")
    if not os.path.isfile(idf_map_csv):
        return [], {}
    
    df_map = pd.read_csv(idf_map_csv)
    
    # Process each building
    for idx, row in df_map.iterrows():
        if row.get('idf_name') and row['idf_name'] != 'ERROR_CREATING_IDF':
            # IDF path
            idf_path = os.path.join(job_output_dir, "output_IDFs", row['idf_name'])
            
            if os.path.isfile(idf_path):
                # Get the building ID
                building_id = str(row['ogc_fid'])
                
                idf_files.append(idf_path)
                building_id_map[idf_path] = building_id
    
    return idf_files, building_id_map

def get_idf_data_info(parser_output_dir: str) -> Dict[str, any]:
    """Get information about parsed IDF data"""
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

def extract_building_id_from_path(file_path: str) -> str:
    """Extract building ID from file path"""
    filename = os.path.basename(file_path)
    
    # Try different patterns
    patterns = [
        r'building_(\d+)_variant_\d+',
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

def find_idf_files_directly(job_output_dir: str) -> List[str]:
    """Find IDF files directly when no registry available"""
    idf_files = []
    
    idf_dir = os.path.join(job_output_dir, "output_IDFs")
    if os.path.isdir(idf_dir):
        for file in os.listdir(idf_dir):
            if file.endswith('.idf'):
                idf_files.append(os.path.join(idf_dir, file))
    
    return idf_files